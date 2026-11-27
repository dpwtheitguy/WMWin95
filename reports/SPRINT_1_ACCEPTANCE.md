# Sprint 1 acceptance — 2026-11-25

Eight of eight revised sprint assignments have passing evidence for the controls and behaviors described below. This accepts the documented increments, not complete Explorer/WordPad compatibility or whole-screen pixel identity. The revised scope is in WIN95LX_PLAN.md; it prioritizes the user's reported defects over the earlier proposed cosmetic sprint.

## Validation

- 47 unit tests passed, zero failures (`python3 -m unittest discover -s tests -q`).
- 12 distinct new interaction scenarios passed at 800×600 and 1280×720 on the host and inside the KVM Linux guest: 48 scenario executions, zero failures. Additional runner verification is repetition, not additional coverage.
- 12 native pixel regions per run, 48 comparisons total, zero differing pixels in these specific regions/states.
- Existing GUI regression suites passed: menu seams once; independent folder windows, common file dialogs, and reference UI each at both resolutions (seven suite executions). These suite counts are separate from the 12 scenarios.
- First host suite invocation encountered a temporary Python-wrapper import-path problem; rerunning with `PYTHONPATH=dev` passed. First guest invocation used an incorrect extracted Xvfb directory; correcting PATH passed. A new runner also initially inherited the host Wayland backend despite starting Xvfb, causing three visual scenarios per resolution to fail; the runner now forces `GDK_BACKEND=x11`. Failed artifacts remain in `repeatable-run`. These setup failures are preserved, not counted as product passes.
- Checks run in isolated homes with disposable fixture files. Source and assets identities, native capture hashes, rectangles, scenario durations and render times are recorded in each JSON report.

Evidence root: [private/screenshots/sprint-20261125](../private/screenshots/sprint-20261125). Machine reports: [host 800](../private/screenshots/sprint-20261125/host-800/report.json), [host 1280](../private/screenshots/sprint-20261125/host-1280/report.json), [guest 800](../private/screenshots/sprint-20261125/guest-800/report.json), [guest 1280](../private/screenshots/sprint-20261125/guest-1280/report.json).

## Accepted increments

| Assignment | Original behavior and implemented increment | Evidence and discovery |
| --- | --- | --- |
| S1-001 | Folder targets accept near misses around icon and label; dragged items cannot become their own destination. Shared geometry matches 31 observed native target samples and a four-pixel initiation threshold. | Three new geometry unit tests; folder-window suite covers independent state and bidirectional transfers; sprint tests exercise normal pointer handlers, redraw the ghost before release, then drop into Recycle Bin. Self-target exclusion prevents rearrangement from attempting a filesystem move. |
| S1-002 | Explorer caption uses measured native text origin and baseline, clips to the caption, and reproduces the tested capital-letter raster. | Native title text region 140×18 has zero differing pixels; fixes the reported high text baseline. |
| S1-003 | File popup begins at measured menu-bar boundary, with native label gutter. Close mnemonic raster matches. Word Wrap has a native checkmark instead of a GTK square checkbox and toggles editor state. | Popup anchor/gutter assertions; Close 26×13 and marker 7×7 exact comparisons; seam suite and menu keyboard/pointer regressions. Removed the extra File-menu Alt+F4 label present only in the native system menu. |
| S1-004 | Native WordPad toolbar button geometry, disabled artwork, font/size fields, ruler and editor edges. Shared bevel/band drawing prevents duplicate white outlines. | Complete 592×30 file and format bands, 592×23 ruler, editor top/left edges and New button compare exactly. Discovery found GTK default edge colors and full-width band highlights; corrected both. |
| S1-005 | Palette selection changes the complete rendered shell and accessory/dialog controls. Checkbox updates before Apply; Apply persists; Cancel discards pending changes; tray icon follows saved preference. | Gradient samples produce 16 colors, 246 colors, 4106 RGB565 colors and 4107 true-color colors. Notepad and its popup stay within 16 colors. Found Cairo memoryview was being interpreted as separate channel values; fixed pixel-word decoding. Checkbox 13×13 is exact. |
| S1-006 | Browse selects real guest images, previews and persists placement, handles invalid files, and cancels without saving. Native named patterns and custom 8×8 editing persist and draw. | Browse/invalid-image/Cancel cases; chooser, cell-click and custom Save/Apply cases. Discovery found a cursor baked into the captured Pattern caption; recaptured with pointer outside the artwork. Clean caption and command buttons now compare exactly. |
| S1-007 | Successful Notepad and WordPad opens/saves update a shared bounded recent list. Start > Documents includes My Documents, deduplicates, hides missing files, and reopens documents. | Two history unit tests; successful open/save and actual Start-menu reopen scenario; persistent JSON with locking. Fifteen-item cap; alphabetic displayed list. |
| S1-008 | Copy into the same folder creates “Copy of …”, then “Copy (2) of …”, matching direct native experiments. Errors use the shared native prompt. Bin supports trash, collision-safe restore and permanent-delete confirmation. | File-operation/trash unit tests, clipboard copies, pointer-driven trash/restore round trip, and native error-dialog scenario. Selected bin item now opens properties rather than restoring immediately. |

## Screenshot and pixel evidence

Original reference: Windows 95 OSR 2.5 with IE4 Desktop Update, 800×600, classic system colors and small fonts. Original captures and private extracted artwork remain outside Git. Implementation comparisons run at both viewport sizes; each JSON lists the precise reference rectangle and implementation origin. Artwork-based controls also have interactive tests; an exact static frame alone does not establish functionality.

- [WordPad before](../private/screenshots/sprint-20261125/before/wordpad-controls.png) and [after](../private/screenshots/sprint-20261125/guest-800/wordpad-after.png).
- [Pattern caption before](../private/screenshots/sprint-20261125/before/pattern-caption.png) and [after](../private/screenshots/sprint-20261125/guest-800/pattern-chooser-after.png).
- [Broken 16-color rendering before](../private/screenshots/sprint-20261125/before/palette-16.png) and [after](../private/screenshots/sprint-20261125/guest-800/palette-0-after.png).
- [Explorer File popup after](../private/screenshots/sprint-20261125/guest-800/explorer-file-menu-after.png), [caption after](../private/screenshots/sprint-20261125/guest-800/explorer-title-after.png), [Word Wrap after](../private/screenshots/sprint-20261125/guest-800/word-wrap-checked-after.png).

Before files are discovery-stage captures from this work session, not a claimed clean historical release baseline. The live pre-deployment WordPad desktop is also preserved in `before/wordpad-live.png`. Exact comparisons establish the named regions only; full desktop images differ in content and window positions.

## Performance

Measured render-only median milliseconds (PNG encoding excluded): host 800×600 9.02; host 1280×720 16.73; guest 800×600 9.69; guest 1280×720 17.48. These are diagnostic samples during scenario execution, not frame-rate guarantees. There is no equivalent clean baseline measurement, so no speedup is claimed. End-to-end boot/reboot timing remains Sprint 2 work.

## Remaining discrepancies and blockers

No blocker prevented these eight scoped increments. Remaining work is explicit:

- Explorer File has reduced contents, including direct New Folder rather than the full native New submenu. Exact measured gutter and Close text do not establish all menu contents or all states.
- WordPad document font metrics still depend on Linux fonts; print/preview, alignment and bullets need fuller implementation. Ruler extension beyond the default native capture needs additional native evidence.
- Palette modes constrain rendered colors; the X11 server remains at its configured 24-bit depth. This is not hardware indexed-color switching.
- Recycle Bin uses home freedesktop Trash; cross-filesystem trash needs further work. Its properties prompt is not the complete native property sheet.
- General management of arbitrary X11 app windows remains outside this sprint. Desktop boot branding, complete sound mappings, every resolution and fractional viewer scale are not accepted by these tests.
- UI tests use deterministic pointer/keyboard handlers and Xvfb windows. Human testing of host mouse capture in the visible QEMU viewers remains useful.

## Repeatable checks and next sprint

`make test` runs units. `make check-ui` includes `make check-sprint-controls`, which saves screenshots and JSON for both resolutions through `dev/run_sprint_checks.py`. Requires Python GTK/Cairo and Xvfb; isolated extracted runtimes were used where host packages were missing. Agent instructions require pointer-free artwork, native region/state measurements, boundary discovery, guest checks and honest evidence scope.

Sprint 2: complete native Explorer menus and property sheets; extend WordPad behavior/font metrics; cross-volume Trash and file-operation dialogs; fractional scale/input tests; general X11 window management; startup sound and measured boot/reboot work.

## Interactive comparison

Both visible QEMU windows are running simultaneously. The Linux KVM guest has the staged and validated release activated. The original Windows 95 reference uses TCG with legacy instruction timing. Both show empty WordPad windows at 600×411, positioned at desktop origin for comparison. [Unscaled side-by-side screenshot](../private/screenshots/sprint-20261125/side-by-side.png): original Windows 95 left, Win95LX right. These are contemporaneous framebuffer captures joined without resampling; host viewer positions can differ. Visible remaining differences include WordPad menu contents and status-bar details, and desktop/taskbar contents.

The corrected repeatable X11 runner passed all 24 scenario executions (12 at each resolution); these repeat the coverage above. Both launchers now default to native-size viewers with zoom-to-fit disabled. Matching standard desktop resolution is 800×600; the Linux saved preference was checked separately from the viewer geometry.

## Explorer follow-up

The subsequent whole-File-menu comparison exposed the limits of the original Close-only acceptance. My Computer now has a complete selection-dependent namespace File profile and additional IE4 bands. See [the Explorer iteration report](EXPLORER_PARITY_2026-11-25.md) for complete-menu measurements, fifty-observation disposition, broader regression results, and remaining work. The earlier eight accepted increments remain scoped to their original recorded regions and behaviors.

## November 26 follow-up: Control Panel controls and layout

The Sounds closed scheme field now has an independently measured zero-difference
310×25 border/padding/text comparison at 800×600 and 1280×720, with long-name
clipping regression. See [Sounds alignment evidence](SOUNDS_ALIGNMENT_2026-11-26.md).
The unit suite passed 243 tests before the subsequent shared-button integration;
that count is a checkpoint, not acceptance of later changes.

User testing then exposed Control Panel namespace icons overflowing a single row
and drawing outside the restored window. The source correction now provides responsive
view layout, overflow scrolling, content clipping and clipped hit targets.
Isolated forced-X11 tests passed 76 captured states across two resolutions,
including description wrapping, resize, movement and each implemented view mode.
See [namespace layout evidence](CONTROL_PANEL_NAMESPACE_LAYOUT_2026-11-26.md).
The regression is included in `make check-ui`; combined guest validation passed (`make test check-ui`, exit 0). No corrected release has been activated
in the user's manual-test VM during this work.

### Combined guest acceptance checkpoint

On November 26, the isolated developer Xvfb run in
`/home/developer/win95lx-combined-qa-20261126` completed `make test check-ui`
with exit status 0: **254 unit tests passed**, followed by all configured rendered
and interaction checks at 800×600 and 1280×720. Fonts additionally has its own
1280×800 evidence. Log: `private/combined-ui-20261126.log`. This includes the new
namespace layout regression, 88 native button cases per resolution, Fonts,
Multimedia, volume popup, Sounds, property sheets, pointer schemes, Mouse, menu
seams, sprint regressions, Explorer selection details, independent folder
transfers, file dialogs and reference UI regions. Named pixel regions retain
their individual reports; passing the suite does not establish whole-desktop
pixel identity or completion of all Control Panel capabilities.

The first combined attempt found the layout harness's moving Git HEAD dependency.
A later attempt waited on an error dialog because the isolated test checkout
lacked its original custom CUR fixture. The historical comparison dependency
was removed, the required fixture was staged, and Mouse's check now validates
its presence before any interactive window opens. The complete corrected suite
then passed. These were test-harness defects, not concealed passing product
results. The user's visible session was neither driven nor restarted.

Fresh independent sound-library staging also verified all 286 WAV files and
semantically identical catalog content. The full asset preparation pipeline now
includes that library explicitly, rather than depending on a prior manual stage.

Remaining Control Panel work includes unregistered Network service/permission
acceptance, additional applets, detailed native-state comparisons, and the
separate window-stacking architecture limitations. Accessibility input backends
and a coalesced volume-update prototype are separate ongoing work, excluded
from this acceptance checkpoint.


## November27 lunch follow-up

Visible guest refreshed to `59dbd3dd304c5c52`: supported Printers namespace and
queue management, My Computer/Control Panel rearrangement, corrected shortcut
overlay, and selected-label clipping correction. Full validation, native
comparison limits,355-unit-test run with two skips, live captures and checkpoints
are recorded in [delivery evidence](LUNCH_DELIVERY_2026-11-27.md). This does not
accept the Add Printer wizard, all Explorer view/menu parity, Desktop Themes or
the Easter eggs.


## November27 namespace and shortcut fidelity

Current visible release `70026f549a5d4525` adds original virtual-object drag/drop
shortcut offers, direct logical-secondary drop context, preserved grab offsets
and corrected32px desktop shortcut labels/selection/profile artwork. Actual
non-admin VM creation was verified.379 guest tests ran with one opt-in skip;
rendered and interaction regression groups completed with failures and
corrections preserved in the evidence. [Consolidated delivery and limits](NAMESPACE_SHORTCUT_FIDELITY_2026-11-27.md),
[native behavior](NAMESPACE_CROSSDROP_2026-11-27.md), and
[shortcut visuals](SHORTCUT_VISUAL_AUDIT_2026-11-27.md) separate measured regions
from whole-OS claims and describe Classic/IE4/configured-Plus coverage.
