"""C: folder navigation and icon-grid pagination."""

from pathlib import Path

from win95lx.explorer.presentation import DriveView

COLUMN_WIDTH, ROW_HEIGHT = 75, 75
PADDING_X, PADDING_Y = 5, 1
SCROLLBAR_WIDTH = 16


class DriveBrowser:
    def __init__(self, root):
        self.view = DriveView(root)
        self.directory = Path('.')
        self.entries = []
        self.scroll = 0
        self.selection = set()
        self.anchor = None

    @property
    def title(self):
        suffix = str(self.directory).replace('/', '\\')
        return 'C:\\' + ('' if suffix == '.' else suffix)

    def navigate(self, relative):
        target = self.view.resolve(relative).relative_to(self.view.root)
        entries = self.view.entries(target)
        self.directory = target
        self.selection.clear()
        self.anchor = None
        self.entries = entries
        self.scroll = 0

    def refresh(self):
        entries = self.view.entries(self.directory)
        self.entries = entries
        self.selection.intersection_update(name for name, _ in entries)
        if self.anchor not in self.selection:
            self.anchor = None

    def grid(self, width, height):
        columns = max(1, (width-SCROLLBAR_WIDTH-PADDING_X)//COLUMN_WIDTH)
        rows = max(1, (height-PADDING_Y-54)//ROW_HEIGHT+1)
        maximum = max(0, (len(self.entries)+columns-1)//columns-rows)
        self.scroll = max(0, min(self.scroll, maximum))
        return columns, rows, maximum

    @staticmethod
    def icon_position(index, columns):
        return PADDING_X+(index%columns)*COLUMN_WIDTH, PADDING_Y+(index//columns)*ROW_HEIGHT

    def page(self, width, height):
        columns, rows, _ = self.grid(width, height)
        start = self.scroll * columns
        return self.entries[start:start+columns*rows]
