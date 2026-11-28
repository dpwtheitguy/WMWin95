# Theme appearance implementation checkpoint — 2026-11-27

This is a bounded implementation checkpoint, **not complete acceptance of every theme appearance setting**. Network work was frozen before this task; see NETWORK_INVENTORY_2026-11-27.md.

## Implemented

- Strict canonical validators for all25 Windows95 system color roles, six system font roles and12 metric fields. Boolean RGB/dimension values, rotated LOGFONT, malformed fields and out-of-bounds values fail before apply.
- Decode actual original NONCLIENTMETRICSA340 and ICONMETRICSA76 records. LOGFONT face bytes after firstNUL are intentionally ignored; those original structures contain uninitialized trailing bytes.
- AppearanceProvider exports actual process values, snapshots live+disk state, applies with redraw callbacks, persists canonical JSON, restores on failure and loads on a subsequent process. No executable theme content runs.
- Painter accepts explicit semantic role strings; menu glyphs use MenuText/menu font. Command buttons use ButtonFace/ButtonHilight/ButtonShadow/ButtonDkShadow/ButtonText/GrayText and actual message font. No PNG RGB substitution: icon/photo pixels stay intact.
- Original TTF library files are registered with Fontconfig only inside the process. Monochrome Cairo/FreeType glyph adapter renders selected original families. Original bitmap MS Sans Serif remains baseline; changed bitmap sizes/styles get a pixel raster adapter.
- PropertySheet wraps the complete subclass draw at its signal boundary, keeps logical geometry intact, grows physical caption/body placement for caption heights above18, inverse-translates physical pointer events once, and exposes physical_size/body_offset/logical_to_physical. Caption text/color actually change; native command glyphs stay centered. Listener removed on window destruction.

## Evidence and tests

- `python3 -m unittest discover -s tests -p 'test_theme*' -q`:111 passed at this checkpoint, including15 new appearance tests. Not111 new appearance tests.
- Command button native regression:88 independent original Win32 cases at800x600 and1280x720, zero different pixels in each named button comparison. Median offscreen draw0.0649ms /0.0714ms. `private/theme-appearance-20261127/buttons-{800,1280}/report.json`.
- Owned disposable Xvfb integration at800x600 and1280x720: actual GDK root framebuffer, XTest physical button input, semantic red caption/green buttontext, original Comic Sans TTF,10px caption expansion, translated body button click, persisted values reloaded, byte-identical baseline framebuffer after rollback. Six grouped acceptance checks per viewport. `private/theme-appearance-20261127/live-{800,1280}-final/report.json` and PNGs. Before/custom/restored captures are retained.
- The first live-check rollback comparison failed because the test left command focus on its physically clicked Test button. Fixture now clears focus before a baseline comparison. This was a fixture state mismatch, not a palette defect; failed run retained in `live-800/`.
- Syntax compilation and git diff whitespace checks passed.

## Explicit remaining discrepancies

1. These rendered TTF glyphs are original font outlines rasterized by Linux FreeType; no GDI pixel-identical claim. Native matched original-font comparisons are still required.
2. Raw captured CPL body chrome remains original gray. Recoloring all matchingRGBs would corrupt embedded art and confuse semantic roles sharing baselineRGB. Exact per-role chrome masks/native redraw remain necessary. A colored button in a raw-gray sheet can therefore differ from original complete theme appearance.
3. Only caption height above18 is consumed by this PropertySheet layout. Smaller caption values clamp at native minimum; border/menu/scroll/small-caption/iconspacing metrics require each owning layout's actual geometry integration. Saving those fields is not proof of rendered effect.
4. The wrapper retains logical hit maps internally; external pointer tests must convert rectangles with logical_to_physical. Framebuffer capture must use physical_size. Modal dialog owner positioning must include body_offset. Root and Themes UI owner informed.
5. GTK accessory CSS, all shell color roles/fonts/layouts, generic dialogs and non-caption property labels have not all been migrated by this agent. Root owns shell integration.
6. Process-local font inventory is required at runtime; missing original families cause explicit validation failure rather than silent family substitution. This does not install fonts globally.
7. No screensaver program support added. Windows.SCR files are executables and cannot be treated as artwork; this checkout currently has no standalone screensaver backend implementation. Linux analog or confined compatibility runtime needs separate engineering and actual preview/idle validation. No host screen/power state changed.

## Ownership

New theme_appearance.py, test_theme_appearance.py, check_theme_appearance.py; shared widgets.py, command_button.py and property_sheet.py. No shell registration, live deployment, policy, reference VM mutation, commit or push performed here. Parent owns remaining integration and consolidated acceptance.
