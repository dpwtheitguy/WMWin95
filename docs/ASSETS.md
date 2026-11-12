# Original bitmap assets

All Microsoft bytes and derived screenshots remain in ignored `private/`. A locally available installation ISO does not grant redistribution rights. Release packaging must allowlist project source and explicitly exclude originals, derived images, fonts, virtual disks and credentials.

`tools/prepare_assets.py` builds a private shell bundle from `private/cabsets/windows95`:

- NE FONT resource 84 from `sserife.fon`: MS Sans Serif, 8 point, 13-pixel cell height. The renderer reads the original glyph widths and column-major bitmap bits; it does not substitute a Linux outline font or use antialiased font rasterization.
- 32x32 shell icons selected from GROUP_ICON entries in `shell32.dll`, preferring original 4-bit variants. Resource IDs and image IDs are recorded in `manifest.json`; the contact sheet makes selection reviewable.
- `arrow_1.cur`, decoded with its recorded hotspot into a GDK cursor.

`src/win95lx/assets/bitmap.py` supports raster FNT 2.x/3.x and common uncompressed icon DIBs. Vector fonts, compressed/extended DIB formats and invert-destination monochrome cursor semantics are not fully supported. It rejects unsupported structures rather than using modern replacement assets. Dimensions, selection and all decoding still require comparison with the installed reference.

The original raw-resource inventories preserve source paths, identifiers, language where present, extraction status, dimensions where decoded and hashes. Some core executable formats remain unsupported (37 records in the second core pass); raw dialogs/menus/strings are not yet semantically reconstructed. Other cabinet families remain pending.

Bold text is currently an explicit one-pixel overstrike in the shared renderer, not an authenticated Windows GDI rasterizer. Icon selection, border geometry, title metrics, cursor behavior and synthesized bold text must be measured before any accuracy claim.

Format basis: Microsoft's historical [Windows 3.1 Programmer's Reference, Resources](https://bitsavers.trailing-edge.com/pdf/microsoft/windows_3.1/Windows_3.1_Programmers_Reference_Volume_4_Resources_1992.pdf), font file format chapter. The decoder is new project code; no third-party font-conversion implementation was copied.

## Original sound declarations

`tools/sound_inventory.py` extracted 26 source assignments from `motown.inf` into `private/sound-assets/events.json`, preserving source lines and the INF hash. `SystemStart` points to the renamed `mssound.wav` (“The Microsoft Sound”). The default `SystemExit` assignment is explicitly empty in this source. No exit sound is invented. Installed registry state, audio hardware and actual playback still require validation; no sound service or playback has been enabled yet.
