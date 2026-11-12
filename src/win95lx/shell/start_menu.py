"""Start menu entries and geometry measured against the 800×600 reference."""

# Each row has a native icon, mnemonic, and either an action or submenu.
ROWS = (
    ('Programs', 20, 'p', None),
    ('Favorites', 'favorites', 'a', None),
    ('Documents', 21, 'd', None),
    ('Settings', 'settings', 's', None),
    ('Find', 'find', 'f', None),
    ('Help', 24, 'h', ('help',)),
    ('Run...', 25, 'r', ('run',)),
    ('Suspend', 26, 'n', ('suspend',)),
    ('Shut Down...', 28, 'u', ('shutdown',)),
)
SUBMENUS = {
    0: (('Accessories', 4, ('submenu', 'accessories')),),
    'accessories': (
        ('Games', 4, ('submenu', 'games')),
        ('Calculator', 'calc', ('accessory', 'calc')),
        ('Notepad', 'notepad', ('accessory', 'notepad')),
        ('WordPad', 'wordpad', ('accessory', 'wordpad')),
    ),
    'games': (('Minesweeper', 'winmine', ('accessory', 'winmine')),),
    1: (('My Computer', 'computer', ('open', 'computer')),
        ('Control Panel', 36, ('open', 'control'))),
    2: (('(C:)', 9, ('open', 'drive')),),
    3: (('Control Panel', 36, ('open', 'control')),
        ('Display Properties', 'display', ('open', 'display'))),
    4: (('Files or Folders...', 23, ('find',)),),
}
FALLBACK_ICONS = {'favorites': 4, 'settings': 22, 'find': 23}
WIDTH = 148
HEIGHT = 339
ROW_HEIGHT = 36


def row_top(menu_top, index):
    return menu_top + 3 + index * ROW_HEIGHT + (9 if index >= 7 else 0)
