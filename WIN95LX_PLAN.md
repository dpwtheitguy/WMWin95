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
