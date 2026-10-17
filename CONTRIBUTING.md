# Contributing

Keep the counter quiet and focused. Existing operations are counting, Reset, Undo and choosing one key. Changes should preserve keyboard focus during counting and use Omarchy's shared UI components.

Run the README's Python, Qt, manifest and Ruff checks. Changes to registration or removal also need `tests/desktop.py --run`. Tests must isolate state; never reset a developer's live counter. Add regression coverage for a behavior change, particularly ownership, interrupted writes, rollback and key capture.

Follow DESIGN.md for UI behavior. Include your tested Omarchy, Hyprland, Quickshell and Python versions in a pull request. Keep claims proportional to the verification actually performed.
