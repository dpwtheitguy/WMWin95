# Original asset library

Win95LX uses original artwork from the user's local Windows 95 media and installed OSR2.5/IE4 reference. Original files, extracted resources, sounds, screenshots, and VM disks stay under ignored `private/`. Git contains extraction tools and provenance procedures, not Microsoft asset binaries.

## Three layers

1. `private/resources/inventory.json`: broad source-media resource archive, including raw PE/NE resources and loose files. The current inventory has 9,617 records: 731 ICON resources, 468 GROUP_ICON records, 360 loose ICO files, 1,269 BITMAP resources, 396 loose BMP files, 406 CURSOR resources and 477 loose WAV records. These are record counts, include duplicates, and are not unique-artwork totals. Seventy source records failed or were unsupported; twenty executables have no resources.
2. `private/resources-core/inventory.json`: another core extraction inventory, with 17,522 records, including 2,195 ICON and 1,482 GROUP_ICON records. It overlaps the first archive; do not add the counts together as unique assets. Thirty-seven source records failed or were unsupported.
3. `private/shell-assets/manifest.json`: curated runtime bundle. At this iteration it has 184 manifest records, including 88 GROUP_ICON records, 18 wallpapers, 13 cursors, original bitmap font, original patterns, startup WAV, and measured reference control artwork. Some group records generate multiple output sizes. This bundle is much smaller than the archives.

`private/sound-assets/events.json` preserves original event declarations with source line and source hash. Its installed-registry verification flags must be respected. Only the startup WAV is currently staged in that sound directory; having hundreds of archived WAV records does not mean every event or Plus! sound scheme works.

## Reproduce and use

`tools/resources.py SOURCE --output NEW_PRIVATE_DIRECTORY` archives PE/NE resources and loose original files, emits source/output hashes, and records unsupported files. Choose a fresh directory; never overwrite reference evidence. `tools/prepare_assets.py` builds the curated shell bundle from `private/cabsets/windows95` and documented native captures. Each new bitmap/font/icon/control extraction needs provenance in the manifest.

For runtime icons, prefer the original 16×16 and 32×32 variants; avoid resampling one to impersonate the other. Group icons identify related sizes and colors, while ICON resources contain individual DIBs. Raw resources need decoding before use. Do not confuse a raw archive with a folder of ready-to-use PNGs.

Prioritize additional original toolbar image lists and enabled/disabled states, menu check/radio glyphs, dialog templates and accelerators, TrueType font families, animated cursors, system-event sounds, and authorized Plus! themes. Inspect archive contents before re-extracting. Record and resolve parser failures before claiming every icon has been recovered. Artwork availability and working control behavior are separate acceptance requirements.
