"""Classic Start button and shortcut context menus."""

from win95lx.shell.widgets import BLACK, LIGHT, NAVY, SHADOW


class StartContext:
    def __init__(self, x, y, rows, width, screen_width, screen_height):
        self.rows = rows
        self.width = width
        self.height = 6 + sum(9 if row is None else 17 for row in rows)
        self.x = max(0, min(int(x), screen_width-width))
        self.y = max(0, min(int(y), screen_height-self.height))
        self.selected = None

    def entries(self):
        y = self.y + 3
        for row in self.rows:
            yield y, row
            y += 9 if row is None else 17

    def at(self, x, y):
        if self.x+3 <= x < self.x+self.width-3:
            for yy, row in self.entries():
                if row and row[1] and yy <= y < yy+17:
                    return yy, row
        return None

    def draw(self, painter):
        painter.window_frame(self.x, self.y, self.width, self.height)
        for index, (y, row) in enumerate(self.entries()):
            if row is None:
                painter.fill(self.x+3, y+3, self.width-6, 1, SHADOW)
                painter.fill(self.x+3, y+4, self.width-6, 1, LIGHT)
                continue
            label, action = row
            selected = self.selected == y
            if selected:
                painter.fill(self.x+3, y, self.width-6, 17, NAVY)
            painter.text(label, self.x+23, y+1, LIGHT if selected else BLACK if action else SHADOW,
                         bold=index == 0)


class SystemContext(StartContext):
    """The control menu drawn below an internal window's title-bar icon."""

    def __init__(self, win, rows, width, screen_width, screen_height):
        super().__init__(win.x+4, win.y+22, rows, width, screen_width, screen_height)
        self.window = win
        self.selected = self.y+3

    def draw(self, painter):
        painter.window_frame(self.x, self.y, self.width, self.height)
        for y, row in self.entries():
            if row is None:
                painter.fill(self.x+3, y+3, self.width-6, 1, SHADOW)
                painter.fill(self.x+3, y+4, self.width-6, 1, LIGHT)
                continue
            label, action = row
            selected = self.selected == y
            if selected:
                painter.fill(self.x+3, y, self.width-6, 17, NAVY)
            color = SHADOW if action is None else LIGHT if selected else BLACK
            bold = label == 'Close'
            painter.text(label, self.x+23, y+1, color, bold=bold)
            if bold:
                painter.text('Alt+F4', self.x+75, y+1, color, bold=True)
