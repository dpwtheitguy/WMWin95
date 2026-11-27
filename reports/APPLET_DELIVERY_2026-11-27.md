# Applet delivery — 27 November 2026

Visible guest release: `ecf12b033a5104fe`. Control Panel now has **12 usable
entries**, including Desktop Themes. Add Printer is a working wizard inside
Printers, not a thirteenth Control Panel applet. This is acceptance of the
subsets below, not every original applet, printer feature or theme component.

Recovery checkpoints were verified: `before-themes-printer-20261127` and
`applets-printer-themes-ready-20261127`. All three prepared Windows95C reference
configurations and Win95LX were checked running after the work. Classic, IE4 and
configured Plus are configurations of that release; RTM/OSR1 are not verified.
Original media, native derivatives, captures, keys and VM disks stay private.

## Delivered behavior

| Entry | Working subset | Remaining limitations |
| --- | --- | --- |
| Control Panel → Desktop Themes | All twelve Plus choices apply wallpaper, pointers and sounds independently; preview, pending selection, Apply, Cancel, reopen, rollback and preservation of unrelated settings. Caption icon/Alt+Space, Move/Escape, Minimize/taskbar restore and Close work. Palette changes refresh the selected representation without discarding edits. | Selected-photo preview conversion/resampling is not pixel accepted. Icons, colors, fonts/metrics, screen savers, combined preview and custom-theme management remain disabled with F1 reasons. Maximize is natively disabled for this fixed-size window. |
| Control Panel → Printers → Add Printer | Native-sized five-page wizard, actual installed-driver discovery, validated addresses, create-only installation, readback, unshared ready queues, human names and refreshed folder. Optional test pages use the normal printing backend. | Full original page-content parity, physical hardware, Windows driver compatibility, full port UI and queue configuration/removal administration are not accepted. |

No desktop elevation/password prompt was introduced. The create-only guest
service authorizes the desktop UID through its Unix socket and cannot mutate a
user-chosen existing queue or grant general administration. It journals ownership
before creation and retains uncertain/partial queues with a truthful error.
See `docs/GUEST_PRIVILEGES.md` and the two applet reports for details.

## Validation and exact scope

- **426 unit tests**, one opt-in skip, passed in the final-source guest rerun.
  Printer and Theme model suites contain22 and25 tests respectively. The opt-in
  skip is not counted as a pass.
- A complete `make test check-ui` run passed on the preceding applet revision
  (425 units then). After final caption/palette/artwork changes, all426 units
  and all four Theme palette/viewport runs passed. The affected Printers shell
  checks also passed at both sizes after final label/cached-caption changes.
  These are retained as separate logs, not misrepresented as one final-source
  uninterrupted all-target run.
- Printer physical-input UAT has seven grouped scenarios at800×600 and1280×720,
  including a deep inventory, near misses, cancellation, failed discovery and
  duplicate Finish input. Three independently measured native command-button
  regions have zero differences at each size. Dynamic driver/endpoint contents
  are adapted, not claimed identical to native Windows hardware lists.
- Eight real private CUPS/IPP scenarios passed: driver discovery, negotiated PPD,
  ready queue/readback, journal, actual PostScript→PWG test-page delivery,
  duplicate names, unreachable endpoint, peer rejection and unavailable service
  are covered by the grouped checks in the backend report. Normal guest queues
  and daemon default were unchanged; all owned fixture processes exited.
- Theme physical-input runs cover800×600 and1280×720, each in256-color and
  TrueColor. Each includes an actual-provider twelve-theme apply/reopen sweep,
  real pointer/keyboard controls, F1, pending edits, conflicting open Properties
  windows, rollback and exact preference-file restoration. The twelve-theme
  sweep uses integration calls, not twelve independent physical-input replays.
- Actual GDK framebuffer comparisons have zero differences for the full Current
  preview393×333, focused Theme combo202×21, eight disabled checked boxes and
  three enabled checked boxes. The native reference is800×600; the larger
  implementation run verifies the same anchored guest-pixel control sizes.
  This does not accept an entire sheet or arbitrary DPI/desktop appearance.
- The selected Nature diagnostic differs68,514/130,869 pixels and its native
  capture includes a pointer in Window Text. It is explicitly rejected as a
  clean full-preview acceptance baseline. The count is diagnostic, not excused
  as harmless noise. TrueColor conversion and native Tile/Center/Stretch across
  modern resolutions remain separate work.

Raw native bitmap palettes and separately named QEMU VGA6 product derivatives
are preserved with hashes/provenance. A logical source image is not the physical
framebuffer. No reference screenshot was transformed into agreement with ours.
The low-color fast path is scene-dependent; these checks do not establish global
palette ownership with multiple colored windows.

## Actual non-admin visible-session proof

Root used QMP pointer/keyboard input in the normal `win95` desktop. Add Printer
created an owned IPP emulator queue through the deployed production service.
Requested attributes and the root-only journal agreed on endpoint, human name,
ready phase, accepting state and unshared state. A second run captured the full
entered name, UI Proof Printer, before Finish and verified the exact folder name.
Only the two exact owned queues were removed by reviewed maintenance after
matching identity/endpoint/journal and confirming no pending jobs. Original queue
inventory/default were restored, and the owned emulator was stopped.

Desktop Themes was opened through Run and its actual Control Panel icon. Root
selected Nature with keyboard input, chose Apply, inspected the changed desktop,
verified actual saved Mouse/Sounds scheme values and preservation of unrelated Mouse/
Sounds fields, exercised Minimize/taskbar restore, system menu and F1, and
observed Nature retained after closing/reopening. Test changes were then removed
by restoring exact original bytes/existence of four known preference files;
display/resolution stayed unchanged. The final session was refreshed and left
at Control Panel with twelve entries for human testing.

Some early QMP captures were transitional: acknowledgement does not mean the
guest consumed every queued key. The first fast name sequence advanced with a
shorter received name; the second paced run observed the complete field. A
reopen capture caught Run midway through typing; the settled capture confirms
the complete command and correctly reopened applet. Rejected/transitional
captures and packaging-fixture failures remain in private evidence. A Python
in-memory transfer crashed before syncing new fixtures; checksum-based rsync
replaced it, missing-reference failures were corrected, and final checks passed.

## Genuine discoveries corrected

Wallpaper persistence without live image-cache propagation; stale Mouse/Sounds
controllers overwriting newer settings; pending Properties conflicts; newly
saved custom sound schemes lost on later Theme Apply; wrong focused-field and
disabled-checkbox geometry; preview border erased by manual pointer cleanup;
wrong interpretation of logical versus physical VGA colors; dead/overlapping
Minimize hit targets and rapid canceled-press focus loss; stale palette source
selection; invisible initial printer manufacturer/model; phantom wizard Close
hit; missing CUPS accepting-state attributes; post-create journal failures losing
partial identity; ignored per-user-default flag; common USB serial URI rejection;
Add Printer's old disabled-gray label; initial queue captions without cached
human names. Each report separates product defects from fixture assumptions.

Performance: owned guest RPC discovery~1.93s and creation~1.55s in the recorded
fixture, off the GTK thread. Theme construction/first draw were milliseconds in
isolated host samples. Physical Apply measurements include the harness's
intentional150ms settling interval and are **not** product latency evidence.
No boot-speed or sustained end-to-end performance improvement is claimed.

## Evidence and next work

- `private/applets-followup-20261127/`: root logs, live screenshots, state and
  restoration proofs. `final-control-panel-ready.png` is the final handoff.
- `reports/PRINTER_WIZARD_NEXT_2026-11-27.md`: original geometry, before/after deep
  inventory failure, transaction/security/printing tests and remaining capability.
- `reports/DESKTOP_THEMES_2026-11-27.md`: native controls, palette/conversion
  investigation, physical tests, caption fixes and unavailable-feature inventory.
- `reports/EXPLORER_DEVELOPMENT_PLAN.md`, its JSON feature matrix, and
  `reports/CLASSIC_WINDOWS_GAMES_INVENTORY.md`: updated lessons and bounded status.
  No new game was built or installed in this iteration.

Next fidelity work: a clean selected-photo native baseline and exact preview
conversion/resampling; complete native theme component integration; printer
configuration/removal and real hardware; broader native window focus/stacking
and palette coordination. Existing Explorer/WM discrepancies remain open.
