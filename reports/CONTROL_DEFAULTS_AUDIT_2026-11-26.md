# Independent shared-control defaults audit — 26 November 2026

This audit found **four reproducible remaining defect classes** and documented native exceptions that must be preserved. The initial audit made no product changes; root subsequently authorized the bounded ComboBox containment correction described below. Network remains frozen. Other agents continue applets while root owns Cairo scrollbar correction and the GTK worker owns actual scrollbar-node/render verification.

Inventory: `config/control-defaults-inventory.json` records **33 control/runtime families**, source paths/hashes, **47 GTK constructor or type-check sites** and **19 legacy `p.button` source sites**. Sites are not live widget counts or accepted-control counts. Some legacy sites are tabs/arrows/fallbacks, so they cannot all be migrated blindly as ordinary command buttons. Timer/Data/OLE are included for completeness; nonvisual components do not have a color-default requirement.

## Independent evidence and confirmed defects

Target standard colors at 96 dpi. Original BUTTON matrix is Windows 95 OSR2.5 classic, 800×600, 256 colors; Display/Network/taskbar observations below are OSR2.5 with IE4 Desktop Update. Plus/custom schemes and larger font metrics require separate baselines. No new original VM actions were needed: reused independently captured, hash-recorded native screenshots/resources and original HWND metadata. No live Linux user display or settings were touched.

### D1 — Legacy command-button drawing still differs

Rendered remaining `Painter.button` against the independent original Win32 BUTTON catalog using the original 13-pixel MS Sans Serif FNT. For OK at 75×23: normal **38**, default **606**, pressed **224** differing pixels. At 108×23: normal **38**, default **804**, pressed **290**. A separate native CPL 75×23 normal sample differs by **38**. The measured `draw_command_button` returns **zero differences in all seven same inputs**. Evidence: `private/research/control-defaults-20261126/legacy-button-comparison.json`, reference digests and generated actual PNGs.

The old painter places ordinary text one pixel lower, paints its default outline outside the provided rectangle and uses a generic pressed bevel. It also has no enabled/focused/mnemonic contract. Shared PropertySheet command buttons already use the measured API; remaining ordinary commands include Mouse dynamic buttons, Display pending/confirmation buttons, Pattern editing, generic native-prompt fallback and Font Preview Print repaint. Other `p.button` sites paint tabs, combo arrows or source-artwork fallbacks and need their own native class profile.

Proposed correction: migrate only semantically ordinary command BUTTON consumers, retaining raw mnemonic labels and actual HWND bounds. Regression: normal/default/focus/pressed/disabled; Enter/default transfer; held pointer out/back/release outside; no paint beyond bounds; native text/margin and complete bevel at two sizes. Existing `test_command_button.py` and `check_command_buttons.py` already provide the measured implementation baseline. Do not claim their acceptance extends to every remaining consumer.

### D2 — Network hand-drawn radio buttons do not match native

Using the same manually configured IP state whose digit interior now matches exactly, compared 13×16 radio regions at actual (36,197) and (36,173) to original (65,264) and (65,240), respectively. Checked Specify-IP differs by **83 pixels**, unchecked automatic-IP by **75**. Original window origin (29,67) comes from independent HWND metadata. Evidence: `network-radio-comparison.json` under the audit evidence directory and its named native/actual screenshots.

`TCPIPWindow.radio` draws circles with Cairo arcs rather than a measured classic OptionButton state. Accessibility uses a separate native-sprite implementation; Mouse also uses source sprites. There is no accepted shared radio contract covering their states.

Proposed correction: independently stage/measure stock radio states, then share the renderer/state model. Regression: selected/unselected, enabled/disabled, keyboard focus and mnemonic, group exclusivity, click label versus glyph, pending Apply/Cancel and containment. Do not copy Network's circle into other applets as the default.

### D3 — Wallpaper list selection ignores focus ownership

`background.draw_list` always paints pending selected wallpaper navy/white. It does not inspect list focus, active window or an open placement ComboBox. Independent original `native-wallpaper-combo-center-open.png` retains the selected Black Thatch row in **gray with black text** while the placement dropdown owns focus. Reproduced current painter: sampled row contains **724 navy pixels**; original sampled selected-label region contains **zero navy**, **763 gray** and **160 black**. These are focus-state color samples, not pixel-aligned exact-difference counts. Source/image/sample rectangles: `background-selection-colors.json` and `background-selection-render.png` in the audit directory.

Proposed correction: explicit selected/focused/active-window state for list painting. Regression: select wallpaper, move focus to placement/Browse/OK, open/close dropdown, deactivate/reactivate sheet; selection remains but its appearance follows native. Repeat after scrolling and check that labels, icon highlight and track retain their independent ownership. Other list/tree consumers need independent focus-state evidence before propagating this style.

### D4 — Shared ComboBox popup text can escape its bounds

`ComboBox.draw_list` paints labels without clipping to its popup. Rendered an 80-character label in a 75-pixel popup on a contrasting parent: **883 non-parent pixels** appear beyond its right boundary. This is an adversarial containment invariant, not a historical pixel-equivalence claim. Evidence: `combo-overflow.json` and `combo-long-label-overflow.png` in the audit directory.

Proposed correction: control-owned popup clipping, bounded text/arrow/gutter geometry and hit intersection. Regression: long labels, zero/one/many items, narrow popup, bottom/right screen edges, selected row and open/closed pointer/keyboard traversal. GTK child-window clipping does not protect this Cairo popup painted on the shell canvas.

## Native colors that are intentional

Do **not** make every light surface gray. Audit sample coordinates, counts and hashes are in `private/research/control-defaults-20261126/native-state-colors.json`.

| Independent native state | Observation | Required handling |
|---|---|---|
| IE4 active Control Panel task button clear interior, (280,583,20,10) | **200/200 pure white pixels** | Retain this measured active-task variant; no automatic checker replacement. Inactive/focused/pressed variants still need their own captures. |
| Open Display placement combo selected row, (362,450,72,13) | Navy interior, white glyphs, **83 yellow perimeter pixels** | Yellow focus perimeter is native in this state. It is not automatically an accidental debug color. |
| Disabled native IPAddress child interior | **200/200 #c0c0c0** in clear sample | Disabled gray field differs from enabled white; retain state-specific surface. |
| Enabled native IPAddress sample | White background with black System glyphs | Keep white interior; System font is distinct from dialog MS Sans Serif. |
| Fresh native Notepad exposed vertical and populated WordPad tracks | Valid exposed 12×100 regions are **1200 white pixels**; WordPad empty has no scrollbar and that earlier body sample is excluded | Explicit measured white application profiles. |
| Fresh native common Open file horizontal track | Sampled 150×12 region is **1800 white pixels** | Explicit white profile for that native dialog/version. |
| Device Manager, Mouse pointer, Sounds tree and Display wallpaper track captures | Independent white exceptions are recorded by root's consumer audit | Preserve per-owner exception records; not an inherited global white default. |

GTK worker owns fresh native track evidence in `private/screenshots/gtk-scrollbars-20261126/native-track-measurements.json`. The generic Cairo/GTK default is classic gray/white stipple; explicit native white track profiles are necessary. Existing `scrollbar-audit-...` directories may predate the current consumer correction; do not treat an earlier self-rendered gray Device Manager check as original evidence or as the final native exception state. Root's current source explicitly passes `track="window"` there.

## Control-family coverage and targeted next regressions

| Family | Current implementation boundary | Highest-value acceptance test |
|---|---|---|
| Labels/text | Original FNT Painter vs GTK labels | Actual glyph baseline/advance, disabled embossing, mnemonic, long-text clip; sample custom/high-contrast scheme separately. |
| CommandButton | Measured shared API plus legacy paths (D1) | Named native states and integrated default/focus/Enter/pointer behavior. |
| CheckBox | Display manual tick, Accessibility/source sprites, Mouse/source frame | Unchecked/checked/mixed if applicable, disabled, Space and focus; compare adjacent label/background. |
| OptionButton | Source sprites and manual Network circles (D2) | Group navigation/exclusivity and all measured states; never treat a circle alone as a radio. |
| Frame/GroupBox | Source frames plus local clear/repaint | Text gap, border ownership, disabled controls and dynamic repaint cannot erase group edge. |
| DropDownList | Shared model, shell popup, independent ChoicePopup | D4 clip, native focus perimeter, arrow and list open/closed, row selection, dismiss/Apply. |
| Editable combo | GTK WordPad family/size and file-type widgets | Entry versus arrow child geometry, typing/paste/selection, dropdown state and theme node colors. |
| Single-line edit | TextEntry state with several paint adapters | Enabled/disabled/read-only/selected/caret, overwrite/insert, clip and password-specific behavior only where present. |
| Multiline edit | Notepad GTK TextView | Wrap off/on, empty/scrollable, caret/selection and editor-bevel ownership; preserve native white. |
| RichTextBox | WordPad model/GTK editor | Mixed formatting, toolbar selection, ruler and document fonts; no inherited gray document background. |
| ListBox | Wallpaper/pointer/choice/network lists | D3 active/inactive selection, multi-select, long item, overflow, keyboard reveal and track exception. |
| ListView | Namespace four modes, GTK files and Fonts | Column headers/sort/resize where supported; modes, auto/manual positions, both scroll axes and clipping. |
| TreeView | Specialized drawn device/event trees; unintegrated Explorer model | Nodes, expand/collapse, connectors, selection focus, keyboard, item-hit margins and per-profile track. |
| H/V scrollbars | Cairo primitive, horizontal adapter and GTK nodes | Track above/below thumb at ends/middle; explicit colors, thumb size/range, arrows/pages/drag, disabled/no overflow. |
| Menu bar | Geometry/Cairo labels and scoped GTK | Text/hit origins, no extra separator/space, access keys, focus transfer and version-specific menu set. |
| Popup menus/check/radio items | Cairo profiles, GTK and native check-mask paths | Contextual enablement, check/radio placement, accelerator column, disabled emboss, selection and submenu boundaries. |
| TabStrip | Native frames, specialized rotating TCP/IP rows; GTK fallback Notebook | Active row rotation, adjacent edge ownership, Tab/CtrlTab, disabled/hot/pressed and long captions. |
| Toolbar | Original Explorer bands and GTK WordPad/dialog tools | Image state and action agree; pressed/disabled, separators, arrow menus and all nodes under theme changes. |
| Slider/TrackBar | Artwork/formulas in Display/Keyboard/Mouse/Multimedia | Tick spacing, thumb shape/position, bounds, focus/disabled, track clicks and keyboard. |
| ProgressBar | No general shared renderer found | Research original determinate/marquee availability before implementing; do not invent a modern spinner. |
| StatusBar | Cairo inset panes versus GTK status strip | Pane boundary ownership, grip, clipped text and selected-count/free-space updates. |
| TaskButton | Separate shared painter | Active white native variant, inactive bevel, title/icon clip, minimize/restore and focus/stack integration. |
| Caption controls | Custom/native-artwork captions | Active/inactive, disabled min/max, held press out/back, system-icon click; distinct from CommandButton. |
| System menu | Shared profiles and external-WM conflict | AltSpace/icon click, Move/Size bounds, disabled commands and no leaked XFCE/IceWM menu. |
| Common/Run/Shutdown/error dialogs | Original artwork, Cairo and GTK fallback branches | Default command, focus/caret/selection, Cancel, actual backend errors, owner stacking and native dimensions. |
| UpDown/SpinButton | Date/time source controls vs GTK advanced display | Arrow held-repeat, bounds, disabled states, typed values and adjacent editor geometry. |
| Image/PictureBox/Shape/Line | Asset decoders/Painter | Palette/alpha/invert pixels, scaled nearest-neighbor, border and clipping; no silent resampling. |
| IPAddress/MaskedEdit | Four bounded fields, original System FNT | Typed sample already exact; add all digits, caret/selection/disabled and atomic paste/octets. |
| Tooltips/disabled reasons | GTK tooltip path from PropertySheet/Fonts/WordPad | Actual visible tooltip CSS/window/font and native delay/wrap/border; source reason text alone is not appearance acceptance. |
| Timer/nonvisual | GLib timers | Cancellation on close, no stale callback, idle/animation cost; no arbitrary color test. |
| Data/OLE | No general VB Data/OLE compatibility | Track as unavailable; service models do not establish VB/OLE compatibility. |

## GTK inheritance and theme-leak trace

`install_menu_style` in `shell/accessories.py` adds a screen provider at application+1 priority. WordPad adds another screen provider at application priority; Notepad adds widget providers, while dialogs add scoped `.win95-file` / `.win95-native-file` rules. A provider attached to a screen affects matching widgets in that process, including child/fallback dialogs. It is not a global theme installation for other X11 applications.

Therefore declarations on only `scrollbar` or only a parent class do not prove actual `contents`, `trough`, `slider`, stepper, disabled, hover or backdrop appearance. The GTK worker found a data-URI image silently falling back; file-URI rendered fixtures and explicit white profiles are being checked independently. Its scope is scrollbar nodes only. No claim is made here that GTK Entry/ComboBox/Button/MenuItem/Tooltip/Notebook inherited colors are accepted merely from CSS text.

Important fallback surfaces remain: Notepad Find; WordPad RTF-conversion confirmation; Calculator/Minesweeper message dialogs; generic file/name/message fallback; advanced Display Notebook/SpinButton and native disabled-reason tooltips. These require actual realized widget paths, computed properties **and rendered pixels**, with normal/disabled/focused/selected/backdrop states. Some native-artwork buttons deliberately hide GTK label/background, so a CSS color difference can be irrelevant unless the visible branch renders it.

## Proposed ongoing defaults gate

Keep an explicit control profile containing class/variant, native release/update, color scheme/palette, font/DPI, enabled/focus/pressed/selected/active state and owner of each adjacent edge. Expected colors come from that reference profile, not an application-wide “all gray” rule. Use parent backgrounds that contrast with both expected white and gray to detect inheritance. Test top/middle/bottom and no-overflow scroll states separately. Exercise state transitions, not only a saved initial frame.

For each changed family, require one meaningful model/input test, independent native region render comparison and integrated consumer UAT at 800×600 plus a larger viewport. Include longest labels, moving/resizing, open popup edges, disjoint focus/selection and no off-control pixels/hits. Record actual test count versus state cases versus repeated resolutions. New lessons become shared constraints only after their native scope is established.

The initial audit added zero product changes/tests. The subsequently authorized D4 correction changes one shared control file and adds **five automated rendering regressions**; other confirmed defects remain open. It produced seven new independent button comparison measurements, two native radio region measurements, focus/color samples and an adversarial combo-containment reproduction. Existing original command-button/scrollbar/Network acceptance reports remain independently scoped. The proposed tests above are work to perform, not invented passing counts.


## Authorized D4 correction and targeted regression

Root authorized the narrow ComboBox containment fix after the independent reproduction. `shell/combo_box.py` now clips the full popup and its text client separately, preserves the black outer border and native yellow focused-selection perimeter, bounds tiny/zero widths and leaves the caller's clipping context unchanged. Empty-choice stepping remains at index zero instead of producing -1. No other widget class/lifecycle was changed.

`tests/test_combo_box_rendering.py`: **5 passing tests**, no failures. Cases exercise selected and unselected long text, border preservation, native focus colors, empty and tiny widths, moved popup/hit boundaries and caller-clip restoration. The fifth compares the complete 75×28 opened focused placement popup against its hash-verified independent native capture at both 800×600 and 1280×720 canvas sizes, with zero differing pixels. That private-reference test explicitly skips if licensed private evidence is unavailable; the other four use a small synthetic test font for containment/state invariants. Existing **10 control-layout tests also passed**.

Adversarial before evidence had **883 outside pixels**. After correction, the same source-FNT reproduction has **zero outside pixels** at both canvas sizes: `private/research/control-defaults-20261126/combo-overflow-after.json` and PNGs. Independent native popup comparison is `combo-native-after-comparison.json`, zero differences across 75×28 pixels. Source/read-only tests establish this component boundary; root's combined shell/guest integration remains pending. D1 legacy buttons, D2 radio and D3 focus-aware list selection remain unfixed by this child.


GTK worker final report: `reports/GTK_SCROLLBARS_2026-11-26.md`, with release evidence under `private/screenshots/gtk-scrollbars-20261126/gtk-release-{800,1280}-{1x,2x}/`. The worker corrected an earlier misclassification: empty native WordPad has no scrollbar, so its white body sample is excluded as trough evidence. Visible populated WordPad/Notepad/file-dialog track profiles remain independently scoped. Final run counts/status must come from that report, not this pending audit snapshot.


D2 follow-up: Network radio correction is component-validated in `NETWORK_2026-11-26.md`: independently captured16-state native matrix,0diff for every case and full normal Win16 Network controls;32 Network tests and two-size fake-service integration pass. Normal-account policy and complete Network acceptance remain blocked. D1 typed migration plan is `LEGACY_BUTTON_MIGRATION_PLAN_2026-11-26.md`; no blanket replacement.
