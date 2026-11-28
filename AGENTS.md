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
