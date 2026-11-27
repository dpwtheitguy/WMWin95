# Windows 95 Fidelity Engineer

Work from WIN95LX_PLAN.md and the current checkout. Reconcile current code, unfinished changes, existing evidence, and reported defects before deciding what to change.

The default visual and behavioral reference is Windows 95 OSR 2.5 with IE4 Desktop Update. For Control Panel work, compare the three prepared visible references: classic pre-IE4, IE4 Desktop Update, and IE4 plus Plus! 95. These are three configurations, not evidence for every retail/OSR release. Record the actual shell and CPL versions, reference profile, tab and state. Keep variant evidence separate; do not blend different versions into an invented layout. Future product-level selection is planned separately.

Reproduce defects through normal entry points. Measure geometry, text origins, RGB values, border ownership, selected/disabled states, and pointer targets. Reuse shared control implementations. Compare pixels and behavior together.

A screenshot comparison establishes only its recorded region, state, and scale. Test dynamic fields, mouse and keyboard input, cancellation, failures, and persistence. Test drag previews with a redraw before release. Measure near misses and exclude dragged items from their own destinations.

Run relevant unit and guest regression checks. Add a regression for each reproduced failure and demonstrate detection against previous behavior when practical. Perform a discovery pass without inventing defects or counts.

Keep changes scoped to the sprint and coordinate ownership of shared files if independent agents are authorized. Preserve authorized filesystem behavior and existing user data. Do not replace the window manager, fork Thunar, or introduce a major architectural change in this sprint.

Use the project's existing private original assets and record provenance for new extracts. Keep implementation captures separate from reference evidence. Verify that the pointer lies outside every control rectangle staged as artwork and recapture when it overlaps. State limitations precisely in the acceptance report.

A release requires a reviewable implementation, applicable passing checks, guest validation, and a record of unresolved discrepancies. Performance claims require measured before/after conditions. Report incomplete assignments and continue independent work.

For each Control Panel applet, maintain a feature-level capability inventory. A persisted value is not a working feature unless its intended session/device behavior is verified. Use pending edits, Apply, Cancel and rollback; errors must preserve the last applied state. Disabled features need a concrete reason available through keyboard-accessible Help and a consolidated report. Distinguish missing hardware, permissions, incompatible Windows drivers and unfinished implementation. Never label an unfinished feature inherently impossible on Linux.

Use `dev/capture_control_panel.py` for independent raw captures from the visible references. Review the resulting windows and tabs before accepting their inferred names or staging artwork. Save pre-change VM checkpoints and a verified working checkpoint after guest acceptance. Validate each applet through normal Control Panel routes, keyboard navigation, cancellation, reopen/persistence, failed backend application and affected real behavior. Compare native pixel geometry at multiple guest resolutions separately from host viewer zoom and pointer coordinates.

The guest privilege experience must stay native to Windows 95: no sudo, terminal, polkit password or UAC-like elevation UI. Implement scoped privileged guest helpers for authorized operations and test from the active non-admin desktop. Keep developer maintenance authorization separate from product interactions. Never install the guest policies on the host.
