"""All state and desktop calls are isolated from the developer's session."""

import concurrent.futures
import errno
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "counter.py"
spec = importlib.util.spec_from_file_location("counter", SCRIPT)
counter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(counter)


class CounterTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix="counter test ü ")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.state = self.root / "counter"
        self.state.mkdir()
        for name, value in (
            ("STATE", self.state),
            ("SETTINGS", self.state / "settings.json"),
            ("SESSION", self.root / "session"),
        ):
            mock = patch.object(counter, name, value)
            mock.start()
            self.addCleanup(mock.stop)

    def own(self, key="F1", **changes):
        return {
            "key": key,
            "description": counter.DESCRIPTION,
            "non_consuming": False,
            "repeat": False,
            "modmask": 0,
        } | changes

    def test_goal_notifies_only_on_upward_crossing(self):
        counter.set_goal(3)
        with patch.object(counter, "notify_goal") as notify:
            counter.change_count("add", 2)
            notify.assert_not_called()
            counter.change_count("add", 5)
            notify.assert_called_once_with(3)
            counter.change_count("increment")
            self.assertEqual(notify.call_count, 1)
            counter.change_count("reset")
            counter.change_count("add", 3)
            self.assertEqual(notify.call_count, 2)
            counter.set_goal(0)
            counter.change_count("add", 10)
            self.assertEqual(notify.call_count, 2)

    def test_goal_notification_closes_only_its_own_id_after_1500ms(self):
        with (
            patch.object(
                counter.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "42\n")
            ) as run,
            patch.object(counter.time, "sleep") as sleep,
        ):
            counter.notify_goal(33)
        self.assertIn("--expire-time=1500", run.call_args_list[0].args[0])
        sleep.assert_called_once_with(1.5)
        self.assertEqual(
            run.call_args.args[0][-2:], ["org.freedesktop.Notifications.CloseNotification", "42"]
        )

    def test_unavailable_notifications_do_not_lose_counts(self):
        counter.set_goal(1)
        with patch.object(counter.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(counter.change_count("increment"), 1)

    def test_power_setting_releases_shortcuts_and_guards_queued_commands(self):
        counter.change_count("add", 7)
        with (
            patch.object(counter, "lease_token", return_value="a" * 32),
            patch.object(counter, "check_conflicts"),
            patch.object(counter, "unregister") as unregister,
            patch.object(counter, "register") as register,
        ):
            counter.set_enabled(False)
            unregister.assert_called_once_with("a" * 32)
            counter.keyboard_count("increment")
            counter.keyboard_count("reset")
            self.assertEqual(counter.read_count(), 7)
            counter.set_key("F8")
            register.assert_not_called()
            counter.set_enabled(True)
            register.assert_called_once_with("F8", "a" * 32)
            counter.keyboard_count("increment")
            self.assertEqual(counter.read_count(), 8)

    def test_concurrent_goal_crossing_sends_one_notification(self):
        counter.set_goal(5)
        with patch.object(counter, "notify_goal") as notify:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                list(pool.map(lambda _: counter.change_count("increment"), range(20)))
            notify.assert_called_once_with(5)

    def test_damaged_optional_goal_does_not_block_counting(self):
        for value in (b"broken", b"-1", b"\xff\xfe"):
            with self.subTest(value=value):
                (self.state / "goal").write_bytes(value)
                counter.change_count("reset")
                self.assertEqual(counter.change_count("increment"), 1)
                with self.assertRaises((counter.CounterError, UnicodeError)):
                    counter.read_goal()
        counter.set_goal(33)
        self.assertEqual(counter.read_goal(), 33)

    def test_failed_power_preference_write_restores_previous_shortcuts(self):
        original = counter.atomic_write

        def fail_enabled(path, text):
            if path.name == "enabled":
                raise OSError(errno.ENOSPC, "Full")
            original(path, text)

        with (
            patch.object(counter, "lease_token", return_value="a" * 32),
            patch.object(counter, "register") as register,
            patch.object(counter, "unregister"),
            patch.object(counter, "atomic_write", side_effect=fail_enabled),
        ):
            with self.assertRaises(OSError):
                counter.set_enabled(False)
            register.assert_called_once_with("F1", "a" * 32)
            self.assertTrue(counter.counting_enabled())

    def test_corrupted_power_preference_can_be_recovered(self):
        (self.state / "enabled").write_bytes(b"\xff")
        with (
            patch.object(counter, "lease_token", return_value="a" * 32),
            patch.object(counter, "register"),
            patch.object(counter, "check_conflicts"),
        ):
            counter.set_enabled(True)
        self.assertTrue(counter.counting_enabled())

    def test_invalid_cli_goal_arguments_fail_without_tracebacks(self):
        for value in ("-1", "1.5", "a", "9" * 101):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "set-goal", value],
                env=dict(os.environ, XDG_STATE_HOME=str(self.root)),
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr)
        self.assertFalse((self.state / "goal").exists())

    def test_notification_wait_holds_neither_counter_nor_settings_lock(self):
        counter.set_goal(1)
        real_run = subprocess.run
        results = []

        def during_toast(_):
            results.append(
                real_run(
                    [sys.executable, str(SCRIPT), "key-increment"],
                    env=dict(os.environ, XDG_STATE_HOME=str(self.root)),
                    capture_output=True,
                    timeout=2,
                )
            )

        with (
            patch.object(
                counter.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "42\n")
            ),
            patch.object(counter.time, "sleep", side_effect=during_toast),
        ):
            counter.keyboard_count("increment")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].returncode, 0)
        self.assertEqual(counter.read_count(), 2)

    def test_first_run_and_zero_floor(self):
        self.assertEqual(counter.change_count("show"), 0)
        self.assertEqual(counter.change_count("undo"), 0)
        self.assertEqual(counter.change_count("increment"), 1)
        self.assertEqual(counter.change_count("reset"), 0)

    def test_adds_multiple_counts_without_crossing_the_limit(self):
        self.assertEqual(counter.change_count("add", 25), 25)
        (self.state / "count").write_text("9" * 100)
        with self.assertRaises(counter.CounterError):
            counter.change_count("add", 2)

    def test_damaged_counts_require_explicit_reset(self):
        for text in ("", "damaged", "-1", "2.5", "9" * 101):
            with self.subTest(text=text):
                (self.state / "count").write_text(text)
                with self.assertRaises(counter.CounterError):
                    counter.change_count("increment")
                self.assertEqual((self.state / "count").read_text(), text)
                self.assertEqual(counter.change_count("reset"), 0)

    def test_concurrent_processes_do_not_lose_counts(self):
        env = dict(os.environ, XDG_STATE_HOME=str(self.root))
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(
                pool.map(
                    lambda _: subprocess.run(
                        [sys.executable, str(SCRIPT), "increment"],
                        env=env,
                        capture_output=True,
                    ),
                    range(200),
                )
            )
        self.assertTrue(all(result.returncode == 0 for result in results))
        self.assertEqual(counter.read_count(), 200)

    def test_process_restart_preserves_total(self):
        env = dict(os.environ, XDG_STATE_HOME=str(self.root))
        subprocess.run([sys.executable, str(SCRIPT), "increment"], env=env, check=True)
        self.assertEqual(
            subprocess.check_output([sys.executable, str(SCRIPT)], env=env, text=True).strip(),
            "1",
        )

    def test_disk_full_preserves_previous_file(self):
        path = self.state / "count"
        path.write_text("42\n")
        with patch.object(counter.os, "replace", side_effect=OSError(errno.ENOSPC, "Full")):
            with self.assertRaises(OSError):
                counter.atomic_write(path, "43\n")
        self.assertEqual(path.read_text(), "42\n")
        self.assertEqual(list(self.state.glob(".count.*")), [])

    def test_permission_failure_is_readable_without_traceback(self):
        self.state.chmod(0o500)
        self.addCleanup(self.state.chmod, 0o700)
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "increment"],
            env=dict(os.environ, XDG_STATE_HOME=str(self.root)),
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr)

    def test_non_utf8_count_is_preserved(self):
        path = self.state / "count"
        path.write_bytes(b"\xff\xfe")
        with self.assertRaises(counter.CounterError):
            counter.change_count("increment")
        self.assertEqual(path.read_bytes(), b"\xff\xfe")
        self.assertEqual(counter.change_count("reset"), 0)

    def test_counter_limit_does_not_write_unreadable_state(self):
        (self.state / "count").write_text("9" * 100)
        with self.assertRaises(counter.CounterError):
            counter.change_count("increment")
        self.assertEqual(counter.read_count(), 10**100 - 1)

    def test_key_names_and_modifiers(self):
        self.assertEqual(counter.canonical_key("f8")[0], "F8")
        for key in ("NotAKey", "F1; bad", "Super_L", "ISO_Level3_Shift", "Num_Lock"):
            with self.subTest(key=key), self.assertRaises(counter.CounterError):
                counter.canonical_key(key)

    def test_settings_survive_restart_and_reject_damage(self):
        self.assertEqual(counter.current_key(), "F1")
        counter.save_key("F8")
        self.assertEqual(counter.current_key(), "F8")
        for text in (
            "",
            "[]",
            '{"version": 3, "key": "F8"}',
            '{"version":1,"key":null}',
        ):
            counter.SETTINGS.write_text(text)
            with self.assertRaises(counter.CounterError):
                counter.current_key()

    def test_existing_shortcut_is_untouched(self):
        with patch.object(
            counter,
            "bindings",
            return_value=[{"key": "F8", "description": "Existing action"}],
        ):
            with self.assertRaisesRegex(counter.CounterError, "already used"):
                counter.check_conflicts("F8", counter.canonical_key("F8")[1])

    def test_keycode_conflicts_fail_closed(self):
        with patch.object(counter, "bindings", return_value=[{"keycode": 42}]):
            with self.assertRaises(counter.CounterError):
                counter.check_conflicts("F8", counter.canonical_key("F8")[1])

    def test_same_key_with_other_modifier_is_still_a_conflict(self):
        with patch.object(counter, "bindings", return_value=[{"key": "F8", "modmask": 64}]):
            with self.assertRaises(counter.CounterError):
                counter.check_conflicts("F8", counter.canonical_key("F8")[1])

    def test_successful_key_change(self):
        with (
            patch.object(counter, "lease_token", return_value="a" * 32),
            patch.object(counter, "check_conflicts"),
            patch.object(counter, "register") as register,
            patch.object(counter, "bindings", return_value=[]),
        ):
            self.assertEqual(counter.set_key("f8"), "F8")
        register.assert_called_once_with("F8", "a" * 32)
        self.assertEqual(counter.current_key(), "F8")

    def test_failed_runtime_change_restores_previous_binding(self):
        counter.save_key("F9")
        with (
            patch.object(counter, "lease_token", return_value="a" * 32),
            patch.object(counter, "check_conflicts"),
            patch.object(
                counter, "register", side_effect=[counter.CounterError("failed"), None]
            ) as register,
            patch.object(counter, "bindings", return_value=[self.own("F9")]),
        ):
            with self.assertRaisesRegex(counter.CounterError, "previous key was restored"):
                counter.set_key("F8")
        self.assertEqual(register.call_args.args, ("F9", "a" * 32))
        self.assertEqual(counter.current_key(), "F9")

    def test_failed_save_restores_runtime_and_settings(self):
        counter.save_key("F9")
        original = counter.save_key
        calls = 0

        def fail_once(key):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise OSError(errno.ENOSPC, "Full")
            return original(key)

        with (
            patch.object(counter, "lease_token", return_value="a" * 32),
            patch.object(counter, "check_conflicts"),
            patch.object(counter, "register") as register,
            patch.object(counter, "save_key", side_effect=fail_once),
            patch.object(counter, "bindings", return_value=[self.own("F9")]),
        ):
            with self.assertRaises(counter.CounterError):
                counter.set_key("F8")
        self.assertEqual(register.call_args.args[0], "F9")
        self.assertEqual(counter.current_key(), "F9")

    def test_service_absent_changes_nothing(self):
        with self.assertRaisesRegex(counter.CounterError, "not running"):
            counter.set_key("F8")
        self.assertFalse(counter.SETTINGS.exists())

    def test_desktop_timeout_is_bounded(self):
        with patch.object(
            counter.subprocess, "run", side_effect=subprocess.TimeoutExpired("hyprctl", 8)
        ) as run:
            with self.assertRaises(counter.CounterError):
                counter.hyprctl("eval", "")
        self.assertEqual(run.call_args.kwargs["timeout"], 8)

    def test_bad_ipc_data_does_not_change_shortcuts(self):
        for response in ("{}", "bad", "[1]"):
            with (
                self.subTest(response=response),
                patch.object(counter, "hyprctl", return_value=response),
            ):
                with self.assertRaises(counter.CounterError):
                    counter.bindings()

    def test_register_verifies_consumption_and_repeat(self):
        for actual in (
            [],
            [self.own("F8", non_consuming=True)],
            [self.own("F8", repeat=True)],
        ):
            with (
                self.subTest(actual=actual),
                patch.object(counter, "hyprctl", return_value="ok"),
                patch.object(counter, "bindings", return_value=actual),
            ):
                with self.assertRaises(counter.CounterError):
                    counter.register("F8", "a" * 32)

    def test_unregistration_is_scoped_to_ownership_token(self):
        with patch.object(counter, "hyprctl", return_value="ok") as ipc:
            counter.unregister("a" * 32)
        code = ipc.call_args.args[1]
        self.assertIn('v.token == "' + "a" * 32 + '"', code)
        self.assertIn("v.binding:remove()", code)
        self.assertNotIn("hl.unbind", code)

    def test_command_path_with_spaces_and_unicode_is_quoted(self):
        with (
            patch.object(counter, "EXECUTABLE", self.root / 'quote " path ü.py'),
            patch.object(counter, "hyprctl", return_value="ok") as ipc,
            patch.object(
                counter,
                "bindings",
                return_value=[
                    self.own("F8"),
                    self.own("F8", description=counter.RESET_DESCRIPTION, modmask=5),
                ],
            ),
        ):
            counter.register("F8", "a" * 32)
        self.assertNotIn("ignore_mods = true", ipc.call_args.args[1])
        self.assertIn("CTRL + SHIFT + F8", ipc.call_args.args[1])
        self.assertIn("ü.py", ipc.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
