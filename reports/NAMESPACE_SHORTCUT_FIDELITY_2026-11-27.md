# Namespace drops and shortcut presentation

Status: validated current-IE4 implementation deployed; bounded reference coverage and remaining discrepancies are explicit below.
Baseline main83aebbc, visible release59dbd3dd304c5c52.

## Coverage

Prepared references cover Windows95C/OSR2.5 Classic, IE4 Desktop Update and
IE4+Plus configurations. They are not evidence for RTM/OSR1 or every OEM build.
Each capture must identify profile, shell version, resolution, palette, focus,
selection and input/modifier state. Preserve rejected/contaminated observations.

## Independently observed so far

- IE4 C: left-drop to desktop shows a Shortcut Yes/No prompt, Yes default:
  “You cannot move or copy this item to this location. Do you want to create a
  shortcut to the item instead?” Independent HWND metadata corrected the initial estimated326×118 crop to
  326×119 in Classic, with Yes/No buttonY82. Fresh per-profile metadata is
  required before full-window acceptance. This is distinct from the374×119
  Create Shortcut menu prompt. Focused Escape is ignored; other input cases
  require independent checks. Earlier modifier captures with a residual modal
  were excluded, not counted as behavior evidence.
- Classic original32×32 drive/folder/ControlPanel/text shortcuts match target
  icon plus GROUP_ICON30 exactly, selected and unselected. Selected appearance
  tints the base only; tinting the overlay would introduce60 differing pixels.
  The previous GROUP_ICON29 shared-hand bug is already fixed in the baseline.
- Classic whole-cell measurements expose actual label defects: text one pixel
  too high, truncation instead of wrapping, missing measured focus rectangle.
  Native standard desktop pitch is75×75. Folder-cell geometry is separate.
  Long labels and other configurations are still under investigation.

## Implementation requirements

Namespace transfers create safe existing-provider links, never filesystem moves
of Linux root or CPL objects. Enable transfer initiation in all views and with
Auto Arrange on; restrict only free internal rearrangement. The drag ghost must
remain visible outside the source pane. Cover desktop, folder background and
folder icon destinations; invalid/covered targets must not create files.

Test Yes/No, keyboard and native close semantics, duplicate names, stale targets,
failed writes/partial batches, source position preservation, reopen and real
pointer events at800×600/1280×720. Use full independent native prompt regions,
not only static art. Namespace source objects must remain available afterward.

Desktop labels need full-cell selected/unselected/inactive comparisons. Preserve
proven icon compositing, manual saved coordinates and existing folder profiles.
Use measured wrapping/focus rules; no blanket claim about other wallpapers,
palettes or long-name states before native evidence. New desktop slots use the
measured75-pixel pitch so ordinary multiline labels fit their allocated rows.

## Selection-mask performance measurement

Root compared commit83aebbc's original `selected_image` with the bounded cached mask on
the host CPU using a64×64 Cairo image target and the original32px drive icon.
Seven samples of1,000 warm calls: median0.1531ms/call before,0.00190ms/call after.
Phase0 rendered bytes are identical. This is a component microbenchmark, not an
80× claim about application or input latency. Evidence and reproducible private
script: `private/namespace-crossdrop-20261127/selection-benchmark.json` and
`benchmark_selection.py`. Mask cache holds strong immutable-surface/phase keys,
bounded128; new assets use new surfaces and mutated alpha needs explicit cache
invalidation. Native IE4 desktop folder base has aY−1 origin and requires phase1;
its shortcut overlay remains at nominal origin and is not tinted.

## Superseded evidence

The initial118px prompt crop omitted a native row. Its initial zero-difference
results were comparisons to an incorrectly cropped artifact, not acceptance of
the full native dialog. Use HWND rectangle/control metadata and a fresh full
326×119 capture for canonical rendering/hits; preserve old captures as rejected
geometry evidence. Also distinguish physical/logical mouse buttons: Plus has a
saved swapped-button setting; normalized primary drag still shows the prompt,
while logical-secondary drag offers Create Shortcut(s) Here/Cancel.

## Final reference findings

Native case matrix: all three prepared configurations show the fallback question
for C:→desktop, ControlPanel→desktop and C:→real folder. Exact sources and
accepted/excluded observations are in `NAMESPACE_CROSSDROP_2026-11-27.md`.
Logical-secondary drop instead offers direct Create Shortcut(s) Here/Cancel.
The native183×49 menu and full326×119 current-IE4 prompt have independent
metadata and rendered comparisons. Escape cancels a drag before drop but does
not dismiss the native Yes/No question afterward.

Fresh independent HWND metadata established326×119 in both Classic and IE4.
Explicit IE4 frame repaint/settling repeatedly retained39 navy caption-border
pixels that differ from Classic/Plus; do not call that an excluded artifact.
The current runtime's alias is the fresh IE4 frame. Alternative prompt assets
are preserved, with inferred Plus geometry explicitly identified. Native empty
volume naming is `Shortcut to  (C).lnk` (two spaces), confirmed by file enumeration.
No automatic rename of existing user shortcuts is performed.

Both default-left Yes and right-menu creation preserve a17×21 source grab
offset: mouse(700,400)→newimage(683,379), and mouse(700,500)→(683,479). The new
desktop link is selected. Source objects remain in My Computer.

The shortcut audit accepted current-IE4 actual renderer/component cases, Classic
components and configured Plus components separately. Plus registry explicitly
overrides drive/folder icons with COOL.DLL; installing Plus alone is not taken
as proof of that configuration. See `SHORTCUT_VISUAL_AUDIT_2026-11-27.md`.

## Guest regression discovery

A new checker assumed Shell's default presentation root was its temporary home.
That is true in the host preview but false in the actual development guest,
where C: intentionally maps to `/`. A fixture tried to create `/Drop Target` and
was denied. No real-root fixture directory was created. Root corrected only the
checker to install/assert an explicit temporary DriveBrowser root before any
writes. Source production behavior was unchanged. The failed log is retained.
Missing private right-menu metadata initially skipped three comparisons; after
copying the actual metadata they all pass. Full final-reference guest unit run:
379 tests, one opt-in skip (actual AccessX is exercised by the UI suite).

A second regression exposed a genuine first-run dependency: after destination
writers stopped implicitly creating folders, a brand-new profile lacked its
Desktop. Shell now explicitly initializes its known profile Desktop once at
startup. Arbitrary stale drop destinations remain rejected. The Printers shell
checker asserts this fresh-profile setup; no production folder-creation guard
was weakened. Read-only independent review found no blocking data-loss issue and
flagged an unnamed GDK key edge case in the new right menu. Its name lookup is
now guarded and the right-menu checker exercises that input without dismissal or
write. These scoped source corrections precede the final combined rerun.

## Live discovery and regression: ghost behind the question

Live VM validation exposed an actual redraw defect: clearing drag state was not
enough while a blocking GtkDialog.run was entered before release queued a draw.
The previous global ghost stayed visible behind the modal. Root reproduced it
against immutable candidate release `d0e11cb6ab0e019d`: actual X11 pixels contained
202 stale ghost pixels250ms into the open question. Root now invalidates the
parent immediately after clearing drag state and before entering the modal.
`dev/check_namespace_modal_ghost.py` checks actual window pixels rather than
calling the draw function from cleared model state. Corrected800×600 and1280×720
runs both contain zero stale pixels, and choosing No leaves Desktop unchanged.
Baseline/fixed logs and captures remain in the guest QA tree and the failing
intermediate release remains available for reproduction. The check is included
in `make check-ui`.

The legacy selection test also assumed every desktop folder base was at nominal
Y. Its resource-composition expectation was corrected to the independently
measured IE4 Y−1 profile. Original Windows full-cell screenshot baselines were
not changed. That target and the remaining check-ui recipe were rerun and passed;
prior stopped logs remain evidence, not a claim of a single uninterrupted pass.

## Final delivery

Visible guest release: `/opt/win95lx/releases/70026f549a5d4525`. Root refreshed
the session, inspected the actual framebuffer, dragged the existing C: icon
to desktop with QMP tablet input, observed the native question with zero stale
ghost, and chose Yes in the non-admin session. A selected arrow-badged shortcut
appeared at the preserved drop offset while C: remained visible in My Computer.
An additional real right-drag opened Create Shortcut(s) Here/Cancel and Escape
closed that menu. One new demonstration shortcut remains on the right side of
the user's desktop; existing files were not deleted/renamed.

Recovery: `before-namespace-shortcuts-20261127` and
`namespace-shortcuts-ready-20261127`. Live captures:
`private/namespace-crossdrop-20261127/live-final-question.png`,
`live-created-shortcut.png`, `live-right-drop.png`.

Final exact-source guest checks:379 tests run, one opt-in skip (AccessX actual
input is covered separately). All check-ui dependency groups and final recipe
completed after correcting documented fixture/stale-expectation failures; logs
are retained rather than asserting one uninterrupted exit0 run. The fixed
selection target, remaining recipe and last modal-fix affected regressions each
returned0. Final379-unit rerun and namespace/prompt checks passed after the last
production edit. New actual-X11 modal ghost tests pass at800 and1280; native
Plus component check also passed independently in the guest.

Not claimed: every original Windows95 release, global profile switching,16px
shortcut variants, all modifier combinations, every long-label overlap, generic
X11 window management or complete caption/taskbar focus parity. Current normal
IE4 desktop32px shortcut cell comparisons and bounded prompt/menu states are
accepted by their independent original-reference checks.
