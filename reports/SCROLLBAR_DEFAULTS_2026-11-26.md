# Scrollbar defaults and Device Manager — November 26, 2026

The initial report identified a white Device Manager track. Independent native review shows the original classic Windows 95 TreeView also has a white exposed track. The real Device Manager defects were a fixed 21-pixel thumb, inaccurate control geometry and an incorrect raised-frame outer band. Those defects exposed much more white than the native control.

## Corrected shared primitives and integration

The generic Cairo scrollbar now explicitly paints classic system-gray/white one-pixel stipple, using a cached nearest-filtered tile. A white track requires explicit `track="window"` and recorded native evidence. Device Manager, Mouse's pointer list, Sounds' tree and the wallpaper list preserve measured white control-specific tracks. Namespace views reuse the shared tile instead of repainting thousands of individual stipple pixels.

Native scrollbar faces have a FACE outer top/left band and an inner white highlight, unlike a normal command button. The shared face renderer now reproduces that shape. `VerticalScrollbar.for_page` provides proportional thumbs; callers with measured artwork remain separately scoped.

Native System measurement established main HWND **410×448**, client region **(30,92,333,263)** and scrollbar **(363,92,16,263)**. The track is 231 pixels. Page16 gives thumb176 for21 visible entries and thumb119 for31. Positions0/7/15 give outer thumb tops16/68/128 relative to the scrollbar. The four complete **16×263** independently captured native scrollbar cases have **zero differing pixels** in the corrected renderer. Sources: `private/system-scroll-20261126/reviewed-v2/measurements.json` and native PNGs; see `SYSTEM_SCROLL_MEASUREMENTS_2026-11-26.md`.

System uses the measured page-aware geometry, corrected frame crop/width, clipped rows, actual page hit regions, thumb dragging and wheel scrolling. Endpoint interaction and control-owned track checks are in `dev/check_scrollbar_tracks.py`. Geometry rounding outside the four captured native fixtures and other full scrollbar states remain independent acceptance work.

## GTK and audit scope

The GTK audit found missing trough-node styling, theme transitions/interpolation, incorrect empty-range thumb behavior and overlay gutters. Scoped shared styling now explicitly handles scrollbar/contents/trough/slider/steppers and relevant states, with generated 1x/2x PNG resources. Native app-specific white tracks are intentional; an empty WordPad actually hides its scrollbar and its editor body must not be mistaken for a track. Detailed 52-case/resolution/scale evidence is in `GTK_SCROLLBARS_2026-11-26.md`.

Primitive tests check default stipple, parent-background isolation, moved phase, endpoints/no-overflow and explicit native exceptions. The real-consumer audit covers System, Fonts, Font Preview, shared ChoicePopup and independent native exception regions. Additional existing suites exercise Mouse/Sounds/Display/file/folder consumers. This is not a claim that every scrollbar's dimensions, arrow press/repeat and all native states are accepted.

The controls skill now requires exposed-track samples above/below thumbs, exact RGB/stipple phase, real node ownership and focused/disabled/selected/scroll-position coverage. Independent review of 33 control families remains recorded in `CONTROL_DEFAULTS_AUDIT_2026-11-26.md`; other legacy command paths and wallpaper-list inactive selection are still open.
