"""Shared Edit command availability; independent of menu painting and GTK."""
from dataclasses import dataclass

@dataclass(frozen=True)
class EditContext:
    selected: int = 0
    entries: int = 0
    clipboard: bool = False
    destination_writable: bool = True
    selection_transferable: bool = True


def edit_rows(context):
    selected = bool(context.selected) and context.selection_transferable
    paste = context.clipboard and context.destination_writable
    return (('Undo','Ctrl+Z','undo',False),None,None,
            ('Cut','Ctrl+X','cut',selected),('Copy','Ctrl+C','copy',selected),
            ('Paste','Ctrl+V','paste',paste),('Paste Shortcut','','paste-shortcut',paste),None,
            ('Select All','Ctrl+A','select-all',bool(context.entries)),
            ('Invert Selection','','invert',bool(context.entries)))
