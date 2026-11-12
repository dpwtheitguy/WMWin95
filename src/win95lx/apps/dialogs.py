"""Shared Windows 95-style file dialogs for the desktop accessories."""

from fnmatch import fnmatchcase
from pathlib import Path

from gi.repository import Gdk, Gtk


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
"""


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
        up.connect('clicked', lambda *_: self.change_folder(self.folder.parent) if self.folder else None)
        grid.attach(up, 2, 0, 1, 1)

        self.files = Gtk.ListStore(str, str, bool)
        self.view = Gtk.TreeView(model=self.files, headers_visible=False, activate_on_single_click=False)
        self.view.append_column(Gtk.TreeViewColumn('Name', Gtk.CellRendererText(), text=0))
        self.view.connect('row-activated', self.activate_row)
        self.view.get_selection().connect('changed', self.select_file)
        scroller = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN, vexpand=True)
        scroller.add(self.view)
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

    def change_folder(self, folder):
        patterns = self.filters[self.filetype.get_active()][1]
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
                label = entry.name + ('/' if directory else '')
                self.files.append((label, str(entry), directory))
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
        _, name, directory = self.files[row]
        if directory:
            self.change_folder(Path(name))
        else:
            self.filename.set_text(Path(name).name)
            self.accept()

    def accept(self):
        name = self.filename.get_text()
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
                answer = message_box(self, 'Confirm Save As', f'Replace {candidate.name}?',
                                     Gtk.MessageType.QUESTION, YES_NO, Gtk.ResponseType.NO)
                if answer != Gtk.ResponseType.YES:
                    return
        elif not candidate.is_file():
            self.feedback.set_text('File not found.')
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


def message_box(parent, title, text, kind, buttons=(('OK', Gtk.ResponseType.OK),),
                default=Gtk.ResponseType.OK):
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
