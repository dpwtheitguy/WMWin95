#!/usr/bin/env python3
"""Render the reusable file dialogs and exercise file selection and confirmation."""

import argparse
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

import gi

gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_foreign('cairo')
from gi.repository import Gdk, GLib, Gtk

from check_menu_seams import flush_draws
from check_reference_ui import compare_region

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools')]
from pixels import read
from win95lx.apps.dialogs import FileDialog, SAVE_CHANGES, file_notice, message_box


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT/'private/shell-assets')
    parser.add_argument('--references', type=Path,
                        default=ROOT/'private/screenshots/start-development-20261110')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)

    parent = Gtk.Window(title='CommonDialog test')
    parent.dialog_assets = args.assets
    parent.set_default_size(580, 400)
    parent.show_all()
    filters = (('Text Documents', ('*.txt',), '.txt'), ('All Files', ('*',), ''))

    def capture(window, state, size):
        assert window.get_size() == size, f'{state} geometry {window.get_size()}'
        pixbuf = Gdk.pixbuf_get_from_window(window.get_window(), 0, 0, *size)
        assert pixbuf is not None
        path = args.output/f'{state}.png' if args.output else Path(folder)/f'{state}.png'
        pixbuf.savev(str(path), 'png', [], [])
        return read(path)

    with TemporaryDirectory() as folder:
        root = Path(folder)
        (root/'Documents').mkdir()
        (root/'readme.txt').write_text('example')
        (root/'notes.log').write_text('filtered')
        for saving, state in ((False,'open'),(True,'save')):
            dialog = FileDialog(parent, root, filters, saving, 'Untitled' if saving else '*.txt')
            dialog.show_all()
            flush_draws(Gtk)
            actual = capture(dialog, state, (426,263))
            reference = read(args.references/f'native-notepad-{state}-dialog.png')
            for x,y,w,h in ((0,0,426,24),(324,26,77,23),(8,53,408,3),
                            (336,199,75,53),(0,261,426,2)):
                count = compare_region(actual,reference,(96+x,131+y,w,h),(x,y))
                assert count == 0, f'{state} region {(x,y,w,h)} differs by {count} pixels'
            assert [row[0] for row in dialog.files] == ['Documents','readme.txt']
            dialog.activate_row(dialog.view, Gtk.TreePath.new_from_indices([0]), None)
            assert dialog.folder == root/'Documents'
            dialog.change_folder(root)
            dialog.set_details(True)
            assert dialog.details_column.get_visible()
            dialog.set_details(False)
            dialog.filename.set_text('readme.txt')
            if saving:
                with patch('win95lx.apps.dialogs.file_notice', return_value=Gtk.ResponseType.NO):
                    dialog.accept()
                assert dialog.path is None
                with patch('win95lx.apps.dialogs.file_notice', return_value=Gtk.ResponseType.YES):
                    dialog.accept()
                assert dialog.path == root/'readme.txt'
                dialog.filename.set_text('untitled')
                dialog.accept()
                assert dialog.path == root/'untitled.txt'
            else:
                dialog.activate_row(dialog.view, Gtk.TreePath.new_from_indices([1]), None)
                assert dialog.path == root/'readme.txt'
            dialog.destroy()

        for state, size, origin, response in (
            ('missing',(338,126),(234,245),Gtk.ResponseType.OK),
            ('overwrite',(291,139),(257,237),Gtk.ResponseType.NO),
        ):
            captures = []
            def inspect_notice():
                notice, = [window for window in Gtk.Window.list_toplevels()
                           if isinstance(window, Gtk.Dialog) and window.get_visible()]
                try:
                    captures.append(capture(notice,state,size))
                finally:
                    notice.response(response)
                return GLib.SOURCE_REMOVE
            GLib.timeout_add(150,inspect_notice)
            assert file_notice(parent,state,'example.txt') == response
            reference = read(args.references/f'native-notepad-{state}-dialog.png')
            x,y = origin
            for left,top,width,height in ((0,0,size[0],25), (0,26,60,57),
                                           (0,size[1]-43,size[0],43)):
                assert compare_region(captures[0],reference,(x+left,y+top,width,height),(left,top)) == 0

        captures = []
        def inspect_prompt():
            dialogs = [window for window in Gtk.Window.list_toplevels()
                       if isinstance(window, Gtk.Dialog) and window.get_visible()]
            prompt, = dialogs
            try:
                captures.append(capture(prompt, 'close', (266,126)))
            finally:
                prompt.response(Gtk.ResponseType.CANCEL)
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(150, inspect_prompt)
        result = message_box(parent, 'Notepad',
                             'The text in the Untitled file has changed.\n\nDo you want to save the changes?',
                             Gtk.MessageType.QUESTION, SAVE_CHANGES, Gtk.ResponseType.YES)
        assert result == Gtk.ResponseType.CANCEL
        count = compare_region(captures[0], read(args.references/'native-notepad-close-dialog.png'),
                               (270,245,266,126),(0,0))
        assert count == 0, f'Close prompt differs by {count} pixels'
    parent.destroy()
    print('Open and Save As frame regions, close prompt, navigation, filter and overwrite checks pass.')


if __name__ == '__main__':
    main()
