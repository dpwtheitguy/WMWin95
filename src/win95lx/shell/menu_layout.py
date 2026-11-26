"""Geometry shared by the classic menu renderers and their checks."""

POPUP_GUTTER = 24
POPUP_ROW_HEIGHT = 17
POPUP_RIGHT_GUTTER = 16
NOTEPAD_FILE_WIDTH = 113
NOTEPAD_HELP_WIDTH = 120
NOTEPAD_HELP_ROWS = ("_Help Topics", None, "_About Notepad")

# Label origins measured relative to the original My Computer window.
EXPLORER_LABELS = ((24, 'File'), (55, 'Edit'), (89, 'View'), (128, 'Go'),
                   (157, 'Favorites'), (217, 'Help'))


def explorer_menubar(font):
    """Return label placement and a nonoverlapping hitbox for each heading."""
    for index, (x, label) in enumerate(EXPLORER_LABELS):
        left = x-6
        if index+1 < len(EXPLORER_LABELS):
            next_x = EXPLORER_LABELS[index+1][0]
            right = next_x-6
        else:
            right = x+font.width(label)+6
        yield label, x, left, right-left


def popup_width(font, labels):
    return POPUP_GUTTER + max((font.width(label) for label in labels), default=0) + POPUP_RIGHT_GUTTER
