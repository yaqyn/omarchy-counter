# Azkar counter

A quiet counter for dhikr while you work in Omarchy. Press one chosen key to count; your typing, focus and media stay undisturbed.

The bar shows only the number. Click it for Reset, Undo and a key chooser: click the key, press your preferred key, then Apply. Escape cancels selection. One press counts once; holding the key does not repeat. The total and selected key survive plugin and desktop restarts.

<img src="assets/panel.png" width="340" alt="Azkar counter panel with a numeric total, Reset and Undo buttons, and the key chooser">

## Requirements

- Omarchy's Quickshell plugin system and native bar components. Tested on **Omarchy 4.0.4**.
- **Hyprland 0.56.2** with the Lua binding API; older Hyprlang-only desktops are unsupported.
- **Quickshell 0.3.1**, including its Wayland shortcut inhibitor.
- **Python 3.11+**, `libxkbcommon`, and `hyprctl` on PATH. No extra Python packages.

These are the desktop versions actually tested. Newer versions may work, but changes to Omarchy's shared components can require maintenance. This is a session counter; the chosen key's normal action is reserved for counting while the plugin is enabled. Login/lock screens and apps that inhibit global shortcuts are outside that guarantee.

## Install

After this repository is published:

```sh
omarchy plugin add https://github.com/yaqyn/omarchy-azkar.git --enable
```

F1 is the default. Existing shortcuts are preserved: if F1 conflicts, the panel explains the conflict and lets you select another key. The chooser temporarily inhibits desktop shortcuts while listening so a selection does not trigger another action. Modifier keys alone cannot be selected; Escape is reserved for cancellation.

There is no installer script, root access, separate executable installation or change to your Hyprland configuration. The repository itself is the plugin.

## Update, disable and remove

```sh
omarchy plugin update qv.azkar
omarchy restart shell

omarchy plugin disable qv.azkar
omarchy plugin enable qv.azkar

omarchy plugin remove qv.azkar
```

Disable and removal release the counting key. Updates keep your saved state; restart the shell after an update to clear cached QML components. Disabling or removing the plugin preserves your total and selected key for reinstalling. To erase that data too, remove `${XDG_STATE_HOME:-$HOME/.local/state}/azkar` **after** removing the plugin.

## Data and architecture

Persistent data lives in `${XDG_STATE_HOME:-$HOME/.local/state}/azkar`:

| File | Purpose |
| --- | --- |
| `count` | Saved nonnegative total |
| `settings.json` | Versioned counting-key preference |
| `service.json` | Local service status for the panel |

Counts and settings use locked, atomic, flushed writes. Invalid count data is preserved until you explicitly Reset. Key changes validate conflicts, verify the registered binding, and restore the previous runtime key and saved settings if they fail.

One event-driven Python helper registers the key for the entire compositor, independent of how many monitors show the widget. It listens for reloads through Hyprland's event socket, and waits without polling. Each press runs a small increment command. Registration belongs to a specific service instance; old teardown cannot remove a newer instance's binding. Cleanup uses `hyprctl` directly so it still works after the plugin directory has been removed.

All commands stay on your machine. The plugin needs no network connection, credentials or telemetry. Like other Omarchy plugins it runs with your user permissions, not in a sandbox.

## Development and verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
/usr/lib/qt6/bin/qmltestrunner -platform offscreen -input tests/qml
omarchy plugin validate .
uvx --from ruff==0.17.1 ruff check .
uvx --from ruff==0.17.1 ruff format --check .
```

For an opt-in real desktop integration test:

```sh
python3 tests/desktop.py --run --keep
```

This starts a temporary **nested desktop window**, a private D-Bus session and an isolated Omarchy configuration. It tests native install/disable/enable/removal, two outputs, reload recovery and saved data without modifying your live counter. It requires an active Wayland desktop and the Omarchy tools. `--keep` retains logs under the printed temporary path.

Build a deterministic archive from a clean committed checkout with `python3 scripts/release.py`. See [verification coverage](docs/VERIFICATION.md) for evidence and remaining hardware checks, [release notes](CHANGELOG.md), and [contributing](CONTRIBUTING.md). Report bugs with desktop versions, steps and relevant errors; do not attach private desktop screenshots or full environment dumps.

## Troubleshooting

- **Key conflict:** choose another key. The counter ignores Shift/Ctrl/Alt, so a shortcut using the same named key with any modifier is a conflict. Physical keycode shortcuts currently require a manual conflict check.
- **Capture unavailable:** close/reopen the panel. The compositor must grant the shortcut inhibitor; the chooser fails safely if it cannot.
- **Unreadable saved count:** inspect or back up the `count` file before Reset. Write errors can mean full storage or incorrect permissions.
- **Key absent after a change:** inspect the inline error and `hyprctl configerrors`. Restart the shell after resolving desktop or dependency errors.
- **Unsupported desktop version:** use a tested Omarchy/Hyprland/Quickshell combination. This plugin deliberately uses the native shell UI rather than shipping its own desktop components.

MIT licensed. Built and maintained by Abdulrahman M. Yaqyn.
