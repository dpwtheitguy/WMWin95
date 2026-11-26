"""User placement of built-in shortcuts in the Start Menu folder tree."""

import json
from pathlib import Path

from win95lx.shell.desktop_icons import write_positions
from win95lx.shell.start_menu import SUBMENUS

FOLDER_TITLES = {None: 'Start Menu', 0: 'Programs', 'accessories': 'Accessories', 'games': 'Games'}
SHORTCUTS = {row[2][1]: (folder, row) for folder in FOLDER_TITLES if folder is not None
             for row in SUBMENUS[folder] if row[2][0] == 'accessory'}


class ShortcutFolders:
    def __init__(self, path=None):
        self.path = path if path is not None else Path.home()/'.config'/'win95lx'/'shortcut-folders.json'
        try:
            saved = json.loads(self.path.read_text())
        except (OSError, ValueError):
            saved = {}
        self.locations = {key: value for key, value in saved.items()
                          if key in SHORTCUTS and self.accepts(value)} if isinstance(saved, dict) else {}

    @staticmethod
    def accepts(folder):
        return type(folder) in (int, str) and folder in FOLDER_TITLES

    def entries(self, folder):
        if folder is None:
            return (('Programs', 4, ('submenu', 0)),)
        if not self.accepts(folder):
            return SUBMENUS[folder]
        folders = tuple(row for row in SUBMENUS[folder] if row[2][0] == 'submenu')
        programs = tuple(row for key, (default, row) in SHORTCUTS.items()
                         if self.locations.get(key, default) == folder)
        return folders + tuple(sorted(programs, key=lambda row: row[0].casefold()))

    def move(self, shortcut, destination):
        if shortcut not in SHORTCUTS or not self.accepts(destination):
            return False
        locations = {**self.locations, shortcut: destination}
        write_positions(self.path, locations)
        self.locations = locations
        return True
