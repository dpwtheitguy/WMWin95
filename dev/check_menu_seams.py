#!/usr/bin/env python3
"""Render the built-in apps and check the rows where menus meet content."""

import argparse
from pathlib import Path
import sys
import time
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

FACE = (192, 192, 192)
GRAY = (128, 128, 128)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
BOARD_FACE = (191, 191, 191)

# The final four rows of the menu followed by the first eight rows of its body.
# Notepad has a recessed editor, WordPad a toolbar edge, Calculator a two-row
# rule, and Minesweeper the raised edge of its board.
EXPECTED = {
    'notepad': (FACE,) * 4 + (GRAY, BLACK) + (WHITE,) * 6,
    'wordpad': (FACE,) * 4 + (WHITE,) + (FACE,) * 7,
    'calc': (FACE,) * 6 + (GRAY, WHITE) + (FACE,) * 4,
    'winmine': (FACE,) * 4 + (WHITE,) * 3 + (BOARD_FACE,) * 3 + (GRAY,) * 2,
}


def find_menu(widget, gtk):
    if isinstance(widget, gtk.MenuBar):
        return widget
    if isinstance(widget, gtk.Container):
        for child in widget.get_children():
            bar = find_menu(child, gtk)
            if bar is not None:
                return bar
    return None


def flush_draws(gtk):
    until = time.monotonic() + .15
    while time.monotonic() < until:
        while gtk.events_pending():
            gtk.main_iteration_do(False)
        time.sleep(.005)


def sample_menu(window, bar, gdk):
    x, y = bar.translate_coordinates(window, 0, 0)
    area = bar.get_allocation()
    width, height = window.get_size()
    pixbuf = gdk.pixbuf_get_from_window(window.get_window(), 0, 0, width, height)
    if pixbuf is None:
        raise RuntimeError('Could not capture the app window')
    pixels = pixbuf.get_pixels()
    stride = pixbuf.get_rowstride()
    channels = pixbuf.get_n_channels()

    def profile(column):
        return tuple(tuple(pixels[row*stride+column*channels:row*stride+column*channels+3])
                     for row in range(y+area.height-4, y+area.height+8))

    # Keep clear of labels, the right frame, and Notepad's scroll bar.
    return [profile(x+area.width-offset) for offset in (24, 30, 36)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT / 'private' / 'shell-assets')
    args = parser.parse_args()

    import gi

    gi.require_foreign('cairo')
    from win95lx.shell.app import Gdk, Gtk, Shell
    from win95lx.shell.accessories import APPLICATIONS

    if not Gtk.init_check()[0]:
        parser.error('An X11 display is required. Run through xvfb-run for isolation.')
    if not (args.assets / 'ms-sans-serif-8.fnt').is_file():
        parser.error('Stage the private shell assets with tools/prepare_assets.py first.')
    if APPLICATIONS.keys() != EXPECTED.keys():
        parser.error('Update the expected menu boundary for the current set of built-in apps.')

    failed = False
    with TemporaryDirectory() as directory, patch('pathlib.Path.home', return_value=Path(directory)):
        shell = Shell(args.assets)
        shell.show_all()
        flush_draws(Gtk)
        for kind, expected in EXPECTED.items():
            shell.launch_accessory(kind)
            flush_draws(Gtk)
            window = shell.accessory_windows.get(kind)
            if window is None:
                print(f'{kind}: could not launch', file=sys.stderr)
                failed = True
                continue
            bar = find_menu(window, Gtk)
            if bar is None:
                print(f'{kind}: no menu bar to check', file=sys.stderr)
                failed = True
                window.destroy()
                continue
            profiles = sample_menu(window, bar, Gdk)
            if all(profile == expected for profile in profiles):
                print(f'{kind}: menu boundary matches')
            else:
                print(f'{kind}: extra or misplaced menu boundary row', file=sys.stderr)
                for index, row in enumerate(zip(*profiles)):
                    if any(color != expected[index] for color in row):
                        print(f'  offset {index-4:+d}: expected {expected[index]}, saw {row}',
                              file=sys.stderr)
                failed = True
            window.destroy()
        shell.disconnect_by_func(Gtk.main_quit)
        shell.destroy()
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
