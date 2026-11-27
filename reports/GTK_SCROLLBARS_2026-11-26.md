# GTK scrollbar audit — 2026-11-26

Completed a bounded audit of all four GtkScrolledWindow construction sites: Notepad, WordPad, fallback FileDialog and native-art FileDialog. This does not audit unrelated GTK controls or claim whole-scrollbar pixel acceptance.

## Independent native measurements

Fresh native IE4 Windows95 screenshots and measurements are in `private/screenshots/gtk-scrollbars-20261126/`. The original VM was protected by the verified `before-gtk-scrollbars-20261126` checkpoint and restored afterward. No documents were saved or settings applied.

- Notepad empty and45-line documents: exposed vertical region(584,80,12,100) is1200/1200 RGB255 pixels.
- WordPad40-line document: exposed vertical region(580,160,12,100) is1200/1200 RGB255 pixels.
- Common File Open at C:\Windows: exposed horizontal region(240,219,150,12) is1800/1800 RGB255 pixels.
- Native empty Notepad retains scrollbars with no thumb and disabled gray arrows. A sampled arrow contains16 RGB128 glyph pixels, versus16 black glyph pixels when enabled.
- **Native empty WordPad has no vertical scrollbar.** An initial white sample there measured editor body, not track. It is explicitly marked invalid in `native-track-measurements.json`; it is not acceptance evidence. WordPad retains AUTOMATIC visibility and uses a non-overlay gutter only when a scrollbar is required.

Consequently, white is an intentional measured application profile in this reference, not proof of a theme leak. Notepad, WordPad and common file dialog profiles explicitly retain white exposed tracks. The file dialog measurement is horizontal; applying its white profile to the corresponding GTK vertical list track is a profile-consistency choice, not a directly captured native vertical comparison. Other Windows versions/themes remain unproven.

## Changes

`SCROLLBAR_STYLE` in `shell/accessories.py` supplies scoped root/contents/trough backgrounds and explicit slider/button states. Generic `win95-app-scrollbar` / `win95-scrollbars` controls use a generated192/255 checker; the measured app profiles explicitly use white. No unscoped global GTK theme override was introduced. Styles are included by standalone Notepad, WordPad and both file dialog providers as well as accessories.

Two public, generated resources are owned project art, not extracted Windows assets:

- `src/win95lx/shell/resources/scrollbar-track.png`:2×2 RGB checker.
- `src/win95lx/shell/resources/scrollbar-track@2.png`:4×4 nearest-pixel replica.

GTK `-gtk-scaled` selects the correct resource at1×/2×. Runtime file URIs resolve relative to the installed module, not a development path. Missing assets fall back to explicit solid192 rather than theme inheritance; the regression preflight requires both resources and fails if either is absent. Root confirmed production installation/archive includes source resources.

`style_scrollbars(scroller)` observes adjustment range changes and replacements. It adds an unscrollable class when upper−lower≤page_size, hides the full-range thumb explicitly, and grays arrows. It does not disable text editing or intercept scrolling, and value-only changes do not cause range-style callbacks. Watchers disconnect on adjustment replacement and widget destruction. The helper is used at the four existing ScrolledWindow construction sites. WordPad and fallback dialogs now disable overlay scrolling; automatic visibility remains intact.

## Genuine defects and lessons

- The old Notepad CSS used root background#e0e0e0 and lacked a deliberate trough profile; WordPad inherited scrollbar style. Explicit app profiles now make appearance deterministic without incorrectly forcing native white tracks gray.
- A valid PNG data URI silently rendered as solid192 in this GTK3 setup. File-backed resources work; the data-URI experiment is excluded.
- A single2×2 PNG interpolated at2× scale into RGB192/203/215/227/231. The explicit@2 resource eliminates intermediate colors.
- A25/75% diagonal gradient produced25% white instead of50%; a30/70%1× experiment passed but was rejected for production in favor of raster resources with verified2× behavior.
- GTK draws a full-length gray slider when an always-visible editor has no scroll range. Its CSS nodes are not marked insensitive, so a range lifecycle hook was necessary to reproduce native empty Notepad.
- Opacity alone did not remove that gadget's visible fill. Explicit transparent background/border and no shadow were necessary.
- An empty→populated→empty transition produced intermediate RGB240 after150ms through inherited GTK animation. Scoped transition/animation suppression corrected the transient mismatch.
- Attempting to draw an automatically hidden empty-list scrollbar triggered GTK allocation warnings. Hidden native states are now checked as visibility behavior and never counted as pixel comparisons.

These findings demonstrate why CSS-source inspection alone is insufficient. The final checks render real GTK nodes and actual application providers, and distinguish observed track pixels, visibility, and unvalidated button geometry.

## Validation

`dev/check_gtk_scrollbars.py` passed at logical800×600 and1280×720, each at GTK scale1× and2× (physical800×600/1280×720/1600×1200/2560×1440). GDK_BACKEND=x11 and GDK_SCALE were forced, WAYLAND_DISPLAY unset, and the X11 display identity asserted.

Each run has52 cases: **46 rendered pixel checks and6 hidden-empty visibility checks**, plus watcher lifecycle assertions. The40 fixture pixel cases cover five profiles ×two orientations ×normal/hover/pressed/disabled states. Actual applications add six visible pixel checks and six hidden states across empty→populated→empty transitions. Generic exposed pixels are exactly50% RGB192 and50% RGB255 with alternating pattern; explicit app tracks are entirely RGB255. No intermediate colors pass. Actual app tests remove the fixture's provider before constructing apps, so they exercise their own installed CSS.

Final evidence:

- `private/screenshots/gtk-scrollbars-20261126/gtk-release-800-1x/`
- `private/screenshots/gtk-scrollbars-20261126/gtk-release-1280-1x/`
- `private/screenshots/gtk-scrollbars-20261126/gtk-release-800-2x/`
- `private/screenshots/gtk-scrollbars-20261126/gtk-release-1280-2x/`

All four report zero failures. Evidence includes source/script identity, native hashes, RGBA observations, rendered PNGs and tested sample regions. Across runs there are184 rendered checks and24 visibility checks; these replay the same control scenarios, not208 unique original captures.

Additional regression checks passed:

- All four accessory menu/body seams: Notepad, WordPad, Calculator and Minesweeper.
- Reusable Open/Save frame regions, close prompt, navigation, filter and overwrite checks (`file-dialog-regression/`).
- Three existing WordPad RTF unit tests, with PYTHONPATH=src.
- Changed modules compile and git diff whitespace checks pass.

## Remaining scope

Native thumb length, exact arrow glyphs, borders, drag tolerances and every whole scrollbar state are not pixel-accepted by this track-only audit. No claim is made for GTK scale3+, fractional compositor scaling, other reference versions, or every GTK control family. No live desktop, deployed build, shared preview or user files/settings were modified. Root's concurrent Accessibility branch is preserved; ChoicePopup was untouched. Async volume work remains frozen separately awaiting review. Printers research resumes after this bounded audit; it remains unregistered.
