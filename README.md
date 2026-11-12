# Win95LX

An evidence-driven Windows 95 desktop preservation project on maintained Linux. Original installation media and an original-shell VM are authoritative; Chicago95 is an audited candidate baseline. **The current shell is an experimental prototype. The comparison report records exact matches for individual assets and remaining full-screen differences.**

## Running milestone

The installed Xubuntu 24.04.5 guest runs a dedicated Win95LX X11 session with KVM and 800×600 as its default resolution. Control Panel → Display offers 20 verified modern resolutions and saves the selected mode for the next login. The desktop uses original Windows 95 bitmap fonts, icons and cursor. Start → Programs opens Notepad, WordPad, Calculator and Minesweeper. The guest boots with the animated Windows 95 OSR 2.5 splash.

The normal `win95` guest account has no administrator groups. The user explicitly authorized its automatic login. The separate `developer` account retains password-authenticated maintenance/sudo access and key-only SSH. All customization is inside the project VM; host desktop settings are unchanged.

Source, native resources, private data and virtual disks remain separate. Original Microsoft assets are kept in ignored `private/` and must never be redistributed. Upstream code/assets remain private pending component-level license review; no third-party theme code has been vendored into our source.

## Development commands

```sh
cd ~/Documents/Windows95
make check
make test
# Boot the installed project VM (requires host execution with KVM access):
python3 dev/start_xubuntu.py --window
python3 tools/qmp.py status
python3 tools/qmp.py click 44 27 --double
python3 tools/qmp.py key ctrl-esc
# Deploy source/assets to the developer account, with tests first:
python3 dev/deploy_preview.py --user developer
# Install the reviewed versioned release into the guest using authenticated sudo:
python3 dev/guest_admin.py dev/guest_install_session.sh
# Record implementation screenshots in a fresh private directory:
python3 dev/capture_shell.py --output private/screenshots/implementation/new-run
```

Do not start a second VM if one is already running. `start_xubuntu.py` boots the installed disk by default; `--boot-iso` explicitly starts the installer ISO. Guest SSH is forwarded only on `127.0.0.1:22295`. The Windows reference VM has no NIC.

The interactive preview uses the X11 QEMU viewer and the guest draws its cursor into the scaled desktop. If QEMU input capture prevents switching to another host app, use View → Grab Input to release it. See the [dialog migration list](docs/DIALOG_MIGRATION.md) for the remaining editor and desktop UI work.

Acquisition and comparison tools use Python's standard library plus system libarchive for archive extraction. The desktop runtime uses guest-installed GTK3, PyGObject and Pycairo. `make test` currently runs 18 tests. Original assets and credentials stay in the ignored private directory.

## Milestone and evidence

- Offline checkpoint: `desktop-milestone-002`; see `reports/linux-checkpoint.json`.
- Seven implementation captures and action/source manifests: `private/screenshots/implementation/run-004/`.
- Earlier `initial-shell` checkpoint caught an incomplete module deployment; it is a debugging artifact, **not** a known-good restore target.
- Core Windows CAB chain: 2,519 files, with 17,522 raw resource records.
- The original-media reference boots under Pentium TCG with `--icount 5`. Matching 800×600 captures and exact pixel counts are recorded in `reports/gui-comparison-2026-11-10.json`.
- Chicago95 pinned audit checkout: `5da19b8b1e2a886ebf6628403023d5fac3acc3ee`.

The shell draws its own desktop and Explorer windows and hosts built-in GTK accessories. Notepad saves plain text and WordPad saves plain text and basic RTF. Calculator implements Standard mode. Minesweeper supports Beginner, Intermediate and Expert. “Close Desktop” ends the session. The measured 148×339 top-level Start menu matches the original capture at 800×600. Whole-desktop and accessory comparisons still have open differences.

## Documentation

- [Development and recovery](docs/DEVELOPMENT.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Reference media and VM configuration](docs/REFERENCE.md)
- [Chicago95 audit](docs/CHICAGO95_AUDIT.md)
- [Original bitmap assets](docs/ASSETS.md)
- [Exact-pixel comparison](docs/VISUAL_REGRESSION.md)
- [Boot splash](docs/BOOT_THEME.md)

Host package/security changes and destructive operations require approval under the project brief. Approval for non-admin automatic login is limited to this development VM. Never weaken Linux security to reproduce historical Windows vulnerabilities.
