#!/usr/bin/env python3
"""Full IE4 My Computer menu and interactive chrome acceptance evidence."""
import argparse,json,sys,hashlib
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
from pixels import read,write
from check_reference_ui import compare_region

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'private/screenshots'/datetime.now(timezone.utc).strftime('computer-%Y%m%dT%H%M%S%fZ'))
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    import gi
    gi.require_foreign('cairo')
    import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from check_menu_seams import flush_draws
    from win95lx.shell.explorer_menu import computer_file_rows
    comparisons=[]
    def compare(actual,name,reference,rect,origin):
        difference=compare_region(actual,read(ROOT/'private/screenshots/start-development-20261110'/reference),rect,origin)
        comparisons.append(dict(name=name,differing_pixels=difference,reference=reference,rect=rect,actual_origin=origin))
    with TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
        (Path(home)/'Desktop').mkdir()
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        shell.state.open('computer');win=shell.state.active
        win.x=win.y=0;win.width=shell.width;win.height=shell.height-28
        win.restored_bounds=(100,65,512,461)
        def capture(name):
            image=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height)
            shell.draw(shell.area,cairo.Context(image));image.write_to_png(str(args.output/(name+'.png')))
            return read(args.output/(name+'.png'))
        normal=capture('computer-after')
        shell.action(('window-menu',win,'File',24))
        opened=capture('file-menu-after')
        assert [r.label for r in computer_file_rows() if r]==['Create Shortcut','Delete','Rename','Properties','My Computer','Work Offline','Close']
        assert len(shell.drive_menu_rows)==3
        assert not any(r.enabled for r in computer_file_rows(selection=None)[:4])
        assert computer_file_rows(selection='(C:)')[3].enabled
        assert not computer_file_rows(selection='Control Panel')[3].enabled
        assert shell.popup[:2]==(11,40),shell.popup
        if shell.width==800:
            compare(opened,'complete open File menubar','native-computer-file-full.png',(0,18,800,22),(0,18))
        compare(opened,'File pressed heading','native-computer-file-full.png',(11,22,32,18),(11,22))
        compare(opened,'File menu status hint','native-computer-file-full.png',(0,551,800,21),(0,shell.height-49))
        compare(opened,'complete File popup','native-computer-file-full.png',(11,40,122,144),(11,40))
        shell.drive_menu_key('Down',False);assert shell.drive_menu_highlight=='computer'
        shell.drive_menu_key('Down',False);assert shell.drive_menu_highlight=='offline'
        shell.drive_menu_key('Return',False);assert shell.work_offline and shell.popup is None
        shell.action(('window-menu',win,'File',24));capture('file-menu-offline-after')
        shell.drive_menu_key('Escape',False);assert shell.popup is None
        shell.action(('explorer-tool',win,'views'));capture('views-menu-after')
        assert shell.popup[2]==(win,'View')
        shell.action(('computer-view-toggle',win,'web_view'));assert not win.web_view
        capture('classic-view-after')
        shell.action(('computer-view-toggle',win,'web_view'));assert win.web_view
        if shell.width==800:
            compare(normal,'toolbar full band','native-computer-web-full.png',(0,42,800,46),(0,42))
            compare(normal,'address band','native-computer-web-full.png',(0,88,800,26),(0,88))
            compare(normal,'complete caption','native-computer-web-full.png',(0,0,800,18),(0,0))
        else:
            compare(normal,'toolbar left','native-computer-web-full.png',(0,42,630,46),(0,42))
            compare(normal,'toolbar right','native-computer-web-full.png',(758,42,42,46),(shell.width-42,42))
            compare(normal,'address left','native-computer-web-full.png',(0,88,200,26),(0,88))
            compare(normal,'address right','native-computer-web-full.png',(776,88,24,26),(shell.width-24,88))
        compare(normal,'Web View computer illustration','native-computer-web-full.png',(4,118,85,85),(4,118))
        compare(normal,'Web View heading','native-computer-web-full.png',(110,136,160,25),(110,136))
        # Selection changes the live command targets, rather than a static disabled picture.
        shell.item_selection=(win,'(C:)')
        shell.action(('window-menu',win,'File',24));capture('file-menu-drive-selected-after')
        assert {r[2] for r in shell.drive_menu_rows}=={'shortcut','properties','computer','offline','close'}
        with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.OK) as prompt:
            shell.action(('explorer-tool',win,'properties'))
            assert prompt.call_args.args[1]=='(C:) Properties'
        shell.item_selection=(win,'Control Panel')
        shell.action(('window-menu',win,'File',24))
        capture('file-menu-control-selected-after')
        assert {r[2] for r in shell.drive_menu_rows}=={'shortcut','computer','offline','close'}
        shell.drive_menu_key('Escape',False)
        shell.action(('explorer-address',win));assert shell.address_window is win
        shell.address_window=None
        shell.press(shell.area,SimpleNamespace(x=700,y=400,button=1,type=Gdk.EventType.BUTTON_PRESS,state=0,time=Gdk.CURRENT_TIME))
        assert shell.item_selection is None
        shell.action(('window-menu',win,'File',24));capture('file-menu-after-clearing-selection')
        assert {r[2] for r in shell.drive_menu_rows}=={'computer','offline','close'}
        shell.popup=None
        shell.item_selection=(win,'Control Panel')
        with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):
            shell.action(('computer-menu',win,'shortcut'))
        shortcut=next(shell.desktop_folder.glob('*.desktop'))
        shell.open_drive_file(shortcut.relative_to(shell._drive.view.root))
        assert shell.state.active.kind=='control'
        shell.state.windows.remove(shell.state.active)
        for band in ('toolbar','address_bar'):
            shell.action(('computer-view-toggle',win,band));capture('hidden-'+band)
            assert not getattr(win,band)
            shell.action(('computer-view-toggle',win,band));assert getattr(win,band)
        compare(normal,'Web View description','native-computer-web-full.png',(20,218,165,32),(20,218))
        compare(normal,'C drive icon and label','native-computer-web-clean.png',(330,175,50,50),(330,175))
        compare(normal,'Control Panel icon and label','native-computer-web-clean.png',(245,245,70,60),(245,245))
        shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    digest=hashlib.sha256()
    for path in sorted((ROOT/'src').rglob('*.py')):
        digest.update(str(path.relative_to(ROOT)).encode());digest.update(path.read_bytes())
    report={'source_sha256':digest.hexdigest(),'viewport':[shell.width,shell.height],
            'assets_manifest_sha256':hashlib.sha256((ROOT/'private/shell-assets/manifest.json').read_bytes()).hexdigest(),
            'reference_sha256':{name:hashlib.sha256((ROOT/'private/screenshots/start-development-20261110'/name).read_bytes()).hexdigest() for name in ('native-computer-file-full.png','native-computer-web-full.png','native-computer-web-clean.png')},
            'comparisons':comparisons,'failed':sum(bool(r['differing_pixels']) for r in comparisons),
            'interaction_checks':['complete menu profile','disabled commands excluded from input','keyboard navigation','Work Offline toggle','Escape','Web View toggle','selection-specific targets','blank click clears selection','Create Shortcut and reopen','address field focus','band toggles']}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));return bool(report['failed'])
if __name__=='__main__':raise SystemExit(main())
