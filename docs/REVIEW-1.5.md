# Counter 1.5 review

Reviewed on 2026-10-20 before publication. This is a scoped engineering review, not a security certification or a claim of universal compatibility.

## Supported and tested baseline

Omarchy 4.0.6-1, Hyprland 0.56.2 with its Lua API, Quickshell 0.3.2 and Qt 6.12 on Linux/Wayland. Runtime Python is standard-library-only; automated tests pass on Python 3.11, 3.13 and 3.14. The 1.4 release's older desktop results do not establish 1.5 compatibility on that stack.

The native panel requires Omarchy's current shared UI components and Quickshell's ShortcutInhibitor. Other desktop environments and older Hyprlang-only versions are unsupported. Goal toasts use optional `notify-send` and `gdbus`; counting remains available when notification support is absent.

## Security and data safety

- Runtime operations use no network, credentials, telemetry, root access or permanent desktop-config edits. Only the selected shortcuts are registered; the plugin does not log arbitrary keystrokes.
- XKB key validation, shell argument quoting, Lua string escaping and hex ownership tokens protect the command boundaries. Subprocess calls use argument lists, bounded timeouts and no `shell=True`.
- Both shortcuts are consuming and nonrepeating, with distinct modifier masks. Conflicting shortcuts are rejected conservatively. Physical keycode bindings require manual conflict review; the plugin fails closed rather than guessing.
- New state directories are private. Locked atomic replacements preserve complete files, including under concurrent counting. Invalid count data is preserved until explicit Reset. A corrupt optional goal cannot disable counting.
- Turning off releases both shortcuts, preserves the tally and guards queued keyboard commands. Key changes while off do not re-enable counting. Runtime/settings rollback is covered by simulated disk failures.
- Reload registration failures release owned shortcuts. Token-scoped cleanup cannot remove a newer owner's shortcuts and survives plugin-directory removal.
- Goal notifications occur only on upward target crossings, including batch additions. Toast waiting holds neither count nor settings locks. Missing notification tools do not discard a saved count. Counter requests 1500 ms and closes its own returned notification ID after 1.5 seconds; daemon policy, DND or scheduling can affect presentation.
- Gitleaks 8.30.1 found no secrets. Bandit reported no medium/high findings; its ten low-severity findings concern subprocess imports, argument-list calls and PATH-based executable resolution. These were manually reviewed. The desktop's PATH/library environment is trusted, as for other unsandboxed user plugins; this is not a privilege boundary.

## Accessibility and simplicity

- The same native panel handles reset, undo, power, goal and key selection. Runtime colors/fonts remain theme-owned.
- CounterButton extends the existing shell button with Qt button roles, accessible names and press actions. The bar also exposes an accessible press action and keyboard activation.
- Controls have a 32-unit minimum height and visible native focus styling. A clipped scrolling viewport automatically reveals focused controls on short/scaled displays. Long totals are visually abbreviated in the bar while the full value remains available to accessibility tools and in the tooltip.
- Goal entry has a descriptive accessible name, decimal validation and explicit save/clear behavior. Desktop shortcuts are inhibited only during capture or goal entry, preventing a numeric counting key from consuming digits.
- Secondary text uses the full theme foreground. Errors use text as well as color and remain readable in the scrollable panel. Feedback requests polite Qt accessibility announcements when supported.
- “Goal reached” remains in the panel after the brief toast disappears. The alert is supplementary; it is not the only indication of success.
- Escape/click-outside dismissal and the existing capture-cancel flow remain available. There are no extra setup screens or new runtime Python dependencies.

## Evidence

- 33 Python tests pass on 3.11, 3.13 and 3.14, including concurrent counts/goal crossing, notification timing/nonblocking behavior, corruption, argument rejection, conflict checks and rollback.
- Eight Qt test cases pass for key mapping and cancellation.
- Sixteen isolated real-desktop scenarios pass at 100% scale with a top bar and at 200% scale with a left bar. A separate 200% top-bar run verified the short-display scrolling behavior. Tests include installation/update/removal, two outputs, reload, helper crash, ten disable/enable cycles, saved goal entry, accessible roles, focus reveal, inhibition and full desktop restart. Test-only QML IPC instrumentation exists only in the temporary fixture, not the shipped plugin.
- Root manifest validation, Ruff and whitespace checks pass. The actual panel capture is `assets/panel.png`; `preview.png` is a generated UI illustration at native 1672 × 941, visibly labelled as an illustration.

## Remaining coverage limits

An actual screen-reader/AT-SPI session has not been tested; metadata/action checks are not a conformance claim. Arbitrary user themes can reduce contrast. Physical reboot/suspend, Fn/media hardware, mixed-DPI monitor hotplug, non-Latin end-to-end capture, all bar placements and older/newer desktop releases need additional environments. Synthetic or programmatically invoked test commands are not evidence of physical keyboard behavior on every layout. Goal alerts can be suppressed by desktop DND. All plugins run with the user's permissions, outside a security sandbox.

Known unsupported configurations are stated above. No unresolved medium/high security finding was identified within this review's scope; that is not a guarantee of absence of vulnerabilities.
