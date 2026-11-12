"""Classic Minesweeper for the Win95LX desktop."""
from io import BytesIO
import random
import time


DIFFICULTIES = {
    'Beginner': (8, 8, 10),
    'Intermediate': (16, 16, 40),
    'Expert': (30, 16, 99),
}
CELL = 16
MARGIN = 9
BOARD_Y = 52


class Minefield:
    """A minefield with first-click safety, flags, and chord reveals."""

    def __init__(self, width, height, mine_count, rng=None):
        self.width = width
        self.height = height
        self.mine_count = mine_count
        self.rng = rng if rng is not None else random.Random()
        self.cells = {(x, y) for y in range(height) for x in range(width)}
        if not 0 < mine_count < len(self.cells):
            raise ValueError('Mine count must leave at least one safe cell')
        self.mines = set()
        self.revealed = set()
        self.flags = set()
        self.questions = set()
        self.state = 'ready'
        self.exploded = None

    def neighbors(self, cell):
        x, y = cell
        return {
            (x + dx, y + dy)
            for dy in (-1, 0, 1)
            for dx in (-1, 0, 1)
            if (dx or dy) and (x + dx, y + dy) in self.cells
        }

    def number(self, cell):
        return len(self.neighbors(cell) & self.mines)

    def mark(self, cell, questions=True):
        if self.state not in ('ready', 'playing') or cell not in self.cells or cell in self.revealed:
            return
        if cell in self.flags:
            self.flags.remove(cell)
            if questions:
                self.questions.add(cell)
        elif cell in self.questions:
            self.questions.remove(cell)
        else:
            self.flags.add(cell)

    def reveal(self, cell):
        if self.state not in ('ready', 'playing') or cell not in self.cells or cell in self.flags:
            return
        if self.state == 'ready':
            self.mines = set(self.rng.sample(sorted(self.cells - {cell}), self.mine_count))
            self.state = 'playing'
        self._reveal_cells({cell})

    def chord(self, cell):
        if self.state != 'playing' or cell not in self.revealed:
            return
        around = self.neighbors(cell)
        if len(around & self.flags) == self.number(cell):
            self._reveal_cells(around)

    def _reveal_cells(self, cells):
        pending = cells - self.flags - self.revealed
        while pending:
            cell = pending.pop()
            if cell in self.mines:
                self.exploded = cell
                self.state = 'lost'
                return
            self.questions.discard(cell)
            self.revealed.add(cell)
            if not self.number(cell):
                pending.update(self.neighbors(cell) - self.revealed - self.flags)
        if len(self.revealed) == len(self.cells) - self.mine_count:
            self.flags = self.mines.copy()
            self.questions.clear()
            self.state = 'won'


BLACK = (0, 0, 0)
WHITE = (1, 1, 1)
PANEL = (0.75, 0.75, 0.75)
GRAY = (0.5, 0.5, 0.5)
RED = (1, 0, 0)
YELLOW = (1, 1, 0)
NUMBER_COLORS = (
    None, (0, 0, 1), (0, 0.5, 0), RED, (0, 0, 0.5),
    (0.5, 0, 0), (0, 0.5, 0.5), BLACK, GRAY,
)
SEGMENTS = (
    (1, 0, 9, 2), (10, 2, 2, 8), (10, 12, 2, 8), (1, 20, 9, 2),
    (0, 12, 2, 8), (0, 2, 2, 8), (1, 10, 9, 2),
)
DIGITS = ('012345', '12', '01643', '01623', '5612', '05623', '056423', '012', '0123456', '056123')


def rectangle(context, x, y, width, height, color):
    context.set_source_rgb(*color)
    context.rectangle(x, y, width, height)
    context.fill()


def bevel(context, x, y, width, height, depth, raised):
    top, bottom = (WHITE, GRAY) if raised else (GRAY, WHITE)
    rectangle(context, x, y, width, height, top)
    rectangle(context, x + depth, y + depth, width - depth, height - depth, bottom)
    rectangle(context, x + depth, y + depth, width - 2 * depth, height - 2 * depth, PANEL)


def draw_counter(context, x, y, value):
    rectangle(context, x, y, 41, 25, BLACK)
    value = min(999, max(-99, value))
    for offset, digit in enumerate(f'{value:03d}'):
        active = '6' if digit == '-' else DIGITS[int(digit)]
        for index, (sx, sy, sw, sh) in enumerate(SEGMENTS):
            color = RED if str(index) in active else (0.25, 0, 0)
            rectangle(context, x + 2 + offset * 13 + sx, y + 1 + sy, sw, sh, color)


def draw_mine(context, x, y):
    rectangle(context, x + 7, y + 2, 2, 12, BLACK)
    rectangle(context, x + 2, y + 7, 12, 2, BLACK)
    rectangle(context, x + 5, y + 4, 6, 8, BLACK)
    rectangle(context, x + 4, y + 5, 8, 6, BLACK)
    rectangle(context, x + 5, y + 5, 2, 2, WHITE)


def draw_flag(context, x, y):
    rectangle(context, x + 8, y + 4, 1, 8, BLACK)
    rectangle(context, x + 5, y + 11, 6, 1, BLACK)
    rectangle(context, x + 4, y + 12, 8, 1, BLACK)
    context.set_source_rgb(*RED)
    context.move_to(x + 8, y + 3)
    context.line_to(x + 3, y + 6)
    context.line_to(x + 8, y + 8)
    context.close_path()
    context.fill()


def draw_face(context, x, y, state, surprised):
    bevel(context, x, y, 26, 26, 2, True)
    context.set_line_width(1)
    context.arc(x + 13, y + 13, 8, 0, 6.284)
    context.set_source_rgb(*YELLOW)
    context.fill_preserve()
    context.set_source_rgb(*BLACK)
    context.stroke()
    for eye in (x + 10, x + 16):
        if state == 'lost':
            context.move_to(eye - 2, y + 9)
            context.line_to(eye + 1, y + 12)
            context.move_to(eye + 1, y + 9)
            context.line_to(eye - 2, y + 12)
            context.stroke()
        else:
            rectangle(context, eye - 1, y + 10, 3 if state == 'won' else 2, 2, BLACK)
    if state == 'won':
        rectangle(context, x + 10, y + 10, 6, 1, BLACK)
    if surprised:
        context.arc(x + 13, y + 16, 2, 0, 6.284)
    elif state == 'lost':
        context.arc(x + 13, y + 19, 4, 3.6, 5.8)
    else:
        context.arc(x + 13, y + 13, 5, 0.5, 2.65)
    context.stroke()


def build_window():
    """Build a standalone GTK3 Minesweeper window."""
    import cairo
    import gi
    gi.require_version('Gdk', '3.0')
    gi.require_version('GdkPixbuf', '2.0')
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
    from win95lx.apps.dialogs import run_dialog

    class MinesweeperWindow(Gtk.Window):
        def __init__(self):
            super().__init__(title='Minesweeper')
            self.set_resizable(False)
            self.set_icon_name('mines')
            self.get_style_context().add_class('win95-minesweeper')
            style = Gtk.CssProvider()
            style.load_from_data(b"""
                window.win95-minesweeper,
                window.win95-minesweeper menubar {
                    background: #c0c0c0;
                    color: black;
                    font-family: "MS Sans Serif", "Liberation Sans", sans-serif;
                    font-size: 11px;
                }
                window.win95-minesweeper menubar > menuitem {
                    min-height: 18px;
                    min-width: 0;
                    padding: 0 7px;
                }
            """)
            Gtk.StyleContext.add_provider_for_screen(
                self.get_screen(), style, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
            self.difficulty = 'Beginner'
            self.questions = True
            layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            self.add(layout)
            self.menu = self.menu_bar()
            layout.pack_start(self.menu, False, False, 0)
            self.board = Gtk.EventBox()
            self.image = Gtk.Image()
            self.board.add(self.image)
            layout.pack_start(self.board, False, False, 0)
            self.board.set_can_focus(True)
            self.board.add_events(
                Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK,
            )
            self.board.connect('button-press-event', self.press_button)
            self.board.connect('button-release-event', self.release_button)
            self.connect('key-press-event', self.press_key)
            self.connect('destroy', self.stop_timer)
            self.new_game()
            self.timer = GLib.timeout_add(150, self.tick)

        def menu_bar(self):
            bar = Gtk.MenuBar()
            game = Gtk.MenuItem.new_with_mnemonic('_Game')
            menu = Gtk.Menu()
            game.set_submenu(menu)
            bar.append(game)
            new_item = Gtk.MenuItem.new_with_mnemonic('_New')
            new_item.connect('activate', self.new_game)
            menu.append(new_item)
            menu.append(Gtk.SeparatorMenuItem())
            group = None
            for difficulty in DIFFICULTIES:
                item = Gtk.RadioMenuItem.new_with_label_from_widget(group, difficulty)
                if group is None:
                    group = item
                item.connect('toggled', self.select_difficulty, difficulty)
                menu.append(item)
            menu.append(Gtk.SeparatorMenuItem())
            marks = Gtk.CheckMenuItem.new_with_mnemonic('_Marks (?)')
            marks.set_active(True)
            marks.connect('toggled', self.toggle_questions)
            menu.append(marks)
            menu.append(Gtk.SeparatorMenuItem())
            exit_item = Gtk.MenuItem.new_with_mnemonic('E_xit')
            exit_item.connect('activate', lambda _: self.destroy())
            menu.append(exit_item)
            help_root = Gtk.MenuItem.new_with_mnemonic('_Help')
            help_menu = Gtk.Menu()
            help_root.set_submenu(help_menu)
            instructions = Gtk.MenuItem.new_with_mnemonic('_Help Topics')
            instructions.connect('activate', self.help)
            help_menu.append(instructions)
            bar.append(help_root)
            return bar

        def help(self, _):
            dialog = Gtk.MessageDialog(
                transient_for=self, modal=True, buttons=Gtk.ButtonsType.OK,
                text='Minesweeper Help',
            )
            dialog.format_secondary_text(
                'Uncover every square that has no mine. Numbers count the adjacent mines. '
                'Left-click to uncover, right-click to mark, and middle-click a number '
                'to uncover its neighbors when the flag count matches. Press F2 for a new game. '
                'The arrow keys move the selection. Space uncovers, F marks, and Enter chords.',
            )
            run_dialog(dialog)
            dialog.destroy()

        def select_difficulty(self, item, difficulty):
            if item.get_active() and self.difficulty != difficulty:
                self.difficulty = difficulty
                self.new_game()

        def toggle_questions(self, item):
            self.questions = item.get_active()
            if not self.questions:
                self.field.questions.clear()
                self.render_board()

        def new_game(self, *_):
            self.field = Minefield(*DIFFICULTIES[self.difficulty])
            self.started = None
            self.elapsed = 0
            self.pressed = None
            self.selected = (0, 0)
            self.keyboard = False
            self.render_board()
            image = self.image.get_pixbuf()
            menu_height = self.menu.get_preferred_height()[0]
            self.resize(image.get_width(), image.get_height() + menu_height)

        def stop_timer(self, *_):
            GLib.source_remove(self.timer)

        def tick(self):
            if self.field.state == 'playing' and self.started is not None:
                elapsed = min(999, int(time.monotonic() - self.started) + 1)
                if elapsed != self.elapsed:
                    self.elapsed = elapsed
                    self.render_board()
            return True

        def move(self, cell, action):
            if action == 'reveal':
                self.field.reveal(cell)
                if self.field.state != 'ready' and self.started is None:
                    self.started = time.monotonic()
                    self.elapsed = 1
            elif action == 'mark':
                self.field.mark(cell, self.questions)
            elif action == 'chord':
                self.field.chord(cell)

        def event_cell(self, event):
            x = event.x - self.image_left()
            if x < MARGIN or event.y < BOARD_Y:
                return None
            cell = int((x - MARGIN) // CELL), int((event.y - BOARD_Y) // CELL)
            return cell if cell in self.field.cells else None

        def on_face(self, event):
            left = self.image_left() + self.face_x()
            return left <= event.x < left + 26 and 13 <= event.y < 39

        def press_button(self, _, event):
            if event.type != Gdk.EventType.BUTTON_PRESS:
                return False
            cell = self.event_cell(event)
            self.keyboard = False
            if cell is not None and event.button in (1, 3) and self.pressed == (cell, 1 if event.button == 3 else 3):
                self.pressed = (cell, 2)
            elif cell is not None or self.on_face(event):
                self.pressed = cell, event.button
            else:
                self.pressed = None
            self.render_board()
            return True

        def release_button(self, _, event):
            cell = self.event_cell(event)
            pressed = self.pressed
            self.pressed = None
            if pressed == (None, 1) and event.button == 1 and self.on_face(event):
                self.new_game()
                return True
            elif cell is not None and pressed and cell == pressed[0]:
                self.move(cell, {1: 'reveal', 2: 'chord', 3: 'mark'}.get(pressed[1]))
            self.render_board()
            return True

        def press_key(self, _, event):
            key = Gdk.keyval_name(event.keyval)
            if key == 'F2':
                self.new_game()
                return True
            directions = {'Left': (-1, 0), 'Right': (1, 0), 'Up': (0, -1), 'Down': (0, 1)}
            actions = {'space': 'reveal', 'f': 'mark', 'F': 'mark', 'Return': 'chord', 'KP_Enter': 'chord'}
            if key in directions:
                x, y = self.selected
                dx, dy = directions[key]
                cell = x + dx, y + dy
                if cell in self.field.cells:
                    self.selected = cell
            elif key in actions:
                self.move(self.selected, actions[key])
            else:
                return False
            self.keyboard = True
            self.render_board()
            return True

        def face_x(self):
            return (self.field.width * CELL + 2 * MARGIN - 26) // 2

        def image_left(self):
            width = self.field.width * CELL + 2 * MARGIN
            return max(0, (self.board.get_allocated_width() - width) // 2)

        def render_board(self):
            width = self.field.width * CELL + 2 * MARGIN
            height = self.field.height * CELL + BOARD_Y + MARGIN
            surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
            context = cairo.Context(surface)
            context.set_antialias(cairo.ANTIALIAS_NONE)
            bevel(context, 0, 0, width, height, 3, True)
            bevel(context, 6, 6, width - 12, 39, 2, False)
            draw_counter(context, 11, 13, self.field.mine_count - len(self.field.flags))
            draw_counter(context, width - 52, 13, self.elapsed)
            surprised = bool(
                self.pressed and self.pressed[0] and self.pressed[1] in (1, 2)
                and self.field.state in ('ready', 'playing')
            )
            draw_face(context, self.face_x(), 13, self.field.state, surprised)
            bevel(context, MARGIN - 3, BOARD_Y - 3, self.field.width * CELL + 6,
                  self.field.height * CELL + 6, 3, False)
            context.select_font_face('Liberation Sans', 0, 1)
            context.set_font_size(14)
            for cell in sorted(self.field.cells):
                self.draw_cell(context, cell)
            png = BytesIO()
            surface.write_to_png(png)
            loader = GdkPixbuf.PixbufLoader.new_with_type('png')
            loader.write(png.getvalue())
            loader.close()
            self.image.set_from_pixbuf(loader.get_pixbuf())

        def draw_cell(self, context, cell):
            field = self.field
            x = MARGIN + cell[0] * CELL
            y = BOARD_Y + cell[1] * CELL
            mine_visible = field.state == 'lost' and cell in field.mines and cell not in field.flags
            pressed = self.pressed == (cell, 1) and field.state in ('ready', 'playing')
            if cell in field.revealed or mine_visible or pressed and cell not in field.flags:
                rectangle(context, x, y, CELL, CELL, GRAY)
                rectangle(context, x + 1, y + 1, CELL - 1, CELL - 1, RED if field.exploded == cell else PANEL)
            else:
                bevel(context, x, y, CELL, CELL, 2, True)
            if mine_visible:
                draw_mine(context, x, y)
            elif cell in field.flags:
                draw_flag(context, x, y)
                if field.state == 'lost' and cell not in field.mines:
                    self.draw_text(context, x, y, '×', RED)
            elif cell in field.questions:
                self.draw_text(context, x, y, '?', BLACK)
            elif cell in field.revealed:
                number = field.number(cell)
                if number:
                    self.draw_text(context, x, y, str(number), NUMBER_COLORS[number])
            if self.keyboard and cell == self.selected:
                context.set_source_rgb(*BLACK)
                context.set_line_width(1)
                context.set_dash([1, 1])
                context.rectangle(x + 2.5, y + 2.5, 11, 11)
                context.stroke()
                context.set_dash([])

        def draw_text(self, context, x, y, text, color):
            context.set_source_rgb(*color)
            extents = context.text_extents(text)
            context.move_to(x + (CELL - extents.width) / 2 - extents.x_bearing, y + 13)
            context.show_text(text)

    return MinesweeperWindow()


def main():
    window = build_window()
    from gi.repository import Gtk
    window.connect('destroy', Gtk.main_quit)
    window.show_all()
    Gtk.main()


if __name__ == '__main__':
    main()
