# Desktop shortcut visual audit — 2026-11-27

The arrow identity was already correct after GROUP_ICON30 replaced29. Comparing the **composited icon and its full label cell** found the remaining defects: label baseline/wrapping/focus, selected-label expansion, inactive selection, opaque wallpaper-label patches, desktop spacing and an IE4 folder-specific offset/checker phase. No icon driver was missing.

## Accepted evidence

| Check | Result | Evidence |
|---|---|---|
| IE4 actual Win95LX renderer + original components,800×600 |28 comparisons,0 differing pixels | `private/shortcut-visual-20261127/release-800/report.json` |
| Same source at1280×1024 |28 comparisons,0 differing pixels | `private/shortcut-visual-20261127/release-1280/report.json` |
| Classic component profile |9 original full-cell comparisons,0 differences | `private/shortcut-visual-20261127/classic-release/report.json` |
| Configured Plus component profile |11 comparisons,0 differences | `private/shortcut-visual-20261127/plus-fullcells/report.json` |
| Label geometry/profile/focus/opaque-background unit tests |9 pass | `tests/test_icon_label_geometry.py` |
| Selection-mask identity/phase/alpha/bounds/cache tests |4 pass | `tests/test_selected_icon_masks.py` |

The IE4 runs share source identity `027b7b4274eb34c74614f4d18167c836a8def2a3badb092a7b17c0fe8edcca50`. Their28 cases include independent native component comparisons, the actual `Shell.draw_desktop` path for C:,folder,Control Panel and text-file shortcuts selected/unselected/inactive,2→8→2-line long-label behavior, and four actual-renderer opaque label unions over original Clouds wallpaper. These are not resource-identity-only assertions. Later checker-only additions improved reference-hash coverage and added the configured Plus checker; parent owns final combined-source regression/deployment.

Private gallery: `private/shortcut-visual-20261127/shortcut-comparison-gallery.png`. Its columns show native, prior renderer **recreated at the same coordinates**, and actual corrected Win95LX rendering. It is not described as a historical full-desktop screenshot.

## Measured defects and corrections

1. Native desktop icon-label text starts at **iconY+36**, with13px line pitch. Old Win95LX desktop text used+35 and a single-line ellipsis. Native ordinary labels wrap within70px; two-line selected labels share one highlight union. `draw_icon_label` now uses the measured baseline and multiline geometry while preserving the existing Control Panel `wrap_label` profile.
2. Native selected label union is `(center−max_line_width//2−2, text_top, max_line_width+4,13*line_count+2)`. Its navy body and yellow focus perimeter are one shared rectangle. Example native Drive rectangle(88,263,49,28); Control Panel(79,188,67,28); one-line file(78,338,68,15). Old code had a15px one-line fill and no desktop focus perimeter.
3. All three configured reference desktops report **75×75** large-icon spacing through scalar `LVM_GETITEMSPACING`, independently corroborating screenshot origins. Root separated desktop75px cells from existing folder76×54 constants and preserved stored manual coordinates. Expanded label hit bounds are handled by the app hook; this report does not certify every possible overlapping-label input scenario.
4. **IE4 folder artwork is special:** use `explorer-folder-32.png` at nominal iconY−1, with checker phase1 when selected; the arrow overlay remains at nominal iconY. At native nominal origin(96,377), base sits at(96,376), overlay at(96,377). Naively shifting the existing phase0 selection leaves705 wrong pixels. The proper phase1 offset produces0 differences. Other IE4 shortcut bases stay nominal/phase0.
5. Inactive desktop selection hides both the icon checker and label highlight/focus. Native Run-dialog captures and delayed native state probes prove this distinction: IE4 long item remains `LVIS_SELECTED|LVIS_FOCUSED=3` internally while foreground class is `#32770`, but its visible label shrinks and its icon becomes unselected. The helper filters effective active selection **before** computing line count.
6. Original IE4 labels are **opaque system-desktop-color patches over wallpaper**, not transparent text. Scalar `LVM_GETTEXTBKCOLOR` stays teal while list background becomes `CLR_NONE` after Clouds wallpaper is applied. Visible native patch bounds exactly equal the whole multiline union, not separate per-line rectangles. The helper fills this union in `desktop_color`; all four actual-renderer wallpaper-label comparisons are0diff.

## Important rejected hypothesis

Do **not** select/dither the arrow badge together with the base icon. Native Classic, IE4 and configured Plus selected shortcuts use the checker on the base first, followed by **untreated GROUP_ICON30**. This composition matches every icon pixel. Selecting the whole composite would introduce60 wrong arrow-badge pixels per tested icon. The optional checker phase fixes only offset base artwork, not arrow compositing.

`Painter.selected_image(...,phase=0)` preserves existing callers. The IE4 folder hook supplies phase1. Static selection masks are cached by the strong source-surface object and phase in a bounded128-entry cache; the key does not use a recyclable numeric object ID. The mask depends on source alpha. A deliberate alpha mutation requires `selected_icon_mask.cache_clear()`; current asset surfaces are immutable. No per-frame disk reads or background-pixel readbacks were added. Parent measured the separate rendering microbenchmark; it is not a whole-UI latency claim.

## Three distinct reference profiles

| Configuration | Folder source/placement | Unselected long label | Active selected long label |
|---|---|---|---|
| Classic Explorer4.00 configuration | Original shell32 GROUP4, nominalY, phase0 | Every wrapped line | Every wrapped line |
| IE4 configuration | Measured Explorer folder sprite,Y−1, phase1 |2 lines with ellipsis | All lines |
| Configured Plus + IE4 reference | Explicit COOL.DLL override, nominalY, phase0 |2 lines with ellipsis | All lines |

A roughly90-character fixture uses8 lines. A roughly200-character Classic fixture remains fully wrapped even unselected and clips at the desktop/taskbar bottom. This was **not** inferred from a newly auto-selected item: native neutral metadata reports selected index−1, focus only on My Computer, and every owned fixture state0. Separate selected metadata records the long item state3. Win95 MAX_PATH limits also constrain the full `.lnk` pathname, so this is not an unqualified claim that every255-character filename can be created in every desktop directory.

For the configured Plus reference, actual HKLM `...Explorer\Shell Icons` maps icon index8 to `cool.dll,0` and index3 to `cool.dll,11`. These resolve to COOL.DLL GROUP1/image6 and GROUP12/image72 respectively,32×32,4bpp, each0diff. Registry `Shell Icon BPP` is the literal string`16`; do not infer the selected resource variant from that setting alone. The queried HKCU overrides/themes keys were absent; that does not prove absence of every theme configuration. Files: `private/reference-tools/shortcut-visual-20261127/plus-registry.json` and the Plus checker's hashed private asset provenance. These are observations of this **configured reference**, not a claim that merely installing Plus always selects these icons. No Plus assets are autoloaded into the current baseline and no product preset toggle was introduced.

## Colors and wallpaper policy

Native Classic standard-palette focus colors were measured on teal,black,silver,red and navy. The rule is **VGA palette index XOR15**, not RGB-channel inversion: teal→red,black→white,silver→gray,red→teal,navy→yellow. `focus_color_for` implements that rule and rejects unmeasured non-VGA colors unless the caller supplies an explicit override. Unselected desktop text is white on measured teal/red/black and black on measured silver. The helper accepts `desktop_color`, `text_color` and `focus_color` overrides for a future appearance provider; it does not sample wallpaper pixels to guess the text color. Arbitrary True Color palettes remain unaccepted.

The first SPI-only wallpaper attempt left Active Desktop teal and was excluded from wallpaper acceptance. Actual `IActiveDesktop.SetWallpaper` and `ApplyChanges` returned success, displayed original Clouds, and supplied the visible opaque-patch evidence. No ignored/blank capture is treated as a passed wallpaper test.

## Reproduction and boundaries

- Baseline actual renderer: isolated `GDK_BACKEND=x11`, unset `WAYLAND_DISPLAY`, owned Xvfb; run `dev/check_shortcut_visuals.py --profile ie4 --shell --output PATH`.
- Classic components: `/usr/bin/python3 dev/check_shortcut_visuals.py --profile classic --output PATH`.
- Configured Plus components: `/usr/bin/python3 dev/check_shortcut_plus_profile.py --output PATH`.
- Baseline uses existing private assets only: original MS Sans Serif8 font, shell32 groups9/30/36/152 and the measured Explorer folder sprite. No new baseline asset stager is required. New native screenshot dependencies are the `private/screenshots/shortcut-{classic,ie4,plus}-*-20261127.png` evidence files; the Plus checker additionally reads the original private COOL.DLL and registry evidence.

Not accepted here:16px shortcut/list/caption variants, arbitrary True Color focus colors, every wallpaper palette, all high-DPI scaling, context-menu ownership focus transitions, multiple adjacent expanded long labels or every maximal-length filename. Existing source commonly falls back from32px for some16px consumers; that is a separate audit target and is not silently called pixel perfect.

Every reference lease used a verified recovery checkpoint. Classic, IE4 and Plus were restored, writable floppy images ejected, and QMP running state verified. Original checkpoints and evidence were preserved. All COM-created `.lnk` fixtures and temporary color/wallpaper changes were confined to reference snapshots. No live Linux display, user files, installed printer queues or host CUPS were changed.
