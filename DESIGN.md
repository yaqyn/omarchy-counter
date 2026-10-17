# Counter

## Intent
A quiet number in the native Omarchy bar, with a small click-open panel for the existing Reset, Undo and counting-key controls. Counting never opens a window, sends a notification, changes focus or repeats while a key is held. No additional features or independent visual identity.

## Canonical components and tokens
Use qs.Ui.BarWidget, WidgetButton, Panel, KeyboardPanel, Button and ShortcutInhibitor. qs.Commons.Style and Color own typography, spacing, geometry and theme colors; no copied palette. Secondary text uses the foreground at 72 percent opacity for legibility. Bar width reserves at least Style.space(44); longer numbers can grow. The panel reserves count and feedback geometry, fits long counts and uses plain text throughout.

## Interaction
Only left click toggles the panel. Opening focuses the neutral panel body. Tab traverses Reset, Undo, key chooser and Apply; Enter activates the focused control; Escape and clicking outside close. Reopening discards an unapplied key edit. Reset and Undo are disabled at zero; Reset remains available when saved count is unreadable. Clicking the key starts a focused capture. The next nonmodifier key becomes the selection; Escape cancels without changing it. ShortcutInhibitor is enabled only for the focused popup while capturing, and disabled on selection, cancellation or panel close. Apply is disabled while capturing, for unchanged selections and while busy. Reset and Undo are disabled during capture. Starting capture clears stale feedback. Errors remain inline. Reset is explicit; Undo subtracts one without going negative.

## State and failure behavior
The count file is authoritative for the total; the versioned state/settings.json file is authoritative for the key. QML reads saved count changes, and refreshes the key on open and after applying. The CLI serializes changes with file locks, atomically replaces complete files, and flushes them to disk. Invalid counts are preserved until explicit Reset. Keys are canonicalized through libxkbcommon, modifiers and conflicting shortcuts are rejected, Hyprland calls have timeouts, and a failed change restores the previous runtime binding and saved settings. Service.qml owns exactly one event-driven helper per compositor. Removal uses token-scoped inline Lua cleanup that survives directory deletion; no permanent configuration changes are installed. The loaded binding is checked for exactly one matching, consuming, nonrepeating shortcut.

## Verification
Isolated Python regression tests cover concurrency, damaged state, atomic-write failure, key validation/conflicts, timeout, malformed desktop responses and rollback. Runtime checks cover clean Hyprland configuration, native panel rendering, keyboard traversal, a successful captured F1/F8/F1 roundtrip, Escape cancellation, modifier handling and capture of the active counting key without incrementing. No browser implementation is involved. Real counter values are not reset during tests.

## Documentation identity
The public cover uses a count and keycap motif, with a slate background and pale blue accent. Exact values, typography and canonical heading icon rules live in [readme-assets/STYLE.md](readme-assets/STYLE.md). This identity applies to documentation only; the plugin continues to inherit the user's Omarchy theme.
