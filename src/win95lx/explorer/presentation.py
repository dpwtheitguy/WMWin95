"""Bounded drive-letter presentation with no Linux paths in the desktop UI."""
from pathlib import Path


class DriveView:
    """Read-only presentation; reject arbitrary paths and symlink escapes."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def resolve(self, relative="."):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise PermissionError("Outside presentation drive")
        return path

    def entries(self, relative="."):
        entries = []
        for item in self.resolve(relative).iterdir():
            if item.name.startswith("."):
                continue
            try:
                if item.resolve().is_relative_to(self.root):
                    entries.append((item.name, item.is_dir()))
            except (OSError, RuntimeError):
                continue
        return sorted(entries, key=lambda item: (not item[1], item[0].casefold(), item[0]))
