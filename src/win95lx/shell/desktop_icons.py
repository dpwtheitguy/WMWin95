"""Desktop icon positions in guest pixels."""

import json
from pathlib import Path

DEFAULTS = {'computer': (0, 2), 'recycle': (0, 152)}
ICON_WIDTH, ICON_HEIGHT = 76, 54
TASKBAR_HEIGHT = 28


class DesktopIcons:
    def __init__(self, path=None):
        self.path = path if path is not None else Path.home() / '.config' / 'win95lx' / 'desktop-icons.json'
        self.positions = DEFAULTS.copy()
        try:
            saved = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        if isinstance(saved, dict):
            for name in DEFAULTS:
                point = saved.get(name)
                if isinstance(point, list) and len(point) == 2 and all(type(value) is int for value in point):
                    self.positions[name] = tuple(point)

    @staticmethod
    def clamp(x, y, width, height):
        return (max(0, min(x, width-ICON_WIDTH)),
                max(0, min(y, height-TASKBAR_HEIGHT-ICON_HEIGHT)))

    def position(self, name, width, height):
        return self.clamp(*self.positions[name], width, height)

    def move(self, name, point):
        positions = {**self.positions, name: point}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(positions) + '\n')
        temporary.replace(self.path)
        self.positions = positions
