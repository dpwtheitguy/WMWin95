#!/usr/bin/env python3
"""Disposable owned-Xvfb Desktop Themes smoke test; no user's session changes."""
import argparse,json,os,select,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]

def child(a):
    import gi
    if a.gi_path:gi.__path__.append(a.gi_path)
    gi.require_foreign('cairo')
    import cairo
    from check_accessibility import owned_display_guard
    if not owned_display_guard(os.environ['DISPLAY'],a.pid):raise RuntimeError('Not the owned Xvfb.')
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.desktop_themes import DesktopThemesWindow,controller_for
    from check_menu_seams import flush_draws
    shell=Shell(a.assets)
    from dataclasses import replace
    shell.display_preferences=replace(shell.display_preferences,palette=1 if a.palette=='256' else 3)
    shell.show_all();flush_draws(Gtk)
    if 'X11' not in type(Gdk.Display.get_default()).__name__:raise RuntimeError('Not X11.')
    controller=controller_for(shell)
    started=time.perf_counter();window=DesktopThemesWindow(shell,controller);construct_ms=(time.perf_counter()-started)*1000;draws=[]
    window.area.connect('draw',lambda *_:draws.append(time.perf_counter()) if not draws else False)
    shell.accessory_windows['themes']=window
    window.connect('destroy',lambda *_:shell.accessory_windows.pop('themes',None))
    window.show_all();flush_draws(Gtk);first_draw_ms=(draws[0]-started)*1000
    a.output.mkdir(parents=True,exist_ok=False)
    def capture(name):
        flush_draws(Gtk);Gdk.Display.get_default().sync();wx,wy=window.get_position()
        image=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),wx,wy,*window.size)
        if image is None:raise RuntimeError('Actual applet framebuffer could not be captured.')
        image.savev(str(a.output/(name+'.png')),'png',[],[])
    capture('current')
    import ctypes
    x11=ctypes.CDLL('libX11.so.6');xtest=ctypes.CDLL('libXtst.so.6')
    x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p
    display=x11.XOpenDisplay(os.environ['DISPLAY'].encode())
    x11.XStringToKeysym.argtypes=[ctypes.c_char_p];x11.XStringToKeysym.restype=ctypes.c_ulong
    x11.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x11.XKeysymToKeycode.restype=ctypes.c_uint
    x11.XFlush.argtypes=[ctypes.c_void_p];x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
    x11.XSetInputFocus.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_ulong]
    from gi.repository import GdkX11
    x11.XSetInputFocus(display,window.get_window().get_xid(),1,0);x11.XFlush(display);flush_draws(Gtk)
    xtest.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    xtest.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    xtest.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    def key(name):
        code=x11.XKeysymToKeycode(display,x11.XStringToKeysym(name.encode()));assert code
        xtest.XTestFakeKeyEvent(display,code,1,0);xtest.XTestFakeKeyEvent(display,code,0,0);x11.XFlush(display);flush_draws(Gtk)
    def root_click(x,y):
        xtest.XTestFakeMotionEvent(display,-1,x,y,0)
        xtest.XTestFakeButtonEvent(display,1,1,0);xtest.XTestFakeButtonEvent(display,1,0,0);x11.XFlush(display);flush_draws(Gtk)
    def click(x,y):
        wx,wy=window.get_position();root_click(wx+x,wy+y)
    def chord(modifier,name):
        modifier_code=x11.XKeysymToKeycode(display,x11.XStringToKeysym(modifier.encode()))
        code=x11.XKeysymToKeycode(display,x11.XStringToKeysym(name.encode()))
        xtest.XTestFakeKeyEvent(display,modifier_code,1,0)
        xtest.XTestFakeKeyEvent(display,code,1,0);xtest.XTestFakeKeyEvent(display,code,0,0)
        xtest.XTestFakeKeyEvent(display,modifier_code,0,0);x11.XFlush(display);flush_draws(Gtk)
    def restore_task():
        shell.area.queue_draw();flush_draws(Gtk)
        x,y,w,h,_=next(hit for hit in shell.hits if hit[-1]==('accessory-task',window))
        root_click(x+w//2,y+h//2);assert window.get_visible()
        x11.XSetInputFocus(display,window.get_window().get_xid(),1,0);x11.XFlush(display);flush_draws(Gtk)
    # Disabled capability reasons are reachable using keyboard Help.
    from gi.repository import GLib
    help_checked=[]
    def close_help():
        dialogs=[item for item in Gtk.Window.list_toplevels() if isinstance(item,Gtk.Dialog) and item.get_visible()]
        if not dialogs:return True
        dialog=dialogs[-1];flush_draws(Gtk);Gdk.Display.get_default().sync()
        x,y=dialog.get_position();w,h=dialog.get_size()
        assert w<=shell.get_screen().get_width() and h<=shell.get_screen().get_height()-28,(w,h)
        Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),x,y,w,h).savev(str(a.output/'keyboard-help.png'),'png',[],[])
        help_checked.append(True);dialog.response(Gtk.ResponseType.OK);return False
    GLib.timeout_add(150,close_help);key('F1');assert help_checked
    x11.XSetInputFocus(display,window.get_window().get_xid(),1,0);x11.XFlush(display);flush_draws(Gtk)
    # Physical server input, not direct invocation of the DrawingArea handlers.
    assert window.focus_action==('theme',),(window.focus_action,window.focus_order())
    key('Home')
    for _ in range(window.names.index('Nature (high color)')):key('Down')
    assert controller.pending.name=='Nature (high color)'
    capture('theme-field-focused');click(482,240)
    assert 'pointers' not in controller.pending.components
    capture('pointer-checkbox-focused');key('space')
    assert 'pointers' in controller.pending.components
    capture('nature-pending')
    # Independent original VM captures; full controls, not implementation-derived baselines.
    from pixels import read
    comparisons=[]
    def compare(reference,actual,name,rect,gate=True):
        rw,rh,rp=read(ROOT/'private/themes-20261127'/reference)
        aw,ah,ap=read(a.output/(actual+'.png'));x,y,w,h=rect
        count=sum(rp[(62+y+dy)*rw+104+x+dx]!=ap[(y+dy)*aw+x+dx] for dy in range(h)for dx in range(w))
        comparisons.append({'name':name,'reference':reference,'actual':actual+'.png','rect':rect,'reference_origin':[104,62],'differing_pixels':count,'gate':gate})
        if gate:assert count==0,(name,count)
    compare('native-current-v2.png','current','focused complete Theme combo',(60,33,202,21))
    for index,y in enumerate((185,210,234,258,283,307,331,356)):
        compare('native-current-v2.png','current','disabled checked component '+str(index),(438,y,13,13))
    for name,y in (('sounds',210),('pointers',234),('wallpaper',258)):
        compare('native-nature-v2.png','nature-pending','enabled checked '+name,(438,y,13,13))
    compare('native-current-clean.png','current','full default current preview',(15,67,393,333),True)
    compare('native-nature-matched-loaded.png','nature-pending','Nature preview diagnostic only: native reference pointer overlaps sample; not clean acceptance',(15,67,393,333),False)
    (a.output/'native-comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    # Native EXE caption controls: Minimize must not start caption dragging.
    pending_before=controller.pending;focus_before=window.focus_action
    config=Path.home()/'.config/win95lx'
    files_before={p.name:p.read_bytes() for p in config.glob('*.json')}
    position_before=window.get_position()
    click(window.size[0]-31,11) # disabled Maximize; not a caption drag target
    assert window.get_visible() and window.get_position()==position_before and window.caption_drag is None
    # A near miss on release cancels the button, not pending editor focus.
    wx,wy=window.get_position()
    xtest.XTestFakeMotionEvent(display,-1,wx+window.size[0]-47,wy+11,0)
    xtest.XTestFakeButtonEvent(display,1,1,0);x11.XFlush(display);flush_draws(Gtk)
    xtest.XTestFakeMotionEvent(display,-1,wx+window.size[0]-90,wy+40,0)
    x11.XFlush(display);flush_draws(Gtk)
    xtest.XTestFakeButtonEvent(display,1,0,0);x11.XFlush(display);flush_draws(Gtk)
    assert window.get_visible() and window.focus_action==focus_before
    assert controller.pending==pending_before and window.get_position()==position_before
    click(window.size[0]-47,11)
    assert not window.get_visible() and controller.pending==pending_before
    assert controller.applied is None and window.caption_drag is None
    restore_task();assert controller.pending==pending_before and window.focus_action==focus_before,(controller.pending,pending_before,window.focus_action,focus_before)
    assert {p.name:p.read_bytes() for p in config.glob('*.json')}==files_before
    click(10,10);assert window.menu_popup is not None
    enabled={row[1][1]:row[2] for row in window.menu_popup.rows if row}
    assert enabled=={'restore':False,'move':True,'size':False,'minimize':True,'maximize':False,'close':True}
    capture('system-menu');key('Escape');assert window.menu_popup is None
    chord('Alt_L','space');assert window.menu_popup is not None
    key('m');assert window.operation is not None
    original=window.get_position();key('Right');assert window.get_position()!=original
    key('Escape');assert window.operation is None and window.get_position()==original
    chord('Alt_L','space');key('n');assert not window.get_visible()
    restore_task();assert controller.pending==pending_before
    assert {p.name:p.read_bytes() for p in config.glob('*.json')}==files_before
    # Palette changes while this window remains open resolve source profiles
    # lazily, retaining pending edits and making no Themes preference writes.
    before_palette=shell.display_preferences.palette
    shell.display_preferences=replace(shell.display_preferences,palette=3 if before_palette==1 else 1)
    window.area.queue_draw();flush_draws(Gtk)
    selected=controller.themes[pending_before.name]['wallpaper']['file']
    assert ('-vga6.bmp' in selected)==(shell.display_preferences.palette==1)
    assert controller.pending==pending_before
    shell.display_preferences=replace(shell.display_preferences,palette=before_palette)
    controller.preflight(controller.pending.components) # refresh without waiting for paint
    selected=controller.themes[pending_before.name]['wallpaper']['file']
    assert ('-vga6.bmp' in selected)==(before_palette==1)
    assert controller.pending==pending_before
    assert {p.name:p.read_bytes() for p in config.glob('*.json')}==files_before
    window.area.queue_draw();flush_draws(Gtk)
    # Real existing providers operate only on this disposable X server/HOME.
    started=time.perf_counter();click(538,423);apply_ms=(time.perf_counter()-started)*1000;capture('nature-applied')
    assert controller.applied==controller.pending
    assert shell.mouse_preferences.scheme=='Plus! / Nature (high color)'
    assert shell.wallpaper.name.startswith('theme-native-800x600-8-t07' if a.palette=='256' else 'theme-wallpaper-na_wall')
    assert shell.wallpaper_images.get(shell.wallpaper.name) is not None
    assert shell.wallpaper_surface(shell.wallpaper.name,shell.display_preferences.palette) is not None
    # Compare actual desktop background pixels, not merely saved preference names.
    desktop=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),0,0,*shell.get_size())
    desktop.savev(str(a.output/'desktop-applied.png'),'png',[],[])
    sample_x=(desktop.get_width()-800)//2+750;sample_y=(desktop.get_height()-600)//2+50
    start=desktop.get_rowstride()*sample_y+sample_x*desktop.get_n_channels()
    assert len(set(desktop.get_pixels()[start:start+40*desktop.get_n_channels()]))>3
    from win95lx.sound import preferences
    assert preferences().scheme=='Plus! / Nature (high color)'
    assert (Path.home()/'.config/win95lx/sounds.json').exists()
    saved=(Path.home()/'.config/win95lx/theme.json').read_bytes()
    previous_mouse=shell.mouse_preferences;previous_wallpaper=shell.wallpaper.name
    config=Path.home()/'.config/win95lx'
    old_files={name:(config/name).read_bytes() for name in ('mouse.json','sounds.json','wallpaper.json','theme.json')}
    sound_provider=controller.providers['sounds'];original_apply=sound_provider.apply
    def fail_after_apply(value):
        original_apply(value)
        raise RuntimeError('Injected failure after actual sound preference application.')
    sound_provider.apply=fail_after_apply;controller.select('Travel (high color)')
    try:
        try:controller.apply()
        except RuntimeError as error:assert 'Injected failure' in str(error)
        else:raise AssertionError('Failure was swallowed.')
    finally:sound_provider.apply=original_apply
    assert shell.mouse_preferences==previous_mouse and shell.wallpaper.name==previous_wallpaper
    assert {name:(config/name).read_bytes() for name in old_files}==old_files
    assert preferences().scheme=='Plus! / Nature (high color)'
    controller.select('Travel (high color)');controller.cancel()
    assert controller.pending==controller.applied
    assert (Path.home()/'.config/win95lx/theme.json').read_bytes()==saved
    # Reopening reconciles the real persisted providers without reapplying.
    reopened=controller_for(shell)
    assert reopened.applied==controller.applied, {name:(provider.export_current(),controller.themes[controller.applied.name].get(name)) for name,provider in controller.providers.items() if name in controller.applied.components}
    assert shell.wallpaper_images[shell.wallpaper.name].get_width()==800
    from dataclasses import replace
    shell.apply_mouse_preferences(replace(shell.mouse_preferences,speed=9))
    # A wallpaper-only selection must leave independent Mouse and Sound changes alone.
    before_mouse=shell.mouse_preferences;before_sounds=(config/'sounds.json').read_bytes()
    reopened.select('Nature (high color)',('wallpaper',));reopened.apply()
    assert shell.mouse_preferences==before_mouse and (config/'sounds.json').read_bytes()==before_sounds
    # Already-open independent property sheets must not overwrite theme edits later.
    shell.launch_accessory('mouse');mouse_window=shell.accessory_windows['mouse']
    mouse_window.controller.pending=replace(mouse_window.controller.pending,speed=8)
    preserved={name:(config/name).read_bytes() for name in old_files}
    controller.select('Travel (high color)')
    try:controller.apply()
    except ValueError as error:assert 'Close Mouse Properties' in str(error)
    else:raise AssertionError('Open Mouse edits were ignored.')
    assert {name:(config/name).read_bytes() for name in old_files}==preserved
    assert mouse_window.controller.pending.speed==8
    controller.select('Nature (high color)',('wallpaper',));controller.apply()
    assert mouse_window.controller.pending.speed==8
    mouse_window.destroy();flush_draws(Gtk)
    shell.launch_accessory('sounds');sounds_window=shell.accessory_windows['sounds']
    sounds_window.controller.pending=sounds_window.controller.pending.assign('.Default','sound-tada.wav')
    sound_pending=sounds_window.controller.pending
    preserved={name:(config/name).read_bytes() for name in old_files}
    controller.select('Travel (high color)')
    try:controller.apply()
    except ValueError as error:assert 'Sounds Properties' in str(error)
    else:raise AssertionError('Open Sounds edits were ignored.')
    assert {name:(config/name).read_bytes() for name in old_files}==preserved
    assert sounds_window.controller.pending==sound_pending
    controller.select('Nature (high color)',('wallpaper',));controller.apply()
    assert sounds_window.controller.pending==sound_pending
    sounds_window.destroy();flush_draws(Gtk)
    shell.open('display');display_window=shell.state.active
    previous_pending=shell.pending_wallpaper
    preserved={name:(config/name).read_bytes() for name in old_files}
    controller.select('Travel (high color)')
    try:controller.apply()
    except ValueError as error:assert 'Display Properties' in str(error)
    else:raise AssertionError('Open Display edits were ignored.')
    assert shell.pending_wallpaper==previous_pending
    assert {name:(config/name).read_bytes() for name in old_files}==preserved
    controller.select('Nature (high color)',('pointers',));controller.apply()
    assert shell.pending_wallpaper==previous_pending
    shell.state.windows.remove(display_window)
    # Every staged theme resolves through real providers and reopens correctly.
    # These are controller integration cases; physical controls are exercised above.
    catalog_checked=[]
    for theme_name in window.controller.themes:
        controller.select(theme_name);controller.apply()
        fresh=controller_for(shell)
        assert fresh.applied==controller.applied,(theme_name,fresh.applied,controller.applied)
        if controller.themes[theme_name]['wallpaper']['file']:assert shell.wallpaper_images.get(shell.wallpaper.name) is not None
        assert shell.mouse_preferences.scheme==controller.themes[theme_name]['pointers']
        assert preferences().scheme==controller.themes[theme_name]['sounds']
        catalog_checked.append(theme_name)
    assert len(catalog_checked)>=12
    # Restore the prior complete selection for the Cancel check.
    controller.select('Nature (high color)');controller.apply();saved=(config/'theme.json').read_bytes()
    window.present();x11.XSetInputFocus(display,window.get_window().get_xid(),1,0);x11.XFlush(display);flush_draws(Gtk)
    click(95,42);key('End');key('Up');key('Return')
    assert controller.pending.name==window.names[-2] and controller.applied.name=='Nature (high color)'
    # Popup consumes Enter; Cancel closes the parent without applying selection.
    click(454,423);assert (Path.home()/'.config/win95lx/theme.json').read_bytes()==saved
    shell.launch_accessory('themes');closed= shell.accessory_windows['themes']
    closed.controller.select('Travel (high color)')
    x11.XSetInputFocus(display,closed.get_window().get_xid(),1,0);x11.XFlush(display);flush_draws(Gtk)
    chord('Alt_L','space');key('c');assert 'themes' not in shell.accessory_windows
    assert (config/'theme.json').read_bytes()==saved
    shell.launch_accessory('themes');accelerator_window=shell.accessory_windows['themes']
    accelerator_window.controller.select('Travel (high color)')
    x11.XSetInputFocus(display,accelerator_window.get_window().get_xid(),1,0);x11.XFlush(display);flush_draws(Gtk)
    chord('Alt_L','space');chord('Alt_L','F4');assert 'themes' not in shell.accessory_windows
    assert (config/'theme.json').read_bytes()==saved
    x11.XCloseDisplay(display)
    (a.output/'report.json').write_text(json.dumps({'display':os.environ['DISPLAY'],'viewport':a.size,'palette':a.palette,'actual_framebuffer':True,'catalog_themes_applied_and_reopened':catalog_checked,'construct_ms':construct_ms,'first_draw_ms':first_draw_ms,'apply_ms':apply_ms,'checks':['native-sized render','physical Minimize/taskbar restore retains pending edits','disabled Maximize cannot drag','caption icon/Alt+Space fixed-size system menu, Move/Escape and Minimize/Close mnemonics','live palette flip updates preview and Apply source without discarding edits or writing files','physical F1 capability Help fits the viewport','current preview and named native control regions exact','actual desktop framebuffer changes immediately','all12 actual-provider theme apply and reopen','open Mouse/Display conflict leaves pending edits/files untouched while unselected components remain allowed','independent wallpaper-only apply preserves Mouse/Sounds' ,'physical Tab/Home/Down theme selection','physical pointer checkbox toggle and Space recheck','pending preview','physical pointer Apply','real wallpaper model','existing pointer scheme applied','sound mapping loaded through runtime provider','failure after real sound application restores wallpaper/pointer/sound and all four exact preference files','physical popup End/Enter then pointer Cancel retains applied selection'],'pixel_acceptance':'named gated regions only; selected theme preview remains nonzero'},indent=2)+'\n')
    window.destroy();shell.disconnect_by_func(Gtk.main_quit);shell.destroy();flush_draws(Gtk)

def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--assets',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--size',default='800x600');p.add_argument('--palette',choices=('256','truecolor'),default='256');p.add_argument('--gi-path',default='/tmp/win95lx-sprint-tools.uouVbC/usr/lib/python3/dist-packages/gi');a=p.parse_args()
    if a.child:return child(a)
    with tempfile.TemporaryDirectory(prefix='win95lx-themes-') as temp:
        folder=Path(temp);assets=folder/'assets';assets.mkdir()
        source=a.assets or ROOT/'private/shell-assets'
        if not source.is_dir():raise RuntimeError('Production asset bundle missing.')
        for file in source.iterdir():
            (assets/file.name).symlink_to(file.resolve())
        read,write=os.pipe();binary=shutil.which('Xvfb') or '/tmp/win95lx-sprint-tools.uouVbC/usr/bin/Xvfb'
        server=subprocess.Popen([binary,'-displayfd',str(write),'-screen','0',a.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);os.close(write)
        try:
            if not select.select([read],[],[],10)[0]:raise RuntimeError('Xvfb startup timeout')
            display=':'+os.read(read,32).decode().strip();env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None)
            env.update(DISPLAY=display,GDK_BACKEND='x11',HOME=str(folder/'home'),XDG_CONFIG_HOME=str(folder/'config'),XDG_CACHE_HOME=str(folder/'cache'),XDG_DATA_HOME=str(folder/'data'))
            Path(env['HOME']).mkdir()
            command=['/usr/bin/python3',__file__,'--child','--pid',str(server.pid),'--assets',str(assets),'--size',a.size,'--palette',a.palette,'--output',str(a.output.resolve()),'--gi-path',a.gi_path]
            subprocess.run(command,env=env,check=True,timeout=45)
        finally:
            os.close(read);server.terminate();server.wait(timeout=10)

if __name__=='__main__':main()
