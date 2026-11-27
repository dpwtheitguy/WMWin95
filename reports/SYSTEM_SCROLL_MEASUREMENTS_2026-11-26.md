# Native System Device Manager scrollbar — November 26, 2026

Measured in the offline classic Windows 95 reference. Checkpoints `before-system-scroll-measure-20261126` and `before-system-scroll-v2-20261126` were verified and restored after their respective probes; floppy returned empty. No device settings were changed. The classic reference is released.

Accepted metadata/screenshots/crops: `private/system-scroll-20261126/reviewed-v2/`; consolidated `measurements.json`. The first pass did not select the Win16 tab and is rejected. Its private General-page screenshots contain license text and must not be shared as evidence.

Actual main HWND: **410×448**, origin (132,120). The native tab/tree classes are `SysTabControl` and `SysTreeView`, not their Win32-suffixed variants. Tree id1100:

- HWND rectangle: **(28,90,353,267)** relative to the sheet.
- Client rectangle: **(30,92,333,263)**, excluding the native scrollbar and inset border.
- Vertical bar: **(363,92,16,263)**; arrows16px each.
- Usable track: **(363,108,16,231)**.
- GetSystemMetrics reports scroll width16, arrow height16 and nominal thumb height16. This does not establish the minimum proportional thumb size.

`GetScrollInfo(SB_VERT,SIF_ALL)` returns actual item units:

| State | Range min/max | Page | Position | Visible expanded items | Outer thumb rectangle |
| --- | --- | ---: | ---: | ---: | --- |
| Original collapsed categories | 0 /20 |16|0|21|(363,108,16,176)|
| All categories expanded, top |0 /30|16|0|31|(363,108,16,119)|
| All expanded, middle |0 /30|16|7|31|(363,160,16,119)|
| All expanded, end |0 /30|16|15|31|(363,220,16,119)|

Total TreeView item count is31 throughout; the original21 expanded-visible items must not be confused with total item count. Visible capacity is16. `TVM_GETITEMHEIGHT` is unsupported here and returns0. `GetScrollBarInfo` is absent on this Win95 USER32, so outer thumb rectangles were measured from raw framebuffer bevel edges. The probe resolves that newer API dynamically and does not import it as a required entry point.

The native thumb includes an outer FACE band with a black right edge, then an inner white highlight. At top it begins at108, not109: counting only the inner bevel would incorrectly report118 instead of119px. Framebuffer center-line color runs are preserved in JSON.

The track ratio yields231×16/21=176px and231×16/31=119.226→119px. In the31-item case, travel is112px; position7 of maximum15 gives52.267→52px, putting the thumb at160. These examples exclude ceiling rounding but do not distinguish floor from nearest rounding. Extreme minimum-thumb behavior was not measured. No additional capture loop was performed to infer unsupported rules.

The exposed native track is **solid white** for this TreeView. A fixed21px thumb creates excessive white space; changing that control's track to gray would hide the geometry defect while contradicting the actual native control. Root owns the System sizing/proportional-thumb implementation and regression integration.

Primary API references: [SCROLLINFO](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-scrollinfo), [GetScrollInfo](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-getscrollinfo), [SCROLLBARINFO](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-scrollbarinfo). Actual Win95 captures determine the measured geometry; current API requirement tables do not establish which functions existed on this historical VM.
