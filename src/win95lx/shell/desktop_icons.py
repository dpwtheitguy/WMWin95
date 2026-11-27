"""Desktop icon positions in guest pixels."""

import json
from pathlib import Path

DEFAULTS = {'computer': (0, 2), 'recycle': (0, 152)}
ICON_WIDTH, ICON_HEIGHT = 76, 54
TASKBAR_HEIGHT = 28
# Native desktop ListView pitch; folder icon geometry is a separate profile.
DESKTOP_CELL_SIZE = (75, 75)


class DesktopIcons:
    CELL_SIZE = DESKTOP_CELL_SIZE

    def __init__(self, path=None):
        self.path = path if path is not None else Path.home() / '.config' / 'win95lx' / 'desktop-icons.json'
        self.positions = DEFAULTS.copy()
        try:
            saved = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        if isinstance(saved, dict):
            for name, point in saved.items():
                if (name in DEFAULTS or name.startswith('file:')) and isinstance(point, list) and len(point) == 2 and all(type(value) is int for value in point):
                    self.positions[name] = tuple(point)

    @staticmethod
    def clamp(x, y, width, height):
        return (max(0, min(x, width-DESKTOP_CELL_SIZE[0])),
                max(0, min(y, height-TASKBAR_HEIGHT-DESKTOP_CELL_SIZE[1])))

    def position(self, name, width, height, default=None):
        return self.clamp(*self.positions.get(name, default), width, height)

    def move(self, name, point):
        positions = {**self.positions, name: point}
        write_positions(self.path, positions)
        self.positions = positions


def desktop_file_slots(entries, height, occupied=()):
    """Find free desktop cells around the actual positions of existing icons."""
    cell_width,cell_height=DESKTOP_CELL_SIZE
    rows = max(1, (height-TASKBAR_HEIGHT-2)//cell_height)
    occupied = list(occupied) if occupied else list(DEFAULTS.values())
    index = 0
    for label, folder in entries:
        while True:
            point = index//rows*cell_width, 2+index%rows*cell_height
            index += 1
            x,y = point
            if all(x+cell_width <= ox or ox+cell_width <= x
                   or y+cell_height <= oy or oy+cell_height <= y for ox,oy in occupied):
                break
        occupied.append(point)
        yield label, folder, point


class ShortcutIcons:
    """Store positions relative to the file pane, separately for each folder."""

    def __init__(self, path=None):
        self.path = path if path is not None else Path.home() / '.config' / 'win95lx' / 'shortcut-icons.json'
        try:
            saved = json.loads(self.path.read_text())
        except (OSError, ValueError):
            saved = {}
        self.positions = saved if isinstance(saved, dict) else {}

    @staticmethod
    def key(folder, label):
        return json.dumps([folder, label], separators=(',', ':'))

    def position(self, folder, label, default):
        value = self.positions.get(self.key(folder, label))
        if isinstance(value, (list, tuple)) and len(value) == 2 and all(type(n) is int for n in value):
            return tuple(value)
        return default

    def move(self, folder, label, point):
        positions = {**self.positions, self.key(folder, label): point}
        write_positions(self.path, positions)
        self.positions = positions


def write_positions(path, positions):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(positions) + '\n')
    temporary.replace(path)
