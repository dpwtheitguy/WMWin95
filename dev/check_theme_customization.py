#!/usr/bin/env python3
"""Owned-Xvfb Themes CRUD/input and 30 actual-provider composition checks.

Composition rows are provider integration, explicitly separate from XTest input.
"""
import argparse,json,os,select,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]

def child(a):
    import gi
    gi.__path__.append(a.gi_path);gi.require_foreign('cairo')
    from check_accessibility import owned_display_guard
    assert owned_display_guard(os.environ['DISPLAY'],a.pid)
    from win95lx.shell.app import Shell,Gtk,Gdk
    from gi.repository import GLib
    from check_menu_seams import flush_draws
    from win95lx.apps.desktop_themes import DesktopThemesWindow,controller_for
    from win95lx.apps.theme_dialogs import ThemeFileDialog,ThemeQuestion
    from win95lx.control_panel.theme_preferences import COMPONENTS
    shell=Shell(a.assets);shell.show_all();flush_draws(Gtk)
    controller=controller_for(shell);window=DesktopThemesWindow(shell,controller);window.show_all();flush_draws(Gtk)
    a.output.mkdir(parents=True,exist_ok=False)
    def capture(widget,name):
        flush_draws(Gtk);Gdk.Display.get_default().sync();x,y=widget.get_position();w,h=widget.get_size()
        Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),x,y,w,h).savev(str(a.output/(name+'.png')),'png',[],[])
    capture(window,'current')
    # Verify measured dialog profiles in the actual GTK framebuffer.
    controller.store.directory.mkdir(parents=True,exist_ok=True)
    dialog=ThemeFileDialog(window,controller.store.directory,saving=True,store=controller.store)
    dialog.show_all();flush_draws(Gtk);capture(dialog,'save-theme')
    assert tuple(dialog.get_size())==(426,264),dialog.get_size()
    dialog.destroy()
    question=ThemeQuestion(window,"Are you sure you want to delete the 'W95UATCurrent' theme?")
    question.show_all();flush_draws(Gtk);capture(question,'delete-theme')
    assert tuple(question.get_size())==(366,119),question.get_size();question.destroy()
    # Physical XTest button enters modal SaveAs; timeout drives its shared entry
    # and Save with actual X key events rather than calling product handlers.
    import ctypes
    x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6')
    x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(os.environ['DISPLAY'].encode())
    x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong
    x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
    x.XFlush.argtypes=[ctypes.c_void_p]
    xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
    xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    xt.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    def key(name):
        code=x.XKeysymToKeycode(d,x.XStringToKeysym(name.encode()));assert code
        xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0);x.XFlush(d)
    def click(widget,px,py):
        wx,wy=widget.get_position();py+=getattr(widget,'body_offset',0) if py>=22 else 0;xt.XTestFakeMotionEvent(d,-1,wx+px,wy+py,0)
        xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d)
    actual=[]
    def save_modal():
        modal=next((w for w in Gtk.Window.list_toplevels() if isinstance(w,ThemeFileDialog) and w.get_visible()),None)
        if modal is None:return True
        for ch in 'uatphysical':key(ch)
        GLib.timeout_add(120,lambda:(click(modal,370,212),False)[1]);return False
    GLib.timeout_add(100,save_modal);click(window,303,42);flush_draws(Gtk)
    assert controller.pending and controller.pending.name=='uatphysical',controller.pending
    assert controller.edited and controller.applied is None
    actual.append('physical SaveAs click / filename keyboard / Save click creates pending definition')
    capture(window,'saved-pending')
    controller.cancel();assert controller.store.exists('uatphysical')
    controller.select('uatphysical');controller.apply()
    fresh=controller_for(shell);assert fresh.applied and fresh.applied.name=='uatphysical'
    actual.append('saved custom theme Apply and independent reopen')
    # Thirty distinct valid combinations across all seven actual providers.
    from copy import deepcopy
    rows=[];originals=dict(controller.store.builtins);assert originals
    baseline=controller.capture_current()
    for number in range(30):
        preset=list(originals)[number%len(originals)]
        value=deepcopy(baseline);value.update(deepcopy(originals[preset]))
        value['colors']['Background']=[number*7%256,128,128]
        value['metrics']['caption_height']=18+number%2
        value['fonts']['icon']['weight']=400 if number%2 else 700
        builtin='UAT combination source'
        controller.store.builtins[builtin]=value;controller.refresh_catalog()
        selected=tuple(c for index,c in enumerate(COMPONENTS) if ((number+1)*5%255 or 255)&(1<<index))
        selected=tuple(c for c in selected if c in controller.themes[builtin] and c in controller.providers)
        assert selected
        before={c:controller.providers[c].export_current() for c in controller.providers}
        controller.select(builtin,selected);controller.apply()
        current={c:controller.providers[c].export_current() for c in controller.providers}
        for c in current:
            if c not in selected:assert current[c]==before[c],(number,c)
            elif c=='wallpaper':
                for field in ('file','mode'):assert current[c][field]==value[c][field],(number,c,field)
            elif c=='pointers':assert current[c]['scheme']==(value[c]['scheme'] if isinstance(value[c],dict) else value[c]),(number,c)
            elif c=='sounds':assert current[c]['scheme']==(value[c]['scheme'] if isinstance(value[c],dict) else value[c]),(number,c)
            else:assert current[c]==value[c],(number,c)
        name='Composition '+str(number+1);controller.save_current(name)
        assert set(controller.themes[name])>=set(current)
        controller.select(name);controller.apply()
        reopened=controller_for(shell);assert reopened.applied and reopened.applied.name==name,(number,reopened.applied)
        for c in current:assert reopened.providers[c].export_current()==current[c],(number,c)
        rows.append({'id':number+1,'preset':preset,'components':selected,'save_apply_reopen':True})
    # Actual modal No/Yes dismissal, definition-only deletion, and reusability.
    window.refresh_names();window.show_all();flush_draws(Gtk)
    deleting=controller.pending.name
    before={c:provider.export_current() for c,provider in controller.providers.items()}
    def answer(letter):
        def respond():
            modal=next((w for w in Gtk.Window.list_toplevels() if isinstance(w,ThemeQuestion) and w.get_visible()),None)
            if modal is None:return True
            key(letter);return False
        GLib.timeout_add(100,respond)
    answer('n');click(window,375,42);flush_draws(Gtk)
    assert controller.store.exists(deleting)
    actual.append('physical Delete / No retains definition')
    answer('y');click(window,375,42);flush_draws(Gtk)
    assert not controller.store.exists(deleting)
    assert {c:provider.export_current() for c,provider in controller.providers.items()}==before
    actual.append('physical Delete / Yes removes definition only; all seven live components unchanged')
    capture(window,'customization-final')
    (a.output/'report.json').write_text(json.dumps({'viewport':a.size,'actual_input_checks':actual,'provider_composition_checks':rows,'native_dialog_sizes':{'save':[426,264],'delete':[366,119]},'pixel_acceptance':'geometry only; full-dialog pixel diff pending'},indent=2))
    window.destroy();shell.disconnect_by_func(Gtk.main_quit);shell.destroy()

def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--assets',type=Path,default=ROOT/'private/shell-assets');p.add_argument('--output',type=Path,required=True);p.add_argument('--size',default='800x600');p.add_argument('--gi-path',default='/tmp/win95lx-sprint-tools.uouVbC/usr/lib/python3/dist-packages/gi');a=p.parse_args()
    if a.child:return child(a)
    with tempfile.TemporaryDirectory(prefix='win95lx-theme-custom-') as tmp:
        folder=Path(tmp);read,write=os.pipe();binary=shutil.which('Xvfb')or'/tmp/win95lx-sprint-tools.uouVbC/usr/bin/Xvfb'
        server=subprocess.Popen([binary,'-displayfd',str(write),'-screen','0',a.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(write,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);os.close(write)
        try:
            assert select.select([read],[],[],10)[0];display=':'+os.read(read,32).decode().strip();env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None)
            env.update(DISPLAY=display,GDK_BACKEND='x11',HOME=str(folder/'home'),XDG_CONFIG_HOME=str(folder/'config'),XDG_CACHE_HOME=str(folder/'cache'),XDG_DATA_HOME=str(folder/'data'));Path(env['HOME']).mkdir()
            subprocess.run(['/usr/bin/python3',__file__,'--child','--pid',str(server.pid),'--assets',str(a.assets.resolve()),'--output',str(a.output.resolve()),'--size',a.size,'--gi-path',a.gi_path],env=env,check=True,timeout=60)
        finally:os.close(read);server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()
