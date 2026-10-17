# Publishing checklist

Target repository: `https://github.com/yaqyn/omarchy-counter`.

The repository is public, with the cover, README and CI published. Formal versioned releases and Omarchy marketplace submission remain separate steps. See [verification evidence](VERIFICATION.md) for the published commit and public installation check.

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
5. Open the [Omarchy plugin submission form](https://plugins.omarchy.org/publish.html) using the repository link.

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
- Preview: `preview.png` (an exact copy of `assets/panel.png`, at the root for marketplace detection)

Marketplace approval is a separate maintainer action. See the [publishing requirements](https://plugins.omarchy.org/publish.html) and [development reference](https://plugins.omarchy.org/develop.html).
