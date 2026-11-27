# Control Panel namespace overflow correction — 2026-11-26

Corrected the screenshot defect: Control Panel applet icons no longer run as one unbounded row or paint onto the teal desktop after resizing. The namespace now has an explicit client clip, intersected icon hit regions, responsive views and reachable scrolling. This is scoped to Control Panel; existing desktop and folder manual arrangements are not globally rearranged.

## Native reference and design

Captured original visible OSR2.5+IE4 Control Panel Large/Small/List/Details at 800×600, then restored checkpoint `before-control-layout-20261126`. Evidence and hashes: `private/screenshots/control-layout-20261126/manifest.json`.

Original maximized Large Icons uses a grid (75-pixel cell pitch observed). Restoring the window preserves previous icon positions and introduces horizontal scrolling; it does not always reflow manual positions. Small Icons also retains arranged positions. List flows down then to the next column and scrolls horizontally. Details has Name/Description headings and both scrollbar axes as needed. Our responsive default uses Auto Arrange for previously unpositioned applets, as requested; switching Auto Arrange off freezes positions across resizes, with scrolling rather than silently discarding them. Full historical manual icon drag/persistence is not newly implemented by this change.

## Changes

- Pure `explorer/namespace_layout.py` calculates Large/Small/List/Details geometry, scrollbar dependency, extent, clamped scroll, hit intersection and selected-item reveal.
- `shell/namespace_view.py` uses original icons/shared classic painters, clipped rows and measured labels. Gray/white stippled tracks, arrow/page clicks, wheel and thumb dragging reach overflow content.
- Control Panel View menu exposes four modes and Auto Arrange with checked states. Window-local mode/scroll/positions do not alter other namespaces.
- `computer_view.py` clips its client; applet paint and hit regions are intersected with the item viewport. Even disabling toolbar/address/Web View retains the responsive renderer.
- Home/End/arrows select and reveal applets. Mode changes reset/clamp obsolete scroll positions; resizing recalculates capacity.
- Information-panel type text and oversized description tokens wrap against measured font width. Description selection still uses existing original Verdana data; no font substitution or scaling.

## Before / after

Same 450×310 window geometry, original row renderer versus corrected renderer:

![Before row overflow](/home/dwilson/Documents/Windows95/private/screenshots/control-layout-accepted-800-20261126/before-row-overflow.png)

![After responsive clipping](/home/dwilson/Documents/Windows95/private/screenshots/control-layout-accepted-800-20261126/after-wrapped-clipped.png)

Regional description and scrolled items at 500×350:

![Wrapped description](/home/dwilson/Documents/Windows95/private/screenshots/control-layout-accepted-800-20261126/regional-description-wrapped.png)

## Validation and limits

**10 new unit tests pass** for narrow/wide grid, all modes, both scrollbar axes, manual position preservation, resize/mode clamping, moved/clipped/offscreen hits, keyboard reveal, measured label/description wrapping and empty/invalid inputs. Additional existing checks passed: 10 control-layout, 5 selection-profile, 3 namespace and 2 browsing-preference tests (30 combined including the new tests).

Forced-X11 isolated render/input regression `dev/research/check_control_panel_layout.py` passed at **800×600 and 1280×720**, 38 captured states per resolution. Six grouped checks cover all four modes at 760/450/290 widths with first/last-item reachability; bounded hit targets; thumb drag; namespace-only pixel comparison asserting **zero changed pixels outside its client rectangle**; move/shrink plus Home/End; manual-preservation versus Auto Arrange reflow; and all bands disabled. The before screenshot deliberately reproduces old overflow and is excluded from corrected hit-bound assertions. JSON reports/checksums are under `private/screenshots/control-layout-accepted-{800,1280}-20261126/`.

One construction test initially assumed even a 1000-pixel viewport must scroll vertically; corrected that test expectation after the wider grid legitimately fit. The isolated regression initially asserted new bounds on the deliberate before screenshot; narrowed that assertion to corrected states. Both failures were in test setup/expectations, not concealed passing app behavior.

No changes were deployed to the user's running Linux VM. Native reference was restored. These results establish bounded rendering, reachability and measured layout behavior in isolated X11 tests; they do not claim all Control Panel modes, scrollbar pixels, menu organization or manual drag behavior are 100% native-identical. Details-column resizing/sorting, per-folder view persistence and full native Arrange Icons submenu remain follow-up work. Existing desktop stacking/focus limitations are documented separately in `WINDOW_MANAGER_FEASIBILITY.md`.

## Layout calculation performance

A host microbenchmark measured 2,000 calculations per mode/width for 20 entries across all four modes and three widths. The slowest case had p95 **0.0345 ms**. Raw samples summary: `private/evidence/namespace-layout-performance-20261126.json`. This covers pure geometry calculation only; input-to-visible-response, repaint and guest viewer latency remain unmeasured for this change.


## Combined-stage harness defect discovered and corrected

The first combined guest run failed before completion because the regression script used `git show HEAD:...` to recreate its historical before image. Staged release QA has no `.git`, and moving HEAD would also cease to represent the old renderer after commit. Removed historical-before generation from the ongoing regression; preserved the already captured before images as independent dated evidence. The script now requires neither Git nor repository history. Ongoing runs capture **37 corrected states per resolution**; the earlier 38-state evidence remains valid as a dated run including its deliberate old-renderer image. This was a harness portability/reproducibility defect, not a newly observed product failure.
