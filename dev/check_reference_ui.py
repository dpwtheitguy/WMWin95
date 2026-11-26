#!/usr/bin/env python3
"""Compare Win95LX control geometry and rendered regions against the Win95 VM."""

import argparse
from functools import lru_cache
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch

from check_menu_seams import find_menu, flush_draws

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tools')]
from pixels import read


def compare_region(actual, reference, expected_rect, actual_origin=None):
    aw, ah, a = actual
    rw, rh, r = reference
    x, y, width, height = expected_rect
    ax, ay = actual_origin if actual_origin else (x, y)
    assert 0 <= ax <= aw-width and 0 <= ay <= ah-height
    assert 0 <= x <= rw-width and 0 <= y <= rh-height
    return sum(
        a[(ay+dy)*aw+ax+dx][:3] != r[(y+dy)*rw+x+dx][:3]
        for dy in range(height) for dx in range(width)
    )


def check_notepad_popup(shell, gtk, gdk, reference, output=None):
    from gi.repository import GLib
    from win95lx.shell.menu_layout import NOTEPAD_HELP_ROWS, NOTEPAD_HELP_WIDTH
    shell.launch_accessory('notepad')
    flush_draws(gtk)
    window = shell.accessory_windows['notepad']
    menu_items = find_menu(window, gtk).get_children()
    item = menu_items[0]
    popup = item.get_submenu()
    popup.popup_at_widget(item, gdk.Gravity.SOUTH_WEST, gdk.Gravity.NORTH_WEST, None)
    popup.select_first(True)
    flush_draws(gtk)
    size = popup.get_allocation()
    if output:
        capture = gdk.pixbuf_get_from_window(popup.get_window(), 0, 0, size.width, size.height)
        capture.savev(str(output/'notepad-file-popup.png'), 'png', [], [])
    labels = [child.get_child() for child in popup.get_children() if child.get_child() is not None]
    result = (size.width, size.height, [label.translate_coordinates(popup, 0, 0)[0] for label in labels],
              [label.get_accel_width() for label in labels])
    popup.popdown()
    help_item = menu_items[-1]
    help_popup = help_item.get_submenu()
    rows = help_popup.get_children()
    assert tuple(None if isinstance(row, gtk.SeparatorMenuItem) else row.get_label()
                 for row in rows) == NOTEPAD_HELP_ROWS
    help_popup.popup_at_widget(help_item, gdk.Gravity.SOUTH_WEST, gdk.Gravity.NORTH_WEST, None)
    help_popup.select_first(True)
    flush_draws(gtk)
    allocation = help_popup.get_allocation()
    assert allocation.width == NOTEPAD_HELP_WIDTH and 45 <= allocation.height <= 50, allocation
    assert rows[0].get_child().get_accel_width() == 0
    if output:
        gdk.pixbuf_get_from_window(help_popup.get_window(),0,0,allocation.width,allocation.height).savev(
            str(output/'notepad-help-menu.png'), 'png', [], [])
    checked = []
    def inspect_about():
        try:
            dialog, = [widget for widget in gtk.Window.list_toplevels()
                       if isinstance(widget, gtk.Dialog) and widget.get_visible()]
            try:
                checked.append(tuple(dialog.get_size()))
                capture = gdk.pixbuf_get_from_window(dialog.get_window(),0,0,*dialog.get_size())
                data, stride, channels = capture.get_pixels(), capture.get_rowstride(), capture.get_n_channels()
                expected_width, _, expected = reference
                for x,y,w,h in ((0,0,348,22),(257,246,76,24),(0,281,348,2)):
                    for row in range(y, y+h):
                        actual = [tuple(data[row*stride+col*channels:row*stride+col*channels+3])
                                  for col in range(x,x+w)]
                        start = (163+row)*expected_width+126+x
                        assert actual == [pixel[:3] for pixel in expected[start:start+w]], (x,row,w)
                checked.append('frame')
                if output:
                    capture.savev(str(output/'notepad-about.png'), 'png', [], [])
            finally:
                dialog.response(gtk.ResponseType.OK)
        except ValueError:
            return GLib.SOURCE_CONTINUE
        return GLib.SOURCE_REMOVE
    help_popup.popdown()
    GLib.timeout_add(120, inspect_about)
    rows[-1].activate()
    assert checked == [(348,283), 'frame'], checked
    window.destroy()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path, default=ROOT/'private'/'shell-assets')
    parser.add_argument('--references', type=Path,
                        default=ROOT/'private'/'screenshots'/'start-development-20261110')
    parser.add_argument('--output', type=Path, help='Write fresh implementation screenshots here')
    parser.add_argument('--size', choices=('800x600', '1280x720'), default='800x600')
    args = parser.parse_args()

    import gi
    gi.require_foreign('cairo')
    import cairo
    from win95lx.shell.app import Gdk, Gtk, Shell
    from win95lx.shell import taskbar
    from win95lx.control_panel.display_preferences import color_surface
    from win95lx.shell.shortcut_folders import ShortcutFolders
    from win95lx.explorer.drive_browser import DriveBrowser
    from win95lx.shell.shutdown_dialog import is_development_guest

    if args.output:
        args.output.mkdir(parents=True)

    @lru_cache(maxsize=None)
    def native(name):
        return read(args.references/f'{name}.png')

    def render(shell, name):
        width, height = shell.area.get_allocated_width(), shell.area.get_allocated_height()
        surface = cairo.ImageSurface(cairo.FORMAT_RGB24, width, height)
        shell.draw(shell.area, cairo.Context(surface))
        if args.output:
            surface.write_to_png(str(args.output/f'{name}.png'))
        surface.flush()
        # Cairo RGB24 stores one native-endian 0x00RRGGBB value per pixel.
        pixels = [(value>>16 & 255, value>>8 & 255, value & 255)
                  for (value,) in struct.iter_unpack('=I', surface.get_data())]
        return width, height, pixels

    swatch = cairo.ImageSurface(cairo.FORMAT_RGB24, 1, 1)
    context = cairo.Context(swatch)
    context.set_source_rgb(0.35, 0.64, 0.84)
    context.paint()
    swatch.flush()
    limited = color_surface(swatch, 0)
    assert bytes(limited.get_data())[:3] != bytes(swatch.get_data())[:3]
    assert color_surface(swatch, 2).get_format() == cairo.FORMAT_RGB16_565
    assert color_surface(swatch, 3) is swatch

    with TemporaryDirectory() as directory, patch('pathlib.Path.home', return_value=Path(directory)):
        shell = Shell(args.assets)
        shell.show_all()
        flush_draws(Gtk)
        assert f'{shell.width}x{shell.height}' == args.size, f'Run at {args.size}'
        shell.show_start()
        shell.state.menu_index = 0
        menu_capture = render(shell, 'start-menu')
        original_menu = read(args.references.parent/'interactive-20261110'/'original-start-programs-800.png')
        assert compare_region(menu_capture, original_menu, (2,237,148,339),
                              shell.menu_origin()) == 0
        shell.show_start()
        shell.open('display')
        win = shell.state.active
        background = render(shell, 'background')
        difference = compare_region(background, native('reference-background-clean-v2'),
                                    (0,0,404,448), (win.x,win.y))
        assert difference == 0, f'Background tab differs by {difference} pixels'
        # Move the thumb and verify that the two arrow buttons stay fixed.
        shell.press(shell.area, SimpleNamespace(
            x=win.x+271, y=win.y+309, button=1, time=Gdk.CURRENT_TIME,
            type=Gdk.EventType.BUTTON_PRESS,
        ))
        shell.motion(shell.area, SimpleNamespace(x=win.x+271, y=win.y+348))
        shell.release(shell.area, SimpleNamespace(button=1))
        assert shell.wallpaper_scroll == shell.wallpaper_max_scroll
        shell.pending_wallpaper = 'Clouds'
        scrolled = render(shell, 'background-scrolled')
        for y in (287,363):
            assert compare_region(scrolled, native('reference-background-clean-v2'),
                                  (265,y,16,16), (win.x+265,win.y+y)) == 0
        assert compare_region(scrolled, native('reference-background-clean-v2'),
                              (265,303,16,21), (win.x+265,win.y+342)) == 0
        print('Background frame, scrollbar arrows, and moved thumb match native reference pixels.')

        def click(x, y):
            shell.press(shell.area, SimpleNamespace(
                x=(win.x+x)*shell.pointer_scale, y=(win.y+y)*shell.pointer_scale, button=1, time=Gdk.CURRENT_TIME,
                type=Gdk.EventType.BUTTON_PRESS,
            ))

        def key(name, modifiers=0):
            shell.key(shell, SimpleNamespace(keyval=Gdk.keyval_from_name(name), state=modifiers))

        shell.wallpaper_scroll = 0
        shell.pending_wallpaper = '(None)'
        render(shell, 'background-disabled-combo')
        click(360, 370)
        assert not shell.wallpaper_combo.expanded
        click(110, 312)
        render(shell, 'background-selected')
        click(360, 370)
        assert shell.wallpaper_combo.expanded and shell.pending_wallpaper_mode == 'center'
        render(shell, 'background-combo-center-open')
        click(320, 403)
        assert not shell.wallpaper_combo.expanded and shell.pending_wallpaper_mode == 'tile'
        tiled = render(shell, 'background-combo-tile-focused')
        assert compare_region(tiled, native('native-wallpaper-black-thatch-tile'),
                              (331,353,16,92), (win.x+265,win.y+287)) == 0
        alt = Gdk.ModifierType.MOD1_MASK
        key('Down', alt)
        assert shell.wallpaper_combo.expanded
        tile_open = render(shell, 'background-combo-tile-open')
        key('Up')
        center_open = render(shell, 'background-combo-center-keyboard')
        assert shell.pending_wallpaper_mode == 'center'
        for actual, name in ((tile_open, 'tile-open'), (center_open, 'center-open')):
            difference = compare_region(actual, native(f'native-wallpaper-combo-{name}'),
                                        (360,427,75,49), (win.x+294,win.y+361))
            assert difference == 0, f'Background combo {name} differs by {difference} pixels'
        assert compare_region(tile_open, center_open, (win.x+125,win.y+76,153,113)) > 0
        key('Escape')
        assert not shell.wallpaper_combo.expanded and shell.pending_wallpaper_mode == 'center'
        focused = render(shell, 'background-combo-center-focused')
        assert compare_region(focused, native('native-wallpaper-combo-center-focused'),
                              (360,427,75,21), (win.x+294,win.y+361)) == 0
        key('F4')
        assert shell.wallpaper_combo.expanded
        key('Down')
        key('Return')
        assert not shell.wallpaper_combo.expanded and shell.pending_wallpaper_mode == 'tile'
        render(shell, 'background-combo-ready-to-apply')
        click(354, 426)
        assert (shell.wallpaper.name, shell.wallpaper.mode) == ('Black Thatch', 'tile')
        render(shell, 'background-combo-applied')
        click(360, 370)
        click(390, 399)
        assert not shell.wallpaper_combo.expanded and shell.pending_wallpaper_mode == 'tile'
        render(shell, 'background-combo-dismissed')
        click(360, 370)
        click(320, 389)
        render(shell, 'background-combo-unapplied')
        click(270, 426)
        assert not shell.state.windows and (shell.wallpaper.name, shell.wallpaper.mode) == ('Black Thatch', 'tile')
        print('Background scrollbar matches its full native selected-state region. Display combo passes pointer and keyboard selection, preview, and Apply.')

        shell.open('display')
        win = shell.state.active
        render(shell, 'display-background-before-settings')
        click(295, 40)
        settings = render(shell, 'display-settings')
        assert shell.display_tab == 'settings'
        if args.size == '800x600':
            for x, y, width, height in ((0,0,404,415), (0,415,320,33), (395,415,9,33)):
                assert compare_region(settings, native('native-settings-clean'),
                                      (66+x,66+y,width,height), (win.x+x,win.y+y)) == 0
            assert compare_region(settings, native('reference-display-settings-native'),
                                  (320,415,75,23), (win.x+320,win.y+415)) == 0
        original = shell.applied_resolution
        key('Tab')
        key('Tab')
        key('Home')
        assert shell.pending_resolution == (800,600)
        key('End')
        assert shell.pending_resolution == shell.resolution_modes[-1]
        shell.pending_resolution = (800,600)
        render(shell, 'display-settings-slider-start')
        click(280, 263)
        shell.motion(shell.area, SimpleNamespace(x=win.x+322, y=win.y+263))
        shell.release(shell.area, SimpleNamespace(button=1))
        assert shell.pending_resolution == shell.resolution_modes[-1]
        changed = render(shell, 'display-settings-changed')
        assert compare_region(changed, native('native-settings-clean'),
                              (386,481,75,23), (win.x+320,win.y+415)) == 0
        target = shell.pending_resolution
        with patch('win95lx.shell.app.set_resolution') as switch, patch('win95lx.shell.app.remember_resolution') as save:
            click(355, 426)
            assert shell.state.dialog == 'resolution-confirm'
            render(shell, 'display-settings-confirm')
            key('Escape')
            assert [call.args for call in switch.call_args_list] == [target, original]
            assert shell.applied_resolution == shell.pending_resolution == original
            save.assert_not_called()
            shell.pending_resolution = target
            key('Return')
            key('y')
            save.assert_called_once_with(*target)
            assert shell.applied_resolution == target and not shell.state.windows
        shell.open('display')
        win = shell.state.active
        shell.action(('display-tab','settings'))
        render(shell, 'display-options')
        click(180,260)
        palette = render(shell, 'display-palette-open')
        assert compare_region(palette, native('native-settings-palette-open'),
                              (99,338,155,54), (win.x+33,win.y+272)) == 0
        click(65,277)
        assert shell.pending_display.palette == 0 and shell.display_preferences.palette == 1
        click(180,326)
        font = render(shell, 'display-font-open')
        assert compare_region(font, native('native-settings-font-open'),
                              (99,406,155,41), (win.x+33,win.y+340)) == 0
        key('Down')
        key('Return')
        assert shell.pending_display.dpi == 120
        render(shell, 'display-large-font-pending')
        click(30,386)
        render(shell, 'display-options-pending')
        click(355,426)
        assert shell.display_preferences.palette == 0
        assert shell.display_preferences.dpi == 120 and shell.display_preferences.tray
        assert shell.display_preferences == type(shell.display_preferences).load(shell.display_preferences_path)
        render(shell, 'display-options-applied')
        assert shell.pointer_scale == 1.25
        assert any(action == ('display-tray-open',) for *_, action in shell.hits)
        click(269,425)
        assert not shell.state.windows
        shell.open('display')
        win = shell.state.active
        shell.action(('display-tab','settings'))
        assert shell.pending_display == shell.display_preferences
        render(shell, 'display-options-reopened')
        click(30,386)
        click(269,425)
        assert shell.display_preferences.tray
        shell.pending_display = type(shell.display_preferences)()
        shell.commit_display_preferences()
        render(shell, 'display-options-restored')
        print('Display Settings native frame, slider input, Apply, Keep and Revert pass.')

        desktop_root = Path(directory)/'loose-desktop'
        (desktop_root/'Desktop'/'Projects'/'Nested').mkdir(parents=True)
        (desktop_root/'Desktop'/'readme.txt').write_text('Desktop document')
        original_drive, original_desktop = shell.drive, shell.desktop_folder
        shell.drive = DriveBrowser(desktop_root)
        shell.desktop_folder = desktop_root/'Desktop'
        shell.refresh_desktop_files()
        render(shell, 'desktop-file-icons')
        assert any(action == ('desktop','file:readme.txt') for *_, action in shell.hits)
        shell.open_desktop_item('file:Projects')
        project = shell.state.active
        assert shell.drive.directory == Path('Desktop/Projects')
        shell.open_drive_entry(project,'Nested',True)
        assert shell.drive.directory == Path('Desktop/Projects/Nested')
        key('BackSpace')
        assert shell.drive.directory == Path('Desktop/Projects')
        shell.state.windows.clear()
        shell.drive, shell.desktop_folder = original_drive, original_desktop
        shell.refresh_desktop_files()
        shell.state.windows.clear()
        shell.wallpaper.apply('Houndstooth','center')
        desktop = render(shell, 'wallpaper-centered')
        origin = ((shell.width-27)//2, (shell.height-25)//2)
        difference = compare_region(desktop, native('reference-wallpaper-centered'), (386,287,27,25), origin)
        assert difference == 0, f'Centered wallpaper differs by {difference} pixels'
        print('Centered wallpaper matches native placement and colors.')

        shell.open('computer')
        win = shell.state.active
        # This reference intentionally has all optional Explorer bands hidden.
        win.toolbar = win.address_bar = win.web_view = False
        explorer = render(shell, 'explorer-menu')
        difference = compare_region(explorer, native('native-explorer-menu-clean'),
                                    (4,22,504,32), (win.x+4,win.y+22))
        assert difference == 0, f'Compact Explorer menu and content transition differ by {difference} pixels'
        for y in (21,54):
            assert compare_region(explorer, native('native-explorer-menu-clean'),
                                  (300,y,140,1), (win.x+300,win.y+y)) == 0
        click(10, 10)
        context = shell.start_context
        assert [row[0] if row else None for row in context.rows] == [
            'Restore', 'Move', 'Size', 'Minimize', 'Maximize', None, 'Close',
        ]
        assert context.rows[0][1] is None
        render(shell, 'explorer-system-menu')
        key('Down')
        key('Return')
        original_x = win.x
        key('Right')
        assert win.x == original_x+8
        key('Escape')
        assert win.x == original_x and shell.window_operation is None
        key('space', alt)
        assert shell.start_context is not None
        key('Escape')
        assert shell.start_context is None
        shell.state.windows.clear()

        result = check_notepad_popup(shell, Gtk, Gdk, native('native-notepad-about'), args.output)
        assert result == (113, 143, [24]*7, [0]*7), f'Notepad File popup metrics: {result}'
        shell.launch_accessory('calc')
        calculator = shell.accessory_windows['calc']
        assert calculator.win95_key_controller.emit('key-pressed', Gdk.KEY_space, 0, alt)
        system_menu, = Gtk.Menu.get_for_attach_widget(calculator)
        rows = [item for item in system_menu.get_children() if not isinstance(item, Gtk.SeparatorMenuItem)]
        assert [item.get_sensitive() for item in rows] == [False, True, False, True, False, True]
        system_menu.popdown()
        calculator.destroy()
        print('Explorer seam and Notepad File popup geometry pass.')

        def item_hit(window, label):
            return next((x, y) for x, y, _, _, action in shell.hits
                        if action[0] == 'item' and action[1] is window and action[3] == label)

        def drag(start, end):
            x, y = start
            shell.press(shell.area, SimpleNamespace(x=x,y=y,button=1,time=Gdk.CURRENT_TIME,
                        type=Gdk.EventType.BUTTON_PRESS))
            x, y = end
            shell.motion(shell.area, SimpleNamespace(x=x,y=y))
            shell.release(shell.area, SimpleNamespace(x=x,y=y,button=1))

        shell.action(('start-folder', 0))
        programs = shell.state.active
        programs.x, programs.y = 10, 10
        shell.action(('start-folder', 'accessories'))
        accessories = shell.state.active
        accessories.x, accessories.y = 250, 215
        render(shell, 'start-folders-before-drop')
        x, y = item_hit(accessories, 'Calculator')
        dx, dy = item_hit(accessories, 'Games')
        drag((x+25,y+10), (dx+25,dy+10))
        assert 'Calculator' not in [row[0] for row in shell.submenu_entries('accessories')]
        assert 'Calculator' in [row[0] for row in shell.submenu_entries('games')]
        shell.action(('start-folder', 'games'))
        games = shell.state.active
        games.x, games.y = 250, 215
        render(shell, 'start-folders-after-game-drop')
        x, y = item_hit(games, 'Calculator')
        drag((x+25,y+10), (75,185))
        reloaded = ShortcutFolders(shell.shortcut_folders.path)
        assert 'Calculator' in [row[0] for row in reloaded.entries(0)]
        assert 'Calculator' not in [row[0] for row in reloaded.entries('games')]
        render(shell, 'start-folders-after-programs-drop')
        shell.state.windows.clear()
        print('Shortcut drops into a folder icon and a separate Programs window both persist.')

        if is_development_guest():
            assert shell.drive.view.root == Path('/')
            shell.open('drive')
            assert ('home', True) in shell.drive.entries and ('usr', True) in shell.drive.entries
            render(shell, 'guest-root-drive')
            shell.state.windows.clear()
        fixture = Path(directory)/'drive-fixture'
        (fixture/'home').mkdir(parents=True)
        (fixture/'home'/'notes.txt').write_text('Test document')
        for index in range(20):
            (fixture/f'file-{index:02d}').touch()
        shell.drive = DriveBrowser(fixture)
        shell.open('drive')
        drive = shell.state.active
        render(shell, 'drive-root-grid')
        assert shell.drive.title == 'C:\\'
        x, y = item_hit(drive, 'home')
        shell.press(shell.area, SimpleNamespace(x=x+25,y=y+10,button=1,time=Gdk.CURRENT_TIME,
                    type=Gdk.EventType._2BUTTON_PRESS))
        assert shell.drive.title == 'C:\\home'
        drive = shell.state.active
        render(shell, 'drive-home-grid')
        x, y = item_hit(drive, 'notes.txt')
        shell.press(shell.area, SimpleNamespace(x=x+25,y=y+10,button=1,time=Gdk.CURRENT_TIME,
                    type=Gdk.EventType._2BUTTON_PRESS))
        editor = shell.accessory_windows['notepad']
        assert editor.text() == 'Test document'
        editor.destroy()
        shell.key(shell, SimpleNamespace(keyval=Gdk.KEY_BackSpace,state=0,string=''))
        assert shell.drive.title == 'C:\\'
        (fixture/'home'/'move.txt').write_text('Move me')
        shell.navigate_drive(drive, 'home')
        win = drive
        ctrl = Gdk.ModifierType.CONTROL_MASK
        render(shell, 'drive-file-source')
        x, y = item_hit(drive, 'notes.txt')
        click(x-drive.x+25, y-drive.y+10)
        shell.release(shell.area, SimpleNamespace(x=x+25,y=y+10,button=1,state=0))
        render(shell, 'drive-file-selected')
        click(66,35)
        render(shell, 'drive-edit-menu')
        assert any(action == ('drive-edit',drive,'copy') for *_, action in shell.hits)
        key('Escape')
        key('e', alt)
        render(shell, 'drive-edit-keyboard')
        key('Down')
        key('Down')
        key('Return')
        assert shell.file_clipboard.sources == (Path('home/notes.txt'),)
        key('BackSpace')
        key('v', ctrl)
        assert (fixture/'notes.txt').read_text() == 'Test document'
        shell.navigate_drive(drive,'home')
        render(shell, 'drive-file-to-cut')
        x, y = item_hit(drive, 'move.txt')
        click(x-drive.x+25, y-drive.y+10)
        shell.release(shell.area, SimpleNamespace(x=x+25,y=y+10,button=1,state=0))
        key('x', ctrl)
        key('BackSpace')
        key('v', ctrl)
        assert (fixture/'move.txt').read_text() == 'Move me' and not (fixture/'home'/'move.txt').exists()
        render(shell, 'drive-file-after-paste')
        # In a small viewport the newly pasted file can be beyond the visible page.
        shell.drive.entries = [item for item in shell.drive.entries if item[0] in ('home','move.txt')]
        render(shell, 'drive-drop-source')
        x, y = item_hit(drive,'move.txt')
        dest_x, dest_y = item_hit(drive,'home')
        drag((x+25,y+10),(dest_x+25,dest_y+10))
        assert not (fixture/'move.txt').exists() and (fixture/'home'/'move.txt').read_text() == 'Move me'
        print('Explorer Cut, Copy, Paste, and folder drag moved real fixture files.')
        shell.action(('drive-scroll', drive, 20))
        assert ('file-19',False) in shell.drive.page(*shell.drive_pane_size(drive))
        key('w', ctrl)
        assert drive not in shell.state.windows
        shell.state.windows.clear()
        print('C: opens folders and text files, returns to the parent, and scrolls through its full listing.')

        for kind in ('notepad','calc','wordpad'):
            shell.launch_accessory(kind)
            flush_draws(Gtk)
            render(shell, f'taskbar-{kind}')
        tasks = render(shell, 'taskbar-multiple-apps')
        reference = native('reference-taskbar-multiple-apps')
        for index in range(3):
            offset = index*(taskbar.MAX_BUTTON_WIDTH+taskbar.BUTTON_GAP)
            difference = compare_region(tasks, reference, (326+offset,576,10,22),
                                        (taskbar.START_X+150+offset,shell.height-24))
            assert difference == 0, f'Task button {index+1} frame differs by {difference} pixels'
        order = shell.task_order.copy()
        assert shell.active_task is order[-1]
        shell.action(('accessory-task', order[0]))
        flush_draws(Gtk)
        render(shell, 'taskbar-switched')
        assert shell.task_order == order and shell.active_task is order[0]
        print('Three task button frames match the native sample, including the active button.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
