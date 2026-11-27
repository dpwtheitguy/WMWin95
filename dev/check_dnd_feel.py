#!/usr/bin/env python3
"""Replay DnD event traces against real Shell handlers on an owned Xvfb only.

Fixture files and settings stay in disposable HOME. This is not a physical
mouse/QEMU/viewer test and makes no claim about those external layers.
"""
import argparse,json,os,select,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def child(args):
    if args.gi_extension_path:
        import gi;gi.__path__.append(str(args.gi_extension_path))
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from check_accessibility import owned_display_guard
    from check_menu_seams import flush_draws
    from win95lx.explorer.drive_browser import DriveBrowser
    from win95lx.shell.desktop_icons import DEFAULTS
    from dataclasses import replace
    from types import SimpleNamespace
    from unittest.mock import patch
    display=Gdk.Display.get_default()
    if 'X11' not in type(display).__name__ or display.get_name()!=args.owned_display or not owned_display_guard(args.owned_display,args.owned_xvfb_pid):raise RuntimeError('Refusing a DnD trace outside its owned Xvfb display.')
    args.output.mkdir(parents=True,exist_ok=False);home=Path.home();root=home/'fixture';(root/'Desktop').mkdir(parents=True);(root/'Source/Nested').mkdir(parents=True);(root/'Source/report.txt').write_text('owned fixture');(root/'Desktop/desktop.txt').write_text('owned desktop fixture')
    shell=Shell(ROOT/'private/shell-assets');shell._drive=DriveBrowser(root);shell.desktop_folder=root/'Desktop';shell.refresh_desktop_files();shell.show_all();shell.resize_to_display(shell.get_screen());flush_draws(Gtk)
    physical=(shell.area.get_allocated_width(),shell.area.get_allocated_height());assert physical==tuple(map(int,args.resolution.split('x'))),physical
    results=[];all_failures=[];trace=[];case_name='';started=time.perf_counter()
    def render(name):
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*physical);shell.draw(shell.area,cairo.Context(surface));surface.write_to_png(str(args.output/(name+'.png')))
    def snapshot():
        return {'file_drag_active':shell.file_drag is not None,'file_drag_point':shell.file_drag_point,'shortcut_drag_point':shell.shortcut_drag_point,'icon_drag_point':shell.icon_drag_point,'desktop_position':shell.desktop_icons.positions.get('file:desktop.txt')}
    def event(kind,point,mods=0):
        scale=shell.pointer_scale;raw=(point[0]*scale,point[1]*scale);e=SimpleNamespace(x=raw[0],y=raw[1],x_root=raw[0],y_root=raw[1],button=1,state=mods|(int(Gdk.ModifierType.BUTTON1_MASK) if kind=='motion' else 0),time=Gdk.CURRENT_TIME,type=Gdk.EventType.BUTTON_PRESS)
        before=snapshot()
        if kind=='press':shell.press(shell.area,e)
        elif kind=='motion':shell.motion(shell.area,e)
        elif kind=='release':shell.release(shell.area,e)
        elif kind=='escape':shell.key(shell,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0))
        trace.append({'case':case_name,'elapsed_ms':round((time.perf_counter()-started)*1000,3),'event':kind,'raw':raw,'logical':point,'state':int(e.state),'before':before,'after':snapshot()})
    def reset(dpi):
        shell.state.windows.clear();shell.file_drag=shell.file_drag_origin=shell.file_drag_point=shell.file_hover=None;shell.shortcut_drag=shell.shortcut_drag_point=shell.shortcut_drop=None;shell.icon_drag=shell.icon_drag_point=None;shell.drag=None;shell.popup=None;shell.state.selection=None;shell.item_selection=None
        shell.desktop_icons.positions=DEFAULTS.copy();shell.shortcut_icons.positions={};shell.display_preferences=replace(shell.display_preferences,dpi=dpi);render('reset-'+str(dpi))
    def check(name,actual,expected,failures):
        if actual!=expected:failures.append({'assertion':name,'actual':actual,'expected':expected})
    def item(win,name):return next(hit for hit in shell.hits if hit[4][0]=='item' and hit[4][1] is win and hit[4][3]==name)
    try:
        for dpi in (96,120,144):
            reset(dpi);case_name=f'file-latch-{dpi}';failures=[];shell.open('drive','Source');win=shell.state.active;win.x,win.y,win.width,win.height=4,70,300,270;render(case_name+'-before');hx,hy,w,h,action=item(win,'report.txt');start=(hx+25,hy+10);far=(start[0]+90,start[1]+40);near=(start[0]+1,start[1]+1)
            event('press',start);event('motion',far);render(case_name+'-far');event('motion',near);render(case_name+'-returned')
            check('latched drag ghost follows pointer back inside initial threshold',shell.file_drag_point,near,failures)
            with patch.object(shell,'drop_drive_selection',wraps=shell.drop_drive_selection) as dropped:event('release',near);check('release remains a drop after threshold was previously crossed',dropped.call_count,1,failures)
            render(case_name+'-after');results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
            reset(dpi);case_name=f'desktop-release-endpoint-{dpi}';failures=[];origin=(180,40);shell.desktop_icons.move('file:desktop.txt',origin);render(case_name+'-before');hx,hy,w,h,action=next(hit for hit in shell.hits if hit[4]==('desktop','file:desktop.txt'));start=(hx+25,hy+10);motion=(start[0]+35,start[1]+20);end=(start[0]+70,start[1]+45)
            event('press',start);event('motion',motion);render(case_name+'-last-motion');event('release',end);expected=shell.desktop_icons.clamp(origin[0]+70,origin[1]+45,shell.width,shell.height);actual=shell.desktop_icons.positions['file:desktop.txt'];check('persisted desktop position uses final release rather than stale motion',actual,expected,failures);render(case_name+'-after');results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
            reset(dpi);case_name=f'shortcut-release-endpoint-{dpi}';failures=[];shell.action(('start-folder','accessories'));win=shell.state.active;win.x,win.y,win.width,win.height=4,70,300,270;render(case_name+'-before');hx,hy,w,h,action=item(win,'Calculator');origin=action[4];start=(hx+25,hy+10);motion=(start[0]+30,start[1]+20);end=(start[0]+50,start[1]+40)
            event('press',start);event('motion',motion);render(case_name+'-last-motion');event('release',end);expected=shell.clamp_shortcut(win,origin[0]+50,origin[1]+40);actual=shell.shortcut_icons.position(win.folder,'Calculator',None);check('persisted shortcut position uses final release rather than stale motion',actual,expected,failures);render(case_name+'-after');results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
        for dpi in (96,120,144):
            reset(dpi);case_name=f'escape-cancel-{dpi}';failures=[];shell.open('drive','Source');win=shell.state.active;win.x,win.y,win.width,win.height=4,70,300,270;render(case_name+'-before');hx,hy,_,_,_=item(win,'report.txt');start=(hx+25,hy+10);end=(start[0]+50,start[1]+35)
            event('press',start);event('motion',end);event('escape',end)
            with patch.object(shell,'drop_drive_selection',wraps=shell.drop_drive_selection) as dropped:event('release',end);check('Escape prevents release operation',dropped.call_count,0,failures)
            check('Escape clears drag ghost',shell.file_drag_point,None,failures);check('Escape preserves source file',(root/'Source/report.txt').read_text(),'owned fixture',failures);check('Escape preserves original selection',sorted(win.browser.selection),['report.txt'],failures);results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
            reset(dpi);case_name=f'near-self-folder-drop-{dpi}';failures=[];shell.open('drive','Source');win=shell.state.active;win.x,win.y,win.width,win.height=4,70,300,270;render(case_name+'-before');hx,hy,_,_,_=item(win,'Nested');start=(hx+25,hy+10);end=(start[0]+8,start[1]+8)
            with patch.object(shell,'transfer_files',wraps=shell.transfer_files) as transfer:
                event('press',start);event('motion',end);render(case_name+'-hover');event('release',end);check('Near-self drop rearranges without filesystem self-transfer',transfer.call_count,0,failures)
            check('Folder survives near-self drop',(root/'Source/Nested').is_dir(),True,failures);results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
            reset(dpi);case_name=f'folder-margin-transfer-{dpi}';failures=[];shell.open('drive','Source');win=shell.state.active;win.x,win.y,win.width,win.height=4,70,300,270;render(case_name+'-before');hx,hy,_,_,_=item(win,'report.txt');start=(hx+25,hy+10);tx,ty,_,_,action=item(win,'Nested')
            from win95lx.shell.drop_geometry import folder_drop_rect
            from win95lx.shell import explorer_chrome
            point=action[4];rect=folder_drop_rect(win.x+explorer_chrome.PANE_X+point[0],win.y+explorer_chrome.PANE_Y+point[1],min(72,shell.font.width('Nested')));end=(rect[0]+1,rect[1]+3)
            event('press',start);event('motion',end);render(case_name+'-hover');event('release',end);check('Margin target receives real file',(root/'Source/Nested/report.txt').exists(),True,failures);check('Move removes source',(root/'Source/report.txt').exists(),False,failures)
            if (root/'Source/Nested/report.txt').exists():(root/'Source/Nested/report.txt').rename(root/'Source/report.txt')
            results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
            reset(dpi);case_name=f'desktop-release-clamp-{dpi}';failures=[];origin=(180,40);shell.desktop_icons.move('file:desktop.txt',origin);render(case_name+'-before');hx,hy,_,_,_=next(hit for hit in shell.hits if hit[4]==('desktop','file:desktop.txt'));start=(hx+25,hy+10);event('press',start);event('motion',(start[0]+10,start[1]+10));event('release',(start[0]+10000,start[1]-1000));expected=shell.desktop_icons.clamp(origin[0]+10000,origin[1]-1000,shell.width,shell.height);check('Final endpoint remains clamped to desktop',shell.desktop_icons.positions['file:desktop.txt'],expected,failures);results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
            reset(dpi);case_name=f'ctrl-copy-same-folder-{dpi}';failures=[];shell.open('drive','Source');win=shell.state.active;win.x,win.y,win.width,win.height=4,70,300,270;render(case_name+'-before');hx,hy,_,_,_=item(win,'report.txt');start=(hx+25,hy+10);end=(win.x+220,win.y+205);mods=int(Gdk.ModifierType.CONTROL_MASK)
            event('press',start,mods);event('motion',end,mods);render(case_name+'-hover');event('release',end,mods);check('Ctrl drag within same folder creates a real copy',(root/'Source/Copy of report.txt').exists(),True,failures);check('Ctrl drag preserves original',(root/'Source/report.txt').read_text(),'owned fixture',failures)
            if (root/'Source/Copy of report.txt').exists():check('Copy bytes match source',(root/'Source/Copy of report.txt').read_bytes(),(root/'Source/report.txt').read_bytes(),failures)
            render(case_name+'-first-copy');hx,hy,_,_,_=item(win,'report.txt');start=(hx+25,hy+10);event('press',start,mods);event('motion',end,mods);event('release',end,mods);check('Repeated Ctrl drag allocates Copy(2)',(root/'Source/Copy (2) of report.txt').exists(),True,failures)
            if (root/'Source/Copy (2) of report.txt').exists():check('Repeated copy bytes match source',(root/'Source/Copy (2) of report.txt').read_bytes(),(root/'Source/report.txt').read_bytes(),failures)
            render(case_name+'-second-copy');hx,hy,_,_,_=item(win,'report.txt');start=(hx+25,hy+10);selection=set(win.browser.selection)
            def fail_copy(original,copied):copied.write(b'partial');raise OSError('Injected owned-fixture copy failure')
            with patch('win95lx.explorer.file_operations.shutil.copyfileobj',side_effect=fail_copy),patch('win95lx.apps.dialogs.message_box') as error:
                event('press',start,mods);event('motion',end,mods);event('release',end,mods);check('Failed copy raises native error route',error.call_count,1,failures)
            check('Failed copy removes partial destination',(root/'Source/Copy (3) of report.txt').exists(),False,failures);check('Failed copy retains source bytes',(root/'Source/report.txt').read_text(),'owned fixture',failures);check('Failed copy retains selection',sorted(win.browser.selection),sorted(selection),failures)
            for name in ('Copy of report.txt','Copy (2) of report.txt'):(root/'Source'/name).unlink(missing_ok=True)
            results.append({'case':case_name,'dpi':dpi,'failures':failures});all_failures.extend(failures)
        from evidence import identity
        report={**identity(ROOT,Path(__file__).resolve()),'display':physical,'backend':type(display).__name__,'display_name':display.get_name(),'uid':os.geteuid(),'cases':results,'failure_count':len(all_failures),'scope':'Actual Shell press/motion/release handlers with disposable filesystem; synthetic logical-DPI/coalesced-endpoint traces, not physical mouse/QEMU/fractional-host-viewer evidence.'}
        (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');(args.output/'traces.json').write_text(json.dumps(trace,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    if all_failures:raise SystemExit(1)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--resolution',choices=('800x600','1280x800'),default='800x600');p.add_argument('--gi-extension-path',type=Path);p.add_argument('--owned-display',help=argparse.SUPPRESS);p.add_argument('--owned-xvfb-pid',type=int,help=argparse.SUPPRESS);args=p.parse_args();args.output=args.output.resolve()
    if args.gi_extension_path is None:
        # Preserve a private matching GI Cairo extension already loaded by a
        # test wrapper when the owned-display child uses sys.executable.
        try:
            import gi
            args.gi_extension_path=next((Path(directory) for directory in gi.__path__ if any(Path(directory).glob('_gi_cairo*.so'))),None)
        except ImportError:pass
    if args.owned_display:return child(args)
    executable=shutil.which('Xvfb')
    if not executable:raise RuntimeError('Xvfb is required for isolated traces.')
    readfd,writefd=os.pipe();server=None
    try:
        server=subprocess.Popen([executable,'-displayfd',str(writefd),'-screen','0',args.resolution+'x24','-nolisten','tcp','-noreset'],pass_fds=(writefd,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);os.close(writefd);writefd=None
        if not select.select([readfd],[],[],5)[0]:raise RuntimeError('Owned Xvfb did not start.')
        number=os.read(readfd,32).decode().strip()
        if not number.isdigit():raise RuntimeError('Invalid display number.')
        with tempfile.TemporaryDirectory(prefix='win95lx-dnd-') as home:
            env={k:v for k,v in os.environ.items() if k!='WAYLAND_DISPLAY'};env.update(DISPLAY=':'+number,GDK_BACKEND='x11',HOME=home,XDG_CONFIG_HOME=home+'/.config',XDG_DATA_HOME=home+'/.local/share',XDG_CACHE_HOME=home+'/.cache')
            cmd=[sys.executable,str(Path(__file__).resolve()),'--owned-display',':'+number,'--owned-xvfb-pid',str(server.pid),'--output',str(args.output),'--resolution',args.resolution]
            if args.gi_extension_path:cmd+=['--gi-extension-path',str(args.gi_extension_path)]
            result=subprocess.run(cmd,env=env,timeout=60);raise SystemExit(result.returncode)
    finally:
        os.close(readfd)
        if writefd is not None:os.close(writefd)
        if server:
            server.terminate()
            try:server.communicate(timeout=3)
            except subprocess.TimeoutExpired:server.kill();server.communicate()
if __name__=='__main__':main()
