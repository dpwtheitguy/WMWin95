# Win95LX delivery plan

Updated 2026-11-25. Sprint 1 scoped increments are validated; see reports/SPRINT_1_ACCEPTANCE.md for evidence and remaining discrepancies.

## Product and reference

Build a Linux desktop whose appearance and ordinary interactions reproduce Windows 95 OSR 2.5 with IE4 Desktop Update. Judge the full experience through normal desktop, Explorer, and application entry points. Use the installed original Windows 95 VM as the reference.

The implementation currently runs a custom shell and built-in GTK applications in a dedicated X11 guest session. General management of arbitrary X11 application windows is a later milestone. Preserve the existing architecture during this sprint.

Engineering instructions are in [Windows 95 Fidelity Engineer](docs/agents/windows95-fidelity-engineer.md). Control APIs are recorded in [the control toolbox](docs/CONTROL_TOOLBOX.md). Reference capture and comparison procedures are in [visual regression](docs/VISUAL_REGRESSION.md).

## Sprint 1 assignments

| ID | Assignment | Acceptance criteria |
| --- | --- | --- |
| S1-001 | Drag and drop | Rearrangement never transfers an item into itself. Match measured native target margins and drag initiation. Support window and desktop transfers, Ctrl-copy, cancellation, and covered windows. |
| S1-002 | Explorer title bars | Match native text origins, capital-letter rasterization, baseline, caption bounds, and clipping. Compare the actual title region. |
| S1-003 | Shared menus | Match checkmarks, gutters, row heights, selection colors, mnemonics, and keyboard behavior. Word Wrap must toggle the editor and show the correct state. |
| S1-004 | WordPad appearance | Compare toolbar, format bar, ruler, editor edge, and gray surfaces with wordpad.exe. Correct duplicated bevels in reusable controls. |
| S1-005 | Display settings | Palette choices visibly affect rendered controls and images. Verify color counts, checkbox feedback, Apply, Cancel, persistence, and taskbar behavior. Record any distinction between rendered palette and X11 server depth. |
| S1-006 | Desktop appearance | Browse loads an image from the guest filesystem. Preview, placement, Apply, Cancel, and restart persistence work. Native named patterns and custom 8x8 editing work. |
| S1-007 | Documents history | Successful opens and saves populate Start > Documents across apps. Include My Documents, deduplication, bounded history, persistence, missing-file handling, and reopening through the menu. |
| S1-008 | File operations and Recycle Bin | Match native same-folder copy naming. Use native error and confirmation dialogs. Files and folders can enter the bin, restore without overwriting, and be permanently deleted after confirmation. |

Start with the smallest reproducible fixes, then advance through independent assignments. Reconcile unfinished working-tree changes before implementation. Preserve working code and existing user preferences.

## Acceptance workflow

For each assignment, record the feature, original behavior, acceptance criteria, relevant unit and interaction checks, reproduced defects, corrections, performance conditions, and remaining discrepancies.

1. Establish a reproducible baseline with build/source identity and current failures.
2. Capture the same native and implementation states. Record resolution, color depth, theme, focus, selection, pointer, and input sequence.
3. Implement a regression that detects the reported failure. Demonstrate the previous failure when practical.
4. Implement through shared controls and normal application entry points.
5. Perform a defect discovery pass across boundaries, cancellation, retry, persistence, and failure behavior. Record findings even when no further defect appears.
6. Compare at 800x600 and 1280x720. Check real pointer behavior at native size and fractional viewer or font scaling where affected.
7. Measure performance against the baseline under stated conditions.
8. Validate in the guest before activating a release. Preserve open unsaved documents.
9. Accept only the behaviors and visual regions demonstrated by the evidence.

Exact pixel claims require zero differing pixels in the named region/state. A captured frame used as artwork still requires interaction tests for its dynamic controls. Keep reference evidence independent from implementation output.

The requested features remain explicit acceptance work until implemented and verified. Record unfinished functionality visibly in engineering reports. Avoid masking a failing requested feature by removing its control.

## Sprint report

Maintain a consolidated report at reports/SPRINT_1_ACCEPTANCE.md with accepted assignments out of eight, unit and interaction scenario totals, passing/failing checks, actual defects, before/after captures, pixel reports, performance measurements, discrepancies, blockers, and recommended Sprint 2 work. Distinguish unit tests, scenarios, assertions, and repeated resolution runs.

Original Windows assets and VM images stay private. Report links can point to local private evidence. User-facing runtime content should follow the reference's layout and wording where it applies to the implemented action.

## Sprint 2 candidates

General X11 window management, remaining Explorer views and property sheets, file associations and shortcuts, fuller WordPad behavior, comprehensive sound event mapping, and end-to-end boot/reboot timing.

## Active follow-up — selection, command context, Edit, navigation, Mouse

Preserve the November 25 Explorer iteration as the baseline. Current user requests extend it with:

1. Selection-dependent Web View details, original template/resource research, original Verdana raster, and same-state comparisons.
2. Working namespace, file and folder shortcuts; native creation prompt; icons/overlays; cancellation, duplicates, reopen, rename/move/copy/trash/restore and broken-link tests. Explain the desktop-Link versus symlink distinction.
3. Modular selection-dependent File profiles; default verbs, capabilities, empty/single/multiple/mixed/protected contexts. Record native and unverified states separately.
4. Edit-menu native captures and per-command unit, interaction, failure, cancellation and persistence regressions. Require screenshots and explain the process.
5. Native single-window browsing and the real Folder Options preference, while retaining explicit new-window opening and independent-window state.
6. Mouse Properties with original Win95 tabs, original available pointer schemes and additional appropriate schemes. Every exposed setting must affect the guest session, Apply/Cancel/persistence must work, and pixel/input tests must substantiate acceptance.

Keep requests cumulative. Do not conflate selecting Control Panel with opening it: inspect native double-click behavior and its folder-browsing setting. Push completed iterations using the repository's configured WMWin95 SSH key, excluding all private original assets and VM data.

## Overnight assignment — November 25–26

Complete and independently recheck the cumulative user requests above; commit and push validated iterations to main. Expand working Control Panel applets where feasible, with original-control screenshots, multi-path unit/regression/interaction tests and explicit hardware/implementation gaps. Take VM snapshots before broader changes. Establish a separate classic Windows 95 reference without IE4 Desktop Update where existing licensed media/snapshots permit. Measure UI and boot performance before claiming improvements. Research DOS-launch choices extensively (FreeDOS, other DOS implementations, DOSBox variants, Linux shells and PowerShell aliases); do not implement the DOS feature in this iteration. Report completed work, evidence, remaining issues and next priorities. Preserve private assets, user preferences and non-admin guest boundaries.

Mouse Properties now has a first working implementation; see reports/MOUSE_PROPERTIES_2026-11-26.md. Do not mark the complete Mouse assignment accepted: pointer trails, named custom schemes, third-party cursor theming, physical-device acceleration and complete modified-state comparisons remain open. The basic and original available animated/Plus schemes are now implemented.

The pointer iteration now stages the basic USER.EXE set as default, retains 3D/large schemes, and adds the original Plus! pointer catalog. Full desktop profile switching is later work; keep Explorer generation, Active Desktop and Plus! customization independent as described in docs/DESKTOP_PROFILES.md. The intended visible reference set is three Windows VMs (classic, IE4, Plus!) and one Win95LX VM. Preserve working-desktop snapshots and do not use recovery snapshots as the default normal launcher behavior.

## Control Panel expansion — November 26

See reports/CONTROL_PANEL_2026-11-26.md for the six routed applets, narrowly accepted native states, actual-backend tests, 47-mode geometry scope, measured palette acceleration, RTM licensing blocker, and remaining feature inventory. No blanket all-applet acceptance is asserted. Continue the remaining applets using native control measurements and effect/rollback tests.

## Guest privilege experience — user direction, November 26

Normal Win95LX settings operations must not expose sudo, terminals, password/elevation prompts or a UAC-like workflow. This is a dedicated development OS. Keep the desktop account non-admin and implement needed privileged guest operations behind narrowly scoped service/polkit helpers; never grant these policies on the host. Present unsupported features with native disabled-state explanations and operation failures with Windows 95-style errors. Do not invent an approval UI. Validate the actual non-admin desktop path, not just a root/fake backend. Developer maintenance SSH/sudo remains an internal tool, not a product interaction.

Track current guest permission requirements in docs/GUEST_PRIVILEGES.md. A declarative installer capability/permission manifest is requested for a later implementation; the ledger is not yet consumed by the installer.

## Hidden-feature fidelity follow-up

Implement the original folder-renaming product-team credits, Volcano 3D Text
screensaver behavior, and CLSID namespace folders. Requirements and regression
matrix: [hidden features](docs/EASTER_EGGS.md). They are pending implementation;
retain the Control Panel work as the primary active stream.
