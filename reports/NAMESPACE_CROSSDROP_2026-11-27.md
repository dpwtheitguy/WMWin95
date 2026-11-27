# Virtual-object drops: My Computer drive and Control Panel

The prepared Classic, IE4 Desktop Update and Plus reference configurations all offer to create a shortcut when a drive or Control Panel object is dropped onto the desktop or a real folder. The patch implements that behavior without moving the Linux root, Control Panel objects or source icons. It preserves manual namespace rearrangement and permits cross-target drops in Large/Small/List/Details with Auto Arrange enabled or disabled.

**Production source is frozen for root's guest regression/deployment. This report does not claim that root's final guest deployment has already passed.** Add/Remove remains paused/read-only; this delivery addresses the higher-priority drag/drop defect.

## Native coverage

All three references use the installed Windows95C/OSR2.5 family. They cover three configurations, not all original Windows95 releases. RTM/OSR1 are not claimed. The Plus reference also has IE4 UI components visible; it is not evidence for every plain-Plus configuration.

| Prepared configuration | C: → desktop | Control Panel → desktop | C: → real folder |
|---|---|---|---|
| Classic | native Yes/No shortcut prompt | same | same, in owned C:\W95DROP |
| IE4 | native Yes/No shortcut prompt | same | same, in actual C:\W95probe |
| Plus | native Yes/No shortcut prompt | same | same, in owned C:\W95DROP |

Source screenshots are in `private/screenshots/namespace-transfer-native-20261127/`; exact case filenames are recorded in `private/research/namespace-crossdrop-20261127/native-matrix.json`. Reference snapshots were taken before probing and restored afterward; temporary floppies were ejected. No live Linux desktop was reset, deployed or changed by this worker.

The logical default-left prompt reads: **You cannot move or copy this item to this location. Do you want to create a shortcut to the item instead?** It has Yes as default and No; focused Escape and Alt+F4 do not dismiss it. There is no active close operation. A clean Ctrl+Shift native IE4 probe still presented this fallback; requested modifiers and actual asynchronous key state were logged. Other modifier combinations are not exhaustively accepted.

The Plus reference had `SM_SWAPBUTTON=1`. A physical-left injection therefore produced the logical-right menu, rather than proving a default-left discrepancy. Subsequent probes normalized logical button choice and logged the swap state. Earlier modifier attempts with an existing inactive Yes/No modal were excluded; WM_CLOSE/Escape was not a valid cleanup mechanism. Cleanup was changed to explicit IDNO before an independent case.

Logical-right drop shows **Create Shortcut(s) Here**, separator, **Cancel**. The actual IE4 USER popup HWND is 183×49; `GetMenuItemRect` gives (3,3,177,17), (3,20,177,9), (3,29,177,17). It right-aligns to the drop point: dropping at (700,400) yields popup origin (517,400). Choosing its shortcut command creates the link directly without the left-drop fallback question.

## Measured prompt and assets

An independent HWND probe caught an important screenshot-crop defect: the actual prompt is **326×119**, at (240,249) in the measured 800×600 references. Yes is (84,82,75,23); No is (165,82,75,23). The original visually estimated 326×118 crop was one row short and its acceptance is superseded. Metadata: `private/reference-tools/namespace-prompt-metadata-v2-20261127/{classic-prompt,ie4-fresh-prompt}.json`.

Fresh IE4 recapture used explicit `RedrawWindow` with frame, children and synchronous repaint, then settling. It reproduced 39 navy pixels in the leftmost three caption-border columns which differ from Classic/Plus. This is an observed installed-reference difference, not a discarded redraw artifact. The current IE4 baseline uses the exact fresh IE4 frame; Classic and Plus alternatives are retained privately. The Plus crop currently borrows corroborated Classic geometry and is explicitly marked as lacking an independent Plus HWND measurement.

`tools/stage_namespace_drop_assets.py` validates HWND dimensions and both button rectangles before deriving the crop, preserves source and metadata hashes, stages profile-keyed prompt PNGs and the native right-menu reference, and creates the current IE4 alias. `tools/prepare_assets.py` invokes it. These assets do not enable any unfinished global profile switch.

The new prompt profile keeps the existing 374×119 menu Create Shortcut profile unchanged. Its command buttons use the shared measured renderer for normal, focused/default and pressed states; the original frame is not used to conceal a misaligned or static pressed button. Testing caught and fixed the generic centering formula's one-pixel hit error. A scoped GtkDialog subclass blocks the inherited DELETE_EVENT→response handler as well as the inactive close operation; merely returning True from a later delete-event callback was insufficient.

## Drag, persistence and failures

A separate namespace drag never invokes file transfer. Source windows activate when dragging their exposed icons; global hit filtering prevents an empty foreground client from passing clicks into covered namespace or desktop icons. Manual placement remains restricted by view/Auto Arrange policy, while external shortcut creation works in all four views. The drag threshold latches, Escape cancels before drop, and release coordinates determine the endpoint. The ghost paints globally above folder windows, rather than remaining clamped inside the source pane.

Native post-drop position was measured by exact 32px icon templates. Source image origin (352,258), source pointer (369,279) gives grab offset (17,21). Right creation at mouse (700,400) placed the new selected desktop image at (683,379); left fallback Yes at mouse (700,500) placed it at (683,479). Both selected-base/untouched-overlay comparisons have zero differing pixels. The pure origin helper preserves that grab offset for ghost and final desktop placement. The new desktop link is selected and desktop focus recorded. Broader internal caption/taskbar focus modeling remains a known separate issue; folder post-creation selection/activation has not received scalar native acceptance in this iteration.

Shortcuts remain safe Linux desktop **Type=Link** entries targeting the Win95LX namespace, rather than filesystem symlinks or moves. Folder shortcuts are resolved through bounded Link parsing for this operation; invalid, looping, nonfolder or out-of-root targets are rejected rather than silently redirecting to desktop background. New source selection and file positions are not changed when the user chooses No or cancels a right-drop menu.

The writer rejects missing/nonfolder destinations rather than creating stale directories, uses exclusive creation and unique names, and removes a newly created partial file on write failure. Batch cleanup only touches files created by that operation. Errors use concise native dialogs and do not expose raw POSIX paths. Native FindFirstFile metadata established that an empty-volume drive really produces **Shortcut to  (C).lnk**, with two spaces; the initially inferred one-space correction was reverted. Duplicate creation never overwrites existing content; the native duplicate counter itself was not established by the single-file enumeration and is not claimed as fully accepted.

## Actual tests and limits

- **29 namespace unit tests pass** in the host environment, including pure geometry/persistence, stale/nonfolder/partial-write failures, bounded folder-Link resolution, and an independent complete native 183×49 resting-menu comparison with zero differing pixels. Native popup hit rows and right alignment are compared to original API metadata.
- Actual XTest→GTK pointer runs at **800×600 and 1280×720 pass 14 behavior groups**: manual movement, endpoint/latch/Escape, all source modes with Auto Arrange on, No/Yes, global ghost, permission/loop failures, Control Panel links, distinct source context and right-drop cancellation/direct creation, real folder targets, activation/covered-hit blocking, persistence and client clipping. Evidence: `private/screenshots/namespace-crossdrop-accepted-{800,1280}-20261127/report.json`.
- Those pointer processes began before the last small pure-origin/desktop-selection/desktop-hit-clip edits; the final unit checks cover the helper and root is rerunning the complete final guest bundle. These prior passes are not substituted for root's final-copy regression.
- Final IE4 prompt checks at both sizes pass the complete **326×119 intrinsic frame with zero differing pixels**, actual Yes/No held/leave/reenter/outside-release, exact hit rectangles, Tab/default focus transfer, mnemonic/Enter and Escape/Alt+F4/DELETE_EVENT behavior: `private/screenshots/namespace-drop-prompt-accepted-{800,1280}-20261127/`. This is intrinsic window/control acceptance; whole-desktop placement, all menu selection states and every modifier combination are not claimed identical.
- Source hashes and unit log: `private/research/namespace-crossdrop-20261127/`. The existing Control Panel layout and root's full applet suite remain mandatory release gates.

The existing desktop label helper is now used with measured IE4 wrapping, focus/selection and 75px hit cells. Folder base Y−1 and selected checker phase1 are applied only to the current desktop IE4 profile; the shortcut arrow stays nominal and untinted. Expanded labels cannot leave interactive hit targets beneath the taskbar. Independent visual work reports 28 complete desktop-cell cases at both resolutions with zero differences; its own report controls that acceptance, not this drag/drop report.

Remaining discrepancies: folder post-drop focus/selection, every right-menu selected/default keyboard state, Ctrl-only/Shift-only/Alt matrix and further historic releases; broad internal caption/taskbar focus; profile-specific desktop/theme dispatch. No complete Explorer or whole-OS identity claim is made.
