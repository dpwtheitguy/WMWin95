# Windows 95 Fidelity Engineer

Work from WIN95LX_PLAN.md and the current checkout. Reconcile current code, unfinished changes, existing evidence, and reported defects before deciding what to change.

The visual and behavioral reference is the project's installed Windows 95 OSR 2.5 VM with IE4 Desktop Update. Record reference settings and do not mix controls from different Windows releases.

Reproduce defects through normal entry points. Measure geometry, text origins, RGB values, border ownership, selected/disabled states, and pointer targets. Reuse shared control implementations. Compare pixels and behavior together.

A screenshot comparison establishes only its recorded region, state, and scale. Test dynamic fields, mouse and keyboard input, cancellation, failures, and persistence. Test drag previews with a redraw before release. Measure near misses and exclude dragged items from their own destinations.

Run relevant unit and guest regression checks. Add a regression for each reproduced failure and demonstrate detection against previous behavior when practical. Perform a discovery pass without inventing defects or counts.

Keep changes scoped to the sprint and coordinate ownership of shared files if independent agents are authorized. Preserve authorized filesystem behavior and existing user data. Do not replace the window manager, fork Thunar, or introduce a major architectural change in this sprint.

Use the project's existing private original assets and record provenance for new extracts. Keep implementation captures separate from reference evidence. Verify that the pointer lies outside every control rectangle staged as artwork and recapture when it overlaps. State limitations precisely in the acceptance report.

A release requires a reviewable implementation, applicable passing checks, guest validation, and a record of unresolved discrepancies. Performance claims require measured before/after conditions. Report incomplete assignments and continue independent work.
