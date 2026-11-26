# Mouse Properties, basic cursors and Plus! — 2026-11-26

Baseline: the local Windows 95 OSR2.5/IE4 installation, 800×600, 256 colors and 96dpi. The implementation also receives 1280×720 checks. This report accepts specific behavior and regions, not the complete historical applet or a finished general window manager.

## Delivered behavior

Control Panel → Mouse opens a native-size four-tab sheet. Open, Properties, Enter and Mouse shortcuts reach the same instance. Buttons, double-click timing, pointer artwork, pointer-file Browse/Use Default, list scrolling, and motion acceleration have working application paths. Apply saves; Cancel discards pending edits while retaining earlier applied changes. Startup restores saved settings. Backend/save failures roll back the session and server settings.

The basic Windows 95 pointers are the default `(None)` scheme. Windows Standard aliases that same basic set. The existing 3D pointers remain optional, with large, extra-large and Animated Hourglasses choices. Basic artwork and hotspots come from the original USER.EXE cursor groups, including the otherwise easily missed pen, I-beam and precision cursor. Resize roles follow the actual registry/INF order, not the numeric filename order.

All pointer assets present in the local Plus! cabinet set are available: 12 theme sets and 15 additional animated pointer choices. Together with the six base/alias choices, the catalog has **33 schemes**, **241 distinct source cursor assets**, and **585 decoded frames**. This is an inventory of this media variant, not a claim about every separately released Plus! edition. It uses original assets rather than lookalike drawings.

CUR/ANI loading preserves dimensions, hotspots, ANI frame order and per-step jiffy durations. Animated choices change actual GDK cursor handles as well as previews. Applying a scheme starts its timeline anew. Preview redraws occur when the displayed frame changes; ordinary themes with only busy/wait animation do not continuously refresh an unchanged desktop arrow. A bounded, scrollable selector makes all 33 choices reachable.

The actual X11 button mapping swaps logical buttons 1/3 without moving wheel or side-button mappings. GTK receives the double-click threshold. The test area uses the pending threshold and the original 32-frame MAIN.CPL jack-in-the-box animation. Motion changes X11 acceleration and verifies readback. Existing server settings are read before an unrelated artwork change, and equivalent acceleration fractions are accepted.

The live guest was switched to the requested basic scheme through Apply, preserving its saved double-click timing and speed. Its prior unapplied Large-pointer preview is preserved in the `before-basic-plus-pointers-pending-large` VM snapshot.

## Native screenshots and acceptance evidence

Original captures are separate from implementation output and remain private. `make check-pointer-catalog` saves a report and every scheme's screenshot at both resolutions. The test runs every scheme through Apply and creates each of its fourteen role cursors: 462 role bindings per resolution, not 462 independent unit tests.

The basic comparisons cover top, middle, bottom and selected-precision list states. Each state checks the complete six-row list, its preview well and each of six pointer images. All fourteen unique roles are covered. **All 32 named basic region assertions have zero differing pixels**, including labels, spacing and selection colors. The Plus! Dangerous Creatures normal arrow and one independently captured animated bee frame also match with zero differing pixels. There are 34 reference-region assertions per resolution, 68 across both runs. This does not claim that every Plus! frame has been independently screen-captured in the native VM.

The full default Buttons sheet, rectangle 44,44,404,448 in its native capture, also has zero differing pixels at both resolutions. The native pointer was outside the staged artwork rectangle.

The comparison test consumes `native-basic-pointers-{top,middle,bottom,cross-selected}.png` and the independent Plus! preview captures in `private/screenshots/start-development-20261110/`. See the current `private/screenshots/pointers-*` and `mouse-*` reports for exact rectangles and failures. The local comparison montage is under `private/screenshots/pointer-comparison-20261126/`.

## Tests and defects found

Project unit tests: **91 passing**. Tests cover preference validation, default basic selection, resize order, Apply/Cancel/restart, backend and save rollback; CUR bounds/hotspots; ANI frame counts, frame order, variable rates, malformed input and original legacy RIFF lengths; animation timeline boundaries/wrap; RLE8 runs/deltas/truncation; and visible reference launch/recovery safety. A complete guest `make test check-ui` passed for the runtime source, including the new Mouse and pointer-catalog scenarios at both resolutions. The additional launcher tests are independent of the runtime GUI.

Interaction checks include pointer and keyboard selection, slider bounds, native test animation, real X11 mapping and acceleration readback, GTK timing, failed application behavior, Cancel, reopening, every role image, CUR Browse/Use Default, popup Escape, long scheme-list navigation, list thumb endpoints, Control Panel routes, and shortcuts. Runtime animation is tested by advancing the clock across a frame boundary and verifying the actual GDK cursor changes.

Genuine defects corrected during this work:

- The separate CUR files were 3D/large schemes; using those as defaults omitted the plain USER.EXE pointers.
- Numeric resize filenames were assigned to the wrong labels.
- Pointer images were five pixels right of the native list origin, the preview was mispositioned, and list labels were two pixels low.
- Basic I-beam/precision inversion pixels disappeared when treated as ordinary icon transparency. The masks are retained; previews reproduce the native selected and gray-well palette results.
- The preview cache initially used inconsistent keys, causing unnecessary decoding. It now caches by frame and background.
- Some original Plus! ANI headers count the RIFF header in the declared size. A narrowly scoped compatibility case handles these originals without accepting arbitrary truncated chunks.
- An unbounded scheme popup would clip the added choices. It now scrolls and supports keyboard access to the final item.
- Applying artwork could have reset existing speed/mapping to defaults. Initialization now reads the server, and Apply rolls back on failure.
- A one-pixel button hit-target mismatch and the missing namespace Enter route were caught and corrected.

## Explicit remaining work

Pointer trails, named custom scheme Save As/Delete and Windows driver replacement remain disabled and explained by Help. General device details are minimal. The sheet's full Alt+Space system menu and large-font/DPI layouts are not accepted yet.

X11 cursor images do not directly implement Windows' screen-dependent XOR inversion. The basic arrow and ordinary opaque artwork are original; I-beam/precision runtime cursors match on a white editor surface, but inversion over arbitrary colored surfaces remains a limitation. The tested applet previews reproduce the measured original palette behavior. Third-party application cursor themes and consistent busy/wait activation across every application still need integration.

Acceleration readback does not prove physical response: an absolute VM tablet may bypass it, and per-device libinput behavior needs a physical relative-device UAT pass. Hardware double-click tolerances and fractional host-viewer scaling also remain manual UAT requirements.

## References and recovery

The intended visible set is Win95LX plus three Windows references: IE4, pre-IE4 classic and Plus!. The temporary headless probe is stopped. Plus! installed successfully in its own copied disk and rebooted; `plus95-desktop-working` and `plus95-pointer-preview-working` checkpoints are retained. The classic disk completed installation from its repaired local C: setup source. Its 800×600, 256-color desktop and pre-IE4 Explorer/Shell32 versions are verified, with `classic-pre-ie4-verified` saved. See the reference-set report for final status.

Reference launchers default to visible GTK windows. Normal launches preserve the latest disk; restoring a snapshot is an explicit recovery action. Visible instruction-clock references use real-time sleep pacing for meaningful animation comparisons. Copyrighted media, original art, fonts, registry data and VM disks are excluded from Git.
