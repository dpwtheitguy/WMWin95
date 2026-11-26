# Win95LX control toolbox

The working target is Windows 95 OSR 2.5 with IE4 Desktop Update. The Visual Basic names are useful for identifying controls. The toolbox below is an implementation inventory and a work list. Availability across VB4, VB5, and VB6 and the precise version of each optional OCX still need verification.

## Reuse the controls we have

| Control | Implementation and usage | Evidence to check |
| --- | --- | --- |
| CommandButton and caption buttons | Use `Painter.button` and `Painter.caption_button` in `src/win95lx/shell/widgets.py`. Keep the hit rectangle aligned with the drawn button. | Capture normal, pressed, default, disabled, and keyboard-focused states before claiming a match. |
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
