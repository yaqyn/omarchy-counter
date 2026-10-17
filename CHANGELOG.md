# Changelog

## 1.4.0

First distributable package, following the local prototype:

- Bundle the backend and use a singleton service for runtime key registration.
- Remove permanent Hyprland configuration edits and external executable requirements.
- Release bindings safely on native disable/removal, including teardown after directory deletion.
- Preserve state across updates, monitor changes, reloads and reinstalls.
- Add isolated failure, concurrency, Qt key-mapping and desktop lifecycle tests.
