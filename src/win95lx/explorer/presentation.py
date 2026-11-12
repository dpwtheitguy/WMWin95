"""Bounded drive-letter presentation with no Linux paths in the desktop UI."""
from pathlib import Path


class DriveView:
    """Read-only presentation; reject arbitrary paths and symlink escapes."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def entries(self, relative="."):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise PermissionError("Outside presentation drive")
        return sorted(
            (item.name, item.is_dir())
            for item in path.iterdir()
            if not item.name.startswith(".")
            and item.resolve().is_relative_to(self.root)
        )
