"""Shut Down Windows dialog geometry and input from the native reference."""

import os
from pathlib import Path

import cairo

from win95lx.shell.widgets import BLACK, LIGHT, NAVY

WIDTH, HEIGHT = 322, 172
OPTIONS = ('Shut down', 'Restart', 'Restart in MS-DOS mode')
BUTTONS = ('OK', 'Cancel', 'Help')
ASSETS = ('poweroff', 'reboot', 'dos')


def is_development_guest():
    if os.uname().nodename != 'win95lx-dev':
        return False
    try:
        return Path('/sys/class/dmi/id/sys_vendor').read_text().strip() == 'QEMU'
    except OSError:
        return False


class ShutdownDialog:
    def __init__(self, assets):
        self.images = {}
        for index, name in enumerate(ASSETS):
            path = assets / f'shutdown-{name}.png'
            if path.is_file():
                self.images[index] = cairo.ImageSurface.create_from_png(str(path))
        self.reset()

    def reset(self):
        self.selection = 0
        self.focus = 0

    def draw(self, shell, painter):
        x = (shell.width - WIDTH) // 2 - 1
        y = (shell.height - HEIGHT) // 2 - 54
        painter.fill(0, 0, shell.width, shell.height, BLACK)
        image = self.images.get(self.selection)
        if image:
            painter.image(image, x, y)
        else:
            painter.window_frame(x, y, WIDTH, HEIGHT)
            painter.fill(x+3, y+3, WIDTH-6, 18, NAVY)
            painter.text('Shut Down Windows', x+5, y+5, LIGHT, bold=True)
            painter.caption_button('close', x+302, y+5)
            icon = shell.images.get(26)
            if icon:
                painter.image(icon, x+14, y+40)
            painter.text('What do you want the computer to do?', x+59, y+40)
            for index, label in enumerate(OPTIONS):
                yy = y+66+index*20
                painter.text('(*)' if index == self.selection else '( )', x+60, yy)
                painter.text(label, x+77, yy)
            for index, label in enumerate(BUTTONS):
                painter.button(label, x+62+84*index, y+139, 78, 23, default=index == 0)
        if self.focus:
            xx = x+67+84*(self.focus-1)
            for offset in range(0, 68, 2):
                painter.fill(xx+offset, y+143, 1, 1, BLACK)
                painter.fill(xx+offset, y+157, 1, 1, BLACK)
            for offset in range(1, 14, 2):
                painter.fill(xx, y+143+offset, 1, 1, BLACK)
                painter.fill(xx+67, y+143+offset, 1, 1, BLACK)
        for index in range(len(OPTIONS)):
            shell.hit(x+59, y+64+index*20, 200, 20, ('shutdown-option', index))
        for index in range(len(BUTTONS)):
            shell.hit(x+62+84*index, y+139, 78, 23, ('shutdown-button', index))
        shell.hit(x+301, y+4, 17, 15, ('shutdown-button', 1))

    def key(self, shell, name, shift=False):
        if name in ('Escape', 'F4'):
            shell.shutdown_button(1)
        elif name in ('Up', 'Down', 'Left', 'Right') and self.focus == 0:
            self.selection = (self.selection + (1 if name in ('Down', 'Right') else -1)) % len(OPTIONS)
        elif name in ('Tab', 'ISO_Left_Tab'):
            self.focus = (self.focus + (-1 if shift or name == 'ISO_Left_Tab' else 1)) % 4
        elif name in ('Return', 'KP_Enter') or (name == 'space' and self.focus):
            shell.shutdown_button(max(0, self.focus-1))
        elif name == 'F1':
            shell.shutdown_button(2)
