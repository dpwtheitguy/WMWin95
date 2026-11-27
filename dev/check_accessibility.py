#!/usr/bin/env python3
"""Owned-Xvfb Accessibility GUI/service UAT; never selects the user's display."""
import argparse,json,os,select,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def owned_display_guard(display,pid):
    """Allow only the exact still-running Xvfb process spawned by this harness."""
    if not pid or display!=os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY') or os.environ.get('GDK_BACKEND')!='x11':return False
    try:
        process=Path('/proc')/str(pid);command=(process/'cmdline').read_bytes().split(b'\0')
        return process.stat().st_uid==os.geteuid() and Path(os.fsdecode(command[0])).name=='Xvfb' and b'-displayfd' in command and b'-nolisten' in command and b'tcp' in command
    except (OSError,ValueError,IndexError):return False

def child(args):
    if args.gi_extension_path:
        import gi;gi.__path__.append(str(args.gi_extension_path))
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    display=Gdk.Display.get_default()
    if 'X11' not in type(display).__name__ or display.get_name()!=args.owned_display:raise RuntimeError('Refusing a GUI/backend outside the owned Xvfb display.')
    if not owned_display_guard(args.owned_display,args.owned_xvfb_pid):raise RuntimeError('The requested display is not the harness-owned Xvfb server.')
    from win95lx.apps.accessibility import AccessibilityWindow,AccessSettings
    from win95lx.control_panel.access_preferences import XKBAccess,ALL_CONTROLS
    from check_menu_seams import flush_draws
    from check_reference_ui import compare_region
    from pixels import read
    from unittest.mock import patch
    from types import SimpleNamespace
    from dataclasses import replace
    backend=XKBAccess(display=args.owned_display,guard=lambda:owned_display_guard(args.owned_display,args.owned_xvfb_pid))
    if args.startup_probe:
        before=backend.snapshot();saved=path=Path.home()/'.config/win95lx/accessibility.json';guard_calls=[]
        def fixture_guard():
            guard_calls.append(True);return args.startup_probe!='denied' and owned_display_guard(args.owned_display,args.owned_xvfb_pid)
        backend.guard=fixture_guard
        with patch('win95lx.control_panel.access_preferences.XKBAccess',return_value=backend) as factory:
            probe_shell=Shell(ROOT/'private/shell-assets');factory.assert_called_once();probe_shell.disconnect_by_func(Gtk.main_quit);probe_shell.destroy()
        if args.startup_probe=='valid':
            from win95lx.control_panel.access_preferences import AccessPreferences
            assert backend.preferences()==AccessPreferences(**json.loads(saved.read_text())).validate() and guard_calls
        else:assert backend.snapshot()==before
        if args.startup_probe=='denied':assert guard_calls
        print('STARTUP_PROBE='+json.dumps({'case':args.startup_probe,'guard_calls':len(guard_calls),'unchanged':backend.snapshot()==before,'uid':os.geteuid(),'display':args.owned_display}));return
    args.output.mkdir(parents=True,exist_ok=False);original=backend.snapshot();checks=[];comparisons=[];path=Path.home()/'.config/win95lx/accessibility.json';shell=None;window=None
    try:
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        started=time.perf_counter();window=AccessibilityWindow(shell,backend,path);construct_ms=(time.perf_counter()-started)*1000;first_draw=[]
        window.area.connect('draw',lambda *_:first_draw.append(time.perf_counter()) if not first_draw else False)
        window.show_all();flush_draws(Gtk);open_ms=(time.perf_counter()-started)*1000;first_draw_ms=(first_draw[0]-started)*1000
        def capture(win,name):
            flush_draws(Gtk);surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*win.size);win.caption_active=True;win.draw(win.area,cairo.Context(surface));file=args.output/(name+'.png');surface.write_to_png(str(file));return read(file)
        for tab,name in enumerate(window.tabs):
            window.action(('tab',tab));actual=capture(window,'accessibility-'+name);source=read(ROOT/'private/shell-assets'/f'accessibility-{name}-frame.png')
            rect=(0,0,367,52);difference=compare_region(actual,source,rect,(0,0));comparisons.append({'region':name+'-caption-tabs','differing_pixels':difference});assert difference==0,(name,difference)
        window.action(('tab',0));window.focus_action=('check','sticky');actual=capture(window,'accessibility-keyboard-focused');source=read(ROOT/'private/shell-assets/accessibility-keyboard-frame.png');rect=(73,121,105,16);difference=compare_region(actual,source,rect,(73,121));comparisons.append({'region':'focused-unchecked-StickyKeys','differing_pixels':difference});assert difference==0,difference
        event=lambda x,y:SimpleNamespace(x=x,y=y,x_root=x,y_root=y,button=1)
        window.press(window.area,event(177,136));window.release(window.area,event(178,136));assert not window.controller.pending.sticky
        window.press(window.area,event(177,136));window.release(window.area,event(177,136));assert window.controller.pending.sticky
        window.key(window,SimpleNamespace(keyval=Gdk.KEY_u,state=Gdk.ModifierType.MOD1_MASK));assert not window.controller.pending.sticky
        window.key(window,SimpleNamespace(keyval=Gdk.KEY_u,state=Gdk.ModifierType.MOD1_MASK));assert window.controller.pending.sticky
        assert not backend.preferences().sticky;window.action(('apply',));assert backend.preferences().sticky;assert json.loads(path.read_text())['sticky'];capture(window,'accessibility-sticky-applied')
        checks.append('StickyKeys full-hitbox edge click, outside-release cancellation and Alt+U routing work; edits remain pending; Apply changes real nonadmin XKB state, saves JSON and keeps window open')
        for kind in ('sticky','toggle','amouse'):
            nested=AccessSettings(window,kind);nested.show_all();capture(nested,kind+'-settings');before=window.controller.pending
            if kind=='sticky':nested.action(('check','sticky_lock'));nested.action(('cancel',));assert window.controller.pending==before
            else:nested.action(('cancel',))
        window.action(('check','filter'));nested=AccessSettings(window,'filter');nested.show_all();actual=capture(nested,'filter-settings-bounce');source=read(ROOT/'private/shell-assets/accessibility-filter-settings-frame.png')
        for name,rect in (('checked-filter-radio',(24,150,170,16)),('multiline-filter-radio',(24,178,179,36))):
            difference=compare_region(actual,source,rect,(rect[0],rect[1]));comparisons.append({'region':name,'differing_pixels':difference});assert difference==0,(name,difference)
        advanced=AccessSettings(nested,'abounce');advanced.show_all();advanced.pending=replace(advanced.pending,bounce_ms=500);actual=capture(advanced,'bounce-native-min');source=read(ROOT/'private/shell-assets/accessibility-abounce-settings-frame.png');rect=(143,64,149,29);difference=compare_region(actual,source,rect,(143,64));comparisons.append({'region':'native-bounce-slider-min','differing_pixels':difference});assert difference==0,difference;advanced.focus_action=('slider','bounce_ms');advanced.key(advanced,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert advanced.pending.bounce_ms==2000;capture(advanced,'bounce-delay-end');advanced.action(('ok',));nested.action(('ok',));window.action(('apply',));assert backend.preferences().bounce and backend.preferences().bounce_ms==2000
        nested=AccessSettings(window,'filter');nested.show_all();nested.action(('mode','slow'));capture(nested,'filter-settings-slow');advanced=AccessSettings(nested,'aslow');advanced.show_all();advanced.pending=replace(advanced.pending,slow_ms=1000);actual=capture(advanced,'slow-native-default');source=read(ROOT/'private/shell-assets/accessibility-aslow-settings-frame.png');rect=(144,280,149,29);difference=compare_region(actual,source,rect,(144,280));comparisons.append({'region':'native-slow-slider-default','differing_pixels':difference});assert difference==0,difference;advanced.focus_action=('slider','slow_ms');advanced.key(advanced,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert advanced.pending.slow_ms==2000;capture(advanced,'slow-delay-end');advanced.action(('ok',));nested.action(('ok',));window.action(('apply',));assert backend.preferences().slow and not backend.preferences().bounce and backend.preferences().slow_ms==2000
        checks.append('Native child Cancel discards edits; nested bounce/slow radio and slider End choices propagate pending-only to parent, then real server timing readback after Apply')
        window.action(('tab',3));window.action(('check','mouse'));window.action(('apply',));assert backend.preferences().mouse;capture(window,'mouse-applied')
        window.action(('tab',4));window.action(('check','automatic_reset'))
        if not window.controller.pending.automatic_reset:window.action(('check','automatic_reset'))
        window.action(('minutes',));flush_draws(Gtk);popup=window.popup_window;assert popup.visible==len(popup.choices)==6;popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_End,state=0));popup.key(popup,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));assert window.controller.pending.reset_seconds==1800;window.action(('apply',));assert backend.preferences().reset_seconds==1800;capture(window,'automatic-reset-applied')
        checks.append('MouseKeys real server enable; native idle-minutes dropdown keyboard End/Enter sets1800sec and actual XKB readback; six-choice popup has no vertical scrollbar')
        before=backend.snapshot();saved=path.read_bytes();window.action(('tab',0));window.action(('check','sticky'))
        with patch('win95lx.control_panel.preferences.save_preferences',side_effect=OSError('Private /home/user/path')),patch.object(window,'error') as error:
            window.action(('apply',));error.assert_called_once();assert 'could not be saved' in str(error.call_args[0][0])
        assert backend.snapshot()==before and path.read_bytes()==saved
        window.action(('cancel',));window=AccessibilityWindow(shell,backend,path);window.show_all();assert window.controller.pending==backend.preferences();capture(window,'reopened-live-state')
        checks.append('Injected persistence failure restores exact real XKB snapshot and prior JSON; Cancel closes without undoing previously applied changes; reopen reads real session state')
        # A disabled checkbox never enters hit/focus/mnemonic routing.
        window.action(('tab',1));flush_draws(Gtk);assert not any(a[0]=='check' for rect,a in window.hits);assert window.disabled
        with patch('win95lx.apps.dialogs.message_box') as helpbox:window.help();assert 'unfinished' in helpbox.call_args[0][2]
        checks.append('Unavailable SoundSentry/ShowSounds controls have no input action; Help exposes concrete unfinished-integration reasons')
        saved=path.read_bytes();applied=backend.preferences()
        def startup(case,new_server=False):
            command=[sys.executable,str(Path(__file__).resolve()),'--startup-probe',case,'--output',str(args.output)]
            if new_server:command+=['--seed-profile',str(path)]
            else:command+=['--owned-display',args.owned_display,'--owned-xvfb-pid',str(args.owned_xvfb_pid)]
            if args.gi_extension_path:command+=['--gi-extension-path',str(args.gi_extension_path)]
            result=subprocess.run(command,env=os.environ.copy(),capture_output=True,text=True,timeout=15);(args.output/('startup-'+case+'-'+str(len(list(args.output.glob('startup-*.log'))))+'.log')).write_text(result.stdout+'\n'+result.stderr)
            assert result.returncode==0,result.stdout+'\n'+result.stderr
            row=next(line.split('=',1)[1] for line in result.stdout.splitlines() if line.startswith('STARTUP_PROBE='));return json.loads(row)
        backend._write(original,ALL_CONTROLS);row=startup('valid');assert backend.preferences()==applied and row['guard_calls']
        for text in ('{bad','[1,2]','null','{"sticky":1}','{"unknown":true}'):
            before=backend.snapshot();path.write_text(text);row=startup('unchanged');assert row['unchanged'] and backend.snapshot()==before
        path.write_bytes(saved);backend._write(original,ALL_CONTROLS);before=backend.snapshot();row=startup('denied');assert row['unchanged'] and backend.snapshot()==before
        startup('valid');assert backend.preferences()==applied
        row=startup('valid',new_server=True);assert row['display']!=args.owned_display and row['guard_calls'] and not row['unchanged']
        checks.append('Fresh backend/Shell processes and a newly spawned Xvfb session restore saved accessibility on their owned server; malformed/list/null/invalid/unknown-key JSON and a denied startup guard leave raw controls unchanged; final valid startup restores the saved state')
        from evidence import identity
        report={**identity(ROOT,Path(__file__).resolve(),[ROOT/'private/accessibility-20261126/native/accessibility-keyboard.png']),'display_backend':type(display).__name__,'display_name':display.get_name(),'display':[display.get_default_screen().get_width(),display.get_default_screen().get_height()],'uid':os.geteuid(),'checks':checks,'comparisons':comparisons,'accessibility_provenance_sha256':__import__('hashlib').sha256((ROOT/'private/shell-assets/accessibility-provenance.json').read_bytes()).hexdigest(),'construct_ms':round(construct_ms,3),'first_draw_ms':round(first_draw_ms,3),'open_with_fixed_150ms_settle_ms':round(open_ms,3),'failed':0,'pixel_scope':'Only named caption/tab bands, focused unchecked StickyKeys, two FilterKeys radio states and two native slider states; other states/full applet remain unaccepted.','service_scope':'Actual nonadmin owned-Xvfb XKB state, real file persistence and rollback; no live guest or physical keyboard mutation.'}
    finally:
        backend._write(original,ALL_CONTROLS);assert backend.snapshot()==original
        if shell:
            for top in list(Gtk.Window.list_toplevels()):
                if top is not shell:top.destroy()
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    report['original_controls_restored']=True;(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--resolution',choices=('800x600','1280x800'),default='800x600');parser.add_argument('--gi-extension-path',type=Path);parser.add_argument('--owned-display',help=argparse.SUPPRESS);parser.add_argument('--owned-xvfb-pid',type=int,help=argparse.SUPPRESS);parser.add_argument('--startup-probe',choices=('valid','unchanged','denied'),help=argparse.SUPPRESS);parser.add_argument('--seed-profile',type=Path,help=argparse.SUPPRESS);args=parser.parse_args();args.output=args.output.resolve()
    if args.gi_extension_path is None:
        # Preserve a private matching GI Cairo extension already loaded by a
        # test wrapper when the owned-display child uses sys.executable.
        try:
            import gi
            args.gi_extension_path=next((Path(directory) for directory in gi.__path__ if any(Path(directory).glob('_gi_cairo*.so'))),None)
        except ImportError:pass
    if args.owned_display:return child(args)
    executable=shutil.which('Xvfb')
    if not executable:raise RuntimeError('Install or privately extract Xvfb for this isolated check.')
    readfd,writefd=os.pipe();server=None
    try:
        server=subprocess.Popen([executable,'-displayfd',str(writefd),'-screen','0',args.resolution+'x24','-nolisten','tcp','-noreset'],pass_fds=(writefd,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);os.close(writefd);writefd=None
        if not select.select([readfd],[],[],5)[0]:raise RuntimeError('Owned Xvfb did not become ready.')
        number=os.read(readfd,32).decode().strip()
        if not number.isdigit():raise RuntimeError('Invalid owned Xvfb display number.')
        with tempfile.TemporaryDirectory(prefix='win95lx-accessibility-') as home:
            env={key:value for key,value in os.environ.items() if key!='WAYLAND_DISPLAY'};env.update(DISPLAY=':'+number,GDK_BACKEND='x11',HOME=home,XDG_CONFIG_HOME=home+'/.config',XDG_DATA_HOME=home+'/.local/share',XDG_CACHE_HOME=home+'/.cache')
            if args.seed_profile:
                target=Path(home)/'.config/win95lx/accessibility.json';target.parent.mkdir(parents=True);target.write_bytes(args.seed_profile.read_bytes())
            command=[sys.executable,str(Path(__file__).resolve()),'--owned-display',':'+number,'--owned-xvfb-pid',str(server.pid),'--output',str(args.output),'--resolution',args.resolution]
            if args.gi_extension_path:command+=['--gi-extension-path',str(args.gi_extension_path.resolve())]
            if args.startup_probe:command+=['--startup-probe',args.startup_probe]
            subprocess.run(command,env=env,check=True,timeout=90)
    finally:
        os.close(readfd)
        if writefd is not None:os.close(writefd)
        if server:
            server.terminate()
            try:server.communicate(timeout=3)
            except subprocess.TimeoutExpired:server.kill();server.communicate()
if __name__=='__main__':main()
