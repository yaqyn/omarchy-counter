#!/usr/bin/env python3
"""Opt-in integration test in a temporary nested desktop, never the live config."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def wait_for(check, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for desktop state")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        action="store_true",
        help="Start a nested desktop window for integration tests",
    )
    parser.add_argument("--keep", action="store_true", help="Keep isolated logs after the test")
    args = parser.parse_args()
    if not args.run:
        parser.error("pass --run to opt into starting a nested desktop")
    for command in (
        "Hyprland",
        "hyprctl",
        "qs",
        "omarchy",
        "dbus-run-session",
        "wtype",
    ):
        if not shutil.which(command):
            parser.error(f"required integration tool not found: {command}")
    if not os.environ.get("WAYLAND_DISPLAY"):
        parser.error("a Wayland session is required for the nested backend")
    # Unix socket paths must be short enough for Hyprland's full instance signature.
    root = Path(tempfile.mkdtemp(prefix="az"))
    root.chmod(0o700)
    processes = []
    handles = []
    results = []

    def record(name):
        results.append(name)
        print("PASS:", name, flush=True)

    env = dict(
        os.environ,
        HOME=str(root),
        XDG_CONFIG_HOME=str(root / ".config"),
        XDG_STATE_HOME=str(root / "state"),
        XDG_RUNTIME_DIR=str(root),
        HYPRLAND_NO_CRASHREPORTER="1",
        AQ_DRM_DEVICES="/dev/null",
    )
    parent_display = Path(os.environ["XDG_RUNTIME_DIR"]) / os.environ["WAYLAND_DISPLAY"]
    compositor_env = env | {"WAYLAND_DISPLAY": str(parent_display)}
    compositor_env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
    config = root / "hyprland.lua"
    config.write_text('hl.monitor({output="", mode="1280x720@60", position="auto", scale=1})\n')

    def start(command, name, environment=env):
        log = (root / name).open("w")
        handles.append(log)
        process = subprocess.Popen(
            command, env=environment, stdout=log, stderr=log, start_new_session=True
        )
        processes.append(process)
        return process

    def run(*command, check=True):
        result = subprocess.run(command, env=env, text=True, capture_output=True, timeout=20)
        if check and result.returncode:
            raise AssertionError(f"{command}: {result.stdout}{result.stderr}")
        return result.stdout.strip() if check else result

    def own():
        return [
            item
            for item in json.loads(run("hyprctl", "-j", "binds"))
            if item.get("description") == "Azkar: count once"
        ]

    def key_is(key):
        items = own()
        return len(items) == 1 and items[0]["key"] == key

    try:
        compositor = start(["Hyprland", "--config", str(config)], "compositor.log", compositor_env)
        wait_for(
            lambda: compositor.poll() is None and bool(list((root / "hypr").glob("*/.socket.sock")))
        )
        signature = next((root / "hypr").iterdir()).name
        env.update(HYPRLAND_INSTANCE_SIGNATURE=signature, WAYLAND_DISPLAY="wayland-1")
        plugin = root / ".config/omarchy/plugins/qv.azkar"
        source = root / "source"
        shutil.copytree(
            REPO,
            source,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "dist", ".ruff_cache"),
        )
        run("git", "init", "-b", "main", str(source))
        run("git", "-C", str(source), "add", "--all")

        def commit_fixture(message):
            run(
                "git",
                "-C",
                str(source),
                "-c",
                "user.name=Abdulrahman M. Yaqyn",
                "-c",
                "user.email=commit@yaqyn.dev",
                "commit",
                "-m",
                message,
            )

        commit_fixture("Installation test fixture")
        url = "https://github.com/yaqyn/omarchy-azkar.git"
        env.update(
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="url." + source.as_uri() + ".insteadOf",
            GIT_CONFIG_VALUE_0=url,
            GIT_ALLOW_PROTOCOL="file",
        )
        disabled = set()
        for manifest in Path(os.environ["OMARCHY_PATH"]).joinpath("shell").rglob("*.json"):
            try:
                data = json.loads(manifest.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(data, dict) and str(data.get("id", "")).startswith("omarchy."):
                disabled.add(data["id"])
        disabled.discard("omarchy.bar")
        shell_config = root / ".config/omarchy/shell.json"
        shell_config.parent.mkdir(parents=True, exist_ok=True)
        shell_config.write_text(
            json.dumps(
                {
                    "version": 1,
                    "disabledPlugins": sorted(disabled),
                    "plugins": [],
                    "bar": {
                        "layout": {
                            "left": [],
                            "center": [],
                            "right": [],
                        }
                    },
                }
            )
        )
        theme = root / ".local/state/omarchy/current/theme"
        theme.parent.mkdir(parents=True)
        source_theme = Path.home() / ".local/state/omarchy/current/theme"
        if source_theme.exists():
            theme.symlink_to(source_theme, target_is_directory=True)
        start(
            [
                "dbus-run-session",
                "--",
                "qs",
                "-p",
                str(Path(os.environ["OMARCHY_PATH"]) / "shell"),
            ],
            "shell.log",
        )
        wait_for(lambda: run("omarchy-shell", "shell", "ping", check=False).returncode == 0)
        run("omarchy", "plugin", "add", url, "--enable", "--yes")
        wait_for(lambda: key_is("F1"))
        record("fresh isolated installation registers one consuming, nonrepeating F1 binding")
        backend = plugin / "azkar.py"
        run(sys.executable, str(backend), "increment")
        assert run(sys.executable, str(backend)) == "1"
        assert not own()[0]["non_consuming"] and not own()[0]["repeat"]
        assert run("hyprctl", "eval", "assert(_G.qv_azkar.binding.ignore_mods)") == "ok"
        record("saved count and actual consuming, nonrepeating, modifier-ignoring binding verified")
        run("hyprctl", "output", "create", "headless", "QA-2")
        wait_for(lambda: len(json.loads(run("hyprctl", "-j", "monitors"))) == 2)
        assert key_is("F1")
        record("two outputs share one binding and saved total")
        run(sys.executable, str(backend), "set-key", "F8")
        run(sys.executable, str(backend), "set-key", "F8")
        assert key_is("F8")
        record("changing and reselecting the same key leaves exactly one binding")
        run("hyprctl", "reload")
        wait_for(lambda: key_is("F8"))
        record("compositor reload restores the saved key")
        update = json.loads((source / "manifest.json").read_text())
        update["version"] = "1.4.1"
        (source / "manifest.json").write_text(json.dumps(update))
        run("git", "-C", str(source), "add", "manifest.json")
        commit_fixture("Upgrade test fixture")
        run("omarchy", "plugin", "update", "qv.azkar", "--yes")
        wait_for(lambda: key_is("F8"))
        assert json.loads((plugin / "manifest.json").read_text())["version"] == "1.4.1"
        assert run(sys.executable, str(backend)) == "1"
        record("native git update preserves the total and selected key")
        lease = root / ("qv.azkar-" + signature) / "lease.json"
        old_pid = json.loads(lease.read_text())["pid"]
        os.kill(old_pid, signal.SIGKILL)
        wait_for(lambda: lease.exists() and json.loads(lease.read_text())["pid"] != old_pid)
        wait_for(lambda: key_is("F8"))
        record("helper crash is recovered without duplicate bindings")
        for _ in range(10):
            run("omarchy", "plugin", "disable", "qv.azkar")
            wait_for(lambda: not own())
            run("omarchy", "plugin", "enable", "qv.azkar")
            wait_for(lambda: key_is("F8"))
        record("ten native disable/enable cycles release and restore the key")
        run("omarchy-shell", "shell", "summon", "qv.azkar")
        time.sleep(0.3)
        run(sys.executable, str(backend), "set-key", "F9")
        assert key_is("F9")
        if shutil.which("grim"):
            run("grim", "-g", "0,0 340x410", str(root / "panel.png"))
        log = (root / "shell.log").read_text()
        assert not any(
            message in log for message in ("ReferenceError", "TypeError", "Unable to assign")
        )
        record("native panel loads without QML type or binding errors")
        run("omarchy-shell", "shell", "hide", "qv.azkar")
        run("hyprctl", "output", "remove", "QA-2")
        assert key_is("F9")
        record("monitor removal does not remove the singleton key service")
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=5)
        processes.clear()
        compositor = start(
            ["Hyprland", "--config", str(config)], "compositor-restarted.log", compositor_env
        )
        wait_for(lambda: bool(list((root / "hypr").glob("*/.socket.sock"))))
        signature = max(
            (socket_path.parent for socket_path in (root / "hypr").glob("*/.socket.sock")),
            key=lambda path: path.stat().st_mtime,
        ).name
        env["HYPRLAND_INSTANCE_SIGNATURE"] = signature
        start(
            ["dbus-run-session", "--", "qs", "-p", str(Path(os.environ["OMARCHY_PATH"]) / "shell")],
            "shell-restarted.log",
        )
        wait_for(lambda: key_is("F9"))
        assert run(sys.executable, str(backend)) == "1"
        record("full nested compositor and shell restart preserves total and key")
        count = run(sys.executable, str(backend))
        saved = (root / "state/azkar/settings.json").read_bytes()
        run("omarchy", "plugin", "remove", "qv.azkar", "--yes")
        wait_for(lambda: not own())
        assert not plugin.exists()
        assert (root / "state/azkar/settings.json").read_bytes() == saved
        assert (root / "state/azkar/count").read_text().strip() == count
        record("native removal releases the key after directory removal and preserves user data")
        print(json.dumps({"passed": results, "count": len(results)}, indent=2))
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        for handle in handles:
            handle.close()
        if args.keep:
            print("Isolated logs:", root)
        else:
            shutil.rmtree(root)


if __name__ == "__main__":
    main()
