"""Windows 95 system-menu profiles and Move/Size interaction."""

from dataclasses import dataclass

COMMANDS = (
    ('restore', 'Restore', 'r'), ('move', 'Move', 'm'),
    ('size', 'Size', 's'), ('minimize', 'Minimize', 'n'),
    ('maximize', 'Maximize', 'x'), ('close', 'Close', 'c'),
)
MENU_WIDTH = 126
ARROWS = {'Left':(-8,0), 'Right':(8,0), 'Up':(0,-8), 'Down':(0,8)}


def options(*, resizable, minimizable, maximized):
    available = (maximized, not maximized, resizable and not maximized,
                 minimizable, resizable and not maximized, True)
    return tuple((*command, enabled) for command, enabled in zip(COMMANDS, available))


@dataclass
class WindowOperation:
    command: str
    original: tuple[int, int, int, int]
    current: tuple[int, int, int, int]
    pointer: tuple[float, float]

    @classmethod
    def begin(cls, command, bounds, pointer):
        return cls(command, tuple(bounds), tuple(bounds), pointer)

    def step(self, dx, dy, screen):
        x, y, width, height = self.current
        screen_width, screen_height = screen
        if self.command == 'move':
            x = min(max(0, x+dx), max(0, screen_width-80))
            y = min(max(0, y+dy), max(0, screen_height-50))
        else:
            width = max(160, min(width+dx, screen_width-x))
            height = max(110, min(height+dy, screen_height-28-y))
        self.current = x, y, width, height
        return self.current

    def motion(self, x, y, screen):
        start_x, start_y = self.pointer
        self.pointer = x, y
        return self.step(int(x-start_x), int(y-start_y), screen)
