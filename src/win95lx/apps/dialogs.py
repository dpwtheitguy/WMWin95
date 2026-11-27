"""Shared Windows 95-style file dialogs for the desktop accessories."""

from fnmatch import fnmatchcase
from pathlib import Path

from gi.repository import Gdk, GdkPixbuf, Gtk, Pango
import cairo

from win95lx.assets.bitmap import BitmapFont
from win95lx.shell.accessories import SCROLLBAR_STYLE,style_scrollbars
from win95lx.shell.widgets import BLACK, FACE, LIGHT, NAVY, Painter


def run_dialog(dialog):
    """Keep keyboard focus with the modal on the standalone X11 desktop."""
    parent = dialog.get_transient_for()
    dialog.present()
    dialog.get_window().focus(Gdk.CURRENT_TIME)
    try:
        return dialog.run()
    finally:
        if parent and parent.get_window():
            parent.get_window().focus(Gdk.CURRENT_TIME)


STYLE = b"""
.win95-file { background: #c0c0c0; color: black; font: 11px "Liberation Sans"; }
.win95-file button, .win95-file combobox button {
    background: #c0c0c0; color: black; border-radius: 0;
    border: 1px solid; border-color: white black black white;
    box-shadow: inset -1px -1px #808080; min-height: 20px;
}
.win95-file entry, .win95-file treeview {
    background: white; color: black; border-radius: 0;
}
.win95-file entry { min-height: 20px; padding: 0 4px; border: 1px solid #808080; }
.win95-file treeview:selected { background: #000080; color: white; }
.win95-file .caption { background: #000080; color: white; font-weight: bold; padding: 2px 4px; }
""" + SCROLLBAR_STYLE


NATIVE_STYLE = b"""
.win95-native-file { background: #c0c0c0; color: black; }
.win95-native-file button { min-width: 0; min-height: 0; padding: 0; border: 0; }
.win95-native-file entry, .win95-native-file treeview {
    background: white; color: black; font: 11px "Liberation Sans";
    border: 0; border-radius: 0; box-shadow: none; min-height: 0; padding: 0;
}
.win95-native-file entry selection, .win95-native-file treeview:selected {
    background: #000080; color: white;
}
.win95-native-file scrollbar { background: #c0c0c0; }
.win95-native-file scrollbar slider {
    background: #c0c0c0; border: 1px solid; border-color: white black black white;
    border-radius: 0; min-height: 15px; min-width: 12px;
}
""" + SCROLLBAR_STYLE


def dialog_art(parent, state):
    while parent is not None:
        assets = getattr(parent, 'dialog_assets', None) or getattr(parent, 'assets', None)
        if assets:
            image = assets/f'file-dialog-{state}.png'
            font = assets/'ms-sans-serif-8.fnt'
            if image.is_file() and font.is_file():
                return assets, cairo.ImageSurface.create_from_png(str(image)), BitmapFont(font.read_bytes())
        parent = parent.get_transient_for()
    return None


def install_style(dialog, css):
    from win95lx.control_panel.display_preferences import install_palette_filter
    parent = dialog.get_transient_for()
    while parent is not None and not hasattr(parent,'display_preferences'):
        parent = parent.get_transient_for()
    if parent is not None:
        install_palette_filter(dialog,lambda: parent.display_preferences.palette)
    style = Gtk.CssProvider()
    style.load_from_data(css)
    screen = dialog.get_screen()
    Gtk.StyleContext.add_provider_for_screen(screen, style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    dialog.connect('destroy', lambda *_: Gtk.StyleContext.remove_provider_for_screen(screen, style))


def fixed_canvas(dialog, width, height, draw):
    dialog.set_resizable(False)
    dialog.set_default_size(width, height)
    fixed = Gtk.Fixed()
    fixed.set_size_request(width, height)
    content = dialog.get_content_area()
    content.set_border_width(0)
    content.set_spacing(0)
    actions = dialog.get_action_area()
    actions.set_no_show_all(True)
    actions.hide()
    content.pack_start(fixed, True, True, 0)
    canvas = Gtk.DrawingArea()
    canvas.set_size_request(width, height)
    canvas.connect('draw', draw)
    fixed.put(canvas, 0, 0)
    return fixed, canvas


def artwork_button(fixed, canvas, label, rect, clicked):
    x, y, width, height = rect
    button = Gtk.Button()
    button.get_accessible().set_name(label)
    button.set_size_request(width, height)
    button.set_opacity(0)
    button.connect('clicked', clicked)
    button.connect('notify::has-focus', lambda *_: canvas.queue_draw())
    button.connect('pressed', lambda *_: canvas.queue_draw())
    button.connect('released', lambda *_: canvas.queue_draw())
    fixed.put(button, x, y)
    return button


class FileDialog(Gtk.Dialog):
    def __init__(self, parent, path, filters, saving=False, name=''):
        title = 'Save As' if saving else 'Open'
        super().__init__(title=title, transient_for=parent, modal=True)
        self.set_decorated(False)
        self.set_default_size(460, 314)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.saving = saving
        self.filters = filters
        self.folder = None
        self.path = None
        self.native_art = dialog_art(parent, 'save' if saving else 'open')
        if self.native_art:
            self.build_native(path, name)
            return
        self.get_style_context().add_class('win95-file')
        style = Gtk.CssProvider()
        style.load_from_data(STYLE)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.connect('destroy', lambda *_: Gtk.StyleContext.remove_provider_for_screen(
            self.get_screen(), style))

        area = self.get_content_area()
        area.set_border_width(4)
        caption = Gtk.Label(label=title, xalign=0)
        caption.get_style_context().add_class('caption')
        area.pack_start(caption, False, False, 0)
        grid = Gtk.Grid(column_spacing=8, row_spacing=6, margin=8)
        area.pack_start(grid, True, True, 0)
        self.location = Gtk.Entry(hexpand=True)
        self.location.connect('activate', lambda entry: self.change_folder(Path(entry.get_text()).expanduser()))
        grid.attach(Gtk.Label(label='Save in:' if saving else 'Look in:', xalign=0), 0, 0, 1, 1)
        grid.attach(self.location, 1, 0, 1, 1)
        up = Gtk.Button(label='Up')
        up.connect('clicked', lambda *_: self.change_folder(self.folder.parent) if self.folder else None if self.folder else None)
        grid.attach(up, 2, 0, 1, 1)

        self.files = Gtk.ListStore(str, str, bool)
        self.view = Gtk.TreeView(model=self.files, headers_visible=False, activate_on_single_click=False)
        self.view.append_column(Gtk.TreeViewColumn('Name', Gtk.CellRendererText(), text=0))
        self.view.connect('row-activated', self.activate_row)
        self.view.get_selection().connect('changed', self.select_file)
        scroller = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN, vexpand=True, overlay_scrolling=False)
        scroller.add(self.view)
        style_scrollbars(scroller)
        grid.attach(scroller, 0, 1, 3, 1)

        self.filename = Gtk.Entry(text=name)
        self.filename.connect('activate', lambda *_: self.accept())
        grid.attach(Gtk.Label(label='File name:', xalign=0), 0, 2, 1, 1)
        grid.attach(self.filename, 1, 2, 1, 1)
        confirm = Gtk.Button(label='Save' if saving else 'Open')
        confirm.connect('clicked', lambda *_: self.accept())
        grid.attach(confirm, 2, 2, 1, 1)
        self.filetype = Gtk.ComboBoxText()
        for label, _patterns, _extension in filters:
            self.filetype.append_text(label)
        self.filetype.set_active(0 if saving else len(filters) - 1)
        self.filetype.connect('changed', self.change_type)
        grid.attach(Gtk.Label(label='Save as type:' if saving else 'Files of type:', xalign=0), 0, 3, 1, 1)
        grid.attach(self.filetype, 1, 3, 1, 1)
        cancel = Gtk.Button(label='Cancel')
        cancel.connect('clicked', lambda *_: self.response(Gtk.ResponseType.CANCEL))
        grid.attach(cancel, 2, 3, 1, 1)
        self.feedback = Gtk.Label(xalign=0)
        grid.attach(self.feedback, 0, 4, 3, 1)
        self.change_folder(path)
        area.show_all()
        self.set_focus(self.filename)

    def build_native(self, path, name):
        assets, _, _ = self.native_art
        self.get_style_context().add_class('win95-native-file')
        install_style(self, NATIVE_STYLE)
        self.details = False
        self.type_index = 0 if self.saving or name == "*.txt" else len(self.filters)-1
        self.feedback = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.location = Gtk.Label()
        self.filetype = self
        self.buttons = []
        self.fixed, self.canvas = fixed_canvas(self, 426, 263, self.draw_native)
        self.files = Gtk.ListStore(str, str, bool, GdkPixbuf.Pixbuf, str)
        self.view = Gtk.TreeView(model=self.files, headers_visible=False, fixed_height_mode=True)
        self.view.connect('row-activated', self.activate_row)
        self.view.get_selection().connect('changed', self.select_file)
        self.view.connect('button-press-event', self.list_context)
        column = Gtk.TreeViewColumn()
        icon = Gtk.CellRendererPixbuf()
        icon.set_fixed_size(16, 16)
        label = Gtk.CellRendererText(xpad=1, ypad=0)
        label.set_fixed_size(-1, 16)
        column.pack_start(icon, False)
        column.add_attribute(icon, 'pixbuf', 3)
        column.pack_start(label, True)
        column.add_attribute(label, 'text', 0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_fixed_width(296)
        self.view.append_column(column)
        self.details_column = Gtk.TreeViewColumn('Size', Gtk.CellRendererText(ypad=0), text=4)
        self.details_column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        self.details_column.set_fixed_width(92)
        self.details_column.set_visible(False)
        self.view.append_column(self.details_column)
        scroll = Gtk.ScrolledWindow(overlay_scrolling=False)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.view)
        style_scrollbars(scroll)
        scroll.set_size_request(403, 133)
        self.fixed.put(scroll, 11, 57)
        self.filename = Gtk.Entry(text=name, width_chars=1)
        self.filename.set_size_request(229, 16)
        self.filename.connect('activate', lambda *_: self.accept())
        self.fixed.put(self.filename, 86, 202)
        self.feedback.set_size_request(405, 12)
        self.fixed.put(self.feedback, 11, 244)
        self.file_icons = {}
        for key, filename in ((True,'file-dialog-folder.png'),(False,'accessory-notepad.png')):
            if (assets/filename).is_file():
                self.file_icons[key] = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(assets/filename),16,16,True)
        up = assets/'file-dialog-up.png'
        self.up_art = cairo.ImageSurface.create_from_png(str(up)) if up.is_file() else None
        controls = (
            ('Folder', (79,26,205,22), self.folder_menu),
            ('Up One Level', (293,26,23,22), lambda *_: self.change_folder(self.folder.parent) if self.folder else None),
            ('Create New Folder', (324,26,23,22), lambda *_: self.edit_entry('new')),
            ('List', (354,26,23,22), lambda *_: self.set_details(False)),
            ('Details', (377,26,24,22), lambda *_: self.set_details(True)),
            ('Save' if self.saving else 'Open', (336,200,75,23), lambda *_: self.accept()),
            ('Cancel', (336,229,75,23), lambda *_: self.response(Gtk.ResponseType.CANCEL)),
            ('File type', (84,226,232,21), self.type_menu),
            ('Help', (386,3,16,16), lambda *_: message_box(
                self, self.get_title(), 'Select a folder and enter a file name.', Gtk.MessageType.INFO)),
            ('Close', (405,3,16,16), lambda *_: self.response(Gtk.ResponseType.CANCEL)),
        )
        for label, rect, action in controls:
            button = artwork_button(self.fixed, self.canvas, label, rect, action)
            self.buttons.append((button, rect))
        self.connect('key-press-event', self.handle_key)
        self.change_folder(path)
        self.get_content_area().show_all()
        self.set_focus(self.filename)
        self.filename.select_region(0, -1)

    def get_active(self):
        return self.type_index

    def draw_native(self, _widget, context):
        _, frame, font = self.native_art
        p = Painter(context, font)
        p.image(frame, 0, 0)
        p.fill(81,29,185,16,LIGHT)
        p.fill(86,202,229,16,LIGHT)
        folder = (self.folder.name or 'Local Disk (C:)') if self.folder else ''
        if self.file_icons.get(True):
            Gdk.cairo_set_source_pixbuf(context,self.file_icons[True],82,28)
            context.paint()
        p.text(folder if len(folder) < 28 else '…'+folder[-25:], 103, 29)
        p.fill(86,229,213,15,LIGHT)
        label = self.filters[self.type_index][0].replace(' (*.txt)', '')
        p.text(label, 88, 229)
        if self.folder and self.folder.parent != self.folder and self.up_art:
            p.image(self.up_art,293,26)
        for button, (x,y,w,h) in self.buttons:
            if button.has_focus():
                for dot in range(4,w-3,2):
                    p.fill(x+dot,y+3,1,1,BLACK)
                    p.fill(x+dot,y+h-4,1,1,BLACK)
        if self.details:
            p.fill(379,28,19,1,BLACK)

    def set_details(self, enabled):
        self.details = enabled
        self.details_column.set_visible(enabled)
        self.view.set_headers_visible(enabled)
        self.canvas.queue_draw()

    def popup_choices(self, button, entries, select):
        menu = Gtk.Menu()
        for label, value in entries:
            item = Gtk.MenuItem(label=label)
            item.connect('activate', lambda _item, value=value: select(value))
            menu.append(item)
        from win95lx.shell.accessories import style_menus
        menu.win95_palette_owner = self
        style_menus(menu)
        menu.show_all()
        menu.popup_at_widget(button, Gdk.Gravity.SOUTH_WEST, Gdk.Gravity.NORTH_WEST, Gtk.get_current_event())

    def folder_menu(self, button):
        folder = self.folder or Path.home()
        candidates = dict.fromkeys([folder, *folder.parents, Path.home()])
        self.popup_choices(button, [(path.name or 'Local Disk (C:)', path) for path in candidates],
                           self.change_folder)

    def type_menu(self, button):
        def select(index):
            self.type_index = index
            self.change_type(self)
        self.popup_choices(button, [(label, index) for index,(label,_,_) in enumerate(self.filters)], select)

    def handle_key(self, _dialog, event):
        if event.keyval == Gdk.KEY_Escape:
            self.response(Gtk.ResponseType.CANCEL)
        elif event.keyval == Gdk.KEY_BackSpace and self.view.has_focus():
            self.change_folder(self.folder.parent)
        elif self.view.has_focus() and event.keyval in (Gdk.KEY_F2,Gdk.KEY_Delete):
            self.edit_entry('rename' if event.keyval == Gdk.KEY_F2 else 'trash')
        else:
            return False
        return True

    def list_context(self, view, event):
        if event.button != 3:
            return False
        row = view.get_path_at_pos(int(event.x),int(event.y))
        if not row:
            return False
        view.get_selection().select_path(row[0])
        menu = Gtk.Menu()
        for name, command in (('Rename','rename'),('Delete','trash')):
            item = Gtk.MenuItem(label=name)
            item.connect('activate', lambda _item, command=command: self.edit_entry(command))
            menu.append(item)
        from win95lx.shell.accessories import style_menus
        menu.win95_palette_owner = self
        style_menus(menu)
        menu.show_all()
        menu.popup_at_pointer(event)
        return True

    def edit_entry(self, command):
        from gi.repository import Gio, GLib
        from win95lx.explorer.file_operations import child_name, move_entry
        model, row = self.view.get_selection().get_selected()
        if command != 'new' and row is None:
            return
        source = Path(model[row][1]) if row is not None else None
        try:
            if command == 'trash':
                response = message_box(self, 'Confirm File Delete', f'Send {source.name} to the Trash?',
                                       Gtk.MessageType.WARNING, YES_NO, Gtk.ResponseType.NO)
                if response == Gtk.ResponseType.YES:
                    Gio.File.new_for_path(str(source)).trash(None)
            else:
                title = 'New Folder' if command == 'new' else 'Rename'
                name = name_dialog(self, title, 'New Folder' if command == 'new' else source.name)
                if name is not None:
                    target = self.folder/child_name(name)
                    if command == 'new':
                        target.mkdir()
                    elif source != target:
                        move_entry(source, target)
        except (OSError, ValueError, GLib.Error) as error:
            self.feedback.set_text(str(error))
            return
        self.change_folder(self.folder)

    def change_folder(self, folder, wildcard=None):
        if folder is None:
            return
        patterns = (wildcard.casefold(),) if wildcard else self.filters[self.filetype.get_active()][1]
        try:
            entries = [(entry, entry.is_dir()) for entry in folder.iterdir() if not entry.name.startswith('.')]
        except OSError as error:
            self.feedback.set_text(error.strerror or 'Could not open this folder.')
            return
        self.folder = folder.resolve()
        self.location.set_text(str(self.folder))
        self.files.clear()
        for entry, directory in sorted(entries, key=lambda item: (not item[1], item[0].name.casefold())):
            if directory or any(fnmatchcase(entry.name.casefold(), pattern) for pattern in patterns):
                if self.native_art:
                    try:
                        size = f'{max(1, (entry.stat().st_size+1023)//1024)} KB' if not directory else ''
                    except OSError:
                        size = ''
                    self.files.append((entry.name, str(entry), directory, self.file_icons.get(directory), size))
                else:
                    label = entry.name + ('/' if directory else '')
                    self.files.append((label, str(entry), directory))
        if self.native_art:
            self.canvas.queue_draw()
        self.feedback.set_text('')

    def select_file(self, selection):
        model, row = selection.get_selected()
        if row is not None and not model[row][2]:
            self.filename.set_text(Path(model[row][1]).name)

    def change_type(self, combo):
        extension = self.filters[combo.get_active()][2]
        name = self.filename.get_text()
        known = {item[2] for item in self.filters if item[2]}
        if self.saving and name and extension and Path(name).suffix.casefold() in known:
            self.filename.set_text(str(Path(name).with_suffix(extension)))
        if self.folder is not None:
            self.change_folder(self.folder)

    def activate_row(self, view, row, column):
        _, name, directory = self.files[row][:3]
        if directory:
            self.change_folder(Path(name))
        else:
            self.filename.set_text(Path(name).name)
            self.accept()

    def accept(self):
        name = self.filename.get_text()
        if not self.saving and any(char in name for char in '*?'):
            self.change_folder(self.folder, name)
            return
        if not name.strip() or self.folder is None:
            return
        candidate = self.folder / Path(name).expanduser()
        if candidate.is_dir():
            self.change_folder(candidate)
            return
        if self.saving:
            extension = self.filters[self.filetype.get_active()][2]
            if not candidate.suffix and extension:
                candidate = candidate.with_suffix(extension)
            if not candidate.parent.is_dir() or candidate.is_dir():
                self.feedback.set_text('Choose an existing folder and a file name.')
                return
            if candidate.exists():
                answer = file_notice(self, 'overwrite', candidate.name)
                if answer != Gtk.ResponseType.YES:
                    return
        elif not candidate.is_file():
            file_notice(self, 'missing', candidate.name)
            return
        self.path = candidate
        self.response(Gtk.ResponseType.OK)


def choose_file(parent, current, filters, saving=False, name=''):
    drive = Path.home() / 'Win95LXDrive'
    folder = current.parent if current else drive if drive.is_dir() else Path.home()
    dialog = FileDialog(parent, folder, filters, saving, name)
    try:
        return dialog.path if run_dialog(dialog) == Gtk.ResponseType.OK else None
    finally:
        dialog.destroy()


YES_NO = (('_Yes', Gtk.ResponseType.YES), ('_No', Gtk.ResponseType.NO))
SAVE_CHANGES = (*YES_NO, ('_Cancel', Gtk.ResponseType.CANCEL))


def name_dialog(parent, title, original):
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    dialog.set_decorated(False)
    dialog.get_style_context().add_class('win95-file')
    install_style(dialog, STYLE)
    content = dialog.get_content_area()
    content.set_border_width(4)
    caption = Gtk.Label(label=title, xalign=0)
    caption.get_style_context().add_class('caption')
    content.pack_start(caption, False, False, 0)
    entry = Gtk.Entry(text=original, activates_default=True, margin=10)
    content.pack_start(entry, False, False, 0)
    dialog.add_buttons('OK', Gtk.ResponseType.OK, 'Cancel', Gtk.ResponseType.CANCEL)
    dialog.set_default_response(Gtk.ResponseType.OK)
    content.show_all()
    entry.grab_focus()
    entry.select_region(0,-1)
    try:
        return entry.get_text() if run_dialog(dialog) == Gtk.ResponseType.OK else None
    finally:
        dialog.destroy()


def file_notice(parent, state, filename):
    art = dialog_art(parent, state)
    saving = state == 'overwrite'
    if not art:
        if saving:
            return message_box(parent, 'Save As', f'Replace {filename}?',
                               Gtk.MessageType.QUESTION, YES_NO, Gtk.ResponseType.NO)
        return message_box(parent, 'Open', f'{filename} was not found.', Gtk.MessageType.WARNING)

    _, frame, font = art
    width, height = frame.get_width(), frame.get_height()
    dialog = Gtk.Dialog(title='Save As' if saving else 'Open', transient_for=parent, modal=True)
    dialog.set_decorated(False)
    dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    dialog.get_style_context().add_class('win95-native-file')
    install_style(dialog, NATIVE_STYLE)

    def draw(_widget, context):
        p = Painter(context, font)
        p.image(frame,0,0)
        y = 33 if saving else 32
        p.fill(62,y,width-67,13,FACE)
        label = filename
        while font.width(label) > width-70:
            label = label[1:]
        if label != filename:
            label = '…'+label[1:]
        p.text(label,62,y)
        return False

    fixed, canvas = fixed_canvas(dialog,width,height,draw)
    default = Gtk.ResponseType.NO if saving else Gtk.ResponseType.OK
    buttons = (('Yes',Gtk.ResponseType.YES,68), ('No',Gtk.ResponseType.NO,149)) if saving else (
        ('OK',Gtk.ResponseType.OK,131),)
    controls = {}
    for label, response, x in buttons:
        controls[response] = artwork_button(fixed,canvas,label,(x,height-37,75,23),
                                            lambda _button, response=response: dialog.response(response))
    artwork_button(fixed,canvas,'Close',(width-21,3,16,16),lambda *_: dialog.response(default))
    def key(_widget, event):
        if saving and event.keyval in (Gdk.KEY_y,Gdk.KEY_Y):
            dialog.response(Gtk.ResponseType.YES)
        elif event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter):
            response = next((response for response, button in controls.items()
                             if button.has_focus()), default)
            dialog.response(response)
        elif event.keyval in (Gdk.KEY_Escape,Gdk.KEY_n,Gdk.KEY_N):
            dialog.response(default)
        else:
            return False
        return True
    dialog.connect('key-press-event',key)
    dialog.get_content_area().show_all()
    controls[default].grab_focus()
    try:
        return run_dialog(dialog)
    finally:
        dialog.destroy()


def native_prompt(parent, title, text, buttons, default, art, kind=Gtk.MessageType.WARNING, profile=None):
    from win95lx.sound import notify
    notify(parent,{Gtk.MessageType.ERROR:'SystemHand',Gtk.MessageType.WARNING:'SystemExclamation',Gtk.MessageType.QUESTION:'SystemQuestion',Gtk.MessageType.INFO:'SystemAsterisk'}.get(kind,'.Default'))
    assets, frame, font = art
    ident = {Gtk.MessageType.ERROR:103,Gtk.MessageType.QUESTION:102,
             Gtk.MessageType.WARNING:101,Gtk.MessageType.INFO:104}.get(kind,104)
    path = assets/f'message-icon-{ident}.png'
    icon = cairo.ImageSurface.create_from_png(str(path)) if path.is_file() else None
    preserve = (title == 'Notepad' and text ==
                'The text in the Untitled file has changed.\n\nDo you want to save the changes?')
    shortcut=profile=='shortcut'
    width=374 if shortcut else 266
    text_top=38 if shortcut else 31
    text_width=300 if shortcut else 196
    close_x=width-(21 if shortcut else 22)
    lines = []
    for paragraph in text.splitlines():
        line = ''
        for word in paragraph.split():
            candidate = f'{line} {word}' if line else word
            if line and font.width(candidate) > text_width:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    height = 119 if shortcut else max(126, 82+len(lines)*13)
    if preserve:
        height = 126
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.set_decorated(False)
    dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    dialog.get_style_context().add_class('win95-native-file')
    install_style(dialog, NATIVE_STYLE)
    controls = []
    selected = default

    def draw(_widget, context):
        p = Painter(context, font)
        if preserve:
            p.image(frame, 0, 0)
        else:
            p.window_frame(0,0,width,height)
            p.fill(3,3,width-6,18,NAVY)
            p.text(title,5,5,LIGHT,bold=True)
            p.caption_button('close',close_x,5)
            context.save()
            context.rectangle(12,30,33,35)
            context.clip()
            if icon:
                p.image(icon,13,32)
            else:
                p.image(frame,0,0)
            context.restore()
            context.save()
            context.rectangle(62,text_top,text_width,height-65)
            context.clip()
            for index, line in enumerate(lines):
                p.text(line,62,text_top+index*13)
            context.restore()
        for label, response, button, x in controls:
            if not preserve or selected != default:
                p.fill(x-1,button_y-1,77,25,FACE)
                p.button(label.lstrip('_'),x,button_y,75,23,default=response==selected,
                         pressed=bool(button.get_state_flags() & Gtk.StateFlags.ACTIVE))
        return False

    button_y=height-(36 if shortcut else 37)
    fixed, canvas = fixed_canvas(dialog, width, height, draw)
    for index,(label,response) in enumerate(buttons):
        gap=3 if shortcut else 6
        x = (width-(len(buttons)*75+(len(buttons)-1)*gap))//2+index*(75+gap)
        button = artwork_button(fixed,canvas,label.lstrip('_'),(x,button_y,75,23),
                                lambda _button, response=response: dialog.response(response))
        controls.append((label,response,button,x))
        def focused(widget, _event, response=response):
            nonlocal selected
            if widget.has_focus():
                selected = response
                canvas.queue_draw()
        button.connect('notify::has-focus', focused)
    responses = {response for _,response in buttons}
    cancel = Gtk.ResponseType.CANCEL if Gtk.ResponseType.CANCEL in responses else Gtk.ResponseType.NO if Gtk.ResponseType.NO in responses else default
    artwork_button(fixed,canvas,'Close',(close_x,4,18,16),lambda *_: dialog.response(cancel))
    def key(_dialog,event):
        if event.keyval == Gdk.KEY_Escape:
            dialog.response(cancel)
        elif event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter):
            dialog.response(selected)
        elif Gtk.ResponseType.YES in responses and event.keyval in (Gdk.KEY_y,Gdk.KEY_Y,Gdk.KEY_n,Gdk.KEY_N):
            dialog.response(Gtk.ResponseType.YES if event.keyval in (Gdk.KEY_y,Gdk.KEY_Y) else Gtk.ResponseType.NO)
        else:
            return False
        return True
    dialog.connect('key-press-event', key)
    dialog.get_content_area().show_all()
    for _,response,button,_ in controls:
        if response == default:
            button.grab_focus()
    try:
        return run_dialog(dialog)
    finally:
        dialog.destroy()


def message_box(parent, title, text, kind, buttons=(('OK', Gtk.ResponseType.OK),),
                default=Gtk.ResponseType.OK, *, profile=None):
    art = dialog_art(parent, 'close')
    if art:
        return native_prompt(parent, title, text, buttons, default, art, kind, profile)
    from win95lx.sound import notify
    notify(parent,{Gtk.MessageType.ERROR:'SystemHand',Gtk.MessageType.WARNING:'SystemExclamation',Gtk.MessageType.QUESTION:'SystemQuestion',Gtk.MessageType.INFO:'SystemAsterisk'}.get(kind,'.Default'))
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.set_decorated(False)
    dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    dialog.set_default_size(340, 116)
    dialog.get_style_context().add_class('win95-file')
    style = Gtk.CssProvider()
    style.load_from_data(STYLE)
    screen = dialog.get_screen()
    Gtk.StyleContext.add_provider_for_screen(screen, style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    content = dialog.get_content_area()
    content.set_border_width(4)
    caption = Gtk.Label(label=title, xalign=0)
    caption.get_style_context().add_class('caption')
    content.pack_start(caption, False, False, 0)
    row = Gtk.Box(spacing=12, margin=10)
    icon = {
        Gtk.MessageType.QUESTION: 'dialog-question',
        Gtk.MessageType.ERROR: 'dialog-error',
        Gtk.MessageType.WARNING: 'dialog-warning',
    }.get(kind, 'dialog-information')
    row.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG), False, False, 0)
    label = Gtk.Label(label=text, xalign=0, wrap=True, max_width_chars=44)
    row.pack_start(label, True, True, 0)
    content.pack_start(row, True, True, 0)
    for label, response in buttons:
        dialog.add_button(label, response).set_size_request(72, -1)
    dialog.set_default_response(default)
    content.show_all()
    try:
        return run_dialog(dialog)
    finally:
        dialog.destroy()
        Gtk.StyleContext.remove_provider_for_screen(screen, style)


def about_dialog(parent, application):
    """Classic ShellAbout layout with Win95LX application details."""
    title = f'About {application}'
    art = dialog_art(parent, 'about')
    if not art:
        return message_box(parent, title, f'{application} for Win95LX', Gtk.MessageType.INFO)
    assets, frame, font = art
    icon_name = {'Notepad':'notepad', 'WordPad':'wordpad', 'Calculator':'calc'}.get(application)
    icon_path = assets/f'accessory-{icon_name}-32.png'
    icon = cairo.ImageSurface.create_from_png(str(icon_path)) if icon_path.is_file() else None
    dialog = Gtk.Dialog(title=title, transient_for=parent, modal=True)
    dialog.set_decorated(False)
    dialog.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
    dialog.get_style_context().add_class('win95-native-file')
    install_style(dialog, NATIVE_STYLE)

    def draw(_canvas, context):
        p = Painter(context,font)
        p.image(frame,0,0)
        if application != 'Notepad':
            p.fill(4,4,290,16,NAVY)
            p.text(title,4,4,LIGHT,bold=True)
        p.fill(13,30,34,36,FACE)
        if icon:
            p.image(icon,15,32)
        p.fill(78,36,254,143,FACE)
        p.fill(78,190,254,48,FACE)
        p.text(application,81,39)
        p.text('Win95LX Development Edition',81,55)
        p.text('Windows 95-style desktop',81,71)
        p.text('Application information',81,119)
        p.text(f'{application} for Linux',81,135)
        p.text('Win95LX',81,191)
        return False

    fixed, canvas = fixed_canvas(dialog,348,283,draw)
    ok = artwork_button(fixed,canvas,'OK',(258,246,75,23),
                        lambda *_: dialog.response(Gtk.ResponseType.OK))
    artwork_button(fixed,canvas,'Close',(326,4,17,16),
                   lambda *_: dialog.response(Gtk.ResponseType.CLOSE))

    def key(_widget, event):
        if event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter,Gdk.KEY_Escape):
            dialog.response(Gtk.ResponseType.OK)
            return True
        return False

    dialog.connect('key-press-event',key)
    dialog.get_content_area().show_all()
    ok.grab_focus()
    try:
        return run_dialog(dialog)
    finally:
        dialog.destroy()
