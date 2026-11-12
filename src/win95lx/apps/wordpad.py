"""WordPad-style GTK editor with plain text and a small RTF format."""
import argparse
import os
import re
import tempfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Style:
    bold: bool = False
    italic: bool = False
    underline: bool = False
    half_points: int = 20


@dataclass(frozen=True)
class Run:
    text: str
    style: Style = Style()


@dataclass
class Group:
    style: Style = Style(half_points=24)
    skip: bool = False
    unicode_fallback: int = 1


TOKEN = re.compile(
    r"\\(?:(?P<word>[a-zA-Z]+)(?P<parameter>-?\d+)? ?"
    r"|'(?P<hex>[0-9a-fA-F]{2})|(?P<symbol>.))"
    r"|(?P<brace>[{}])|(?P<text>[^\\{}]+)",
    re.S,
)
HIDDEN_GROUPS = {
    'fonttbl', 'colortbl', 'stylesheet', 'info', 'pict', 'object',
    'filetbl', 'listtable', 'listoverridetable', 'generator',
    'header', 'headerl', 'headerr', 'footer', 'footerl', 'footerr',
    'fldinst', 'datastore', 'themedata',
}
TEXT_CONTROLS = {
    'par': '\n', 'line': '\n', 'tab': '\t', 'emdash': '\u2014',
    'endash': '\u2013', 'lquote': '\u2018', 'rquote': '\u2019',
    'ldblquote': '\u201c', 'rdblquote': '\u201d', 'bullet': '\u2022',
}
TEXT_SYMBOLS = {'{': '{', '}': '}', '\\': '\\', '~': '\u00a0', '_': '\u2011'}
ATTRIBUTES = {'b': 'bold', 'i': 'italic', 'ul': 'underline'}


def read_rtf(data):
    """Read text, character emphasis and size from Windows ANSI/Unicode RTF."""
    source = data.decode('latin-1').strip()
    if not source.startswith('{\\rtf'):
        raise ValueError('The file does not begin with an RTF header.')
    groups = []
    group = Group()
    chunks = []
    fallback = 0
    position = 0

    def emit(text):
        nonlocal fallback
        if group.skip or not text:
            return
        if fallback:
            consumed = min(fallback, len(text))
            fallback -= consumed
            text = text[consumed:]
        if text:
            if chunks and chunks[-1][0] == group.style:
                chunks[-1][1].append(text)
            else:
                chunks.append((group.style, [text]))

    while position < len(source):
        match = TOKEN.match(source, position)
        if not match:
            raise ValueError('The RTF file contains an incomplete escape.')
        position = match.end()
        brace, word, parameter, hex_byte, symbol, text = (
            match[name] for name in ('brace', 'word', 'parameter', 'hex', 'symbol', 'text')
        )
        value = int(parameter) if parameter is not None else None
        if brace == '{':
            groups.append(group)
            group = replace(group)
        elif brace == '}':
            if not groups:
                raise ValueError('The RTF file has an unmatched group.')
            group = groups.pop()
            if not groups and position != len(source):
                raise ValueError('Unexpected data after the RTF document.')
        elif word == 'bin':
            if value is None or value < 0 or position + value > len(source):
                raise ValueError('Invalid binary data in the RTF file.')
            position += value
        elif symbol == '*' or word in HIDDEN_GROUPS:
            group.skip = True
        elif group.skip:
            continue
        elif word == 'u' and value is not None:
            fallback = 0
            emit(chr(value & 0xffff))
            fallback = group.unicode_fallback
        elif word == 'uc' and value is not None:
            group.unicode_fallback = max(0, value)
        elif word in ATTRIBUTES:
            group.style = replace(group.style, **{ATTRIBUTES[word]: value != 0})
        elif word == 'ulnone':
            group.style = replace(group.style, underline=False)
        elif word == 'fs' and value is not None and 2 <= value <= 326:
            group.style = replace(group.style, half_points=value)
        elif word == 'plain':
            group.style = Style(half_points=24)
        elif word in TEXT_CONTROLS:
            emit(TEXT_CONTROLS[word])
        elif hex_byte:
            emit(bytes.fromhex(hex_byte).decode('cp1252', errors='replace'))
        elif symbol in TEXT_SYMBOLS:
            emit(TEXT_SYMBOLS[symbol])
        elif text:
            emit(text.replace('\r', '').replace('\n', '').encode('latin-1')
                 .decode('cp1252', errors='replace'))

    if groups:
        raise ValueError('The RTF document ends before its last group is closed.')
    return [
        Run(''.join(parts).encode('utf-16-le', errors='surrogatepass')
            .decode('utf-16-le', errors='replace'), style)
        for style, parts in chunks
    ]


def escape_rtf(text):
    escaped = []
    for char in text:
        if char in '\\{}':
            escaped.append('\\' + char)
        elif char == '\n':
            escaped.append(r'\par ' + '\n')
        elif char == '\t':
            escaped.append(r'\tab ')
        elif ' ' <= char <= '~':
            escaped.append(char)
        else:
            encoded = char.encode('utf-16-le')
            for offset in range(0, len(encoded), 2):
                value = int.from_bytes(encoded[offset:offset + 2], 'little', signed=True)
                escaped.append(f'\\u{value}?')
    return ''.join(escaped)


def write_rtf(runs):
    pieces = [r'{\rtf1\ansi\ansicpg1252\uc1\deff0{\fonttbl{\f0 Times New Roman;}}\f0 ']
    for run in runs:
        style = run.style
        controls = f'\\fs{style.half_points}\\b{int(style.bold)}\\i{int(style.italic)}\\ul{int(style.underline)} '
        pieces.append(controls + escape_rtf(run.text))
    return (''.join(pieces) + '}\n').encode('ascii')


def atomic_write(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
            temporary = Path(file.name)
            file.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


CSS = b"""
.win95-wordpad {
    background-color: #c0c0c0; color: #000000;
    font-family: "MS Sans Serif", "Liberation Sans", sans-serif; font-size: 11px;
}
.win95-wordpad menubar, .win95-wordpad .toolbar, .win95-wordpad .status {
    background: #c0c0c0; color: #000000;
}
.win95-wordpad menubar { padding: 0; min-height: 19px; }
.win95-wordpad menubar > menuitem { padding: 0 6px; min-height: 19px; }
.win95-wordpad .toolbar {
    border-top: 1px solid white; border-bottom: 1px solid #808080; padding: 3px 5px;
}
.win95-wordpad .toolbar button, .win95-wordpad .toolbar entry {
    color: #000000; border-radius: 0;
    border: 1px solid; border-color: white #404040 #404040 white;
    min-height: 18px; min-width: 0; padding: 0 2px; box-shadow: none;
}
.win95-wordpad .toolbar button { background: #c0c0c0; }
.win95-wordpad .toolbar button:checked, .win95-wordpad .toolbar button:active {
    background: #c0c0c0; border-color: #404040 white white #404040;
}
.win95-wordpad .toolbar entry { background: white; border-color: #404040 white white #404040; }
.win95-wordpad .toolbar .wordpad-family button { background: white; }
.win95-wordpad .toolbar .wordpad-family arrow { background: #c0c0c0; }
.win95-wordpad textview, .win95-wordpad textview text {
    background: white; color: black; font-family: "Times New Roman", "Liberation Serif", serif;
    font-size: 10pt;
}
.win95-wordpad textview text selection { background: #000080; color: white; }
.win95-wordpad .status { border-top: 1px solid #808080; padding: 0 3px; }
"""


def build_window(assets=None):
    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gtk', '3.0')
    try:
        gi.require_foreign('cairo')
        ruler_available = True
    except ImportError:
        ruler_available = False
    from gi.repository import Gdk, Gtk, Pango
    from win95lx.apps.dialogs import SAVE_CHANGES, choose_file, message_box, run_dialog

    class WordPad(Gtk.Window):
        def __init__(self):
            super().__init__()
            self.set_default_size(610, 420)
            self.get_style_context().add_class('win95-wordpad')
            provider = Gtk.CssProvider()
            provider.load_from_data(CSS)
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            self.accelerators = Gtk.AccelGroup()
            self.add_accel_group(self.accelerators)
            self.path = None
            self.external_rtf = None
            self.style_tags = {}
            self.tag_styles = {}
            self.pending_style = Style()
            self.loading = False
            self.syncing = False
            self.undo_stack = []
            self.before_edit = None
            self.saved = []
            self.buffer = Gtk.TextBuffer()
            self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            self.view = Gtk.TextView(buffer=self.buffer)
            self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
            self.view.set_left_margin(8)
            self.view.set_right_margin(8)
            self.view.set_top_margin(6)
            self.view.set_bottom_margin(6)
            self.buffer.connect('begin-user-action', self.begin_edit)
            self.buffer.connect('end-user-action', self.end_edit)
            self.buffer.connect_after('insert-text', self.style_inserted_text)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.add(box)
            bar = Gtk.MenuBar()
            self.add_menu(bar, '_File', (
                ('_New', '<Control>n', self.new),
                ('_Open...', '<Control>o', self.open_dialog),
                ('_Save', '<Control>s', self.save),
                ('Save _As...', '<Control><Shift>s', self.save_as),
                None, ('E_xit', '<Alt>F4', self.close),
            ))
            self.add_menu(bar, '_Edit', (
                ('_Undo', '<Control>z', self.undo), None,
                ('Cu_t', '<Control>x', lambda: self.buffer.cut_clipboard(self.clipboard, True)),
                ('_Copy', '<Control>c', lambda: self.buffer.copy_clipboard(self.clipboard)),
                ('_Paste', '<Control>v', lambda: self.buffer.paste_clipboard(self.clipboard, None, True)),
                None, ('Select _All', '<Control>a', self.select_all),
            ))
            self.add_menu(bar, '_View', (
                ('_Toolbar', '', lambda: self.toggle_widget(files)),
                ('_Format Bar', '', lambda: self.toggle_widget(formatting)),
                ('_Ruler', '', lambda: self.toggle_widget(ruler)),
            ))
            self.add_menu(bar, '_Insert', (
                ('_Date and Time', '', self.insert_datetime),
            ))
            self.add_menu(bar, 'F_ormat', (
                ('_Bold', '<Control>b', lambda: self.toggle_format('bold')),
                ('_Italic', '<Control>i', lambda: self.toggle_format('italic')),
                ('_Underline', '<Control>u', lambda: self.toggle_format('underline')),
            ))
            self.add_menu(bar, '_Help', (
                ('_About WordPad', 'F1', self.about),
            ))
            box.pack_start(bar, False, False, 0)

            files = self.toolbar(box)
            for icon, label, callback, gap in (
                ('new', 'New', self.new, 0), ('open', 'Open', self.open_dialog, 0),
                ('save', 'Save', self.save, 0), ('print', 'Print', None, 8),
                ('preview', 'Print Preview', None, 0), ('find', 'Find', None, 8),
                ('cut', 'Cut', lambda: self.buffer.cut_clipboard(self.clipboard, True), 8),
                ('copy', 'Copy', lambda: self.buffer.copy_clipboard(self.clipboard), 0),
                ('paste', 'Paste', lambda: self.buffer.paste_clipboard(self.clipboard, None, True), 0),
                ('undo', 'Undo', self.undo, 0),
                ('datetime', 'Date and Time', self.insert_datetime, 8),
            ):
                button = self.toolbar_button(icon, label)
                button.set_margin_start(gap)
                button.set_sensitive(callback is not None)
                if callback:
                    button.connect('clicked', lambda _, function=callback: function())
                files.pack_start(button, False, False, 0)

            formatting = self.toolbar(box)
            family = Gtk.ComboBoxText()
            family.get_style_context().add_class('wordpad-family')
            family.append_text('Times New Roman')
            family.set_active(0)
            family.set_size_request(237, -1)
            formatting.pack_start(family, False, False, 0)
            self.size = Gtk.ComboBoxText.new_with_entry()
            for points in (8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 28, 36, 48, 72):
                self.size.append_text(str(points))
            self.size.get_child().set_width_chars(3)
            self.size.set_margin_start(10)
            self.size.set_margin_end(10)
            self.size.set_tooltip_text('Font size in points')
            self.size.connect('changed', self.size_changed)
            self.size.get_child().connect('activate', self.size_entered)
            self.size.get_child().connect('focus-out-event', self.size_entered)
            formatting.pack_start(self.size, False, False, 0)
            self.format_buttons = {}
            for attribute in ('bold', 'italic', 'underline'):
                button = self.toolbar_button(attribute, attribute.capitalize(), toggle=True)
                button.connect('toggled', self.format_toggled, attribute)
                formatting.pack_start(button, False, False, 0)
                self.format_buttons[attribute] = button
            for icon, label, gap in (
                ('color', 'Text Color', 0), ('left', 'Align Left', 8),
                ('center', 'Center', 0), ('right', 'Align Right', 0),
                ('bullets', 'Bullets', 8),
            ):
                button = self.toolbar_button(icon, label)
                button.set_sensitive(False)
                button.set_margin_start(gap)
                formatting.pack_start(button, False, False, 0)

            ruler = Gtk.DrawingArea() if ruler_available else Gtk.Box()
            ruler.set_size_request(-1, 21)
            if ruler_available:
                ruler.connect('draw', self.draw_ruler)
            box.pack_start(ruler, False, False, 0)

            viewport = Gtk.ScrolledWindow()
            viewport.set_shadow_type(Gtk.ShadowType.IN)
            viewport.add(self.view)
            box.pack_start(viewport, True, True, 0)
            self.status = Gtk.Label(label='For Help, press F1', xalign=0)
            self.status.set_size_request(-1, 18)
            self.status.get_style_context().add_class('status')
            box.pack_start(self.status, False, False, 0)
            self.set_focus(self.view)
            self.sync_formatting()
            self.buffer.connect('mark-set', self.mark_moved)
            self.connect('delete-event', lambda *_: not self.confirm_discard())
            self.update_title()

        def add_menu(self, bar, label, entries):
            menu_item = Gtk.MenuItem.new_with_mnemonic(label)
            menu = Gtk.Menu()
            menu_item.set_submenu(menu)
            bar.append(menu_item)
            for entry in entries:
                if entry is None:
                    menu.append(Gtk.SeparatorMenuItem())
                    continue
                label, shortcut, callback = entry
                item = Gtk.MenuItem.new_with_mnemonic(label)
                item.connect('activate', lambda _, function=callback: function())
                if shortcut:
                    key, modifiers = Gtk.accelerator_parse(shortcut)
                    item.add_accelerator('activate', self.accelerators, key, modifiers, Gtk.AccelFlags.VISIBLE)
                menu.append(item)

        def toolbar(self, parent):
            toolbar = Gtk.Box()
            toolbar.get_style_context().add_class('toolbar')
            parent.pack_start(toolbar, False, False, 0)
            return toolbar

        def toolbar_button(self, icon, label, toggle=False):
            button = Gtk.ToggleButton() if toggle else Gtk.Button()
            button.set_tooltip_text(label)
            button.set_focus_on_click(False)
            image_path = assets / f'wordpad-toolbar-{icon}.png' if assets else None
            if image_path and image_path.is_file():
                button.set_image(Gtk.Image.new_from_file(str(image_path)))
                button.set_size_request(23, 22)
            else:
                button.set_label(label[0] if toggle else label)
            return button

        def draw_ruler(self, widget, cr):
            width = widget.get_allocated_width()
            cr.set_source_rgb(0.5, 0.5, 0.5)
            cr.rectangle(5, 3, width - 10, 17)
            cr.fill()
            cr.set_source_rgb(1, 1, 1)
            cr.rectangle(6, 4, width - 12, 14)
            cr.fill()
            cr.select_font_face('sans-serif')
            cr.set_font_size(9)
            cr.set_source_rgb(0, 0, 0)
            for x in range(11, width - 5, 12):
                inch, division = divmod(x - 11, 96)
                if division == 0 and inch:
                    cr.move_to(x - 2, 15)
                    cr.show_text(str(inch))
                else:
                    cr.rectangle(x, 8, 1, 6 if division == 48 else 3)
                    cr.fill()
            for x, upper in ((10, True), (10, False), (width - 7, False)):
                tip = 10 if upper else 11
                base = 2 if upper else 18
                cr.move_to(x, tip)
                cr.line_to(x - 4, base)
                cr.line_to(x + 4, base)
                cr.close_path()
                cr.set_source_rgb(0.75, 0.75, 0.75)
                cr.fill_preserve()
                cr.set_source_rgb(0, 0, 0)
                cr.set_line_width(1)
                cr.stroke()

        def toggle_widget(self, widget):
            widget.set_visible(not widget.get_visible())

        def insert_datetime(self):
            self.buffer.begin_user_action()
            try:
                self.buffer.delete_selection(True, True)
                self.buffer.insert_at_cursor(datetime.now().strftime('%m/%d/%Y'))
            finally:
                self.buffer.end_user_action()

        def about(self):
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK, text='WordPad',
            )
            dialog.format_secondary_text('Win95LX WordPad')
            run_dialog(dialog)
            dialog.destroy()

        def style_at(self, iterator):
            return next((self.tag_styles[tag] for tag in iterator.get_tags() if tag in self.tag_styles), Style())

        def apply_style(self, start, end, style):
            for tag in self.style_tags.values():
                self.buffer.remove_tag(tag, start, end)
            if style == Style():
                return
            tag = self.style_tags.get(style)
            if tag is None:
                tag = self.buffer.create_tag(
                    None, weight=Pango.Weight.BOLD if style.bold else Pango.Weight.NORMAL,
                    style=Pango.Style.ITALIC if style.italic else Pango.Style.NORMAL,
                    underline=Pango.Underline.SINGLE if style.underline else Pango.Underline.NONE,
                    size_points=style.half_points / 2,
                )
                self.style_tags[style] = tag
                self.tag_styles[tag] = style
            self.buffer.apply_tag(tag, start, end)

        def snapshot(self, start=None, end=None):
            cursor = (start or self.buffer.get_start_iter()).copy()
            limit = end or self.buffer.get_end_iter()
            runs = []
            while cursor.compare(limit) < 0:
                style = self.style_at(cursor)
                stop = cursor.copy()
                if not stop.forward_to_tag_toggle(None) or stop.compare(limit) > 0:
                    stop = limit.copy()
                text = self.buffer.get_text(cursor, stop, True)
                if runs and runs[-1].style == style:
                    runs[-1] = Run(runs[-1].text + text, style)
                else:
                    runs.append(Run(text, style))
                cursor = stop
            return runs

        def set_runs(self, runs):
            self.loading = True
            try:
                self.buffer.set_text(''.join(run.text for run in runs))
                offset = 0
                for run in runs:
                    stop = offset + len(run.text)
                    self.apply_style(self.buffer.get_iter_at_offset(offset),
                                     self.buffer.get_iter_at_offset(stop), run.style)
                    offset = stop
                self.buffer.place_cursor(self.buffer.get_start_iter())
            finally:
                self.loading = False
            self.pending_style = runs[0].style if runs else Style()
            self.sync_formatting()

        def begin_edit(self, _buffer):
            if not self.loading:
                self.before_edit = self.snapshot()

        def end_edit(self, _buffer):
            if self.loading or self.before_edit is None:
                return
            current = self.snapshot()
            if current != self.before_edit:
                self.undo_stack.append(self.before_edit)
                if len(self.undo_stack) > 50:
                    self.undo_stack.pop(0)
                self.update_title(current)
            self.before_edit = None

        def style_inserted_text(self, _buffer, location, text, _length):
            if not self.loading:
                start = self.buffer.get_iter_at_offset(location.get_offset() - len(text))
                self.apply_style(start, location, self.pending_style)

        def mark_moved(self, _buffer, location, mark):
            if self.loading or self.before_edit is not None or mark.get_name() != 'insert':
                return
            bounds = self.buffer.get_selection_bounds()
            iterator = bounds[0] if bounds else location.copy()
            if not bounds and not iterator.starts_line():
                iterator.backward_char()
            self.pending_style = self.style_at(iterator)
            self.sync_formatting()

        def sync_formatting(self):
            self.syncing = True
            try:
                for name, button in self.format_buttons.items():
                    button.set_active(getattr(self.pending_style, name))
                self.size.get_child().set_text(f'{self.pending_style.half_points / 2:g}')
            finally:
                self.syncing = False

        def format_toggled(self, button, attribute):
            if not self.syncing:
                self.change_format(**{attribute: button.get_active()})

        def size_changed(self, combo):
            if combo.get_active() >= 0:
                self.size_entered(combo.get_child())

        def size_entered(self, entry, *_):
            if self.syncing:
                return False
            try:
                half_points = round(float(entry.get_text()) * 2)
            except (OverflowError, ValueError):
                half_points = 0
            if 2 <= half_points <= 326 and half_points != self.pending_style.half_points:
                self.change_format(half_points=half_points)
            elif not 2 <= half_points <= 326:
                self.sync_formatting()
            return False

        def toggle_format(self, attribute):
            self.change_format(**{attribute: not getattr(self.pending_style, attribute)})

        def change_format(self, **attributes):
            self.pending_style = replace(self.pending_style, **attributes)
            bounds = self.buffer.get_selection_bounds()
            if bounds:
                start, end = bounds
                offset = start.get_offset()
                runs = self.snapshot(start, end)
                self.buffer.begin_user_action()
                try:
                    for run in runs:
                        stop = offset + len(run.text)
                        self.apply_style(self.buffer.get_iter_at_offset(offset),
                                         self.buffer.get_iter_at_offset(stop),
                                         replace(run.style, **attributes))
                        offset = stop
                finally:
                    self.buffer.end_user_action()
            self.sync_formatting()
            self.view.grab_focus()

        def select_all(self):
            self.buffer.select_range(self.buffer.get_end_iter(), self.buffer.get_start_iter())

        def undo(self):
            if self.undo_stack:
                self.set_runs(self.undo_stack.pop())
                self.update_title()

        def update_title(self, runs=None):
            runs = self.snapshot() if runs is None else runs
            self.dirty = runs != self.saved
            name = self.path.name if self.path else 'Document'
            self.set_title(f'{name}{" *" if self.dirty else ""} - WordPad')
            self.status.set_text('Modified' if self.dirty else 'For Help, press F1')

        def message(self, title, detail):
            message_box(self, 'WordPad', f'{title}\n\n{detail}', Gtk.MessageType.ERROR)

        def confirm_discard(self):
            self.update_title()
            if not self.dirty:
                return True
            name = self.path.name if self.path else 'Document'
            response = message_box(self, 'WordPad', f'Save changes to {name}?',
                                   Gtk.MessageType.QUESTION, SAVE_CHANGES, Gtk.ResponseType.YES)
            return response == Gtk.ResponseType.NO or response == Gtk.ResponseType.YES and self.save()

        def new(self):
            if self.confirm_discard():
                self.path = None
                self.external_rtf = None
                self.saved = []
                self.undo_stack.clear()
                self.set_runs([])
                self.update_title()

        def chooser(self, save=False):
            filters = (
                ('Rich Text Format (*.rtf)', ('*.rtf',), '.rtf'),
                ('Text Documents (*.txt)', ('*.txt',), '.txt'),
                ('All Files (*.*)', ('*',), ''),
            )
            name = self.path.name if self.path else 'Document.rtf'
            return choose_file(self, self.path, filters, save, name if save else '')

        def open_dialog(self):
            if not self.confirm_discard():
                return
            path = self.chooser()
            if path is not None:
                self.load(path)

        def load(self, path):
            try:
                data = path.read_bytes()
                external_rtf = None
                if path.suffix.lower() == '.rtf' or data.lstrip().startswith(b'{\\rtf'):
                    runs = read_rtf(data)
                    if data != write_rtf(runs):
                        external_rtf = path.resolve()
                else:
                    try:
                        text = data.decode('utf-8-sig')
                    except UnicodeDecodeError:
                        text = data.decode('cp1252', errors='replace')
                    if '\0' in text:
                        raise ValueError('This file is neither plain text nor supported RTF.')
                    text = text.replace('\r\n', '\n').replace('\r', '\n')
                    runs = [Run(text)] if text else []
            except (OSError, ValueError) as error:
                self.message('Could not open the document', error)
                return
            self.set_runs(runs)
            self.path = path
            self.external_rtf = external_rtf
            self.saved = self.snapshot()
            self.undo_stack.clear()
            self.update_title()

        def save(self):
            if self.path is None:
                return self.save_as()
            runs = self.snapshot()
            if self.path.suffix.lower() != '.rtf' and any(run.style != Style() for run in runs):
                return self.save_as()
            return self.save_to(self.path, runs)

        def save_as(self):
            path = self.chooser(save=True)
            return path is not None and self.save_to(path, self.snapshot())

        def save_to(self, path, runs):
            extension = path.suffix.lower()
            if extension not in ('.rtf', '.txt'):
                self.message('Choose a file format', 'Use .rtf for rich text or .txt for plain text.')
                return False
            if extension == '.txt' and any(run.style != Style() for run in runs):
                self.message('The document contains formatting', 'Save as .rtf to keep formatting.')
                return False
            data = (write_rtf(runs) if extension == '.rtf' else
                    ''.join(run.text for run in runs).replace('\n', '\r\n').encode('utf-8'))
            try:
                if self.external_rtf == path.resolve():
                    dialog = Gtk.MessageDialog(
                        transient_for=self, modal=True, message_type=Gtk.MessageType.WARNING,
                        buttons=Gtk.ButtonsType.OK_CANCEL, text='Replace the original RTF document?',
                    )
                    dialog.format_secondary_text(
                        'This version of WordPad keeps text, bold, italic, underline, and point size. '
                        'Use Save As to keep the original and save a separate copy.'
                    )
                    dialog.set_default_response(Gtk.ResponseType.CANCEL)
                    response = run_dialog(dialog)
                    dialog.destroy()
                    if response != Gtk.ResponseType.OK:
                        return False
                atomic_write(path, data)
            except OSError as error:
                self.message('Could not save the document', error)
                return False
            self.path = path
            self.external_rtf = None
            self.saved = runs
            self.update_title(runs)
            return True

    return WordPad()


def run_editor(initial_path, assets=None):
    window = build_window(assets)
    from gi.repository import Gtk
    window.connect('destroy', Gtk.main_quit)
    window.show_all()
    window.view.grab_focus()
    if initial_path:
        window.load(initial_path)
    Gtk.main()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', type=Path)
    parser.add_argument('--assets', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    run_editor(args.file, args.assets)


if __name__ == '__main__':
    main()
