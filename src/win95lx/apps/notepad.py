"""The Win95LX plain-text editor."""

import argparse
import codecs
from datetime import datetime
import math
import os
from pathlib import Path
import stat
import tempfile

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk, GLib, Gtk, Pango
from win95lx.apps.dialogs import SAVE_CHANGES, choose_file, message_box, run_dialog


MENU_STYLE = b"""
.notepad-menu {
    background: #c0c0c0;
    color: #000;
    padding: 0;
    border-radius: 0;
    font-size: 11px;
}
.notepad-menu > menuitem {
    color: #000;
    padding: 2px 6px;
    min-height: 13px;
}
.notepad-menu > menuitem:hover {
    background: #000080;
    color: #fff;
}
scrollbar.notepad-scrollbar {
    -GtkScrollbar-has-backward-stepper: true;
    -GtkScrollbar-has-forward-stepper: true;
    background: #e0e0e0;
}
scrollbar.notepad-scrollbar slider, scrollbar.notepad-scrollbar button {
    background: #c0c0c0;
    color: #000;
    border: 1px solid;
    border-color: #fff #404040 #404040 #fff;
    border-radius: 0;
    margin: 0;
    padding: 0;
    box-shadow: inset -1px -1px #808080;
}
scrollbar.notepad-scrollbar button:disabled { color: #808080; }
scrollbar.notepad-scrollbar.vertical slider, scrollbar.notepad-scrollbar.vertical button {
    min-width: 14px;
}
scrollbar.notepad-scrollbar.horizontal slider, scrollbar.notepad-scrollbar.horizontal button {
    min-height: 14px;
}
.notepad-editor {
    font-family: monospace;
    font-size: 10pt;
}
.notepad-editor-frame, .notepad-editor-scroll {
    border: 1px solid;
    border-radius: 0;
    padding: 0;
    box-shadow: none;
}
.notepad-editor-frame { border-color: #808080 #fff #fff #808080; }
.notepad-editor-scroll { border-color: #000 #c0c0c0 #c0c0c0 #000; }
menu.notepad-menu {
    border-style: solid;
    border-width: 2px;
    border-color: #fff #404040 #404040 #fff;
}
"""


def read_document(path):
    data = path.read_bytes()
    for bom, encoding in (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16-le"),
        (codecs.BOM_UTF16_BE, "utf-16-be"),
    ):
        if data.startswith(bom):
            text = data[len(bom):].decode(encoding.removesuffix("-sig"))
            break
    else:
        try:
            text = data.decode("utf-8")
            encoding = "utf-8" if not data.isascii() else "cp1252"
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="surrogateescape")
            if any(0xDC80 <= ord(char) <= 0xDCFF for char in text):
                text = data.decode("latin-1")
                encoding = "latin-1"
            else:
                encoding = "cp1252"

    crlf = text.count("\r\n")
    endings = {"\r\n": crlf, "\n": text.count("\n") - crlf, "\r": text.count("\r") - crlf}
    newline = max(endings, key=endings.get)
    return text.replace("\r\n", "\n").replace("\r", "\n"), encoding, newline


def write_document(path, text, encoding, newline):
    text = text.replace("\n", newline)
    try:
        data = text.encode(encoding)
    except UnicodeEncodeError:
        encoding = "utf-8-sig"
        data = text.encode(encoding)
    if encoding in ("utf-16-le", "utf-16-be"):
        data = (codecs.BOM_UTF16_LE if encoding.endswith("le") else codecs.BOM_UTF16_BE) + data

    target = path.resolve()
    try:
        mode = stat.S_IMODE(target.stat().st_mode)
    except FileNotFoundError:
        mode = None

    fd, name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            if mode is not None:
                os.fchmod(output.fileno(), mode)
        os.replace(name, target)
    finally:
        Path(name).unlink(missing_ok=True)
    return encoding


class NotepadWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="Untitled - Notepad")
        self.set_default_size(480, 310)
        self.set_wmclass("notepad", "Win95LX")
        self.set_icon_name("accessories-text-editor")
        self.path = None
        self.encoding = "cp1252"
        self.newline = "\r\n"
        self.saved_text = ""
        self.undo_text = None
        self.user_action_before = None
        self.loading = False
        self.print_settings = Gtk.PrintSettings()
        self.page_setup = Gtk.PageSetup()
        self.menu_style = Gtk.CssProvider()
        self.menu_style.load_from_data(MENU_STYLE)

        self.accels = Gtk.AccelGroup()
        self.add_accel_group(self.accels)
        layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(layout)
        menu_bar = Gtk.MenuBar()
        self.style_menu(menu_bar)
        layout.pack_start(menu_bar, False, False, 0)

        self.view = Gtk.TextView(monospace=True)
        editor_style = self.view.get_style_context()
        editor_style.add_class("notepad-editor")
        editor_style.add_provider(self.menu_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.view.set_left_margin(2)
        self.view.set_right_margin(2)
        self.buffer = self.view.get_buffer()
        self.buffer.connect("begin-user-action", self.begin_edit)
        self.buffer.connect("end-user-action", self.end_edit)
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        self.add_menu(menu_bar, "_File", [
            ("_New", self.new, "<Primary>n"),
            ("_Open...", self.open, "<Primary>o"),
            ("_Save", self.save, "<Primary>s"),
            ("Save _As...", self.save_as, None),
            None,
            ("Page Se_tup...", self.setup_print_page, None),
            ("_Print", self.print_document, None),
            None,
            ("E_xit", self.close, None),
        ])
        self.add_menu(menu_bar, "_Edit", [
            ("_Undo", self.undo, "<Primary>z"),
            None,
            ("Cu_t", lambda: self.buffer.cut_clipboard(clipboard, True), "<Primary>x"),
            ("_Copy", lambda: self.buffer.copy_clipboard(clipboard), "<Primary>c"),
            ("_Paste", lambda: self.buffer.paste_clipboard(clipboard, None, True), "<Primary>v"),
            ("De_lete", lambda: self.buffer.delete_selection(True, True), None),
            None,
            ("Select _All", self.select_all, "<Primary>a"),
            ("Time/_Date", self.insert_date, "F5"),
            None,
            ("_Word Wrap", self.toggle_wrap, None),
        ])
        self.add_menu(menu_bar, "_Search", [
            ("_Find...", self.find, "<Primary>f"),
            ("Find _Next", self.find_next, "F3"),
        ])
        self.add_menu(menu_bar, "_Help", [
            ("_Help Topics", self.show_help, "F1"),
            None,
            ("_About Notepad", self.show_about, None),
        ])
        self.find_text = ""
        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_overlay_scrolling(False)
        self.scroller.set_policy(Gtk.PolicyType.ALWAYS, Gtk.PolicyType.ALWAYS)
        for scrollbar in (self.scroller.get_hscrollbar(), self.scroller.get_vscrollbar()):
            context = scrollbar.get_style_context()
            context.add_class('notepad-scrollbar')
            context.add_provider(self.menu_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.scroller.add(self.view)
        frame = Gtk.Box()
        for widget, style_class in ((frame, "notepad-editor-frame"),
                                    (self.scroller, "notepad-editor-scroll")):
            context = widget.get_style_context()
            context.add_class(style_class)
            context.add_provider(self.menu_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        frame.pack_start(self.scroller, True, True, 0)
        layout.pack_start(frame, True, True, 0)
        self.connect("delete-event", lambda *_: not self.confirm_discard())
        self.set_focus(self.view)

    def style_menu(self, widget):
        context = widget.get_style_context()
        context.add_class("notepad-menu")
        context.add_provider(self.menu_style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def add_menu(self, menu_bar, label, actions):
        top = Gtk.MenuItem.new_with_mnemonic(label)
        menu = Gtk.Menu()
        self.style_menu(menu)
        top.set_submenu(menu)
        menu_bar.append(top)
        for action in actions:
            if action is None:
                menu.append(Gtk.SeparatorMenuItem())
                continue
            caption, callback, shortcut = action
            item_class = Gtk.CheckMenuItem if callback == self.toggle_wrap else Gtk.MenuItem
            item = item_class.new_with_mnemonic(caption)
            item.connect("activate", lambda _item, invoke=callback: invoke())
            if shortcut:
                key, modifiers = Gtk.accelerator_parse(shortcut)
                item.add_accelerator("activate", self.accels, key, modifiers, Gtk.AccelFlags.VISIBLE)
            menu.append(item)

    def text(self):
        start, end = self.buffer.get_bounds()
        return self.buffer.get_text(start, end, True)

    def begin_edit(self, _buffer):
        if not self.loading:
            self.user_action_before = self.text()

    def end_edit(self, _buffer):
        if self.user_action_before is not None and self.user_action_before != self.text():
            self.undo_text = self.user_action_before
        self.user_action_before = None

    def replace_text(self, text):
        self.loading = True
        try:
            self.buffer.set_text(text)
            self.buffer.place_cursor(self.buffer.get_start_iter())
        finally:
            self.loading = False

    def undo(self):
        if self.undo_text is not None:
            original = self.text()
            self.replace_text(self.undo_text)
            self.undo_text = original

    def select_all(self):
        self.buffer.select_range(*self.buffer.get_bounds())

    def insert_date(self):
        self.buffer.begin_user_action()
        try:
            self.buffer.delete_selection(True, True)
            self.buffer.insert_at_cursor(datetime.now().strftime("%I:%M %p %m/%d/%y").lstrip("0"))
        finally:
            self.buffer.end_user_action()

    def toggle_wrap(self):
        wrap = Gtk.WrapMode.WORD_CHAR if self.view.get_wrap_mode() == Gtk.WrapMode.NONE else Gtk.WrapMode.NONE
        self.view.set_wrap_mode(wrap)
        horizontal = Gtk.PolicyType.ALWAYS if wrap == Gtk.WrapMode.NONE else Gtk.PolicyType.NEVER
        self.scroller.set_policy(horizontal, Gtk.PolicyType.ALWAYS)

    def setup_print_page(self):
        self.page_setup = Gtk.print_run_page_setup_dialog(self, self.page_setup, self.print_settings)

    def print_document(self):
        try:
            gi.require_foreign("cairo")
        except ImportError:
            self.message(Gtk.MessageType.ERROR, "Printing requires the Python GTK Cairo bindings.")
            return
        gi.require_version("PangoCairo", "1.0")
        from gi.repository import PangoCairo

        operation = Gtk.PrintOperation(default_page_setup=self.page_setup, print_settings=self.print_settings)
        operation.set_job_name(self.path.name if self.path else "Untitled")
        operation.set_unit(Gtk.Unit.POINTS)
        pages = []

        def paginate(job, context):
            font = Pango.FontDescription.from_string("Monospace 10")
            measure = context.create_pango_layout()
            measure.set_font_description(font)
            measure.set_width(int(context.get_width() * Pango.SCALE))
            measure.set_wrap(Pango.WrapMode.CHAR)
            measure.set_text(self.text(), -1)
            line_height = math.ceil(font.get_size() / Pango.SCALE * 1.25)
            lines_per_page = max(1, int(context.get_height() / line_height))
            data = self.text().encode()
            lines = []
            for line in measure.get_lines_readonly():
                lines.append(data[line.start_index:line.start_index + line.length].decode())
            for start in range(0, len(lines), lines_per_page):
                pages.append("\n".join(lines[start:start + lines_per_page]))
            job.set_n_pages(len(pages))

        def draw_page(_job, context, number):
            layout = context.create_pango_layout()
            layout.set_font_description(Pango.FontDescription.from_string("Monospace 10"))
            layout.set_text(pages[number], -1)
            PangoCairo.show_layout(context.get_cairo_context(), layout)

        operation.connect("begin-print", paginate)
        operation.connect("draw-page", draw_page)
        try:
            result = operation.run(Gtk.PrintOperationAction.PRINT_DIALOG, self)
            if result == Gtk.PrintOperationResult.APPLY:
                self.print_settings = operation.get_print_settings()
        except GLib.Error as error:
            self.message(Gtk.MessageType.ERROR, "Cannot print this document.", str(error))

    def show_help(self):
        self.message(
            Gtk.MessageType.INFO, "Notepad Help",
            "Use File to open, save, or print plain text. Use Edit > Word Wrap to fit lines "
            "to the window and Search > Find to locate text.",
        )

    def show_about(self):
        self.message(Gtk.MessageType.INFO, "About Notepad", "Notepad for Win95LX")

    def find(self):
        dialog = Gtk.Dialog(title="Find", transient_for=self, modal=True)
        dialog.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Find Next", Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        entry = Gtk.Entry(text=self.find_text, activates_default=True, margin=8)
        dialog.get_content_area().add(entry)
        entry.show()
        entry.grab_focus()
        response = run_dialog(dialog)
        query = entry.get_text()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and query:
            self.find_text = query
            self.find_next()

    def find_next(self):
        if not self.find_text:
            self.find()
            return
        selection = self.buffer.get_selection_bounds()
        cursor = selection[1] if selection else self.buffer.get_iter_at_mark(self.buffer.get_insert())
        flags = Gtk.TextSearchFlags.CASE_INSENSITIVE
        match = cursor.forward_search(self.find_text, flags, None)
        if match is None:
            match = self.buffer.get_start_iter().forward_search(self.find_text, flags, cursor)
        if match:
            start, end = match
            self.buffer.select_range(start, end)
            self.view.scroll_to_iter(start, 0.1, False, 0, 0)
        else:
            self.message(Gtk.MessageType.INFO, f'Cannot find "{self.find_text}".')

    def message(self, message_type, message, detail=None):
        text = f"{message}\n\n{detail}" if detail else message
        message_box(self, "Notepad", text, message_type)

    def confirm_discard(self):
        if self.text() == self.saved_text:
            return True
        name = self.path.name if self.path else "Untitled"
        response = message_box(self, "Notepad", f"Do you want to save the changes to {name}?",
                               Gtk.MessageType.QUESTION, SAVE_CHANGES, Gtk.ResponseType.YES)
        return response == Gtk.ResponseType.NO or (response == Gtk.ResponseType.YES and self.save())

    def set_document(self, path, text="", encoding="cp1252", newline="\r\n"):
        self.path = path
        self.saved_text = text
        self.encoding = encoding
        self.newline = newline
        self.undo_text = None
        self.replace_text(text)
        self.update_title()

    def update_title(self):
        self.set_title(f"{self.path.name if self.path else 'Untitled'} - Notepad")

    def new(self):
        if self.confirm_discard():
            self.set_document(None)

    def choose_path(self, saving=False):
        filters = (("Text Documents (*.txt)", ("*.txt",), ".txt"),
                   ("All Files (*.*)", ("*",), ""))
        name = self.path.name if self.path else "Untitled.txt"
        return choose_file(self, self.path, filters, saving, name if saving else "")

    def open(self):
        if self.confirm_discard():
            path = self.choose_path()
            if path is not None:
                self.open_path(path)

    def open_path(self, path):
        path = Path(path).absolute()
        try:
            text, encoding, newline = read_document(path)
            if "\0" in text:
                raise ValueError("The file contains null characters.")
        except (OSError, ValueError) as error:
            self.message(Gtk.MessageType.ERROR, f"Cannot open {path.name}.", str(error))
            return False
        self.set_document(path, text, encoding, newline)
        return True

    def save_as(self):
        path = self.choose_path(saving=True)
        return path is not None and self.save_path(path)

    def save(self):
        return self.save_as() if self.path is None else self.save_path(self.path)

    def save_path(self, path):
        path = Path(path).absolute()
        text = self.text()
        if path == self.path and text == self.saved_text and path.exists():
            return True
        try:
            self.encoding = write_document(path, text, self.encoding, self.newline)
        except (OSError, RuntimeError) as error:
            self.message(Gtk.MessageType.ERROR, f"Cannot save {path.name}.", str(error))
            return False
        self.path = path
        self.saved_text = text
        self.update_title()
        return True


def main(argv=None):
    parser = argparse.ArgumentParser(description="Win95LX Notepad")
    parser.add_argument("filename", nargs="?", type=Path)
    args = parser.parse_args(argv)
    window = NotepadWindow()
    window.connect("destroy", Gtk.main_quit)
    window.show_all()
    if args.filename is not None:
        window.open_path(args.filename)
    Gtk.main()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
