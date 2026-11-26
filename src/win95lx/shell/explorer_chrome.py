"""Measured chrome for the Explorer window with its optional toolbars hidden."""

import cairo

from win95lx.shell.menu_layout import explorer_menubar
from win95lx.shell.widgets import BLACK, FACE, LIGHT, SHADOW

STRIP_TOP = 22
MENU_TOP = 25
MENU_HEIGHT = 22
POPUP_TOP = 45
PANE_X = 6
PANE_Y = 54
PANE_BOTTOM = 24


def draw(p, win, artwork, hit):
    x, y, w, h = win.x, win.y, win.width, win.height
    p.bevel(x+4, y+52, w-8, h-74, True)
    p.fill(x+5, y+53, w-10, 1, BLACK)
    p.fill(x+5, y+53, 1, h-76, BLACK)
    p.fill(x+PANE_X, y+PANE_Y, w-2*PANE_X, h-PANE_Y-PANE_BOTTOM, LIGHT)
    if len(artwork) == 3 and w >= 292:
        left, middle, right = (artwork[part] for part in ('left', 'middle', 'right'))
        p.image(left, x+4, y+STRIP_TOP)
        p.cr.save()
        p.cr.rectangle(x+246, y+STRIP_TOP, w-292, left.get_height())
        p.cr.clip()
        p.cr.set_source_surface(middle, x+246, y+STRIP_TOP)
        p.cr.get_source().set_extend(cairo.EXTEND_REPEAT)
        p.cr.paint()
        p.cr.restore()
        p.image(right, x+w-46, y+STRIP_TOP)
    else:
        for offset, color in ((22, FACE), (23, SHADOW), (24, LIGHT),
                              (47, SHADOW), (48, LIGHT), (52, SHADOW), (53, BLACK)):
            p.fill(x+5, y+offset, w-10, 1, color)
        for label, offset, _, _ in explorer_menubar(p.font):
            p.text(label, x+offset, y+29)
    for label, offset, left, width in explorer_menubar(p.font):
        hit(x+left, y+MENU_TOP, width, MENU_HEIGHT, ('window-menu',win,label,offset))
