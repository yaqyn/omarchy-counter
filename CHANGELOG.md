# Changelog

## 1.5.0

- Reset with Ctrl + Shift + the selected counting key. Counting uses the unmodified key; other modifier combinations pass through.
- Turn counting on/off from the panel; preserve the total and preference across restarts.
- Save an optional goal and show a 1.5-second notification on upward crossings.
- Refresh the preview with a generated illustration of the final UI; retain the real panel capture.


## 1.4.0

First distributable Counter package, following the local prototype:

- Rebrand the unpublished prototype as Counter, with azkar, repetitions and tally counting in its description.
- Bundle the backend and use a singleton service for runtime key registration.
- Remove permanent Hyprland configuration edits and external executable requirements.
- Release bindings safely on native disable/removal, including teardown after directory deletion.
- Preserve state across updates, monitor changes, reloads and reinstalls.
- Add isolated failure, concurrency, Qt key-mapping and desktop lifecycle tests.
