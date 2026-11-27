# Win95LX control toolbox

The working target is Windows 95 OSR 2.5 with IE4 Desktop Update. The Visual Basic names are useful for identifying controls. The toolbox below is an implementation inventory and a work list. Availability across VB4, VB5, and VB6 and the precise version of each optional OCX still need verification.

For Control Panel, keep classic, IE4 and Plus reference captures separate and record actual CPL versions. See the fidelity engineer instructions and `dev/capture_control_panel.py`. Raw automated tab labels are hypotheses until the images are reviewed. Static original artwork does not establish working controls; every changed setting needs a backend-effect, Apply/Cancel, failure and persistence check. Disabled features must explain their actual limitation, including when implementation is merely unfinished.

## Reuse the controls we have

| Control | Implementation and usage | Evidence to check |
| --- | --- | --- |
| CommandButton | Use `draw_command_button`, `metrics`, `parse_label`, and `resolve_default` in `src/win95lx/shell/command_button.py`. Pass original raw ampersand labels and actual HWND bounds. PropertySheet.button defers painting to resolve one enabled default command; it registers command Enter and Alt mnemonics. | `dev/check_command_buttons.py`: 88 original Win32/CPL cases, eight states, two widths, exact pixels at800×600 and1280×720. `dev/check_control_panel.py --buttons-only`: integrated GTK focus/default transfer, pointer bounds, mnemonic routing and true Add Language HWND geometry. See `reports/COMMAND_BUTTONS_2026-11-26.md`; standard-color96dpi text commands only. |
| Caption buttons | Use `Painter.caption_button` in `src/win95lx/shell/widgets.py`; keep the hit rectangle aligned with the drawn button. | Caption controls are separate from the measured CommandButton states; capture their own normal, pressed, disabled and focus behavior. |
| VScrollBar | Use `VerticalScrollbar` in `src/win95lx/shell/scrollbar.py`. Pass the viewport height and maximum value, then use `thumb_top` and `value_at` for drawing and dragging. The Background tab supplies native scrollbar sprites and C: reuses the control for its icon grid. | Verify both arrows, page-up/down, the thumb at both endpoints, and the same control size at a larger display mode. |
| Slider (TrackBar) | Display Settings uses shared slider geometry in `control_panel/display_settings.py`. The two Windows 95 sliders select the same mode on the single guest display. | Compare the native idle frame, test dragging and keyboard bounds, and exercise Apply, confirmation, and rollback. |
| Menu bar and popup | Use `menu_layout.py` for the Explorer headings, popup dimensions, and hitboxes. GTK accessories use the scoped styling in `accessories.py`. Keep an intentional content bevel with the pane that owns it. | Check heading origins, popup label gutters, accelerator visibility, row spacing, Escape, and mouse/keyboard selection. |
| Task button | Use `draw_task_button` and `button_width` from `taskbar.py`. Give the renderer a small icon, title, width, and active state. | Verify inactive and pressed frames, title clipping, task order, and switching between internal and GTK windows. |
| ComboBox | Use `ComboBox` in `src/win95lx/shell/combo_box.py` for selection state, row hit testing, and the popup renderer. Display Properties supplies the native field artwork and uses the shared list for wallpaper placement, color palette, and font size. | Compare open rows and closed focus against the original. Exercise pointer, keyboard, disabled state, dismissal, and Apply/Cancel. |
| ListBox and TabStrip | The Background tab uses native layout, with separate rendering for list selection and scrollbar. | Compare focused and unfocused selection, tabs, and the entire scrollbar track, including exposed track pixels after the selection changes. |
| System menu | Use `system_menu.py` for command order, enabled states, and Move/Size bounds. The shell and GTK accessories share those profiles. | Test caption-icon click, Alt+Space, Restore/Move/Size/Minimize/Maximize/Close, and disabled commands on fixed-size windows. Compare native profiles by app. |
| TextBox, OptionButton, and CommonDialog | See Run, Shut Down, and the shared file dialogs in `apps/dialogs.py` for current working states. | Verify caret, selection, default button, Cancel, focus return, and validation. The file dialogs still need full reference comparisons. |

## Inventory for the next passes

| Family | Candidates |
| --- | --- |
| Basic form controls | Label, TextBox, CommandButton, CheckBox, OptionButton, Frame, ComboBox, ListBox, HScrollBar, VScrollBar |
| Graphics and layout | PictureBox, Image, Shape, Line, menu and form chrome |
| File navigation | DriveListBox, DirListBox, FileListBox, Open and Save CommonDialog |
| Common Controls and other add-ins | TabStrip, Toolbar, StatusBar, ProgressBar, Slider, TreeView, ListView, ImageList, UpDown, RichTextBox, MaskedEdit |
| Runtime or data controls | Timer, Data, OLE container. Inventory these for completeness. Prioritize visual work where an app needs it. |

## Run the checks

Run `make test` for layout and interaction logic, then `make check-ui` for the rendered menu boundaries and reference-region comparisons at 800×600 and 1280×720. These checks use the staged assets and local screenshots in `private/`. See `docs/VISUAL_REGRESSION.md` for the capture workflow. For each newly implemented state, add the original capture, render the matching implementation state, and compare the smallest region that establishes the claim.

## Explorer namespace controls

`computer_view.py` renders the IE4 My Computer bands and Web View using independently sourced original control artwork, live address text, namespace icons, and matching pointer targets. `explorer_menu.py` owns My Computer's File profile and measured popup. Resolve command capability from the current selection and item type; an empty-selection screenshot must never become an always-disabled menu. Filesystem folder menus continue to use their own file-operation selection model.

`text_entry.py` supplies shared caret, selection, replacement, arrows, Home/End, Delete/Backspace and Ctrl+A behavior for single-line edit controls. Its first consumer is the address field. Reuse it instead of clearing the field merely because Ctrl+A was pressed.

Run `dev/check_computer_view.py` under Xvfb at 800×600 and 1280×720 (or `make check-computer-view`). It saves complete menus, selected-item states, band toggles, original hashes, and pixel rectangles. Namespace shortcut serialization is in `explorer/namespace.py`; unknown links must never execute arbitrary commands.

## Mouse property sheet and animation

`apps/mouse.py` owns the native 404×448 sheet, pending edits, pointer/keyboard hit targets and original AVI test playback. Reuse `MouseController` in `control_panel/mouse_preferences.py` for Apply/Cancel/persistence/rollback. Read actual backend state before applying unrelated settings; applying an artwork choice must not reset existing button mapping or acceleration. X11 acceleration readback does not prove an effect on an absolute tablet or a libinput device.

`assets/rle8.py` decodes bounded BI_RLE8 key/delta frames and preserves the prior image. `tools/stage_mouse_animation.py` stages the original private MAIN.CPL AVI and transparency. New animation consumers need independent input tests as well as a resource-derived frame; never substitute a static picture for a working control.

Run `make check-mouse` for both viewport sizes. See `reports/MOUSE_PROPERTIES_2026-11-26.md` for exactly accepted regions and the still-unimplemented trails, scheme management and theming paths.

## Native property-sheet measurements

Build `tools/native/w95probe.c` using `dev/build_reference_probe.py` for an i386-compatible reference tool. Run it inside a reference (for example `W95PROBE.EXE keyboard 0`) to collect child HWND geometry, fonts, combo choices, enabled states, trackbar ranges and a matching BMP in C:\W95PROBE. Keep captures private. Do not infer a page origin from the painted top of a GroupBox: its text and border do not coincide with its HWND bounds. `pixel_rect` requires explicit measured origin and font base. Verify VM checkpoints with `dev/snapshot_vm.py`; raw writable floppy media can prevent a complete save.

## Scrollbar track ownership and audit

`VerticalScrollbar.draw` defaults to classic system gray/white one-pixel stipple.
It owns the entire trough, independent of the containing white file/list pane.
`track="window"` is an explicit exception for independently measured native
Device Manager, Mouse pointer, Sounds tree and Display wallpaper-list tracks. Preserve a native
exception's reference/version record; do not use it as a general default.
Device Manager explicitly preserves the white exposed track measured in the
classic native TreeView. It is not inherited from GTK or the parent background.

`dev/check_scrollbar_tracks.py` samples exposed troughs in real Device Manager,
Fonts, Font Preview and ChoicePopup consumers. It verifies independent native
white exceptions as well. Primitive tests cover top/middle/bottom, no overflow,
parent-color isolation and movement phase. GTK audit covers the trough node as
well as the scrollbar background; a correct thumb alone is insufficient.

For a page-aware viewport, use `VerticalScrollbar.for_page(height, maximum, page)`. Do not use a fixed thumb from a reference with a different item count. Device Manager uses native page 16 and a 263px bar; its main HWND is 410×448. Full native strip comparisons and actual drag/wheel tests are in `dev/check_scrollbar_tracks.py`.

Custom GTK popups use shared coordinate translation/outside replay from `apps/popup_events.py`. Grabbed outside events can arrive on the Window, not its DrawingArea. Handle parent/direct destruction and focus changes explicitly; test the initiating outside click reaches the intended control once.

### Shortcut versus shared-folder overlays

In the project's original `shell32.dll` GROUP_ICON resources, **29 is the shared
hand; 30 is the shortcut arrow**. Resource IDs are not zero-based icon indexes.
Desktop and Explorer shortcuts use the target's base icon plus GROUP_ICON30.
Keep share overlays separate. Inspect the extracted artwork independently and
exercise both actual renderers; a test repeating the implementation's incorrect
resource choice cannot establish fidelity. `check_printers_shell.py` checks both
renderer identities, and `check_selection_details.py` compares the composed
shortcut pixels against the original arrow resource.
