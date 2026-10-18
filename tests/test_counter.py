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
        } | changes

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
            patch.object(counter, "bindings", return_value=[self.own("F8")]),
        ):
            counter.register("F8", "a" * 32)
        self.assertIn("ignore_mods = true", ipc.call_args.args[1])
        self.assertIn("ü.py", ipc.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
