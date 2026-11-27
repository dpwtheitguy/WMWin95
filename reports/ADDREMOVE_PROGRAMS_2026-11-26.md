# Add/Remove Programs — isolated prototype acceptance, November 26

Status: **unregistered, read-only prototype**, ready for integration review; not a working package installer or accepted compatibility-profile switch. The existing live Control Panel was not changed. No packages, games, Office, guest policies, host settings or startup media were installed/changed.

This implements the approved home described in `docs/FUNCTIONAL_PROFILES.md`: Add/Remove Programs → Windows Setup. The optional curated Installed Programs entry **Desktop Enhancements** opens that same page. It adds no default Control Panel icon. All 39 feature entries and four presets from `config/functional-profiles.json` remain unavailable until their actual consumers and Apply/Cancel contracts are accepted; unknown live values remain `None`, not invented installed/unchecked state.

## Original measurements and implementation

Primary evidence is licensed original Windows 95C native HWND metadata, native screenshots and shipped dialog resources. Classic, IE4 and Plus captures were reviewed at `private/screenshots/cpl-20261126/{classic-reviewed-run2,ie4-run2,plus-remaining}/addremove-*.png`; installed-program contents differ by configuration. No claim of RTM coverage is made.

Fresh IE4 measurements are under `private/reference-tools/addremove-native-20261126/metadata/` and `private/reference-tools/addremove-details-native-20261126/metadata/`. Main window: 367×443, 96 dpi, 8-bit; page origin (13,51), 341×349; 13px MS Sans Serif. Main footer HWNDs are 75×23 at (121,410), (202,410), (283,410). Windows Setup list is (24,123,320,94), with 18px owner-drawn rows and **11×11 checklist glyphs**. This is a SETUPX owner-drawn **ListBox**, not a TreeView. The actual compact Details dialog is 347×379 with its own OK/Cancel, no caption Help button. APPWIZ.CPL PE resource 101 and SETUPX.DLL NE resources 379,378,4202 are parsed by the private stager.

The deliberately scoped list uses measured native glyph assets, shared bitmap text, shared command buttons and shared vertical-scrollbar geometry. A native exposed track rectangle (329,180,12,16) contains 192/192 pure white pixels; that explicit `window` trough is recorded in `private/shell-assets/addremove-track-measurement.json`, rather than inheriting arbitrary GTK white. Full owner-drawn row/focus/scrollbar acceptance remains outstanding.

`tools/stage_addremove_assets.py` stages seven provenance records, four native frames, three checklist glyphs, HWND metadata, dialog resources and the track measurement. Native assets and hashes remain private. A real capture defect was discovered: the fresh Startup Disk screenshot was occluded by the Win16 Details child despite correct main HWND metadata. It is explicitly excluded as a frame source; the independently archived unobscured IE4 Startup Disk page at (22,22,367,443) is used with its own hash and source rectangle. The native capture VMs were returned to their pre-probe snapshots and the temporary floppy ejected.

## Model, input and transaction boundary

`control_panel/addremove_preferences.py` supplies immutable catalogue/snapshot data, cached explicit activation/refresh, a curated `dpkg-query` reader and a typed transaction boundary. No APT/sudo/shell command is constructed. The default builtin-only registry makes no package subprocess call. Registered application labels are shown, not the complete Debian dependency list. Package arguments and feature identifiers are bounded/validated.

Actual loading and future service execution run off the GTK thread; paint and list interaction read in-memory state. Late loading results after window destruction are discarded. The component list is one Tab stop, supports selection, keyboard Home/End, scrolling, arrow/page hits and thumb dragging, and clips partial-row text and hit targets to the client. Details edits are independent pending data: child Cancel discards, child OK merges to the parent, parent Apply is the transaction boundary.

Only an explicitly writable injected service can change accepted component IDs. Tests demonstrate stale-state rejection, pre-commit cancellation, scoped rollback and authoritative readback with a fake service. Recovery failure remains explicit and invalidates the cache; it is never reported as success. Invalid requests do not poison pending data. This is a service contract, **not evidence that APT installation or version rollback already works**.

Unavailable Install, Have Disk and Create Disk have specific reasons exposed through the existing property-sheet Help/tooltip paths. Unavailable feature checkboxes have no toggle action. Current global state is disclosed as unavailable in Details; presets are not represented as currently active.

## Acceptance evidence

| Layer | Actual result |
|---|---|
| Pure model unit tests | 20 passing in `tests/test_addremove_preferences.py` |
| Isolated GTK 800×600 | pass; eight exact region comparisons, zero differing pixels; eight behavior groups |
| Isolated GTK 1280×720 | pass; same eight comparisons and eight behavior groups |
| Real installations | zero |
| Live registration/deployment | none |

GUI results/screenshots: `private/screenshots/addremove-prototype-final-{800,1280}-20261126/report.json` and adjacent PNGs. The eight comparison regions are caption/tabs for all three main pages, native default OK on Install/Windows Setup, and Cancel on all three pages. These include reused original static frame regions and freshly rendered shared command buttons; they do **not** establish complete dynamic-list or whole-applet identity. Startup Disk native Create Disk owns default focus, while that unavailable command intentionally leaves our OK as the enabled default; that native OK comparison is explicitly omitted.

Behavior checks cover all 43 entries unavailable/unknown; same-page Desktop Enhancements routing; disabled keyboard/pointer toggles; child Cancel/OK; fake async Apply/readback; injected partial failure rollback with pending edits preserved; actual wheel/arrow/page and thumb endpoints; keyboard selected-item reveal; client hit clipping; ten cached repaints; one native list Tab stop; and destroyed-window async result rejection. All GUI tests use an explicit isolated X11 display, temporary HOME and read-only/fake services. They refuse primary display :0/:1.

The measured construct/load/**settle** duration was 159.93ms at 800 and 163.92ms at1280. The harness deliberately calls its normal event-flush settling helper; these values are **not first-paint latency** or a cold-boot benchmark. No responsiveness or boot-speed improvement is claimed. Source/config hashes and the unit log are in `private/research/addremove-prototype-20261126/`.

Prototype defect discovery corrected atomic pending validation, partial-row checkbox hit overflow, description painting behind Details/count controls, missing thumb dragging, inappropriate one-Tab-stop-per-row behavior, and stale async completion. The capture occlusion and native Startup Disk default-button mismatch were caught by comparisons rather than waived as identical.

## Remaining release gates and next integration

1. Implement and review the scoped typed guest installer service, exact curated package registry, allowlists, dependency/conflict resolution, cancellation/progress, persistence and realistic package recovery. No blanket APT/sudo policy.
2. Bind the first real compatibility settings to actual consumers, validate profile dependency resolution and apply mode (live/reopen/session restart/reboot), then enable only those entries. Root's entire catalogue remains read-only now.
3. Replace prototype generic category imagery with measured per-component assets; accept dynamic selected/unfocused/disabled/focus rows, owner-drawn checkboxes and scroll geometry independently. The custom category text and current unknown-state glyphs are deliberate new component data, not a claim that original Windows shipped these options.
4. Finish native startup-media capability or keep it disabled with the existing specific reason. Have Disk intentionally cannot install arbitrary unregistered content.
5. Integrate staging/registration through root review only after the service and actual feature bindings exist; add resolved-profile notification, reopening/preservation and real nonadmin guest tests before shipping. Preserve the current eight accepted applet backends and live desktop.
