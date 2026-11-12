"""Standard-mode Calculator for the Win95LX desktop.

The arithmetic engine is independent of GTK. Run the application with
`python3 -m win95lx.apps.calculator`.
"""
from decimal import Decimal, DecimalException, localcontext
import operator
import re


OPERATIONS = {
    '+': operator.add,
    '-': operator.sub,
    '*': operator.mul,
    '/': operator.truediv,
}
NUMBER = re.compile(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d{1,4})?', re.ASCII)
DISPLAY_DIGITS = 13


class Calculator:
    """Immediate-execution arithmetic with entry, repeat, and memory state."""

    def __init__(self):
        self.memory = Decimal(0)
        self.clear()

    def clear(self):
        self.entry = '0'
        self.entering = False
        self.left = None
        self.operation = None
        self.repeat = None
        self.error = None

    @property
    def display(self):
        if self.error:
            return self.error
        return self.entry if '.' in self.entry or 'e' in self.entry else self.entry + '.'

    @property
    def memory_active(self):
        return bool(self.memory)

    def paste(self, text):
        text = text.strip()
        if len(text) > 48 or not NUMBER.fullmatch(text):
            return False
        value = Decimal(text)
        if value and abs(value.adjusted()) > 999:
            return False
        if self.error:
            self.clear()
        self._set_value(value)
        if self.operation is None:
            self.repeat = None
        self.entering = True
        return True

    def _set_value(self, value):
        if not value:
            self.entry = '0'
            return
        if abs(value.adjusted()) > 999:
            raise OverflowError
        with localcontext() as context:
            context.prec = DISPLAY_DIGITS
            rounded = (+value).normalize()
        if -5 <= rounded.adjusted() < DISPLAY_DIGITS:
            self.entry = format(rounded, 'f')
        else:
            self.entry = format(rounded, 'e')

    def press(self, key):
        """Apply a keypad label or a canonical operation symbol."""
        if key == 'MC':
            self.memory = Decimal(0)
            return
        if key == 'C':
            self.clear()
            return
        if self.error:
            if key == 'CE' or key == '.' or key in '0123456789' and len(key) == 1:
                self.clear()
            else:
                return
        try:
            with localcontext() as context:
                context.prec = 32
                self._press(key)
        except (DecimalException, OverflowError):
            self.error = 'Error'
            self.left = self.operation = self.repeat = None
            self.entering = False

    def _press(self, key):
        if key in '0123456789' and len(key) == 1 or key == '.':
            self._digit(key)
            return
        value = Decimal(self.entry)
        if key == 'CE':
            self.entry = '0'
            self.entering = True
        elif key == 'Back' and self.entering:
            self.entry = self.entry[:-1] if 'e' not in self.entry else '0'
            if self.entry in ('', '-', '+'):
                self.entry = '0'
        elif key == '+/-':
            if value:
                self.entry = self.entry.removeprefix('-') if value < 0 else '-' + self.entry
            self.entering = True
        elif key in OPERATIONS:
            if self.operation and self.entering:
                self._set_value(OPERATIONS[self.operation](self.left, value))
            self.left = Decimal(self.entry)
            self.operation = key
            self.repeat = None
            self.entering = False
        elif key == '=':
            if self.operation:
                self.repeat = self.operation, value
                self._set_value(OPERATIONS[self.operation](self.left, value))
                self.left = self.operation = None
            elif self.repeat:
                operation, right = self.repeat
                self._set_value(OPERATIONS[operation](value, right))
            self.entering = False
        elif key in ('sqrt', '1/x', '%'):
            if key == 'sqrt':
                value = value.sqrt()
            elif key == '1/x':
                value = 1 / value
            else:
                value /= 100
                if self.operation in ('+', '-'):
                    value *= self.left
            self._set_value(value)
            self.entering = self.operation is not None
        elif key == 'MR':
            self._set_value(self.memory)
            self.entering = True
        elif key == 'MS':
            self.memory = value
            if self.operation is None:
                self.entering = False
        elif key == 'M+':
            result = self.memory + value
            if result and abs(result.adjusted()) > 999:
                raise OverflowError
            self.memory = result
            if self.operation is None:
                self.entering = False

    def _digit(self, digit):
        if not self.entering or 'e' in self.entry:
            self.entry = '0'
            self.entering = True
            if self.operation is None:
                self.repeat = None
        if digit == '.':
            if '.' not in self.entry:
                self.entry += digit
        elif len(self.entry.replace('.', '').lstrip('-')) < DISPLAY_DIGITS:
            self.entry = digit if self.entry == '0' else self.entry + digit


CLIENT_WIDTH = 268
CLIENT_HEIGHT = 244
KEY_WIDTH = 36
KEY_HEIGHT = 28
KEY_COLUMNS = (10, 62, 102, 142, 182, 222)
KEY_ROWS = (
    ('MC', '7', '8', '9', '/', 'sqrt'),
    ('MR', '4', '5', '6', '*', '%'),
    ('MS', '1', '2', '3', '-', '1/x'),
    ('M+', '0', '+/-', '.', '+', '='),
)

STYLE = b"""
window.win95-calculator,
window.win95-calculator .calculator-panel,
window.win95-calculator menubar {
    background: #c0c0c0;
    color: #000;
}
window.win95-calculator * {
    font-family: "MS Sans Serif", "Liberation Sans", sans-serif;
    font-size: 12px;
}
window.win95-calculator menubar {
    border: none;
    box-shadow: none;
    padding: 0;
}
window.win95-calculator menubar > menuitem {
    min-width: 0;
    min-height: 14px;
    padding: 0 4px;
}
window.win95-calculator .menu-rule {
    background: #fff;
    border-top: 1px solid #808080;
    min-height: 1px;
}
window.win95-calculator .readout,
window.win95-calculator .memory-indicator {
    color: black;
    border: 1px solid;
    border-color: #808080 #fff #fff #808080;
    box-shadow: inset 1px 1px #000, inset -1px -1px #c0c0c0;
}
window.win95-calculator .readout {
    background: white;
    padding: 0 7px 0 2px;
}
window.win95-calculator .key {
    background: #c0c0c0;
    color: #00f;
    border: 1px solid;
    border-color: #fff #000 #000 #fff;
    border-radius: 0;
    box-shadow: inset -1px -1px #808080;
    padding: 0;
    min-width: 0;
    min-height: 0;
}
window.win95-calculator .key label {
    font-size: 14px;
    font-weight: bold;
}
window.win95-calculator .key.operation { color: #f00; }
window.win95-calculator .key.function { color: #000080; }
window.win95-calculator .key.command { color: #800000; }
window.win95-calculator .key:active {
    border-color: #808080 #fff #fff #808080;
    box-shadow: inset 1px 1px #000;
}
"""

def build_window():
    """Create a GTK3 Calculator window. GTK is loaded only for the UI."""
    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gdk, Gtk
    from win95lx.apps.dialogs import run_dialog

    class CalculatorWindow(Gtk.Window):
        def __init__(self):
            super().__init__(title='Calculator')
            self.set_resizable(False)
            self.get_style_context().add_class('win95-calculator')
            self.calculator = Calculator()
            self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            provider = Gtk.CssProvider()
            provider.load_from_data(STYLE)
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

            self.set_default_size(CLIENT_WIDTH, CLIENT_HEIGHT)
            self.set_mnemonics_visible(True)
            content = Gtk.Fixed()
            content.set_size_request(CLIENT_WIDTH, CLIENT_HEIGHT)
            panel = Gtk.EventBox()
            panel.get_style_context().add_class('calculator-panel')
            panel.add(content)
            self.add(panel)

            menu = self.build_menu()
            menu.set_size_request(CLIENT_WIDTH - 2, 16)
            content.put(menu, 2, 0)
            menu_rule = Gtk.Box()
            menu_rule.get_style_context().add_class('menu-rule')
            menu_rule.set_size_request(CLIENT_WIDTH, 2)
            content.put(menu_rule, 0, 22)

            self.readout = Gtk.Label(xalign=1)
            self.readout.get_style_context().add_class('readout')
            self.readout.set_size_request(249, 26)
            content.put(self.readout, 10, 37)

            self.memory_indicator = Gtk.Label()
            self.memory_indicator.get_style_context().add_class('memory-indicator')
            self.memory_indicator.set_size_request(KEY_WIDTH, 26)
            content.put(self.memory_indicator, 10, 69)
            for column, key in enumerate(('Back', 'CE', 'C')):
                button = self.button(key, 'command', width=49)
                content.put(button, 103 + 53 * column, 69)

            for row, keys in enumerate(KEY_ROWS):
                for column, key in enumerate(keys):
                    style = ''
                    if column in (0, 4) or key == '=':
                        style = 'operation'
                    elif column == 5:
                        style = 'function'
                    button = self.button(key, style)
                    content.put(button, KEY_COLUMNS[column], 103 + 34 * row)
            self.connect('key-press-event', self.on_key)
            self.refresh()

        def build_menu(self):
            bar = Gtk.MenuBar()
            accelerators = Gtk.AccelGroup()
            self.add_accel_group(accelerators)
            for title, items in (
                ('_Edit', (('_Copy', self.copy, 'c'), ('_Paste', self.paste, 'v'))),
                ('_View', (('S_tandard', None, None),)),
                ('_Help', (('_Help Topics', self.help, None), ('_About Calculator', self.about, None))),
            ):
                root = Gtk.MenuItem.new_with_mnemonic(title)
                menu = Gtk.Menu()
                root.set_submenu(menu)
                for label, callback, shortcut in items:
                    if callback is None:
                        item = Gtk.CheckMenuItem.new_with_mnemonic(label)
                        item.set_draw_as_radio(True)
                        item.set_active(True)
                        item.connect('activate', lambda entry: entry.set_active(True))
                    else:
                        item = Gtk.MenuItem.new_with_mnemonic(label)
                        item.connect('activate', callback)
                    if shortcut:
                        item.add_accelerator(
                            'activate', accelerators, Gdk.keyval_from_name(shortcut),
                            Gdk.ModifierType.CONTROL_MASK, Gtk.AccelFlags.VISIBLE,
                        )
                    menu.append(item)
                bar.append(root)
            return bar

        def button(self, key, style, width=KEY_WIDTH):
            button = Gtk.Button(label=key)
            button.set_size_request(width, KEY_HEIGHT)
            button.set_focus_on_click(False)
            button.get_style_context().add_class('key')
            if style:
                button.get_style_context().add_class(style)
            button.connect('clicked', lambda _: self.press(key))
            return button

        def refresh(self):
            self.readout.set_text(self.calculator.display)
            self.memory_indicator.set_text('M' if self.calculator.memory_active else '')

        def press(self, key):
            self.calculator.press(key)
            self.refresh()

        def copy(self, _):
            if not self.calculator.error:
                self.clipboard.set_text(self.calculator.display, -1)

        def paste(self, _):
            self.clipboard.request_text(self.paste_text)

        def paste_text(self, _, text):
            if text is not None and self.calculator.paste(text):
                self.refresh()

        def message(self, title, body):
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK, text=title,
            )
            dialog.format_secondary_text(body)
            run_dialog(dialog)
            dialog.destroy()

        def help(self, _):
            self.message(
                'Calculator Help',
                'Use the keypad or number keys. Enter evaluates, Backspace removes a digit, '
                'Delete clears the entry, and Esc clears the calculation. F9 changes the sign. '
                'Memory shortcuts use Ctrl+L, Ctrl+R, Ctrl+M, and Ctrl+P.',
            )

        def about(self, _):
            self.message('Calculator', 'Win95LX Standard Calculator')

        def on_key(self, _, event):
            name = Gdk.keyval_name(event.keyval) or ''
            if event.state & Gdk.ModifierType.CONTROL_MASK:
                key = {'l': 'MC', 'r': 'MR', 'm': 'MS', 'p': 'M+'}.get(name.lower())
            else:
                key = {
                    'Return': '=', 'KP_Enter': '=', 'equal': '=', 'KP_Equal': '=',
                    'BackSpace': 'Back', 'Escape': 'C', 'Delete': 'CE', 'KP_Delete': 'CE',
                    'period': '.', 'KP_Decimal': '.', 'KP_Separator': '.',
                    'plus': '+', 'minus': '-', 'asterisk': '*', 'slash': '/',
                    'KP_Add': '+', 'KP_Subtract': '-', 'KP_Multiply': '*', 'KP_Divide': '/',
                    'percent': '%', 'F9': '+/-',
                }.get(name)
                digit = name.removeprefix('KP_')
                if key is None and len(digit) == 1 and digit in '0123456789':
                    key = digit
            if key is None:
                return False
            self.press(key)
            return True

    return CalculatorWindow()


def main():
    window = build_window()
    from gi.repository import Gtk
    window.connect('destroy', Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
