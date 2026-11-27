# Explorer development and reuse plan — 26 November 2026

This is an implementation audit and development plan, not acceptance of a complete Explorer. Control Panel work remains the primary task. We retained the current shell/window manager and did not fork Thunar, install another desktop, or change shared shell code. The machine-readable companion is `config/explorer-feature-matrix.json`: 52 feature observations and 25 reuse candidates, with status meanings and source paths.

## Decision after searching existing projects

Existing work is substantial. It would be wrong to say nobody has built this. Some projects provide native file-manager semantics, some provide classic appearance, and others implement Windows-compatible shell APIs. None was built or runtime-tested in this research pass; none is accepted here as a complete, pixel-identical Windows 95 Explorer replacement.

Recommended next investigation: use **GIO asynchronous filesystem/volume/monitor operations behind our existing controls**, and separately build a disposable evaluation of **Linux-explorer** before deciding whether to adapt backend code. Keep our historical UI contract independent of backend choice. Compare XFE and libfm for hard filesystem cases. Reusing their complete windows would require appearance and interaction work; replacing the desktop would be a separate architectural decision.

| Candidate | Verified scope and fit | Decision |
|---|---|---|
| [Linux-explorer](https://github.com/JackTulli/Linux-explorer) | Native C/Xlib Windows 2000 desktop, Explorer and applets; MIT code. Inspected actual Explorer/file-operation source. Tree expansion scans synchronously and caps a directory at 512 names. Own toolkit/WM differs from ours. | Isolated build evaluation; selective adaptation after tests. Microsoft artwork licensing remains separate. |
| [xclass applications](https://xclass.sourceforge.net/applications.html) | Historical native Win95/98-style C++ Xlib widgets plus Explorer application. Upstream warns applications can be unfinished. Toolkit LGPL stated; Explorer archive/license not inspected. | Valuable historical comparison; verify app license and behavior first. |
| [XFE](https://sourceforge.net/projects/xfe/) | Native Explorer/Commander file manager: tree, file panes, search, remote access. Project lists GPL2. | Evaluate operation behavior and responsiveness; not established pixel-identical. |
| [libfm](https://github.com/lxde/libfm), [libfm-qt](https://github.com/lxqt/libfm-qt), [PCManFM-Qt](https://github.com/lxqt/pcmanfm-qt) | Actual file-manager/library infrastructure. libfm COPYING is GPL2; libfm-qt LGPL2.1+ with component exceptions. Qt changes toolkit dependencies. | Backend feasibility spike with license/interface review. |
| [GIO](https://gnome.pages.gitlab.gnome.org/gtk/gio/overview.html) | GObject filesystem, mounts, monitors, asynchronous I/O and cancellation infrastructure. Fits existing GTK ecosystem. | First backend spike; native dialogs and operation semantics remain ours. |
| [QFileSystemModel](https://doc.qt.io/qt-6/qfilesystemmodel.html), [QtFM](https://github.com/rodlie/qtfm) | Qt model/file-manager alternatives; Qt model populates in a worker. QtFM repository verified but source/license not audited. | Alternative model reference, not immediate GTK integration. |
| [ReactOS Explorer](https://github.com/reactos/reactos/tree/master/base/shell/explorer), [Wine Explorer](https://github.com/wine-mirror/wine/tree/master/programs/explorer) | Free reimplementations using Win32 shell services. ReactOS Explorer also depends on browseui/shell32 components; Wine has /e,/root,/select parsing. | Behavior/architecture reference; not native Linux drop-ins. GPL/LGPL obligations apply to copied code. |
| [Chicago95](https://github.com/grassmunk/Chicago95), [SE98 theme](https://github.com/nestoris/se98-wm-theme), [Win98SE icons](https://github.com/nestoris/Win98SE) | GTK/window themes, icons and theme importing. Component licenses and artwork provenance differ. | Reuse fallback styling where appropriate; no Explorer semantic implementation supplied. |
| [IceWM](https://github.com/ice-wm/icewm), [FVWM95](https://fvwm95.sourceforge.net/) | Window managers/taskbars; FVWM95 companion Explorer is separate. | Reference only; current scope excludes replacing WM. |
| [Bevel95](https://github.com/madkmedia/Bevel95) | Rust classic shell targeting Windows 11/MSVC, GPL3-or-later own code. | Relevant visual methods; no verified Linux port here. |
| [Microsoft WinFile](https://github.com/microsoft/winfile) | Legitimate MIT historical File Manager source, Win32 target, archived March 2025. It is not Explorer source. | Historical algorithms/reference; porting requires work. |
| [98.css](https://github.com/jdan/98.css), [React95](https://github.com/React95/React95), [daedalOS](https://github.com/DustinBrett/daedalOS) | MIT web controls or browser desktop/VFS. | Design/reference only; browser architecture does not provide our native Linux integration. |
| [wieslawsoltes/Win95](https://github.com/wieslawsoltes/Win95) | Browser desktop/VFS; explicit code license not found in inspected root files. Font license is separate. | Reference only until grant verified. |
| [felixrieseberg/windows95](https://github.com/felixrieseberg/windows95) | Electron/v86 actual guest appliance. | Reference appliance, not a Linux Explorer implementation; guest licensing remains separate. |

Research date: 2026-11-26. Eighteen Git repository HEADs are recorded in `private/research/explorer-plan/repo-pins.json`; raw README/license/source downloads have hashes in `upstream-fetch.json` and `source-fetch.json`. Activity metadata is in `repos-initial.json` and `repos-second.json`. Activity is not proof of correctness. Text fetched from moving default branches is hashed separately; it must not be assumed to match a later HEAD without verifying. No leaked Microsoft source is needed or used.

## Audit: substantial implementation to retain

`src/win95lx/explorer/` already has namespaces, capability-driven File/Edit commands, clipboard, copy/move, same-folder copy names, trash, safe shortcuts, descriptions and browsing preferences. `shell/app.py`, `computer_view.py` and `model.py` supply folder windows and navigation. Preserve these instead of starting over.

There are real gaps: Run Explorer opens My Computer and cannot parse shell arguments; Programs lacks the distinct Windows Explorer entry; Explore currently opens an ordinary folder. There is no rendered folder tree, Small Icons/List/Details layout, operation Undo journal, complete Folder Options/File Types, complete drive/network inventory, full property sheets, or accepted asynchronous operation/progress/cancellation pipeline. Several toolbar operation buttons have drawing/hit regions without complete command dispatch. Existing per-window state/history is newer than some older reports; audit current code rather than treating old report blockers as current facts.

File shortcuts are safe `.desktop` Type=Link records with namespace/path metadata and target icons plus overlay. They are not symlinks and are not binary `.lnk` compatibility. Existing copy/move primitives protect against replacement races, but cross-filesystem moves, metadata, collisions and native naming rules still need a broader contract. Existing tests prove selected behaviors, not full Explorer fidelity.

## Historical baseline and native evidence

Original private media `private/cabsets/windows95/setupc.inf` creates **Windows Explorer at Programs root**, using `Explorer.exe /n,/e,%30%`. `shell.inf` defines separate Folder Open and Explore verbs. Original `tips.txt` documents Explorer switches, multiple selection and keyboard/drag modifiers. The [archived Microsoft command-line article](https://jeffpar.github.io/kbarchive/kb/130/Q130510/) corroborates `/e`, `/root`, `/select` behavior. These do not justify executing arbitrary shell text.

Captured the visible OSR2.5+IE4 reference at **800×600**, launched `explorer /n,/e,c:\windows`, probed File/Edit/View/Tools and restored our own checkpoint `before-explorer-plan-20261126`. Hashes, launch recipe and checkpoint are in `private/screenshots/explorer-plan-20261126/capture.json`.

![Original IE4 Explorer](/home/dwilson/Documents/Windows95/private/screenshots/explorer-plan-20261126/ie4-explorer-windows.png)

Observed: caption “Exploring - Windows”; All Folders tree with close button/splitter, connectors, small icons and scrollbars; right pane initially List with column flow; address C:\WINDOWS; menus File/Edit/View/Go/Favorites/Tools/Help. View includes Explorer Bar, as Web Page, four view modes, Customize this Folder, Arrange/Line Up, Refresh and Folder Options. Tools has Find in this captured configuration. The tree was scrolled: do not mistake the top visible folder for a `/root` boundary. No pixel-difference acceptance is claimed against our unimplemented tree.

Classic reference was owned by the Fonts worker. Classic/Plus native Explorer captures remain required; do not project IE4 menus onto classic. Windows 98 may fill later research gaps but must not silently become our Windows 95 baseline. Plus theme components do not imply IE4 Desktop Update, Folder Web View or Active Desktop.

## Modular profile contract (proposed, not runtime-integrated)

Store independently: `os_release`, `shell_generation`, `folder_web_view`, `active_desktop`, enabled `plus_components`, browsing preference and font/DPI metrics. OS edition alone must not pick shell menus. Web View and Active Desktop require Desktop Update capability but can be independently disabled. Plus themes, pointers and large-icon preference remain independent components.

Provide explicit presets Classic 95, Classic+Plus, IE4 with classic desktop, IE4 Active Desktop, and IE4+Plus. Each preset references a captured, named baseline; do not claim RTM accepted without an operating reference. Preserve existing browsing preferences when introducing a versioned settings schema; validate values, apply defaults only to missing fields, atomically persist and retain unknown keys for forward compatibility. Migration needs idempotence and restart tests. This is a proposed contract, not a user-visible toggle added in this pass.

Explorer launch is a typed request: new-window, explore/tree mode, root namespace and selected item. Parse quoted paths and recognized switches without shell evaluation. Distinguish My Computer Open, folder Open, Explore, Win+E and Programs Explorer. `/root` confines navigation; `/select` reveals and selects the target; malformed, inaccessible and missing targets get measured native dialogs. Reuse the same command resolver for menus, keyboard and toolbar.

## Implementation sequence after Control Panel priority

1. Backend evaluation: build disposable Linux-explorer/XFE examples; benchmark GIO adapters. Compare copy, rename, cross-filesystem move, symlink and monitor behavior with current safe primitives. Keep UI unchanged. Record explicit retain/adapt decisions.
2. Safe launch parser and Programs-root shortcut; profile capability objects and command-state tests. Integrate lazy tree only after namespace adapters and worker scheduling exist.
3. Tree rendering, keyboard focus, splitter and independent window state. Reuse shared scrollbar/menu primitives and exact native font metrics; no filesystem I/O during painting.
4. Four view modes and durable per-folder settings. Details columns/sorting and status totals must share one item model.
5. Complete toolbar dispatch, transactional operations/Undo, progress/cancel/retry, external refresh and cross-window drag. Native association, properties, Find and Folder Options follow as separate accepted features.
6. Add profile-specific Web View/customization only after classic feature acceptance. Keep unavailable device features visibly disabled with concrete reasons, not fake success.

## Acceptance and regression protocol

For each feature, select a named native configuration; capture original and ours at equal **guest** resolution, font size, color depth, window bounds, selection, focus and open menu state. Record host viewer zoom separately. Save raw unscaled framebuffers and metadata/checksums; only align explicitly anchored crops, never resize screenshots to hide differences. Produce full image, anchored crop, overlay, difference mask, mismatch count/ratio and control-edge/text-baseline measurements. Check normal, hover, focused, selected, disabled, pressed, checked and scrolled states. Native gray tracks/disabled embossing/menu gutters and title baseline are acceptance requirements.

Behavior matrix per command: no selection / one file / one folder / shortcut / system object / multi-selection; valid/invalid clipboard; writable/read-only/disappeared target. Exercise mouse, keyboard and toolbar entry points and assert identical command resolver results. Confirm errors, cancellation and restart persistence. Test folder-to-folder, desktop-to-folder and Start-menu organization with drops near icon edges, label area, inter-icon whitespace and folder border; measure tolerance against original rather than guessing.

Unit/regression candidates:

- Launch: quoted paths and switch order; `/root` escape prevention; `/select` missing target; new vs reused window; unsupported switch native error; no shell execution.
- Tree: expand/collapse and keyboard; stale/out-of-order results; deleted/recreated keys; inaccessible/disconnected directories; link loops; two-window state; paint makes zero filesystem calls.
- Views: every mode at small/large fonts; ordering tie breakers; column width/scroll; rename boundaries; selection retained after refresh; empty/huge folder.
- Operations: same-folder Copy of naming; collision races; move across filesystems; partial permission failures; symlinks; read-only targets; cancellation and Undo after each operation; shortcut target icon and broken targets.
- Menus: each option's label/order/mnemonic/shortcut/check/gutter geometry and contextual capability; toolbar and menu enabled states must agree; Help/About scaling and top-left system menu included.
- Preferences: version migration, corrupt input fallback, atomic writes, independent window/folder preferences and settings after session restart.

Existing entry points to extend: `tests/test_edit_commands.py`, `test_selection_profiles.py`, `test_explorer_operations.py`, `test_explorer_namespace.py`, `test_browsing_preferences.py`; guest `dev/check_computer_view.py`, `check_selection_details.py`, `check_folder_windows.py`, `check_file_dialogs.py`, `check_reference_ui.py`. Their existence is not evidence they all ran in this pass.

Proposed performance budgets, not measured acceptance: cached input-to-paint p95 ≤ one 60Hz frame; no UI-thread folder enumeration; first visible rows incremental on slow storage; cancellation acknowledges promptly; startup must not scan entire trees. Measure on the actual guest with recorded CPU/RAM/disk/profile, warm/cold state and repeated samples. Test 640×480, 800×600, 1024×768 and configured modern resolutions without inferring DPI from resolution. Require no overlap/clipping and stable pointer scaling; native pixel comparison only where the original can render the same mode.

## Completed development and evidence limits

Added unintegrated `src/win95lx/explorer/tree_model.py` and **13 passing tests** in `tests/test_explorer_tree_model.py` (0.032 seconds on this host in the final run). Tests cover lazy reads, no drawing I/O, independent windows, keyboard, collapsed late results, stale refresh, removed/recreated node generations, retryable errors, blocked cycles, invalid/duplicate entries, a 10,000-folder viewport, sorting/hidden items, links/outside roots and permission errors. A defect found during construction allowed an old callback to attach to a removed/recreated path; monotonic per-window generation tokens fix it and a regression test covers it.

The model is not an Explorer GUI, does not schedule its own workers and does not establish native visual acceptance or slow-storage responsiveness. UI integration remains deliberately paused for upstream reuse evaluation and Control Panel completion. No new Explorer functionality has been deployed. Five original captures exist; no corresponding new-tree screenshot, zero-difference report, guest feature acceptance or whole-UI performance claim is supplied.

Next handoff: evaluate reusable backends, capture classic Explorer when its VM is free, then accept launch/tree as one bounded feature using the protocol above. Preserve native checkpoints and private assets; do not redistribute proprietary artwork with code merely because an upstream repository includes it.

## Priority integration blocker: stacking and focus across applications

Root's current integration experiment found a desktop-level defect, beyond individual Explorer features: the fullscreen shell paints all internal Explorer frames, while applets and accessories are separate undecorated `Gtk.Window`s. Raising/focusing the shell to use Start or taskbar can cover those native windows with the desktop. Avoiding the raise alone leaves shell-painted menus/Run behind native applets. Manually raising every app together is a diagnostic workaround, not acceptance. Source corroboration: `shell/app.py` accessory launch calls `present()`, close/task-minimize returns focus to the shell, and shell input paths focus the fullscreen GDK window. `apps/property_sheet.py:136` accepts Escape without excluding Control, so Ctrl+Esc can cancel an applet instead of opening Start. Root observed the integration failure; this child has not independently replayed or fixed it.

This is **P0 before increasing the number of applets/features**. Preserve the eight working applet backends, property-sheet chrome and pending edits. Distinct folder paths and pixel-perfect controls cannot establish a working desktop if activating Start hides unrelated applications.

Actual reusable WM capabilities were inspected, not inferred from screenshots:

- [Linux-explorer client management at the pinned revision](https://github.com/JackTulli/Linux-explorer/blob/0e50375e22231811b16398fd12d85ccf780a0f69/wm/client.c) has decoration-hint handling, transient ownership/raising, native focus, minimize/restore and client reparenting. Its `wm.c` processes MapRequest/ConfigureRequest/UnmapNotify; `input.c` registers global keys. These are meaningful machinery absent from a painted virtual-window stack. They do not prove compatibility with our GTK windows or justify adopting its taskbar/desktop wholesale. Twenty pinned WM source files and hashes are in `private/research/explorer-plan/wm-source-fetch.json`.
- [IceWM client code](https://github.com/ice-wm/icewm/blob/17907bdef5de6d18f9002a11d5c11abb8c1f6a42/src/wmclient.cc) handles WM_TAKE_FOCUS, WM_DELETE_WINDOW, transient hints and _NET_ACTIVE_WINDOW. Its frame/manager sources provide actual native window management. This makes it a candidate for a window-management-only nested trial; disable competing taskbar/desktop rather than showing two shells. Existing style/GTK compatibility still needs verification.
- [XFWM4 focus](https://gitlab.xfce.org/xfce/xfwm4/-/blob/master/src/focus.c) and [stacking](https://gitlab.xfce.org/xfce/xfwm4/-/blob/master/src/stacking.c) are another important baseline since this project already targets XFCE. Event code explicitly deals with vanished windows, transient relationships and focus-stealing prevention. Exact downloaded source hashes are in `wm-alternatives-fetch.json`; these moving-branch files are not pinned commit acceptance evidence.

The lowest-disruption path to evaluate is **retain applets and their native GTK windows, reuse a real X11 WM for focus/stacking, and adapt shell surfaces gradually**. A real WM alone cannot reorder Explorer frames inside one fullscreen shell separately from applets. Separate desktop background, taskbar and popup/menu surfaces; expose each Explorer frame as its own undecorated native window using existing renderer/backend state. Keep desktop below normal windows, taskbar in its intended layer, owner-relative dialogs above owner, and popup menus above relevant applications without raising the desktop. Set explicit desktop/dock/normal/popup and transient relationships. Decide who owns Ctrl+Esc/Alt+Tab/system shortcuts; there must be exactly one global routing authority.

Perform this only as a nested-display/VM-checkpoint experiment first. Do not rewrite applet controls, file operations or settings to fit another project's toolkit. Compare existing XFWM4, minimal IceWM and Linux-explorer WM-only feasibility before choosing. The all-in-one latter may require disentangling its shell surfaces; record that cost instead of assuming a switch disables everything. An alternative is implementing native focus/stack management in our shell, but it means owning X11 client lifecycle/global key/transient protocols; it is a larger maintenance commitment. No shared GUI migration is authorized by this plan or performed here.

Acceptance scenarios for the integration spike:

1. Open two overlapping Explorer folders, Notepad with unsaved text and two property sheets with unapplied changes. Click Start/taskbar/background repeatedly. Inactive windows remain visible wherever not physically occluded; no window jumps below the desktop.
2. Open Start submenus over each native applet and Run over Explorer. Menus remain visible, input goes to the top intended surface, clicking outside dismisses only the menu and restores previous app focus.
3. Press Ctrl+Esc while every applet control has focus, including text entries, lists, sliders and modal message boxes. Start opens according to native modal behavior; no Cancel/close action occurs and pending edits persist. Plain Escape still cancels/dismisses its proper target.
4. Task-button minimize/restore, Alt+Tab and owner/dialog activation agree. Minimized windows stay minimized; restoring preserves location, selection, scroll and unsaved text. A dialog cannot disappear behind its owner, and closing an owner has defined transient handling.
5. Move, resize and maximize each native/internal migrated window with mixed applets open. Verify title active/inactive pixels, z-order, task selection, pointer capture and scaling at 800×600 and modern modes.
6. Launch/destroy an external GTK application, simulate an app crash and open a new app while Start is open. No stale task entry, lost keyboard focus or fullscreen desktop raise. Reboot/restart preserves the chosen session architecture.

Instrument X window IDs, active-window/stacking properties, focus events, screenshot timestamps and task states before/after each action. Pure tests cover routing priority, modifier-aware Escape handling, transient ownership and window lifecycle models; guest regressions must use real mixed windows and assert both visibility and input. Capture original Windows 95 equivalent multi-app states at equal resolution, then ours; a single isolated applet screenshot cannot pass this gate. These are planned tests; no new passing integration count is claimed.


Follow-up isolated experiment completed: see `reports/WINDOW_MANAGER_FEASIBILITY.md`. Actual copied shell on private Xvfb reproduced no-WM covering, verified XFWM4/IceWM stacking improvements, confirmed covered Start/Run and Ctrl+Esc cancellation, and demonstrated native-popup layering. No production deployment.
