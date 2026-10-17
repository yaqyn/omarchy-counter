# Verification record

Local release-candidate checks performed on 2026-10-17. This records evidence, not a promise of compatibility with every Omarchy installation.

## Tested environment

| Component | Version |
| --- | --- |
| Omarchy | 4.0.4-1 |
| Hyprland | 0.56.2, Lua configuration |
| Quickshell | 0.3.1 |
| Qt | 6.11.2 |
| Python | 3.11, 3.14 and 3.15; 3.13 additionally configured in CI |

## Automated local checks

- Python: 22 tests, including 200 concurrent increment processes, state persistence, non-UTF-8/corrupt data, count limits, simulated disk-full failure, actual permission denial, key conflicts, timeout, rollback and token-scoped removal.
- Qt: six key-capture test functions, plus Qt's setup/cleanup cases. Uses actual Qt enums, with printable, function, keypad, media, modifier and non-Latin mappings.
- Omarchy: root manifest accepted by `omarchy plugin validate`.
- Ruff: lint and formatting checks.
- Release: deterministic archive, checksum and validation of the extracted plugin.

## Isolated desktop integration

`tests/desktop.py --run --keep` starts a nested Hyprland compositor and an Omarchy shell on a private D-Bus session, with temporary HOME, config, state and runtime directories. It never installs into the real user's configuration.

The test exercises the real native `omarchy plugin add`, `update`, `disable`, `enable` and `remove` commands. Git rewrites the test HTTPS URL to a temporary local source repository, so this validates installation mechanics without making a network request or publishing anything. Public GitHub connectivity remains a post-publication check.

Twelve scenarios passed:

1. Fresh native installation registers exactly one consuming, nonrepeating F1 binding.
2. Saved state and the actual modifier-ignoring binding are verified.
3. Two outputs share one binding and saved total.
4. Changing and reselecting the same key leaves one binding.
5. Compositor reload restores the selected key.
6. Native Git update preserves total and key.
7. Killing the helper triggers recovery without duplicate registration.
8. Ten native disable/enable cycles release and restore the key.
9. The native panel loads without QML type or binding errors.
10. Removing an output preserves the singleton service.
11. Restarting the entire nested compositor and shell preserves total and key.
12. Native removal releases the key even after directory deletion, preserving data.

These use virtual outputs and an installed software stack on one host. Synthetic key injection into an inactive nested compositor is not treated as evidence of physical-key behavior.

## Live interaction checks

The local prototype's selected-key, Apply, cancellation and feedback paths were checked in the live desktop through screenshots and keyboard navigation. The final package was rendered in the nested desktop, then installed in the live desktop with its saved count and key preserved, one active binding, healthy service status and no Hyprland configuration errors. Ordinary counting remains an active-session shortcut rather than a kernel-level keyboard remap.

## Checks that still require another environment

- A physical machine reboot and suspend/resume cycle.
- Real external-monitor hotplug and mixed-DPI hardware.
- Physical laptop Fn/media keys and multiple keyboard models.
- End-to-end typing/capture under non-Latin layouts; the key-name mapping itself has automated coverage.
- Older/newer Omarchy, Hyprland and Quickshell versions beyond the tested combination.
- Actual GitHub Actions results and public Git installation after repository publication.

Record these as unverified until performed. Do not describe the plugin as universally tested or make an unlimited-production-readiness claim.
