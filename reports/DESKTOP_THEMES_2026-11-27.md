# Desktop Themes — working three-component subset, final review

Current delivery: registered in release `ecf12b033a5104fe`; wallpaper, pointers
and sounds are functional. Root completed normal non-admin UI Apply/reopen and
exact preference restoration. Full selected-photo/whole-theme fidelity remains
open. [Consolidated delivery](APPLET_DELIVERY_2026-11-27.md) records final checks
and scope. Earlier sections retain prototype findings and superseded states.

The final iteration below supersedes historical prototype limitations that are explicitly resolved. Full selected-theme preview and all components are not accepted.

Original source: private Plus!95 media, PLUS.INF and CAB members. PLUS.INF
lists THEMES.EXE 4.40.0.310 (86,016 bytes) and THEMES.CPL (15,360 bytes).
Running `themes.exe` in the working Plus95 reference opens **Desktop Themes**.
The native dialog is 591×449 guest pixels at (104,62) in its 800×600 session.
`private/themes-20261127/native-settled.png` records the actual fully rendered
window; `native-launch.png` is an incomplete first paint and is not accepted.
`native-first-theme.png` actually records the open theme chooser, not a selected
theme. Preserve that distinction when staging evidence.

Recovery checkpoint `before-themes-20261127` was verified before inspection and
restored afterward. No theme was applied. The Plus reference lease is released.

Native controls include Theme, Save As, Delete, Screen Saver preview, Pointers,
Sounds, etc. preview, seven component checkboxes, OK, Cancel and Apply.
Component labels are Screen saver; Sound events; Mouse pointers; Desktop
wallpaper; Icons; Colors; Font names and styles; Font and window sizes. Current Windows settings disables
the component controls. Native preview includes actual desktop icons and sample
active/inactive/message windows. This is not a generic tabbed property sheet.

The new unregistered model parses original manifest names and theme component
references without executing any EXE/SCR. PLUS.INF maps both 16-bit WAV and 8-bit
WA8 files to the same installed long names; callers select this explicitly.
Paths are confined to the private source library. Ten non-default theme files
currently pass full parsing. DEFAULT and WIN95 include base Windows Media
references requiring an explicit additional source mapping. WIN95HC contains
an isolated `av` line which the strict parser rejects; provenance inspection is
pending. Existing pointer and sound staging already read their specific sections
and offer all twelve Plus schemes, so this full-parser limitation does not mean
those schemes are absent from the product.

Nineteen CPU tests pass: atomic apply/persistence; Cancel; component subset;
failure after mutation at each of three providers; persistence failure; rollback
failure reporting; unsupported/duplicate/unknown selections; unavailable provider;
8/16-bit alias selection; ambiguous manifest rejection; safe theme resolution;
and traversal/external-path rejection. Additional tests exercise the actual
Wallpaper and SoundBackend/PreferenceController models, missing wallpaper,
pending edits and exact old preference bytes. These CPU tests do not establish
GUI acceptance. PreferenceProvider captures the raw backend snapshot as well as
preference bytes; restoring through Apply would needlessly validate old WAVs and
could fail to restore an already valid original backend state. This defect was
found by the added real-controller test and corrected.
Two additional cases verify reopening loads the persisted selection without
reapplying providers, and malformed/unknown/unsupported saved selections produce
no backend effects. Initial prototype lost the selection on reopen; corrected.

An unregistered UI and private asset stager now exist. The stager provides all
twelve Plus95 theme wallpaper mappings, original-byte copies and provenance;
it reads only the Desktop section rather than executing or forgiving unrelated
malformed data. Existing staged Plus pointer and sound schemes supply their
corresponding components. Save As, Delete, screen saver preview and combined
pointer/sound preview are disabled with reasons. Unsupported colors, font/style,
window metrics and icons are disabled. Wallpaper-only preview is functional;
native sample windows/icons are not reproduced. Original Stretch behavior is
not reproduced: current Wallpaper supports center/tile. This is a discrepancy.

Owned-Xvfb UAT at both 800×600 and 1280×800 passed seven checks each, recorded in
`private/themes-20261127/{800,1280}-transaction-verified/report.json`. It applies
Nature using the actual Wallpaper model, changes the existing Plus cursor scheme
in the isolated session, loads Sounds through the runtime preference reader,
then injects a failure after actual Travel sound application. Wallpaper, mouse
and sound state plus all four exact JSON files restore to Nature. Cancel retains
the applied selection. These use UI action/model calls, not a complete physical
pointer/keyboard UAT matrix. No live desktop or hardware settings were touched.

At 800×600 construction measured 3.54ms, first draw 7.64ms and Apply 17.90ms.
These are single isolated-host samples, not guest boot or sustained benchmarks.
Static caption and outer bottom frame are zero differing pixels at both sizes,
because they reuse the native frame. This does not accept dynamic controls,
text, preview, checkbox rendering or scheme propagation pixels. Machine-readable
results are `private/themes-20261127/static-region-comparison.json`.

The applet remains **not ready to register or deploy**. Native preview parity,
actual input UAT, measured control states, error/Help interaction, reopening,
caption-system-menu compatibility and remaining visual comparisons are pending.

Next: validate physical pointer/keyboard interactions and error states, replace
the hand-painted checkbox with independently measured shared/native controls,
implement native preview parity and compare dynamic states before registration.

## Independent follow-up: physical input and preview

`800-preview-final` and `1280-preview-final` add real XTest input on the owned
X server: Tab/Home/Down select Nature; pointer toggles Mouse pointers; Space
rechecks it; pointer Apply commits; opening the actual chooser and End/Enter
selects a different pending theme; pointer Cancel retains all applied files.
Full real-provider rollback still passes at both sizes. The harness explicitly
sets input focus on its own window because Xvfb runs without a window manager.

This caught a genuine tab-order bug: inherited caption Close shared Cancel's
action ID and appeared before the Theme field. Desktop Themes now supplies
explicit field/component/button order. No shared PropertySheet was changed.
The original EXE caption is not a question-mark CPL; its maximize region no
longer incorrectly invokes Help. Minimize/maximize/system-menu parity remains
pending and no behavior is invented for those buttons.

Checkboxes now reuse the independently measured native 13×13 Accessibility
checkbox sprites already in the private library. Native Plus disabled checkbox
border measurement establishes origin (438,185), correcting the prototype's
one-pixel offsets. Focused enabled labels receive a dotted rectangle; disabled
text uses embossed white/shadow. New focused field and checkbox screenshots
are preserved. These states still need independent full native comparisons.

The preview now combines theme wallpaper with original default desktop-icon and
sample-window pixels. Colors/icons/font components are disabled, so preview
keeps their current default appearance rather than pretending these components
were applied. A **derived product layer** makes the original teal transparent
and clears the captured pointer from a uniform white sample edit region. The
raw native image is untouched and this derived layer is never baseline evidence.
Pointer cleanup rectangle is explicitly recorded in the stager. Stretch and
alternate current appearances remain discrepancies. No new reference lease was
taken during this follow-up and no live Linux display was accessed.


## Final functional subset — November27

The module is ready for the root's production-bundle guest review and normal
Control Panel registration. Root owns deployment, restart and consolidated sprint
acceptance. This agent did not deploy the live VM or commit. Supported components
are Desktop wallpaper, Mouse pointers and Sound events, independently selectable.
All twelve original Plus theme mappings resolve actual supplied wallpaper,
pointer and sound libraries. Existing providers handle the session effects;
no Windows executable/screensaver runs in Linux.

### Genuine defects corrected

* Persisting wallpaper was insufficient: the prototype never populated
  `shell.wallpaper_images`, so the live desktop could remain teal until restart.
  Apply/rollback now decode the active custom wallpaper, invalidate the cached
  palette surface and repaint. The integration test checks the actual GDK root
  framebuffer outside the applet as well as the live image cache.
* The old pointer adapter rewrote device settings from a stale MouseController.
  `PointerThemeProvider` reads current session preferences and changes only
  artwork/overrides; speed, button mapping and double-click timing stay intact.
* Saved theme metadata could mislabel independently changed preferences. Reopen
  reconciles selected components against actual wallpaper placement, pointer
  scheme/overrides and complete sound-event mapping. Canonical resolved file
  paths are compared; an initial symlink-path comparison falsely invalidated a
  valid applied theme and the production-bundle integration test caught it.
* A Sounds applet opened and closed after Themes construction could have saved
  a new custom scheme. CurrentPreferenceProvider reloads authoritative saved
  sound preferences at transaction time, preserving those schemes on success
  and restoring exact bytes plus consistent backend state on failure.
* Already-open Display, Mouse and Sounds editors keep their own pending edits.
  Selected conflicting components are rejected before any provider mutation,
  with a native close-properties-first error. Unselected components may proceed.
  Tests preserve the other applet's pending values and all preference bytes.
  This is a bounded adaptation; live controller rebasing remains future work.
* Full native Theme field measurement found the prototype selection/text1–2px
  too high and missing a black inset. Its complete202×21 focused field now
  matches the native capture. Checkbox pitch is not a constant24px: native
  top coordinates are185,210,234,258,283,307,331,356. All were corrected.
* Disabled boxes incorrectly lost their check marks. The actual13×13 native
  disabled-checked control is staged separately; enabled controls reuse shared
  measured sprites. Current Windows settings is now a reachable first chooser
  item and initial keyboard focus matches the native field.
* Manual pointer cleanup in the old preview layer erased48 adjacent border
  pixels. A fresh pointer-free native capture replaced that source; no invented
  white cleanup is applied. Opaque desktop-color label unions remain opaque
  over wallpaper, rather than accidentally transparent.

### Native image pipeline and profile limits

Original Plus THEMES.EXE/MSJPEG32 does more than decode a JPEG. An independent
native probe confirmed8bpp/800×600 initially. Its24bpp mode required a reference
reboot at640×480 (the driver did not offer24bpp800×600). At24bpp, applying Nature
produced `C:\Windows\Plus!.bmp` as640×480×16 RGB555 with visible dithering.
The private original bitmap, source probe, GetDeviceCaps/EnumDisplaySettings
log and screenshots are preserved; this does not establish the complete native
TrueColor conversion/preview algorithm.

A separate native batch applied all twelve themes at800×6008bpp and copied
actual generated BMPs into an owned reference directory. The exported log has
thirteen successful copies: Dangerous Creatures was repeated identically as
Current Windows settings insertion changed the combo list. Twelve unique theme
names map to all twelve source themes. Windows Default has no wallpaper and its
failed copy is correctly excluded. Every copied theme bitmap is800×600×8,
BI_RGB. No screenshot pixel supplies these image files. Source JPEGs remain
staged alongside the native converted versions.

The logical BMP palette still differed from QMP pixels. This was independently
explained by the prepared QEMU VGA6 DAC's component expansion, specified in
[QEMU8.2.2 vga_int.h](https://github.com/qemu/qemu/blob/v8.2.2/hw/display/vga_int.h#L146-L152):
source106/92/117 becomes physical104/95/119. The stager preserves raw logical
BMPs and emits explicitly named VGA6-profile derivatives by changing palette
entries only. Current256-color product mode uses that named source profile;
TrueColor keeps the original JPEG. This is not a universal physical-PC palette
rule and does not change the global palette filter. Generated image indexes,
geometry and original source bytes are preserved. Staging returns42 provenance
records, including both forms of each native bitmap, original THEMES.CPL
GROUP_ICON101 at16/32px, measured disabled check, frame, preview layer and catalog.
The native description is “Personalize your computer.”, STRING block1,index3.

Original conversion evidence:
`private/reference-tools/themes-batch-export-v2-20261127/W95THM2/{CATALOG.TXT,T*.BMP}`.
`dev/build_theme_reference_export.py` builds a private repeatable reference-only
exporter; it does not launch or mutate a VM itself. Native controls must already
be open, the output guest directory must be new, and reference restoration is
mandatory after collection. Before/after recovery used the verified checkpoint
`before-themes-physical-20261127`. Reference is restored, running, with floppy
ejected. No other reference VM was used.

### Actual-framebuffer acceptance and remaining discrepancies

`dev/check_themes.py --palette {256,truecolor}` uses an explicitly supplied
production asset bundle (default `private/shell-assets`), an owned Xvfb and
actual GDK root-framebuffer crops. It no longer silently overlays stale prototype
assets or uses a direct draw call that bypasses the final palette filter.
The current256 scene remains within256 unique colors, so the existing bounded
palette fast path preserves its named colors. Both palette modes are repeated
at800×600 and1280×720. Native controls/caption are standard-color96dpi only.

Gated exact regions: complete focused Theme combo202×21; all eight disabled
checked boxes13×13; three supported enabled checked boxes13×13; complete default
Current Windows settings preview393×333. These are zero differing pixels in
actual-framebuffer runs. Preview sample artwork is original private artwork;
zero reconstruction does not prove a full theme renderer or every appearance.
Physical cases include F1 capability Help within viewport; field navigation;
checkbox pointer/Space; Apply; open chooser End/Enter; Cancel; provider rollback;
reopening; current metadata; all twelve real-provider apply/reopen cases; and
conflict preservation for Display/Mouse/Sounds. The twelve-theme sweep uses
controller integration calls, not twelve repetitions of physical input.

The selected Nature photo preview remains **not pixel accepted**. A diagnostic
800×600256 run differs68,514/130,869 pixels, bounding box[1,1,393,333). The native
Nature capture also has a pointer inside Window Text and is therefore rejected
as a clean full-preview acceptance baseline. It remains only diagnostic evidence.
Palette mismatch is explained/fixed for the named profile, but native preview
conversion/dither/resampling still differs; do not claim that the remaining
count is only a pointer or harmless noise. A clean matched selected-photo
capture and complete conversion protocol are the next fidelity task.
TrueColor uses modern JPEG decoding and remains similarly unaccepted. Current
preview placement stretches to the native measured inner preview surface;
complete Tile/Center/Stretch and modern-resolution native conversion parity are
not accepted. Full theme icons/colors/fonts/metrics are disabled rather than
previewed as if applied. The original outer caption/frame reconstruction is
not blanket whole-window acceptance.

Unavailable controls, with keyboard F1 explanations: Screen saver; combined
Pointers/Sounds preview; Icons; Colors; Font names/styles; Font/window sizes;
Save As custom theme; Delete installed theme. Actual engineering reasons are
missing compatible screen-saver provider/preview, shell icon/color/font/metric
integration and theme-package management. These are implementation gaps, not
inherent impossibilities on Linux. General EXE minimize/maximize/system-menu
parity remains the shared window-manager work; no caption button invokes fake
Help. Full all-Windows-version comparisons are not claimed: this applet targets
the prepared Plus95 configuration of Windows95C.

Final unit suite:25 standalone CPU tests. Actual final run paths and performance
samples are appended below after all four palette/resolution runs finish.


All four exact-final-source owned-Xvfb runs passed (including F1 and all12
provider/reopen sweeps). Each also wrote actual GDK captures, preference-effect
checks and the named native-region comparisons. Performance below is a single
isolated host sample per run, with concurrent QA load; Apply includes physical
input/event delivery and draw flushing. It is not guest latency, a sustained
benchmark or a boot-speed claim. The helper deliberately waits150ms in `flush_draws` (dev/check_menu_seams.py42–47),
which dominates the measured physical Apply interval. That interval must not be
reported as actual UI/backend latency; it does not establish a150ms product delay. Preview images are cached per immutable
source path, rather than decoded again on every redraw.

| Viewport | Palette | Construct ms | First draw ms | Physical Apply ms | Evidence folder |
| --- | --- | ---: | ---: | ---: | --- |
| 800x600 | 256 | 5.93 | 14.87 | 153.68 | private/themes-20261127/800-256-delivery |
| 1280x720 | 256 | 3.97 | 15.17 | 154.48 | private/themes-20261127/1280-256-delivery |
| 800x600 | truecolor | 5.99 | 15.94 | 155.40 | private/themes-20261127/800-truecolor-delivery |
| 1280x720 | truecolor | 5.07 | 17.38 | 151.27 | private/themes-20261127/1280-truecolor-delivery |

`dev/build_theme_reference_export.py` also cross-compiled successfully into
`private/reference-tools/themes-export-build-verified`; this build was not run
in any VM. Final source and private evidence are frozen for root guest review.


## Final caption and live-palette follow-up

Root review found a concrete enabled-but-dead Minimize caption button: the
PropertySheet caption drag rectangle overlapped its native EXE bounds. The
Desktop Themes subclass now owns the measured Minimize(536,4,16,15), caption
icon(3,3,18,17), title drag region and disabled Maximize(552,4,16,15) separately.
Native Maximize artwork is visually disabled: the measured glyph interior has
42shadow and29white pixels, with zero black pixels. It remains disabled with
an F1/tooltip reason; this is screenshot-state evidence, not a fresh HWND-style
probe. Minimize hides the window, focuses the shell and keeps its task button;
physical taskbar restoration retains pending component choices and client focus
without writing preferences. Caption dragging cannot consume those buttons.

The existing FontMenu and WindowOperation implement a fixed-size, minimizable
system-menu profile. Caption-icon click and Alt+Space expose Restore(disabled),
Move, Size(disabled), Minimize, Maximize(disabled), separator, Close(Alt+F4).
Native distinct m/n/c mnemonics route Move/Minimize/Close; keyboard Move plus
Escape restores the original position, and Close cancels pending theme edits.
Tests use actual XTest events and taskbar coordinates. This accepts those bounded
input cases, not every system-menu pixel, double-click nuance or out-of-window
pointer-move behavior. Shared general window-management parity is not asserted.

A cached profile resolver now retains original catalog data, rebuilding wallpaper
source paths only when the global palette changes. Preview drawing and Apply
preflight both refresh it. A Display palette change after Themes was opened
therefore cannot apply a stale256/TrueColor source. The model/UI regression flips
palette both directions while retaining the same pending selection/components,
checks the selected file profile, checks Apply's refresh without a paint, and
verifies no Theme preference files were written by that refresh. Those palette
flips simulate the already-tested Display preference update rather than driving
the entire Display page again. No shared palette renderer was changed.

The earlier “general EXE minimize/system-menu pending” historical note is
superseded for the bounded behavior above. Maximize/Size are intentionally native
disabled states for this fixed-size dialog, not enabled unfinished features.


Caption discovery also caught release-outside cancellation losing the client's
focus. A physical press/move-out/release regression now leaves the window visible,
its position unchanged, pending settings intact and the old client focus restored.
The visible system-menu Alt+F4 accelerator is routed even while its popup owns the
grab; Close via that accelerator and the c mnemonic both discard pending edits
without changing persisted theme state. Ctrl+Esc releases the popup before handing
Start to the shell. Final palette/resolution checks retain the named zero-pixel
gates; exact final guest source validation is performed by root after this freeze.


The rapid canceled-press then successful Minimize test initially failed in all
four new near-miss runs: GTK emitted a duplicate double-click press for the same
hold, replacing the remembered client focus with the Minimize action. The final
handler records client focus only on the first press. Corrected800×600256 input
passed before the final three paired runs. Prior failure output is retained;
this does not invalidate the earlier non-near-miss passing scenarios.

All four repeated-press-fixed palette/resolution runs completed successfully at
`private/themes-20261127/{800-caption-repeated-press-fixed,1280-caption-repeated-press-fixed,800-truecolor-caption-repeated-press-fixed,1280-truecolor-caption-repeated-press-fixed}/`. Each retained zero differences
in every gated native region and passed12 actual-provider apply/reopen cases.
The final source is frozen for the root's guest validation.
