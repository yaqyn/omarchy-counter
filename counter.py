#!/usr/bin/env python3
"""Persistent counter and transactional Hyprland key settings. Standard library only."""

import argparse
import ctypes
import fcntl
import json
import os
import re
import selectors
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

STATE = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state") / "counter"
SETTINGS = STATE / "settings.json"
EXECUTABLE = Path(__file__).resolve()
RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR", "/run/user/" + str(os.getuid())))
SIGNATURE = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
# The compositor chooses this value, but never trust it as a path component.
if SIGNATURE and not re.fullmatch(r"[A-Za-z0-9_.-]+", SIGNATURE):
    SIGNATURE = ""
SESSION = RUNTIME / ("yaqyn.counter-" + (SIGNATURE or "no-session"))
DESCRIPTION = "Counter: count once"


class CounterError(Exception):
    """A recoverable error suitable for the panel."""


@contextmanager
def locked(name):
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / name).open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def atomic_write(path, text):
    """Readers see the old or complete new value; flush it before returning."""
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb" if isinstance(text, bytes) else "w") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        Path(temporary).unlink(missing_ok=True)


def read_count():
    try:
        value = (STATE / "count").read_text().strip()
    except FileNotFoundError:
        return 0
    except UnicodeError as error:
        raise CounterError("Saved count is unreadable. Reset to start again.") from error
    if not re.fullmatch(r"[0-9]{1,100}", value):
        raise CounterError("Saved count is unreadable. Reset to start again.")
    return int(value)


def change_count(action):
    with locked("lock"):
        if action == "reset":
            value = 0  # Explicit reset can also recover a damaged state file.
        else:
            count = read_count()
            if action == "show":
                return count
            if action == "increment" and count >= 10**100 - 1:
                raise CounterError("Count limit reached. Reset to start again.")
            value = count + 1 if action == "increment" else max(0, count - 1)
        atomic_write(STATE / "count", f"{value}\n")
        return value


def current_key():
    try:
        data = json.loads(SETTINGS.read_text())
    except FileNotFoundError:
        return "F1"
    except (ValueError, TypeError, UnicodeError) as error:
        raise CounterError("Saved counting key is unreadable. Choose a key to recover.") from error
    if (
        not isinstance(data, dict)
        or data.get("version") != 1
        or not isinstance(data.get("key"), str)
    ):
        raise CounterError("Saved counting key is unreadable. Choose a key to recover.")
    return canonical_key(data["key"])[0]


def save_key(key):
    atomic_write(SETTINGS, json.dumps({"version": 1, "key": key}) + "\n")


def key_library():
    library = ctypes.CDLL("libxkbcommon.so.0")
    library.xkb_keysym_from_name.argtypes = [ctypes.c_char_p, ctypes.c_int]
    library.xkb_keysym_from_name.restype = ctypes.c_uint32
    library.xkb_keysym_get_name.argtypes = [
        ctypes.c_uint32,
        ctypes.c_char_p,
        ctypes.c_size_t,
    ]
    library.xkb_keysym_get_name.restype = ctypes.c_int
    return library


def canonical_key(name):
    library = key_library()
    if not re.fullmatch(r"[A-Za-z0-9_]{1,64}", name):
        raise CounterError("Use a key name such as F1, F8, Pause or Scroll_Lock.")
    symbol = library.xkb_keysym_from_name(name.encode(), 1)
    if not symbol:
        raise CounterError("Unknown key. Try F1, F8, Pause or Scroll_Lock.")
    # Modifier keys change global typing state; they cannot be a private counter.
    if 0xFFE1 <= symbol <= 0xFFEE or 0xFE01 <= symbol <= 0xFE13 or symbol in (0xFF7E, 0xFF7F):
        raise CounterError("Choose a key other than Shift, Ctrl, Alt, Super or a lock modifier.")
    buffer = ctypes.create_string_buffer(128)
    if library.xkb_keysym_get_name(symbol, buffer, len(buffer)) <= 0:
        raise CounterError("Could not read this key name.")
    return buffer.value.decode(), symbol


def hyprctl(*arguments):
    try:
        result = subprocess.run(
            ["hyprctl", *arguments],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CounterError("Cannot reach Hyprland. Try again in your desktop session.") from error
    if result.returncode:
        raise CounterError("Hyprland could not complete the change. Try again.")
    return result.stdout.strip()


def bindings():
    try:
        result = json.loads(hyprctl("-j", "binds"))
        if not isinstance(result, list) or not all(isinstance(item, dict) for item in result):
            raise ValueError("Invalid binding list")
        return result
    except (ValueError, TypeError) as error:
        raise CounterError("Cannot read desktop shortcuts. No key was changed.") from error


def lua_string(value):
    return json.dumps(str(value), ensure_ascii=False)


def check_conflicts(key, symbol):
    library = key_library()
    for binding in bindings():
        other = library.xkb_keysym_from_name(str(binding.get("key", "")).encode(), 1)
        if other == symbol and binding.get("description") != DESCRIPTION:
            label = binding.get("description") or "another desktop shortcut"
            raise CounterError(f"{key} is already used by {label}.")
        if binding.get("keycode") and binding.get("description") != DESCRIPTION:
            raise CounterError(
                "A physical-key shortcut needs a manual conflict check before selecting this key."
            )


def register(key, token):
    command = shlex.join([sys.executable, str(EXECUTABLE), "increment"])
    # Keep the actual binding object, so removal cannot unbind someone else's key.
    code = (
        f"if _G.yaqyn_counter_cancelled and _G.yaqyn_counter_cancelled[{lua_string(token)}] then return end; "
        "local old = _G.yaqyn_counter; if old then pcall(function() old.binding:remove() end); _G.yaqyn_counter = nil end; "
        f"local new = hl.bind({lua_string(key)}, hl.dsp.exec_cmd({lua_string(command)}), "
        f"{{ description = {lua_string(DESCRIPTION)}, ignore_mods = true }}); "
        f"_G.yaqyn_counter = {{ token = {lua_string(token)}, binding = new }}"
    )
    response = hyprctl("eval", code)
    if response != "ok":
        raise CounterError("Hyprland could not register the counting key.")
    own = [item for item in bindings() if item.get("description") == DESCRIPTION]
    if (
        len(own) != 1
        or own[0].get("key") != key
        or own[0].get("non_consuming")
        or own[0].get("repeat")
    ):
        raise CounterError("The counting key did not load correctly.")


def unregister(token, cancel=False):
    prefix = (
        (
            "_G.yaqyn_counter_cancelled = _G.yaqyn_counter_cancelled or {}; "
            f"_G.yaqyn_counter_cancelled[{lua_string(token)}] = true; "
        )
        if cancel
        else ""
    )
    response = hyprctl(
        "eval",
        prefix + "local v = _G.yaqyn_counter; "
        f"if v and v.token == {lua_string(token)} then "
        "pcall(function() v.binding:remove() end); _G.yaqyn_counter = nil end",
    )
    if response != "ok":
        raise CounterError("Could not release the counting key.")


def status(error="", active=False):
    atomic_write(STATE / "service.json", json.dumps({"error": error, "active": active}) + "\n")


def lease_token():
    try:
        data = json.loads((SESSION / "lease.json").read_text())
        token = data["token"]
        if not isinstance(token, str) or not re.fullmatch(r"[a-f0-9]{32}", token):
            raise ValueError("Invalid lease")
        return token
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise CounterError(
            "Counter service is not running. Enable the plugin and try again."
        ) from error


def set_key(name):
    key, symbol = canonical_key(name.strip())
    with locked("settings.lock"):
        token = lease_token()
        check_conflicts(key, symbol)
        previous_settings = SETTINGS.read_bytes() if SETTINGS.exists() else None
        owned = [item for item in bindings() if item.get("description") == DESCRIPTION]
        previous_key = owned[0].get("key") if len(owned) == 1 else None
        try:
            register(key, token)
            save_key(key)
            status(active=True)
        except (CounterError, OSError) as error:
            try:
                if previous_key:
                    register(previous_key, token)
                else:
                    unregister(token)
                if previous_settings is None:
                    SETTINGS.unlink(missing_ok=True)
                elif not SETTINGS.exists() or SETTINGS.read_bytes() != previous_settings:
                    atomic_write(SETTINGS, previous_settings)
            except (CounterError, OSError) as restore_error:
                raise CounterError(
                    "Key change failed; restoring the previous key needs attention."
                ) from restore_error
            raise CounterError("Key change failed. Your previous key was restored.") from error
    return key


def release(token):
    """Safe even if teardown beats startup or another instance already replaced us."""
    SESSION.mkdir(mode=0o700, parents=True, exist_ok=True)
    with locked("settings.lock"):
        atomic_write(SESSION / ("cancel-" + token), "cancelled\n")
        unregister(token, cancel=True)
        try:
            if lease_token() == token:
                (SESSION / "lease.json").unlink(missing_ok=True)
                status(active=False)
        except CounterError:
            pass


def serve(token=None):
    """One service per compositor; stdin and signals tie its lifetime to the shell."""
    if not SIGNATURE or not (RUNTIME / "hypr" / SIGNATURE / ".socket2.sock").exists():
        raise CounterError("A running Hyprland Lua session is required.")
    STATE.mkdir(parents=True, exist_ok=True)
    SESSION.mkdir(mode=0o700, parents=True, exist_ok=True)
    token = token or uuid.uuid4().hex
    stop_read, stop_write = socket.socketpair()
    previous_handlers = {}

    def request_stop(signum, frame):
        try:
            stop_write.send(b"x")
        except OSError:
            pass

    for number in (signal.SIGTERM, signal.SIGINT):
        previous_handlers[number] = signal.signal(number, request_stop)
    selector = selectors.DefaultSelector()
    events = socket.socket(socket.AF_UNIX)
    try:
        events.connect(str(RUNTIME / "hypr" / SIGNATURE / ".socket2.sock"))
        selector.register(sys.stdin, selectors.EVENT_READ, "parent")
        selector.register(stop_read, selectors.EVENT_READ, "stop")
        selector.register(events, selectors.EVENT_READ, "desktop")
        with (SESSION / "owner.lock").open("a") as owner:
            # Hot reload may briefly overlap services. Wait without blocking shutdown.
            while True:
                try:
                    fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if any(item.data in ("parent", "stop") for item, _ in selector.select(0.05)):
                        return

            def restore():
                with locked("settings.lock"):
                    if (SESSION / ("cancel-" + token)).exists():
                        return False
                    atomic_write(
                        SESSION / "lease.json",
                        json.dumps({"token": token, "pid": os.getpid()}) + "\n",
                    )
                    try:
                        key, symbol = canonical_key(current_key())
                        check_conflicts(key, symbol)
                        register(key, token)
                        if not (STATE / "count").exists():
                            with locked("lock"):
                                if not (STATE / "count").exists():
                                    atomic_write(STATE / "count", "0\n")
                        status(active=True)
                    except (CounterError, OSError) as error:
                        status(str(error), active=False)
                    return True

            if not restore():
                return
            pending = b""
            try:
                while True:
                    for item, _ in selector.select():
                        if item.data in ("stop", "parent"):
                            return
                        data = events.recv(65536)
                        if not data:
                            return
                        pending += data
                        while b"\n" in pending:
                            line, pending = pending.split(b"\n", 1)
                            if line.startswith(b"configreloaded>>"):
                                if not restore():
                                    return
            finally:
                with locked("settings.lock"):
                    try:
                        unregister(token, cancel=True)
                    except CounterError:
                        pass  # The compositor may already have exited.
                    (SESSION / "lease.json").unlink(missing_ok=True)
                    status(active=False)
    finally:
        selector.close()
        events.close()
        stop_read.close()
        stop_write.close()
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        nargs="?",
        default="show",
        choices=(
            "show",
            "increment",
            "undo",
            "reset",
            "key",
            "set-key",
            "serve",
            "release",
        ),
    )
    parser.add_argument("key_name", nargs="?")
    args = parser.parse_args()
    if args.action in ("serve", "release"):
        if args.key_name is not None and not re.fullmatch(r"[a-f0-9]{32}", args.key_name):
            parser.error("service ownership token must be 32 hexadecimal characters")
        if args.action == "release" and args.key_name is None:
            parser.error("release requires a service ownership token")
    elif (args.action == "set-key") != (args.key_name is not None):
        parser.error("set-key requires one key name; other commands take no key name")
    try:
        if args.action == "serve":
            serve(args.key_name)
        elif args.action == "release":
            release(args.key_name)
        elif args.action == "set-key":
            print(f"Counting key: {set_key(args.key_name)}")
        elif args.action == "key":
            print(current_key())
        else:
            value = change_count(args.action)
            if args.action == "show":
                print(value)
    except (CounterError, OSError, OverflowError) as error:
        message = (
            str(error)
            if isinstance(error, CounterError)
            else "Could not save or read the counter. Check your local files and try again."
        )
        print(message, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
