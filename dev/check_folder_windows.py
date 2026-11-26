#!/usr/bin/env python3
"""Exercise independent Explorer windows, desktop transfers and native frame pixels."""

import argparse
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tools'), str(ROOT/'dev')]
from check_menu_seams import flush_draws
from check_reference_ui import compare_region
from pixels import read


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT/'private/shell-assets')
    parser.add_argument('--references', type=Path, default=ROOT/'private/screenshots/start-development-20261110')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    import gi
    gi.require_foreign('cairo')
    import cairo
    from win95lx.shell.app import Shell, Gtk, Gdk
    from win95lx.explorer.drive_browser import DriveBrowser
    from win95lx.shell.desktop_icons import ShortcutIcons

    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
    with TemporaryDirectory() as folder, patch('pathlib.Path.home', return_value=Path(folder)):
        root = Path(folder)
        (root/'Desktop').mkdir()
        (root/'Source'/'Nested').mkdir(parents=True)
        (root/'Target').mkdir()
        (root/'Desktop'/'desktop.txt').write_text('From desktop')
        (root/'Source'/'report.txt').write_text('Report')
        for index in range(40):
            (root/'Source'/f'z{index:02d}.txt').write_text(str(index))
        shell = Shell(args.assets)
        # This suite deliberately covers the explicit separate-window mode.
        from win95lx.explorer.browsing import BrowsingPreferences
        shell.browsing_preferences=BrowsingPreferences(single_window=False)
        shell._drive = DriveBrowser(root)
        shell.desktop_folder = root/'Desktop'
        shell.refresh_desktop_files()
        shell.show_all()
        flush_draws(Gtk)

        def render(name):
            w, h = shell.area.get_allocated_width(), shell.area.get_allocated_height()
            image = cairo.ImageSurface(cairo.FORMAT_RGB24,w,h)
            shell.draw(shell.area,cairo.Context(image))
            image.flush()
            if args.output:
                image.write_to_png(str(args.output/f'{name}.png'))
            return w,h,[(value>>16&255,value>>8&255,value&255) for value, in struct.iter_unpack('=I',image.get_data())]

        def press(x,y,state=0,double=False):
            shell.press(shell.area,SimpleNamespace(x=x,y=y,button=1,time=Gdk.CURRENT_TIME,state=state,
                        type=Gdk.EventType._2BUTTON_PRESS if double else Gdk.EventType.BUTTON_PRESS))

        def drag(start,end,state=0):
            press(*start,state)
            shell.motion(shell.area,SimpleNamespace(x=end[0],y=end[1],state=state))
            render('drag-preview')
            shell.release(shell.area,SimpleNamespace(x=end[0],y=end[1],button=1,state=state))
            render('after-transfer')

        def item(window,name):
            x,y,_,_,_ = next(hit for hit in shell.hits if hit[4][0]=='item'
                            and hit[4][1] is window and hit[4][3]==name)
            return x+25,y+10

        def activate(window):
            shell.action(('task',window)) if window is not shell.state.active else None
            render('activated')

        # A dragged desktop folder is redrawn under the pointer before release.
        # It must never become its own filesystem drop target.
        (root/'Desktop/Loose Folder').mkdir()
        shell.refresh_desktop_files()
        render('desktop-folder-before-rearrange')
        dx,dy,_,_,_ = next(hit for hit in shell.hits if hit[4]==('desktop','file:Loose Folder'))
        with patch.object(shell,'transfer_files') as transfer:
            drag((dx+25,dy+10),(shell.width-150,80))
            transfer.assert_not_called()
        assert (root/'Desktop/Loose Folder').is_dir()
        assert shell.desktop_icons.positions['file:Loose Folder'] != (dx,dy)
        (root/'Desktop/Loose Folder').rmdir()
        shell.refresh_desktop_files()

        shell.open('drive','Source')
        first = shell.state.active
        first.x, first.y, first.width, first.height = 4,25,350,310
        render('source')
        press(*item(first,'report.txt'))
        shell.release(shell.area,SimpleNamespace(x=item(first,'report.txt')[0],y=item(first,'report.txt')[1],button=1,state=0))
        shell.action(('drive-scroll',first,2))
        shell.open('drive','Target')
        second = shell.state.active
        second.x,second.y,second.width,second.height = 410,25,350,310
        render('independent')
        assert first.browser.selection == {'report.txt'} and first.browser.scroll == 2
        assert second.browser.directory == Path('Target') and second.browser.scroll == 0
        shell.open('drive','Source')
        assert shell.state.active is first and first.browser.scroll == 2 and len(shell.state.windows)==2
        first.browser.scroll = 0
        initial = render('two-folders')
        reference = read(args.references/'native-explorer-menu-clean.png')
        for win in (first,second):
            # The native menu's left artwork and adjacent rows remain identical in each window.
            assert compare_region(initial,reference,(4,22,242,32),(win.x+4,win.y+22)) == 0
        reference_folders = read(args.references/'native-independent-folders-compact.png')
        # First icon is at (27,55) relative to the compact original folder window.
        assert compare_region(initial,reference_folders,(49,77,32,32),
                              (first.x+27,first.y+55)) == 0
        # A small rearrangement ending over the same folder icon only saves its position.
        with patch.object(shell,'transfer_files') as transfer:
            x,y = item(first,'Nested')
            drag((x,y),(x+8,y+8))
            transfer.assert_not_called()
        assert (root/'Source/Nested').is_dir()
        render('folder-rearranged')
        drag(item(first,'report.txt'),(second.x+160,second.y+170))
        assert not (root/'Source/report.txt').exists()
        assert (root/'Target/report.txt').read_text() == 'Report'
        assert ('report.txt',False) not in first.browser.entries
        assert ('report.txt',False) in second.browser.entries
        assert first.browser.directory == Path('Source') and second.browser.directory == Path('Target')
        # Ctrl-drag an already selected file while retaining the source.
        second.browser.selection = {'report.txt'}
        render('before-copy')
        drag(item(second,'report.txt'),(first.x+160,first.y+170),Gdk.ModifierType.CONTROL_MASK)
        assert (root/'Source/report.txt').read_text() == (root/'Target/report.txt').read_text()
        # Desktop -> window uses the source path recorded by the desktop item.
        render('desktop-source')
        dx,dy,_,_,_ = next(hit for hit in shell.hits if hit[4]==('desktop','file:desktop.txt'))
        # Move windows clear of the desktop icon.
        first.y = second.y = 160
        render('desktop-visible')
        dx,dy,_,_,_ = next(hit for hit in shell.hits if hit[4]==('desktop','file:desktop.txt'))
        drag((dx+25,dy+10),(second.x+160,second.y+170))
        assert (root/'Target/desktop.txt').read_text() == 'From desktop'
        assert not (root/'Desktop/desktop.txt').exists()
        # Window -> desktop.
        activate(second)
        second.browser.scroll = 0
        render('folder-to-desktop')
        drag(item(second,'desktop.txt'),(shell.width-55,75))
        assert (root/'Desktop/desktop.txt').read_text() == 'From desktop'
        assert not (root/'Target/desktop.txt').exists()
        # A failed collision preserves source and target and leaves unrelated view state intact.
        from win95lx.apps.dialogs import message_box
        (root/'Target/collision.txt').write_text('target')
        (root/'Source/collision.txt').write_text('source')
        first.browser.scroll = 2
        second.browser.selection = {'report.txt'}
        with patch('win95lx.apps.dialogs.message_box') as error:
            shell.transfer_files((Path('Source/collision.txt'),),Path('Target'))
            assert error.called
        assert (root/'Target/collision.txt').read_text() == 'target'
        assert (root/'Source/collision.txt').read_text() == 'source'
        assert first.browser.scroll == 2 and second.browser.selection == {'report.txt'}
        activate(first)
        first.browser.scroll = 0
        render('reposition-before')
        origin = item(first,'report.txt')
        drag(origin,(first.x+220,first.y+110))
        key = 'drive:'+str(root/'Source')
        position = shell.shortcut_icons.position(key,'report.txt',None)
        assert position is not None
        assert ShortcutIcons(shell.shortcut_icons.path).position(key,'report.txt',None)==position
        assert shell.shortcut_icons.position('drive:'+str(root/'Target'),'report.txt',None) is None
        # Escape cancels the drag before release and preserves the file.
        render('cancel-before')
        start = item(first,'report.txt')
        end = (second.x+160,second.y+170)
        press(*start)
        shell.motion(shell.area,SimpleNamespace(x=end[0],y=end[1]))
        shell.key(shell,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0))
        shell.release(shell.area,SimpleNamespace(x=end[0],y=end[1],button=1,state=0))
        assert (root/'Source/report.txt').read_text() == 'Report'
        # A folder opens as a new window while the parent selection remains intact.
        render('nested-before')
        press(*item(first,'Nested'),double=True)
        nested = shell.state.active
        assert nested is not first and nested.browser.directory == Path('Source/Nested')
        assert first.browser.directory == Path('Source')
        assert len(shell.state.windows)==3
        # Moving an open parent directory updates the open child view's path.
        shell.transfer_files((Path('Source/Nested'),),Path('Target'))
        assert nested.browser.directory == Path('Target/Nested')
        assert nested.title == 'C:\\Target\\Nested'
        assert (root/'Target/Nested').is_dir()
        # Reopening the same canonical folder reuses its window with saved selection.
        shell.open('drive','Target')
        assert shell.state.active is second and second.browser.selection == {'report.txt'}
        shell.action(('minimize',second))
        assert second.minimized and first.browser.directory == Path('Source')
        shell.open('drive','Target')
        assert shell.state.active is second and not second.minimized
        # A fully covered folder cannot receive a drop through the covering window.
        shell.open('computer')
        cover = shell.state.active
        cover.x,cover.y,cover.width,cover.height = second.x,second.y,second.width,second.height
        render('occluded-target')
        assert shell.file_drop_destination(second.x+100,second.y+100) is None
        shell.action(('close',cover))
        # Font scaling maps real pointer coordinates back to each folder's hit targets.
        shell.pending_display = shell.display_preferences.__class__(dpi=120)
        assert shell.commit_display_preferences()
        first.x,first.y,first.width,first.height = 4,150,280,270
        second.x,second.y,second.width,second.height = 330,150,280,270
        activate(first)
        first.browser.scroll = 0
        (root/'Source/scaled.txt').write_text('scaled transfer')
        shell.refresh_file_views()
        # Keep this test object visible even in a small viewport.
        first.browser.entries = [entry for entry in first.browser.entries if entry[0]=='scaled.txt']
        render('scaled-folders')
        scale = shell.pointer_scale
        assert scale == 1.25
        start = item(first,'scaled.txt')
        end = (second.x+150,second.y+180)
        drag(tuple(value*scale for value in start),tuple(value*scale for value in end))
        assert (root/'Target/scaled.txt').read_text() == 'scaled transfer'
        assert not (root/'Source/scaled.txt').exists()
        shell.pending_display = shell.display_preferences.__class__()
        shell.commit_display_preferences()
        shell.action(('close',nested))
        assert first in shell.state.windows and second in shell.state.windows
        render('final')
        shell.disconnect_by_func(Gtk.main_quit)
        shell.destroy()
    print('Independent folder paths, selection, scroll, positions, native chrome, and bidirectional transfers pass.')


if __name__ == '__main__':
    main()
