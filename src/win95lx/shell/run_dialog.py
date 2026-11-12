"""The Windows 95 Run dialog and its Win95LX command allowlist."""

from win95lx.shell.widgets import BLACK, FACE, LIGHT, NAVY, SHADOW

COMMANDS = {
    'notepad': ('accessory', 'notepad'),
    'wordpad': ('accessory', 'wordpad'),
    'write': ('accessory', 'wordpad'),
    'calc': ('accessory', 'calc'),
    'winmine': ('accessory', 'winmine'),
    'explorer': ('open', 'computer'),
    'control': ('open', 'control'),
    'desk.cpl': ('open', 'display'),
    'c:': ('open', 'drive'),
}

BROWSE_COMMANDS = (
    ('Calculator', 'calc.exe'),
    ('Control Panel', 'control.exe'),
    ('Display Properties', 'desk.cpl'),
    ('Local Disk (C:)', 'C:'),
    ('Minesweeper', 'winmine.exe'),
    ('Notepad', 'notepad.exe'),
    ('Windows Explorer', 'explorer.exe'),
    ('WordPad', 'wordpad.exe'),
)


def resolve_command(value):
    command = value.strip().casefold()
    if command.endswith('.exe'):
        command = command[:-4]
        if command in ('desk.cpl', 'c:'):
            return None
    return COMMANDS.get(command)


class RunDialog:
    WIDTH = 346
    HEIGHT = 163
    FIELD = 0
    OK = 1
    CANCEL = 2
    BROWSE = 3

    def __init__(self):
        self.history = []
        self.reset()

    def reset(self):
        self.text = ''
        self.caret = 0
        self.selected = False
        self.focus = self.FIELD
        self.panel = None
        self.panel_index = 0
        self.error = ''

    def geometry(self, shell):
        return 5, max(0, shell.height - self.HEIGHT - 32)

    def edit(self, replacement, *, backspace=False, delete=False):
        if self.selected:
            start, end = 0, len(self.text)
        elif backspace:
            start, end = max(0, self.caret - 1), self.caret
        elif delete:
            start, end = self.caret, self.caret + 1
        else:
            start = end = self.caret
        if len(self.text) - (end - start) + len(replacement) > 260:
            return
        self.text = self.text[:start] + replacement + self.text[end:]
        self.caret = start + len(replacement)
        self.selected = False
        self.error = ''

    def rows(self):
        if self.panel == 'browse':
            return BROWSE_COMMANDS
        if self.panel == 'history':
            return [(command, command) for command in self.history]
        return ()

    def activate_panel(self, name):
        self.panel = name if self.panel != name else None
        self.panel_index = 0
        if name != 'help':
            self.focus = self.FIELD

    def choose(self, index):
        self.text = self.rows()[index][1]
        self.caret = len(self.text)
        self.selected = True
        self.panel = None
        self.focus = self.FIELD
        self.error = ''

    def submit(self, shell):
        if not self.text.strip():
            return
        target = resolve_command(self.text)
        if target is None:
            self.error = 'Choose a Win95LX command from Browse.'
            self.selected = True
            self.focus = self.FIELD
            return
        command = self.text.strip()
        self.history = [command] + [item for item in self.history if item.casefold() != command.casefold()][:5]
        shell.state.dialog = None
        shell.action(target)

    def handle_action(self, shell, action):
        kind = action[0]
        if kind == 'run-field':
            self.focus = self.FIELD
            self.selected = False
            self.caret = len(self.text)
            self.panel = None
        elif kind == 'run-panel':
            self.activate_panel(action[1])
        elif kind == 'run-choice':
            self.choose(action[1])
        elif kind == 'dialog-submit':
            self.submit(shell)
        elif kind == 'cancel':
            self.panel = None
            shell.state.dialog = None
        else:
            return False
        return True

    def handle_key(self, shell, event):
        from gi.repository import Gdk, Gtk

        name = Gdk.keyval_name(event.keyval)
        ctrl = event.state & Gdk.ModifierType.CONTROL_MASK
        alt = event.state & Gdk.ModifierType.MOD1_MASK
        shift = event.state & Gdk.ModifierType.SHIFT_MASK
        if name == 'Escape':
            if self.panel:
                self.panel = None
            else:
                shell.state.dialog = None
        elif name == 'F1':
            self.activate_panel('help')
        elif alt and name in ('b', 'B'):
            self.activate_panel('browse')
        elif alt and name in ('o', 'O'):
            self.focus = self.FIELD
            self.selected = bool(self.text)
        elif name in ('Tab', 'ISO_Left_Tab'):
            self.panel = None
            self.focus = (self.focus + (-1 if shift or name == 'ISO_Left_Tab' else 1)) % 4
            if self.focus == self.OK and not self.text.strip():
                self.focus = self.FIELD if shift or name == 'ISO_Left_Tab' else self.CANCEL
        elif name in ('Up', 'Down') and self.focus == self.FIELD:
            if not self.panel:
                self.activate_panel('history')
            elif rows := self.rows():
                direction = 1 if name == 'Down' else -1
                self.panel_index = (self.panel_index + direction) % len(rows)
        elif name in ('Return', 'KP_Enter') or name == 'space' and self.focus != self.FIELD:
            if self.rows():
                self.choose(self.panel_index)
            elif self.panel:
                self.panel = None
            elif self.focus == self.BROWSE:
                self.activate_panel('browse')
                self.focus = self.FIELD
            elif self.focus == self.CANCEL:
                shell.state.dialog = None
            else:
                self.submit(shell)
        elif self.focus == self.FIELD and not alt:
            if ctrl and name in ('a', 'A'):
                self.selected = bool(self.text)
            elif ctrl and name in ('c', 'C', 'x', 'X') and self.selected:
                Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.text, -1)
                if name.lower() == 'x':
                    self.edit('')
            elif ctrl and name in ('v', 'V'):
                def paste(_clipboard, text, _data):
                    if text and shell.state.dialog == 'run' and self.focus == self.FIELD:
                        self.panel = None
                        self.edit(''.join(char for char in text if char.isprintable()))
                        shell.area.queue_draw()
                Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).request_text(paste, None)
            elif not ctrl and name == 'BackSpace':
                self.edit('', backspace=True)
            elif not ctrl and name == 'Delete':
                self.edit('', delete=True)
            elif name in ('Left', 'Right', 'Home', 'End'):
                if name == 'Home':
                    self.caret = 0
                elif name == 'End':
                    self.caret = len(self.text)
                else:
                    self.caret = max(0, min(len(self.text), self.caret + (1 if name == 'Right' else -1)))
                self.selected = False
            elif not ctrl and event.string and event.string.isprintable():
                self.panel = None
                self.edit(event.string)

    def draw(self, shell, p):
        x, y = self.geometry(shell)
        w, h = self.WIDTH, self.HEIGHT
        p.window_frame(x, y, w, h)
        p.fill(x+w-1, y+1, 1, h-2, SHADOW)
        p.fill(x+w-2, y+1, 1, 1, LIGHT)
        p.fill(x+w-2, y+2, 1, h-4, FACE)
        p.fill(x, y+h-1, w, 1, BLACK)
        p.fill(x+3, y+3, w-5, 18, NAVY)
        p.text('Run', x+5, y+5, LIGHT, bold=True)
        p.bevel(x+308, y+5, 16, 14)
        for dy, segments in enumerate((((1, 4),), ((0, 2), (4, 2)), ((0, 2), (4, 2)),
                                       ((3, 2),), ((2, 2),), ((2, 2),), (), ((2, 2),), ((2, 2),))):
            for dx, length in segments:
                p.fill(x+313+dx, y+7+dy, length, 1, BLACK)
        p.caption_button('close', x+326, y+5)
        shell.hit(x+308, y+5, 16, 14, ('run-panel', 'help'))
        shell.hit(x+326, y+5, 16, 14, ('cancel',))
        if 160 in shell.images:
            p.image(shell.images[160], x+14, y+40)
        p.text('Type the name of a program, folder, document, or Internet', x+57, y+40)
        p.text('resource, and Windows will open it for you.', x+57, y+53)
        p.text('Open:', x+14, y+85)
        p.fill(x+14, y+97, p.font.width('O'), 1, BLACK)
        self.draw_field(shell, p, x, y)
        if self.error:
            p.text(self.error, x+58, y+105)
        self.draw_buttons(shell, p, x, y)
        if self.panel:
            self.draw_panel(shell, p, x, y)

    def draw_field(self, shell, p, x, y):
        p.fill(x+57, y+82, 275, 21, LIGHT)
        p.fill(x+57, y+82, 274, 1, SHADOW)
        p.fill(x+57, y+82, 1, 20, SHADOW)
        p.fill(x+58, y+83, 272, 1, BLACK)
        p.fill(x+58, y+83, 1, 18, BLACK)
        p.fill(x+58, y+101, 273, 1, FACE)
        p.fill(x+331, y+83, 1, 19, LIGHT)
        p.bevel(x+314, y+84, 16, 17)
        p.fill(x+330, y+83, 1, 19, FACE)
        p.fill(x+314, y+84, 15, 1, FACE)
        p.fill(x+314, y+85, 1, 15, FACE)
        p.fill(x+315, y+85, 13, 1, LIGHT)
        p.fill(x+315, y+86, 1, 13, LIGHT)
        for line, width in enumerate((7, 5, 3, 1)):
            p.fill(x+318+line, y+90+line, width, 1, BLACK)
        shell.hit(x+59, y+84, 255, 17, ('run-field',))
        shell.hit(x+314, y+84, 16, 17, ('run-panel', 'history'))
        p.cr.save()
        p.cr.rectangle(x+59, y+84, 255, 17)
        p.cr.clip()
        caret = p.font.width(self.text[:self.caret])
        text_x = x+61 - max(0, caret-250)
        if self.selected and self.focus == self.FIELD:
            p.fill(text_x, y+85, p.font.width(self.text), 14, NAVY)
        p.text(self.text, text_x, y+85, LIGHT if self.selected and self.focus == self.FIELD else BLACK)
        if self.focus == self.FIELD and not self.selected and self.text:
            p.fill(text_x+caret, y+86, 1, 13, BLACK)
        p.cr.restore()

    def draw_buttons(self, shell, p, x, y):
        for index, (label, left, action) in enumerate((
            ('OK', 96, ('dialog-submit',)),
            ('Cancel', 177, ('cancel',)),
            ('Browse...', 258, ('run-panel', 'browse')),
        ), 1):
            if index == self.OK:
                p.fill(x+left, y+124, 75, 23, BLACK)
                p.bevel(x+left+1, y+125, 73, 21)
            else:
                p.bevel(x+left, y+124, 75, 23)
            tx = x+left + (75 - p.font.width(label))//2
            ty = y+128
            if index == self.OK and not self.text.strip():
                p.text(label, tx+1, ty+1, LIGHT)
                p.text(label, tx, ty, SHADOW)
            else:
                p.text(label, tx, ty)
                shell.hit(x+left, y+124, 75, 23, action)
            if index == self.BROWSE:
                p.fill(tx, ty+12, p.font.width('B'), 1, BLACK)
            if index == self.focus:
                for fx in range(x+left+4, x+left+71, 2):
                    p.fill(fx, y+127, 1, 1, BLACK)
                    p.fill(fx, y+143, 1, 1, BLACK)

    def draw_panel(self, shell, p, x, y):
        rows = self.rows()
        px = x+57
        row_height = 17
        title = {
            'browse': 'Browse for a Win95LX command',
            'history': 'Recent commands' if rows else 'No recent commands',
            'help': 'Use Browse to choose an available command.',
        }[self.panel]
        height = 20 + row_height * len(rows)
        py = max(0, y+82-height)
        p.window_frame(px, py, 275, height)
        p.text(title, px+5, py+3)
        for index, (label, _) in enumerate(rows):
            row_y = py+17 + index*row_height
            selected = self.panel_index == index
            if selected:
                p.fill(px+3, row_y, 268, row_height, NAVY)
            p.text(label, px+7, row_y+1, LIGHT if selected else BLACK)
            shell.hit(px+3, row_y, 268, row_height, ('run-choice', index))
