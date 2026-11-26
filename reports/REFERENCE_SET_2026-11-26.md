# Visible reference set — 2026-11-26

The intended set is three Windows 95 references and one Win95LX development VM. All four have interactive GTK windows; the temporary headless probe is stopped. This report is updated as the classic installation completes.

| Machine | Current status | Recovery checkpoints |
|---|---|---|
| Win95LX Development | Working desktop and Mouse/basic/Plus pointer iteration, 800×600 | `win95lx-basic-plus-pointers-working`; earlier `validated-ab30f60`; pending prior Large-pointer preview in `before-basic-plus-pointers-pending-large` |
| Original / IE4 reference | Existing working original Windows 95 with IE4 Desktop Update, 800×600 | `ie4-reference-working-20261126`, previous original checkpoints retained |
| Windows 95 + Plus reference | Plus! installed from local original media, rebooted successfully, 800×600; theme pointer preview available | `plus95-desktop-working`, `plus95-pointer-preview-working`, `plus95-realtime-pointer-preview` |
| Windows 95 Classic | First hard-disk restart reached final Windows configuration; display verification and accepted desktop checkpoint still pending | original installer disk retained; `before-harddisk-boot-repair`; repaired disk has `classic-dos-local-setup-ready`, `classic-setup-first-restart-ready` |

Snapshots are internal QEMU RAM/disk checkpoints, not standalone off-machine backups. A snapshot called working means that desktop was observed usable; it does not imply every prototype applet is complete.

## Launch and recovery

Use `python3 dev/start_reference_variant.py ie4`, `classic`, or `plus`. It reads the prepared private profile and opens a visible window. If that machine is already running it does not start a duplicate. Normal launches preserve current disk contents and do not automatically rewind to an old checkpoint. Recovery is explicit: `--restore-snapshot NAME` restores the checkpoint's disk and RAM state. `--dry-run` prints the planned command.

The original `dev/start_reference.py` also defaults to a visible window. Visible instruction-clock references use sleep pacing so animation comparisons are not made against an intentionally sped-up idle clock. IE4 and Plus were resumed from current RAM checkpoints when their pacing was changed; their open application state was preserved. No network adapter is enabled in these Windows reference machines.

## Classic boot repair

The early installer snapshot was started through a CD image that emulated a read-only A: drive. Setup tried to write its boot batch files there and failed. Swapping a writable floppy did not replace that emulated destination.

The repair preserves that original disk and checkpoints. A separate private copy was made from its early Setup state, the primary partition was marked active, DOS boot paths were supplied, and the original setup media was copied into C:\WIN95. The DOS CD driver was removed from this repair path after its ATAPI probe stalled. Setup then ran from the local C: source, completed file copying without those A: write errors, restarted from the hard disk, and reached its final Control Panel/Start Menu/Help configuration phase. Original vendor executable files were not patched.

The classic reference is not accepted until its desktop, lack of IE4 Desktop Update and comparison display mode are verified. Merely switching off Active Desktop in the IE4 installation does not create a pre-IE4 shell.

## Future product profiles

Explorer generation, Active Desktop and optional Plus customization are independent choices. See `docs/DESKTOP_PROFILES.md`. The currently implemented Plus support in Win95LX is its pointer library, not the complete Plus application pack.
