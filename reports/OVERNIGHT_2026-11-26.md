# Overnight iteration — 2026-11-26

This is an incremental acceptance report, not acceptance of all reported issues or all Control Panel applets. Baseline: the local Windows 95 OSR2.5 installation with IE4 Desktop Update, 800×600 guest pixels. Wider-layout checks also run at 1280×720.

## Implemented

- Selection-aware File command profiles separated from menu painting: empty namespace, drive, protected system folder, file, folder, shortcut, mixed selection and read-only model cases. Default Open is bold. This does not cover every shell extension or file association verb.
- Explorer information panel uses original installed HTT/REGINST text and monochrome Verdana glyphs staged privately. Selection updates name, type and description; drive statistics read the actual filesystem. Multi-selection follows the observed template name-list limit. Responsive column sizing follows the original percentage layout.
- Safe Linux Type=Link shortcuts for namespace objects, files and folders, unique native-style duplicate names, hidden storage extension, target icon and original arrow overlay. Opening, copying, renaming, moving, recycling and restoring links preserve their target. Broken targets and cycles are rejected. These are not Windows binary `.lnk` files and are not symlinks.
- Same-window navigation with independent Back/Forward snapshots and explicit separate-window support. Saved browsing policy defaults to same-window; its settings UI is still pending.
- Edit availability is now a separate context model. Added real-file Cut/Copy/Paste/Paste Shortcut/Select All/Invert workflows and screenshots. Native row origins, disabled embossing and the second-word Shortcut mnemonic were corrected. Undo remains disabled: a safe reversible operation journal is not implemented.
- Display tray-icon persistence now has a shell-restart rendered regression case in addition to default, Apply and Cancel coverage. Existing saved true values are respected; the default remains false.
- Removed the incorrect direct Display Properties entry from Start → Settings. Display remains in Control Panel. Unimplemented native Settings entries remain hidden rather than launching unrelated actions. This is a deliberately incomplete submenu, not full historical parity.
- Asset staging retains all 42 original `.cur` variants with native dimensions/hotspots and both `.ani` files, with source hashes. A complete working Mouse Properties applet and animation support are still pending.

## Native comparison evidence

Private local captures and comparison JSON are kept under `private/screenshots`. They are intentionally excluded from Git.

The selection suite compares these original regions:

| Region/state | Reference rectangle | Result |
|---|---|---|
| Selected Control Panel name/type | 20,218,150,30 | zero differing pixels at 800×600 and 1280×720 |
| Selected Control Panel icon and label | 245,245,70,60 | zero differing pixels, with percentage-column origin at 1280 |
| Complete Control Panel information block | 20,218,212,170 | zero differing pixels at 800×600 |
| Edit Cut through Invert Selection rows, empty clipboard/no selection | 50,82,150,110 | zero differing pixels at both acceptance resolutions |

These are regional claims. The complete Explorer screen is not identical: device inventory, window contents, some toolbar states and unimplemented features still differ. The Edit reference has a prior native Undo operation, so its Undo row is deliberately excluded from the matching region. The wider information column wraps differently; an 800px full-paragraph screenshot is not used to falsely enforce a narrow wrap at 1280px.

Review captures: `private/screenshots/overnight-20261126/selection-side-by-side.png` (Win95LX left, original right), `native-edit-empty.png`, and `win95lx-edit-measured.png`. Selection reports include source/reference hashes and exact rectangles.

## Defects discovered and corrected

1. Text shortcuts used the Notepad application icon rather than the native text-document association; `.txt` now uses shell32 group 152 and `.ini` group 151.
2. A 16px fallback icon could overpaint an already drawn 32px icon.
3. Selected native icons lacked the opaque-pixel checkerboard treatment and focus-label frame.
4. Verdana advances initially used antialiased metrics rather than native monochrome advances, changing wrapping.
5. Explorer navigation created a separate Control Panel window rather than following the configured same-window policy.
6. Edit text origins were one pixel high/right; disabled mnemonic underlines lacked their highlighted embossing; Paste Shortcut underlined the first S rather than the second-word S.
7. A broad dialog edit introduced an undefined button coordinate in existing overwrite/not-found notices. The rendered file-dialog suite caught it; the original coordinate was restored and the suite rerun.
8. A wide-layout test incorrectly expected the narrow information-column line breaks. Its full-paragraph pixel assertion is now limited to the resolution for which a native reference exists.

## Validation and performance

73 unit tests pass. The GUI suite includes menu seams, sprint control workflows, full My Computer chrome regions, independent folder transfers, shared file dialogs, Display Settings, shortcut workflows, selection information and Edit workflows at 800×600 and 1280×720. Guest validation and release status are recorded below once the run finishes. A missing private screenshot fixture interrupted the first guest run; this was a fixture-transfer defect, not a passing run.

The added `dev/measure_shell.py` measures Cairo CPU render time and explicitly excludes event input, X presentation, compositor and viewer delay. Initial host 1280×720 medians/p95 over 100 frames: desktop 14.69/15.51 ms, computer 16.22/17.00 ms, selected information panel 17.40/18.12 ms. These are a baseline, not a demonstrated speedup, and the exact source hash is recorded in the private JSON.

The development guest reports 1.762s kernel + 1.399s userspace = 3.162s, with graphical.target at 1.391s userspace. This excludes firmware and does not establish visible-desktop readiness. No speculative service removals were made.

## Research and recovery

Both visible VMs have `overnight-before-20261125` snapshots. An isolated native probe allows research without fighting the user's visible reference for input. All four native Mouse Properties tabs and the actual Folder Options Custom Settings dialog were captured.

A separate pre-IE4 clone resumed the original licensed Setup, copied files and reached its boot preparation stage. It hit the original boot-CD emulation write-protection problem for DRVSPACE.BAT. A private writable floppy did not fix the emulated A: destination; the clone advanced past that batch-file copy and is now stopped with a `classic-files-copied` checkpoint. The classic desktop has not booted or been accepted. The visible IE4 reference and its disk were not replaced. Remaining work: repair boot paths/partition state on the offline clone, finish Setup, verify pre-IE4 versions and capture a clean desktop. Merely disabling Web View would not meet this requirement.

Original installed HTT and REGINST resources supplied the description text and layout rules; decompilation was unnecessary. No unverified leaked source was used. Original fonts, media, registry files and vendor artwork remain private.

DOS options, integration contract and measurement plan are in `docs/DOS_PROMPT_RESEARCH.md`. Recommendation: prototype DOSEMU2/FDPP against DOSBox-X; do not replace Bash with PowerShell based on aliases. Research only; no DOS runtime or shell changes were installed.

## Remaining work, in priority order

1. Build and validate Mouse Properties against the captured four native tabs; apply actual device/session settings, persist them, and test Apply/Cancel/restart. Stage assets alone do not make the applet functional.
2. Implement safe Explorer Undo and complete namespace Edit semantics; capture selected files/folders and clipboard states from the original.
3. Add the working Folder Options UI and remaining Start Settings entries as their functionality becomes available.
4. Finish the pre-IE4 reference boot and capture classic Explorer/control baselines.
5. Extend Control Panel applets individually with actual input effects and persistence. No additional empty applets were exposed as completed work.
6. Remaining visual/behavioral gaps include information-panel scrollbar thumb/page interactions, enabled Forward artwork, complete drive statistics formatting, full file-association verbs and printer/recycle namespaces.

## Release verification

The development guest completed `make test check-ui` successfully: 73 unit tests, 24 sprint scenarios, 23 My Computer reference-region comparisons and 7 selection/Edit region comparisons, plus menu seam, folder-transfer, file-dialog and Display workflows at both resolutions. The reference-region counts are region/state assertions, not a claim of that many independent tests. The last one-pixel shortcut-button hit-target correction receives a separate two-resolution selection-suite rerun before activation.

Guest CPU render baseline (1280×720, 100 frames/state): desktop median 16.23 ms / p95 21.62 ms; computer 17.86 / 18.59 ms; selected panel 19.11 / 20.08 ms. These figures were collected during validation activity and are not an isolated-machine benchmark or a demonstrated optimization.

The release is activated only after those checks. See Git history for the commit and verified main-branch push; copyrighted evidence remains local.
