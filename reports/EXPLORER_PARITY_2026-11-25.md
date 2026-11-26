# Explorer comparison iteration — November 25, 2026

The original reference is Windows 95 OSR2.5 with IE4 Desktop Update. This iteration corrects My Computer's missing File-menu profile, standard toolbar, address band, Web View header and icon layout, maximized caption, and menu status feedback. It does not establish whole-desktop identity or completion of all fifty observations.

The old single Close row has been replaced with context-dependent namespace commands. Empty selection disables the first four commands. Selecting C: enables shortcut creation and properties; Control Panel enables shortcut creation. Ordinary files and folders retain their separate filesystem selection/operation handling. These namespace capabilities must not be applied globally to every Explorer window. Future native selected-state captures are still required before asserting complete parity for every item type.

The shared Restore glyph was corrected. Maximized My Computer uses the native caption geometry and clipping. Toolbar art comes from individually extracted native controls; address text, selection/caret editing, menu states, command hit targets and namespace icons are live. The address field accepts C: and Linux paths. Create Shortcut prompts before creating safe internal links on the desktop, preserves existing shortcuts, and reopens them without executing arbitrary desktop commands. Properties uses real capacity data but is not yet the complete native drive property sheet. View offers band/Web View toggles, not the entire native View menu.

## Evidence and tests

Evidence is under `private/screenshots/explorer-iteration-20261125/`. `release-host-800`, `release-host-1280`, `release-guest-800`, and `release-guest-1280` contain screenshots, source/asset/reference hashes, viewport metadata, interaction assertions and rectangle-level pixel reports. `release-live-comparison.json` checks the visible guest capture against the original VM reference. Original and implementation images are stored separately; joined comparison figures do not resample either source.

The new acceptance script is `dev/check_computer_view.py`, included in `make check-ui` at both resolutions. It covers complete File contents, empty and selected command targets, keyboard navigation, Work Offline toggle, Escape, clearing selection with a blank click, Create Shortcut and reopening, Properties dispatch, address focus, and band/Web View toggles. Pure unit tests cover namespace links/capabilities and edit-control selection/caret operations.

52 unit tests pass. Existing menu seams, sprint scenarios, independent folder transfers, common file dialogs and reference-control suites are also run. Final validation: 12 new native-region comparisons per resolution on host and guest (48 comparisons), all with zero differences. The new interaction checks passed in all four runs. `make check-ui` passed, including 12 existing sprint scenarios at both resolutions, menu seams, folder transfers, file dialogs, and reference controls. `make test` passed all 52 unit tests and compilation. Logs are preserved with the private evidence. Early failing captures are retained; one test fixture initially omitted the timestamp required by a real pointer event and was corrected. A pressed-heading state and status-label origin also failed exact comparisons before correction. These failures were not treated as passing evidence.

Exact claims cover recorded regions/states: the full empty-selection File popup, pressed File heading/open menubar, toolbar, address band, maximized caption, Web View artwork/description, C: icon/label and Control Panel icon/label. Wider-view checks separately compare fixed left/right edges. Static artwork checks are supplemented by interaction assertions; they do not prove every command or dialog is complete.

The live upper 800×174 Explorer region, complete File popup, File status hint, and 246×184 comparison crop have been measured with zero differences against the original captured state. Other screenshot areas differ, including device inventory, Quick Launch and status/tray settings. No full-desktop zero-difference result is claimed. No performance improvement is claimed; this iteration has no comparable timing baseline.

## Fifty-observation disposition

“Matched” below means the recorded state/region, not every possible state. Several entries in the earlier fifty-item list were settings or contents differences rather than independent drawing defects.

| # | Observation | Disposition |
| --- | --- | --- |
| 1 | Outer frame | Maximized My Computer caption/frame geometry corrected; normal mode retained. |
| 2 | Caption icon inset | Matched, including native clipping. |
| 3 | Caption text inset | Full maximized caption matched. |
| 4 | File menu origin | Complete open menubar and popup matched. |
| 5 | Menu heading spacing | Open menubar matched at 800×600. |
| 6 | Content starts immediately after menu | Standard/address bands now occupy their native rows. |
| 7 | Missing standard toolbar | Full band matched. |
| 8 | Back | Present; disabled at namespace root. Navigation history remains future work. |
| 9 | Back history arrow | Present in original control artwork; history popup remains future work. |
| 10 | Forward | Present; disabled at namespace root. |
| 11 | Forward history arrow | Present; history popup remains future work. |
| 12 | Up | Present; namespace root has no parent. |
| 13 | Cut | Toolbar present. General namespace clipboard behavior remains incomplete. Filesystem Cut works in folder windows. |
| 14 | Copy | Toolbar present. General namespace clipboard behavior remains incomplete. Filesystem Copy works. |
| 15 | Paste | Toolbar present. Namespace-root Paste is incomplete; folder Paste works. |
| 16 | Undo | Artwork present; a general file-operation undo stack remains unimplemented. |
| 17 | Delete | Artwork present; root namespace objects stay protected. Filesystem delete/trash remains working. |
| 18 | Properties | Selection-aware C: dispatch and real disk statistics; full native property sheet remains. |
| 19 | Views | Opens implemented View options; full native view modes/menu remain. |
| 20 | Views arrow | Present with clickable View control. |
| 21 | Toolbar separators | Full band matched. |
| 22 | Toolbar grip | Artwork matched; dragging/reordering bands remains. |
| 23 | Address bar | Present, editable and navigates supported locations. |
| 24 | Address label | Band matched. |
| 25 | Address icon | Original small variant; band matched. |
| 26 | Address text | Idle band matched; shared caret/selection editing implemented. |
| 27 | Address dropdown | Basic navigation choices work; complete native hierarchy/history remains. |
| 28 | Address border | Band matched, including end button and stretched edges. |
| 29 | Web View | Default header/layout present and toggleable. Full dynamic item descriptions remain. |
| 30 | Large computer illustration | Matched. |
| 31 | Blue disc | Matched as part of illustration. |
| 32 | My Computer heading | Matched. |
| 33 | Heading rule | Native placement implemented; covered by the live upper-region comparison. |
| 34 | Description text | Default description matched; selected-item description states remain. |
| 35 | Left descriptive area | Native default layout implemented. |
| 36 | Icon starting height | Native C: and Control Panel rectangles matched. |
| 37 | Two objects versus five | Actual contents difference, not a reason to fabricate device entries. |
| 38 | A: floppy | Reference hardware inventory differs; device enumeration remains. |
| 39 | Windows95C D: | Reference has mounted original media; Linux guest does not share that inventory. |
| 40 | Printers folder | Namespace feature remains to implement with working printer management. |
| 41 | Hard-drive artwork | Original image and label now match the measured rectangle. |
| 42 | C: placement | Matched in Web View. |
| 43 | Control Panel placement | Matched in Web View. |
| 44 | Four-item row versus two items | Grid origins corrected for existing items; actual inventory still differs. |
| 45 | Object count | Reports actual two objects; reference's captured zero is not copied as fake data. File-menu hints now replace count while the menu is open. |
| 46 | Status sections | Three sections implemented, with a full-width File-menu hint. More status states remain to compare. |
| 47 | Status location indicator | Original computer icon and location label present. |
| 48 | Quick Launch | Still missing; default launch targets need functional implementations. |
| 49 | Task button follows Start | Still differs because Quick Launch is absent. |
| 50 | Tray setting and clock | User/VM settings differ. Preserve actual time and the user's settings-icon preference. |

The additional File-menu observations—seven commands, two separators, widths, gutter, row positions, disabled embossing, checkmark, mnemonics and Close placement—are covered by the whole-popup comparison. The previous Close-only test did not establish these and is no longer the acceptance boundary for My Computer.

## Asset library

See `docs/ORIGINAL_ASSET_LIBRARY.md` for the raw archives, curated runtime bundle, duplicate-count caveat, unsupported source records, sound event declarations, and reproduction commands. Private original resources, licensed media, VM images, credentials and comparison screenshots remain ignored by Git. Public reports refer to local evidence; reproducing visual tests requires the private source bundle.

## Delivered build

Source SHA-256: `22312b2aebfd75e75ececfa4ea97bc48358ecb637ce17bda09c74d10c4157c67`. The host and guest reports agree. This tested build is activated in the visible Linux guest. Original Windows 95 and Win95LX remain open simultaneously.

[Identical File-menu comparison crop](../private/screenshots/explorer-iteration-20261125/release-file-menu-comparison.png): original left, Win95LX right, unscaled. [Full desktops with remaining differences](../private/screenshots/explorer-iteration-20261125/release-full-desktop-comparison.png). The full-desktop pair is intentionally retained to make the inventory, Quick Launch, and tray differences reviewable.
