#!/usr/bin/env python3
"""Exercise Sprint 1 controls and write per-scenario acceptance evidence."""

import argparse
from functools import wraps
import json
import hashlib
import statistics
from pathlib import Path
import struct
import sys
from tempfile import TemporaryDirectory
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
from check_menu_seams import find_menu,flush_draws
from check_reference_ui import compare_region
from pixels import read


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,default=ROOT/'private/shell-assets')
    parser.add_argument('--references',type=Path,default=ROOT/'private/screenshots/start-development-20261110')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    import gi
    gi.require_foreign('cairo')
    import cairo
    from win95lx.shell.app import Shell,Gdk,Gtk,RECYCLE_TARGET
    from win95lx.explorer.drive_browser import DriveBrowser
    from win95lx.explorer.trash import TrashStore
    from win95lx.recent_documents import RecentDocuments
    from win95lx.control_panel.wallpaper import Wallpaper
    from win95lx.control_panel.display_preferences import DisplayPreferences,color_surface
    from win95lx.shell.drop_geometry import folder_drop_rect,contains

    results=[]
    differences=[]
    timings=[]
    with TemporaryDirectory() as folder,patch('pathlib.Path.home',return_value=Path(folder)):
        root=Path(folder)
        (root/'Desktop').mkdir()
        (root/'Documents').mkdir()
        shell=Shell(args.assets)
        shell._drive=DriveBrowser(root)
        shell.desktop_folder=root/'Desktop'
        shell.trash=TrashStore(root/'Trash')
        shell.show_all()
        flush_draws(Gtk)

        def render(name):
            width,height=shell.area.get_allocated_width(),shell.area.get_allocated_height()
            image=cairo.ImageSurface(cairo.FORMAT_RGB24,width,height)
            start=perf_counter()
            shell.draw(shell.area,cairo.Context(image))
            timings.append({'name':name,'milliseconds':round((perf_counter()-start)*1000,3)})
            path=args.output/(name+'.png')
            image.write_to_png(str(path))
            return read(path)

        def capture(widget,name):
            flush_draws(Gtk)
            width,height=widget.get_allocated_width(),widget.get_allocated_height()
            image=Gdk.pixbuf_get_from_window(widget.get_window(),0,0,width,height)
            path=args.output/(name+'.png')
            image.savev(str(path),'png',[],[])
            return read(path)

        def exact(name,actual,reference,rect,origin):
            count=compare_region(actual,read(args.references/(reference+'.png')),rect,origin)
            differences.append({'name':name,'reference':reference,'reference_rect':rect,
                                'actual_origin':origin,'differing_pixels':count})
            assert count==0,f'{name}: {count} differing pixels'

        def scenario(name):
            def decorate(function):
                @wraps(function)
                def invoke():
                    start=perf_counter()
                    try:
                        function()
                        result={'name':name,'passed':True}
                    except Exception as error:
                        result={'name':name,'passed':False,'error':f'{type(error).__name__}: {error}'}
                    result['elapsed_seconds']=round(perf_counter()-start,4)
                    results.append(result)
                    print(json.dumps(result),flush=True)
                    shell.state.windows.clear()
                    shell.state.dialog=None
                    shell.popup=None
                    for window in tuple(shell.accessory_windows.values()):
                        window.destroy()
                    shell.pending_display=DisplayPreferences()
                    shell.commit_display_preferences()
                    shell.pending_pattern_rows=(0,)*8
                    return result['passed']
                return invoke
            return decorate

        @scenario('S1-001 native drag target margins')
        def drag_margins():
            rect=folder_drop_rect(33,77,shell.font.width('Color'))
            for filename in ('native-drop-tolerance','native-drop-tolerance-edges','native-drop-tolerance-final'):
                samples=json.loads((args.references/(filename+'.json')).read_text())
                for sample in samples:
                    assert contains(rect,*sample['pointer']) == bool(sample['target_highlight_pixels']),sample
            assert contains(rect,42,94) and not contains(rect,40,94)
            assert contains(rect,88,94) and not contains(rect,90,94)

        @scenario('S1-002 Explorer title capital rows and baseline')
        def title():
            shell.open('computer')
            win=shell.state.active
            actual=render('explorer-title-after')
            exact('Explorer title text',actual,'native-explorer-menu-clean',(24,4,140,18),(win.x+24,win.y+4))

        @scenario('S1-003 Explorer File popup anchor gutter and Close glyph')
        def explorer_menu():
            shell.open('drive','Documents')
            win=shell.state.active
            shell.action(('window-menu',win,'File',24))
            actual=render('explorer-file-menu-after')
            x,y,context=shell.popup
            assert (x-win.x,y-win.y)==(15,45)
            exact('Explorer Close text and mnemonic',actual,'native-explorer-file-menu-review',
                  (39,195,26,13),(x+24,y+79))

        @scenario('S1-003 Word Wrap checkmark and row geometry')
        def word_wrap():
            shell.launch_accessory('notepad')
            window=shell.accessory_windows['notepad']
            flush_draws(Gtk)
            item=find_menu(window,Gtk).get_children()[1]
            popup=item.get_submenu()
            wrap=popup.get_children()[-1]
            popup.popup_at_widget(item,Gdk.Gravity.SOUTH_WEST,Gdk.Gravity.NORTH_WEST,None)
            flush_draws(Gtk)
            assert (popup.get_allocated_width(),popup.get_allocated_height())==(137,169)
            capture(popup,'word-wrap-unchecked-after')
            popup.popdown()
            wrap.activate()
            assert window.view.get_wrap_mode()==Gtk.WrapMode.WORD_CHAR
            popup.popup_at_widget(item,Gdk.Gravity.SOUTH_WEST,Gdk.Gravity.NORTH_WEST,None)
            actual=capture(popup,'word-wrap-checked-after')
            exact('Word Wrap native checkmark',actual,'native-notepad-wordwrap-checked',
                  (89,239,7,7),(9,154))
            popup.popdown()
            wrap.activate()
            assert window.view.get_wrap_mode()==Gtk.WrapMode.NONE

        @scenario('S1-004 WordPad toolbar bevels and ruler')
        def wordpad():
            shell.launch_accessory('wordpad')
            window=shell.accessory_windows['wordpad']
            actual=capture(window,'wordpad-after')
            button=window.command_buttons['new']
            x,y=button.translate_coordinates(window,0,0)
            assert (x,y)==(10,47),('New button origin',x,y)
            exact('WordPad New button bevel and icon',actual,'reference-wordpad',(120,157,23,22),(x,y))
            x,y=window.ruler.translate_coordinates(window,0,0)
            assert (x,y,window.ruler.get_allocated_height())==(4,103,23),('Ruler',x,y,window.ruler.get_allocation())
            exact('WordPad ruler',actual,'reference-wordpad',(114,213,592,23),(x,y))
            for name in ('cut','copy','paste','undo'):
                button=window.command_buttons[name]
                if button.get_sensitive():
                    continue
                x,y=button.translate_coordinates(window,0,0)
                assert button.get_allocated_width()==23
            exact('WordPad complete file toolbar',actual,'reference-wordpad',(114,153,592,30),(4,43))
            exact('WordPad complete format toolbar',actual,'reference-wordpad',(114,183,592,30),(4,73))
            exact('WordPad editor top edge',actual,'reference-wordpad',(114,236,592,2),(4,126))
            exact('WordPad editor left edge',actual,'reference-wordpad',(114,236,2,260),(4,126))
            assert window.buffer.get_char_count()==0

        @scenario('S1-005 checkbox visible before Apply and persisted after Apply')
        def checkbox():
            shell.open('display')
            win=shell.state.active
            shell.action(('display-tab','settings'))
            shell.action(('display-tray',))
            assert shell.pending_display.tray and not shell.display_preferences.tray
            actual=render('taskbar-checkbox-checked-after')
            exact('Display taskbar checkbox',actual,'native-settings-checkbox',
                  (90,446,13,13),(win.x+24,win.y+380))
            shell.action(('resolution-apply',win,False))
            assert shell.display_preferences.tray
            assert DisplayPreferences.load(shell.display_preferences_path).tray
            render('display-tray-after')
            assert any(action==('display-tray-open',) for *_,action in shell.hits)
            shell.action(('display-tray',))
            assert not shell.pending_display.tray
            shell.action(('close',win))
            shell.open('display')
            assert shell.pending_display.tray
            # A fresh shell must respect the saved preference, not reapply its default.
            restarted=Shell(args.assets)
            restarted.show_all();flush_draws(Gtk)
            image=cairo.ImageSurface(cairo.FORMAT_RGB24,restarted.width,restarted.height)
            restarted.draw(restarted.area,cairo.Context(image))
            image.write_to_png(str(args.output/'tray-restarted-enabled.png'))
            assert restarted.display_preferences.tray
            assert any(action==('display-tray-open',) for *_,action in restarted.hits)
            restarted.disconnect_by_func(Gtk.main_quit);restarted.destroy()
            shell.action(('display-tray',))
            shell.action(('resolution-apply',shell.state.active,False))
            assert not DisplayPreferences.load(shell.display_preferences_path).tray
            render('tray-disabled-after-apply')
            assert not any(action==('display-tray-open',) for *_,action in shell.hits)

        @scenario('S1-005 full rendered palette color counts')
        def palettes():
            shell.wallpaper_images['Gradient']=cairo.ImageSurface(cairo.FORMAT_RGB24,64,64)
            context=cairo.Context(shell.wallpaper_images['Gradient'])
            for y in range(64):
                for x in range(64):
                    context.set_source_rgb(x/63,y/63,((x*7+y*11)%64)/63)
                    context.rectangle(x,y,1,1)
                    context.fill()
            shell.wallpaper.names+=('Gradient',)
            shell.wallpaper.apply('Gradient','center')
            counts={}
            for palette in (3,0,1,2):
                shell.pending_display=DisplayPreferences(palette=palette)
                assert shell.commit_display_preferences()
                actual=render(f'palette-{palette}-after')
                counts[palette]=len({pixel[:3] for pixel in actual[2]})
            assert counts[3]>256 and counts[0]<=16 and counts[1]<=256,counts
            (args.output/'palette-counts.json').write_text(json.dumps(counts,indent=2)+'\n')
            shell.launch_accessory('notepad')
            shell.pending_display=DisplayPreferences(palette=0)
            shell.commit_display_preferences()
            actual=capture(shell.accessory_windows['notepad'],'notepad-16-colors-after')
            assert len({pixel[:3] for pixel in actual[2]})<=16
            window=shell.accessory_windows['notepad']
            item=find_menu(window,Gtk).get_children()[0]
            popup=item.get_submenu()
            popup.popup_at_widget(item,Gdk.Gravity.SOUTH_WEST,Gdk.Gravity.NORTH_WEST,None)
            actual=capture(popup,'notepad-file-menu-16-colors-after')
            assert len({pixel[:3] for pixel in actual[2]})<=16
            popup.popdown()

            shell.wallpaper.apply('(None)','center')

        @scenario('S1-006 Browse preview Apply and image persistence')
        def browse():
            image=cairo.ImageSurface(cairo.FORMAT_RGB24,21,13)
            context=cairo.Context(image)
            context.set_source_rgb(.2,.4,.6)
            context.paint()
            path=root/'Documents'/'Background.png'
            image.write_to_png(str(path))
            shell.open('display')
            with patch('win95lx.apps.dialogs.choose_file',return_value=path):
                shell.action(('wallpaper-help','Browse'))
            assert shell.pending_wallpaper==path.name
            render('browse-picture-preview-after')
            shell.action(('wallpaper-apply',shell.state.active,False))
            restored=Wallpaper(set(),shell.wallpaper.path)
            assert restored.name==path.name and restored.custom[path.name]==str(path)
            assert shell.load_background_image(restored.custom[path.name]).get_width()==21
            with patch('win95lx.apps.dialogs.choose_file',return_value=None):
                shell.action(('wallpaper-help','Browse'))
            assert shell.pending_wallpaper==path.name
            invalid=root/'Documents'/'Invalid.png'
            invalid.write_text('invalid image')
            with patch('win95lx.apps.dialogs.choose_file',return_value=invalid),patch('win95lx.apps.dialogs.message_box') as error:
                shell.action(('wallpaper-help','Browse'))
                assert error.called
            assert shell.pending_wallpaper==path.name

        @scenario('S1-006 Pattern chooser and saved desktop pixels')
        def pattern():
            from win95lx.control_panel.pattern_dialog import PatternDialog
            shell.open('display')
            from gi.repository import GLib
            def choose():
                window=next((window for window in Gtk.Window.list_toplevels()
                             if isinstance(window,PatternDialog) and window.get_visible()),None)
                if window is None:
                    return GLib.SOURCE_CONTINUE
                window.select(window.names.index('Bricks'))
                actual=capture(window,'pattern-chooser-after')
                exact('Pattern clean caption',actual,'native-pattern-clean',(25,43,318,25),(0,0))
                exact('Pattern command buttons',actual,'native-pattern-clean',(255,77,75,53),(230,34))
                def edit_pixel():
                    editor=next((widget for widget in Gtk.Window.list_toplevels()
                                 if isinstance(widget,Gtk.Dialog) and widget.get_title()=='Edit Pattern' and widget.get_visible()),None)
                    if editor is None:
                        return GLib.SOURCE_CONTINUE
                    event=Gdk.Event.new(Gdk.EventType.BUTTON_PRESS)
                    event.x,event.y,event.button=20,54,1
                    event.window=editor.pattern_canvas.get_window()
                    editor.pattern_canvas.emit('button-press-event',event)
                    capture(editor,'pattern-editor-after')
                    editor.response(Gtk.ResponseType.OK)
                    return GLib.SOURCE_REMOVE
                GLib.timeout_add(100,edit_pixel)
                window.edit()
                assert window.names[window.selected]=='Custom'
                window.accept()
                return GLib.SOURCE_REMOVE
            GLib.timeout_add(100,choose)
            shell.action(('wallpaper-help','Pattern'))
            assert shell.pending_pattern=='Custom' and any(shell.pending_pattern_rows)
            shell.pending_wallpaper='(None)'
            shell.action(('wallpaper-apply',shell.state.active,False))
            restored=Wallpaper(set(),shell.wallpaper.path)
            assert restored.pattern=='Custom'
            shell.state.windows.clear()
            render('desktop-pattern-after')
            expected=list(shell.desktop_patterns['Bricks'])
            expected[0] ^= 128
            assert restored.pattern_rows==tuple(expected)
            shell.wallpaper.apply('(None)','center','(None)',(0,)*8)

        @scenario('S1-007 opened and saved documents populate and reopen')
        def documents():
            path=root/'Documents'/'Example.txt'
            path.write_text('Recent document')
            shell.launch_accessory('notepad')
            editor=shell.accessory_windows['notepad']
            assert editor.open_path(path)
            assert path in RecentDocuments().entries()
            entries=shell.submenu_entries(2)
            assert entries[0][0]=='My Documents'
            recent=next(row for row in entries if row[2]==('recent-document',str(path)))
            assert recent[0]=='Example'
            editor.destroy()
            shell.action(recent[2])
            assert shell.accessory_windows['notepad'].text()=='Recent document'
            saved=root/'Documents'/'Saved.txt'
            assert shell.accessory_windows['notepad'].save_path(saved)
            assert saved in RecentDocuments().entries()
            shell.show_start()
            shell.state.menu_index=2
            shell.menu_path=[(2,0)]
            render('recent-documents-after')
            shell.show_start()

        @scenario('S1-008 same-folder clipboard names and Recycle Bin round trip')
        def recycle():
            (root/'Documents'/'CopyTest.txt').write_text('Keep this')
            shell.open('drive','Documents')
            win=shell.state.active
            browser=shell.browser_for(win)
            browser.selection={'CopyTest.txt'}
            shell.drive_edit(win,'copy')
            shell.drive_edit(win,'paste')
            shell.drive_edit(win,'paste')
            assert (root/'Documents/Copy of CopyTest.txt').read_text()=='Keep this'
            assert (root/'Documents/Copy (2) of CopyTest.txt').read_text()=='Keep this'
            render('same-folder-copy-after')
            bin_x,bin_y=shell.desktop_icons.position('recycle',shell.width,shell.height)
            assert shell.file_drop_destination(bin_x+37,bin_y+18)==(None,RECYCLE_TARGET)
            hit=next(hit for hit in shell.hits if hit[4][0]=='item' and hit[4][1] is win and hit[4][3]=='CopyTest.txt')
            source_x,source_y=hit[0]+25,hit[1]+10
            shell.press(shell.area,SimpleNamespace(x=source_x,y=source_y,button=1,time=Gdk.CURRENT_TIME,
                        state=0,type=Gdk.EventType.BUTTON_PRESS))
            shell.motion(shell.area,SimpleNamespace(x=bin_x+37,y=bin_y+18,state=0))
            render('recycle-bin-drop-preview-after')
            with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):
                shell.release(shell.area,SimpleNamespace(x=bin_x+37,y=bin_y+18,button=1,state=0))
            assert not (root/'Documents/CopyTest.txt').exists()
            key,original,_=next(entry for entry in shell.trash.entries() if entry[1].name=='CopyTest.txt')
            assert original==root/'Documents/CopyTest.txt'
            shell.open('recycle')
            render('recycle-bin-after')
            shell.trash_selection={key}
            shell.trash_command('restore')
            assert (root/'Documents/CopyTest.txt').read_text()=='Keep this'
            assert not shell.trash.entries()

        @scenario('S1-008 native Explorer error dialog')
        def error_dialog():
            from gi.repository import GLib
            from win95lx.apps.dialogs import message_box
            checked=[]
            def inspect():
                window=next((window for window in Gtk.Window.list_toplevels()
                             if isinstance(window,Gtk.Dialog) and window.get_visible()),None)
                if window is None:
                    return GLib.SOURCE_CONTINUE
                try:
                    checked.append(window.get_style_context().has_class('win95-native-file'))
                    assert tuple(window.get_size())==(266,126)
                    capture(window,'native-explorer-error-after')
                finally:
                    window.response(Gtk.ResponseType.OK)
                return GLib.SOURCE_REMOVE
            GLib.timeout_add(100,inspect)
            result=message_box(shell,'Error Moving File','The destination folder cannot be used.',
                               Gtk.MessageType.ERROR)
            assert result==Gtk.ResponseType.OK and checked==[True]

        for function in (drag_margins,title,explorer_menu,word_wrap,wordpad,checkbox,palettes,browse,pattern,documents,recycle,error_dialog):
            function()
        shell.disconnect_by_func(Gtk.main_quit)
        shell.destroy()

    digest=hashlib.sha256()
    for path in sorted((ROOT/'src').rglob('*.py')):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(path.read_bytes())
    for comparison in differences:
        path=args.references/(comparison['reference']+'.png')
        comparison['reference_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    report={'source_sha256':digest.hexdigest(),
            'assets_manifest_sha256':hashlib.sha256((args.assets/'manifest.json').read_bytes()).hexdigest(),
            'viewport':[shell.width,shell.height],
            'render_timings':timings,
            'render_median_milliseconds':statistics.median(item['milliseconds'] for item in timings),
            'scenarios':results,'pixel_comparisons':differences,
            'passed':sum(result['passed'] for result in results),
            'failed':sum(not result['passed'] for result in results)}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return 1 if report['failed'] else 0


if __name__=='__main__':
    raise SystemExit(main())
