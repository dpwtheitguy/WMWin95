# Trusted95 shared screensaver runtime — 2026-11-27

Production runtime/stager implementation complete for this bounded checkpoint. All22 staged95/Plus presentations now share one prepared trusted runtime. Their original executable basenames and distinct per-saver settings are preserved. Original-reference pixel acceptance remains separate.

## Implemented behavior

- Optional schema1 runtime_groups/font_profiles extend the catalog without changing its public format number. Only the declared builtin95 Windows95/Plus95 group shares a prefix. Legacy/third-party entries without this declaration remain isolated by identity.
- The new trusted path is `<state>/groups/trusted95/prefix`; originals live under `C:\Win95LX\Savers\<identity>`. Existing `<state>/<identity>/prefix` directories are neither deleted nor modified. Conflicting old per-prefix General preferences are not silently merged into the new globally shared state.
- A shared baseline marker fingerprints Wine binary/core/INF metadata, runner version, runtime recipe2, genuine font hashes and classic color recipe. Separate presentation markers fingerprint each package. Preparing a second package only copies its small files; it does not initialize another prefix, rerun font setup or restart the server.
- The stager includes a separate classic95 font profile containing original SSERIFE.FON and VGASYS.FON, hashes and25 validated system color roles. NE bitmap-font containers are validated separately from presentation PE32 executable dependencies. Failed font/bundle rebuilds retain the previous bundle and clean temporary staging state.
- Prefix preparation registers those genuine fonts and maps MS Shell Dlg/MS Shell Dlg2 to MS Sans Serif. The actual first config font trace selects the original sserife.fon bitmap; this is not a renamed fallback font.
- One group flock covers cold preparation, an owned child and bounded Wine-server cleanup. Another runtime instance cannot launch or cold-prepare into that active group. Already-prepared, non-mutating warm prepare remains a no-op. An instance owning no process performs no kill. Cleanup failure retains its lease for retry instead of admitting a new owner into a potentially live session.
- prepare/ready/environment/launch/stop remain API-compatible. No embedded companion host ships in this checkpoint. Future helpers must acquire operation ownership before spawning; environment() alone is not a lease.

## Defect discovery: visible updater branding

The first real LinuxGTK Lens probe proved actual desktop refraction, but visual inspection found the Wine configuration-update progress box captured inside the saver image. This was a real immersion defect missed by process-only checks.

Preparation now removes DISPLAY and WAYLAND_DISPLAY for its worker-only wineboot and silent registry operations, stops/waits for that owned prefix server, and publishes a managed `.update-timestamp` disable guard. A normal interactive launch therefore cannot expose an automatic prefix updater. Explicit controlled wineboot-u still forces an update when the fingerprint changes; Wine INF/core metadata and recipe changes invalidate readiness. Linked/hardlinked update guards are rejected before invoking Wine. The Wine9 source implements this internal guard and explicit force-update behavior. [Wine9 initialization source](https://raw.githubusercontent.com/wine-mirror/wine/wine-9.0/programs/wineboot/wineboot.c).

The new actual GTK probe observes exactly identical visible pixels before/after cold preparation, then a moving Lens sphere over the non-Wine GTK checkerboard with no updater box. No captured-background bridge or additional prefix companion process is needed for Lens.

## Actual production proof

`dev/check_saver_group_runtime.py` runs the real production runtime with its real staged bundle in a disposable guest state tree and an owned Xvfb. No normal user preference, existing prefix or visible test desktop is used.

Final exact-source evidence: `private/screensaver-wine-20261127/group-production-quiet-final/`.

| Measurement/check | Observed result |
|---|---|
| Staged presentations |22 |
| Wine prefixes / wineboot invocations |1 /1 |
| Complete test state apparent size |611657716 bytes, about583MiB |
| Fresh-prefix prepare on warmed development guest |3109.68ms, worker-only |
| Second package warm prepare |4.24ms |
| Remaining all-package preparation |88.35ms |
| Shared General Mute Sound |Nature0→1; Travel reopens1 |
| Same-engine distinct alias state |Science BlackHole1; Sixties0; Science reopens1 |
| Concurrent second-instance launch |Rejected while first config remains alive |
| Other instance idle stop |No Wine command, first config remains alive |
| Original bitmap font selection |Verified actual Wine font trace |
| Existing-identity migration fixture |Bytes unchanged |
| New grouped Nature + all five stock3D engines |Different actual3/5s frames; physical mouse exits0 |
| Owned Xvfb / temporary state cleanup |Exit0 / removed |

The report records runtime/checker/catalog source hashes. The final runtime source hash matches the implementation at this checkpoint. The earlier interactive-preparation proof took26seconds, but it is historical evidence under different cache/runtime conditions—not a controlled speedup benchmark. Fresh-prefix initialization is still work and should be prepared off the GTK thread, preferably before the user requests a saver. Warm preparation is a few milliseconds.

A separate real LinuxGTK background test is retained at `lens-linux-quiet/`; its pre/post-prepare pixel digest is identical, the original Lens distorts the checkerboard, temporal frames differ and physical mouse dismissal returns18. Exit18 is observed for this original engine and is not treated as a failed dismissal. `lens-linux-gtk/` retains the earlier updater-branding defect as a negative control.

## Tests and genuine corrections

-119 screensaver unit/regression tests pass, including29 new shared-group/font/quiet-preparation cases over the original runtime baseline.
-186 theme tests pass at this checkpoint.
- Actual guest checks exercise cold/warm IO, real original config handlers, original font selection, kernel group-lock exclusion, state persistence, original animation and XTest dismissal. They are not mocked unit results.
- Fixed the per-presentation roughly581MiB duplication and historically incorrect isolation of Plus General settings.
- Fixed the visible Wine updater leak found by a screenshot of a real GTK background.
- Fixed a parser corner case permitting exact dot/dot-dot identities; rejected identities are covered by regression assertions.
- Added failed-font rebuild rollback/temp cleanup, installed-font tamper checks and cleanup-failure lease retention tests.

Syntax compilation and diff whitespace checks pass. Unit fixture updates for newly required NE fonts are not counted as product defects.

## Recovery and integration

The checkpoint `before-saver-runtime-groups-20261127` was verified before broad preparation. Its evidence is `gl-runtime/before-runtime-groups-checkpoint.json`. Product source changes are limited to screensaver_runtime.py, stage_screensaver_assets.py, their tests and the new disposable proof tools. No live installation, user test-VM reset, shared UI edit or commit/push was performed by this agent.

The installer dependency manifest's installed-version audit already passes16/16 packages, including32-bit GLX/DRI and OSMesa. Those system dependencies remain distinct from private original font/executable assets.

Root should regenerate the private bundle, include these source changes in its normal immutable release, run the consolidated suite, and reset the human test session only through its normal deployment flow. The UI agent confirmed its host uses public APIs and releases its own idle lease before cold group warmup; queued stale requests are generation-canceled.

Remaining acceptance: original-VM matched control/window pixel regions, all individual saver parameters/help/font-picker content, audio, every functional-level combination and final human interaction on the deployed build. This checkpoint does not claim those untested areas are complete.
