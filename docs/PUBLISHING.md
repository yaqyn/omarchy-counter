# Publishing checklist

Target repository: `https://github.com/yaqyn/omarchy-counter`.

The repository is public, with the cover, README and CI published. Counter is listed in the Omarchy marketplace. New commits require an exact-commit update request; pushing GitHub alone does not update the verified snapshot. See [verification evidence](VERIFICATION.md) for the published commit and public installation check.

## Before uploading

1. Run the README checks, including the isolated desktop test for lifecycle changes.
2. Verify the compatibility claims against `VERIFICATION.md`.
3. Validate the root manifest and inspect the preview for private desktop content.
4. Commit with the owner's identity, then run `python3 scripts/release.py`.
5. Extract the archive and validate its manifest. Rebuilding the same commit should produce the same checksum.

## Publish

1. Create the public GitHub repository and push the reviewed commit.
2. Check GitHub Actions for that exact commit; local success is not CI evidence.
3. Verify native installation from the public URL in an isolated desktop.
4. Publish a versioned release with the archive and SHA-256 checksum.
5. For this existing listing, use the marketplace “Verify or update a listed plugin” issue form. Select “Verify and publish a newer upstream commit” and include `yaqyn.counter`, the repository URL and the full current HEAD SHA. The earlier submission is issue #11984; do not create a duplicate initial submission.

Listing draft:

- Name: Counter
- ID: `yaqyn.counter`
- Author: Abdulrahman M. Yaqyn
- Category: Productivity
- Tags: Bar, Hyprland, Quickshell
- Suggested missing marketplace tag: Islamic
- Additional GitHub search topics: islamic, dhikr, azkar, minimalist, tally-counter
- Summary: A minimalist tally counter for azkar (Islamic remembrance), repetitions and everyday counting, with a reserved key and native controls.
- License: MIT
- Preview: `preview.png`, a generated illustration based on the final native panel. `assets/panel.png` remains the real screenshot.

Marketplace approval is a separate maintainer action. See the [publishing requirements](https://plugins.omarchy.org/publish.html) and [development reference](https://plugins.omarchy.org/develop.html).
