# Win95LX project instructions

Read WIN95LX_PLAN.md and docs/agents/windows95-fidelity-engineer.md for fidelity work.

Reuse the shared controls described in docs/CONTROL_TOOLBOX.md. Follow docs/VISUAL_REGRESSION.md for original-VM captures, exact comparisons, and guest checks. Preserve reference evidence and private assets.

Treat screenshot appearance, input behavior, errors, and persistence as acceptance requirements for the changed feature. Update the sprint acceptance report with actual evidence and unresolved discrepancies.

## Applet completeness gate

User requirement, 27 November 2026: deliver each applet as complete as possible.
Before calling an applet complete, inventory every native control and workflow,
implement each feasible Linux equivalent, and test its actual effects, keyboard
and pointer input, Apply/Cancel, persistence, failure recovery and native visuals.
A working subset must be labeled incomplete, with a concrete remaining-work plan;
unimplemented software features are not hardware limitations. Disabled controls
need accessible reasons and a delivered capability list. Do not move on with
routine Save/Delete/customization controls left as unexplained future work.
For Themes specifically, Save As, Delete, custom combinations, browsing/import,
and at least30 distinct valid customization scenarios are explicit requirements.

## Installer dependency inventory

Record every new runtime package, architecture requirement, optional service and
private asset input in `config/installer-dependencies.json`; see
`docs/INSTALLER_DEPENDENCIES.md`. Dependency installation belongs to setup, never
an applet click handler. Capture target package versions and resolver logs;
package presence alone does not accept feature behavior.

## Feature ledger

Use `config/feature-ledger.json` as the compact work index; validate/query with
`tools/feature_ledger.py`. Update meaningful implementation, validation, delivery
and blocker changes with evidence paths. RTM/OSR release, Plus components, IE4
Desktop Update, Active Desktop and folder Web View are separate dimensions.
No evidence inheritance across profiles; missing entries mean not tested. A
prepared reference is not feature acceptance. Keep detailed captures/reports
linked separately and hand off changed facts rather than repeated full reports.
This ledger is planning metadata, not an applet runtime dependency.

## Early visual gate across reference configurations

Before expanding a shared control, compare a small representative state in both
prepared classic and IE4 Desktop Update references. Add the Plus95 reference for
theme-sensitive colors/fonts/metrics/assets or Plus-only features. Match guest
resolution, color depth, locale, font settings, focus and selection, and record
the actual OS/component versions. Capture normal/focused/disabled/pressed states
where relevant before propagating the control to more consumers.

Reuse sealed matching captures when inputs have not changed. Keep separate
expected profiles where Windows differs; do not average them into one design.
A feature absent from a profile needs documented not-applicable evidence rather
than a fabricated screenshot. Failed gates hold that change. Final full-window
and physical input tests remain required.

These prepared references are configurations of OSR2.5. They do not establish
RTM, retailSP1 or OSR1 acceptance. Record unavailable release/profile evidence as
not_tested in the feature ledger, with a follow-up instead of silently inheriting
acceptance from OSR2.5.
