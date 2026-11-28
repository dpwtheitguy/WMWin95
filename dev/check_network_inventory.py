#!/usr/bin/env python3
"""Owned-X11 delayed/deep Network inventory UAT; never configures networking."""
import argparse,ctypes as C,json,os,select,shutil,subprocess,sys,tempfile,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def child(a):
    import gi
    if a.gi_path:gi.__path__.append(a.gi_path)
    gi.require_foreign('cairo')
    from check_accessibility import owned_display_guard
    assert owned_display_guard(os.environ['DISPLAY'],a.pid)
    # Imported QA helpers may prepend the active checkout. Reassert the
    # requested immutable source before loading any application modules.
    sys.path.insert(0,str(a.source.resolve()))
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.network import NetworkWindow,TCPIPWindow
    source_file=Path(sys.modules[NetworkWindow.__module__].__file__).resolve()
    assert source_file.is_relative_to(a.source.resolve()),source_file
    from win95lx.control_panel.network_preferences import NetworkState,Connection,IPv4Config,NetworkError
    from check_menu_seams import flush_draws
    x=C.CDLL('libX11.so.6');xt=C.CDLL('libXtst.so.6')
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
    x.XFlush.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
    x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_uint
    x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
    xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
    xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
    xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
    d=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert d
    from gi.repository import GdkX11,GLib
    def focus(w):x.XSetInputFocus(d,w.get_window().get_xid(),1,0);x.XFlush(d);flush_draws(Gtk)
    def key(name):
        code=x.XKeysymToKeycode(d,Gdk.keyval_from_name(name));assert code
        xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0);x.XFlush(d);flush_draws(Gtk)
    def pointer(w,px,py,button=None,down=None):
        wx,wy=w.get_position();xt.XTestFakeMotionEvent(d,0,wx+px,wy+py,0)
        if button is not None:xt.XTestFakeButtonEvent(d,button,int(down),0)
        x.XFlush(d);flush_draws(Gtk)
    def click(w,px,py,button=1):pointer(w,px,py,button,True);pointer(w,px,py,button,False)
    def capture(w,name):
        flush_draws(Gtk);pix=Gdk.pixbuf_get_from_window(w.get_window(),0,0,*w.size);assert pix
        pix.savev(str(a.output/(name+'.png')),'png',[],[])
    def wait(w):
        until=time.monotonic()+3
        while w.loading and time.monotonic()<until:flush_draws(Gtk);time.sleep(.01)
        assert not w.loading
    class Backend:
        def __init__(self,fail=False):
            self.gate=threading.Event();self.fail=fail;self.calls=[];self.read_threads=[]
            self.value=NetworkState('win95lx-dev',tuple(Connection(f'00000000-0000-4000-8000-{i:012d}',('Adapter '+str(i))if i<11 else'Long adapter '+'Z'*150,'w95uat'+str(i),'dummy',IPv4Config())for i in range(12)))
        def preferences(self):
            self.read_threads.append(threading.get_ident());self.gate.wait(5)
            if self.fail:raise NetworkError('The network service is unavailable.')
            return self.value
        def apply(self,pending,baseline):self.calls.append((pending,baseline));self.value=pending
        def restore(self,value):self.value=value
    a.output.mkdir(parents=True,exist_ok=False);checks=[];windows=[]
    shell=Shell(a.assets);shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk)
    try:
        backend=Backend();started=time.perf_counter();window=NetworkWindow(shell,backend);construct_ms=(time.perf_counter()-started)*1000;windows.append(window)
        (a.output/'construction.json').write_text(json.dumps({'construct_ms':construct_ms,'inventory_gate_open':backend.gate.is_set(),'source':str(source_file)})+'\n')
        assert construct_ms<250,'Constructor waited for the deliberately blocked inventory.'
        window.show_all();focus(window);capture(window,'loading')
        assert window.loading and not any(action==('ok',)for _,action in window.hits)
        beats=[];token=GLib.timeout_add(15,lambda:(beats.append(time.monotonic())or True));flush_draws(Gtk);GLib.source_remove(token);assert beats
        key('Escape');assert window.closed and not window.get_visible()and not backend.calls
        backend.gate.set();flush_draws(Gtk);assert window.closed and not backend.calls
        checks.append('Blocked read runs off GTK thread, timer still dispatches; physical Escape destroys loading window; late callback never mutates UI/settings')
        backend=Backend();backend.gate.set();window=NetworkWindow(shell,backend);windows.append(window);window.show_all();focus(window);wait(window);capture(window,'deep-initial')
        assert all(t!=threading.get_ident()for t in backend.read_threads)
        key('End');assert window.selected==11 and window.list_top==7
        assert any(action==('connection',11)for _,action in window.hits);capture(window,'deep-last-selected')
        key('Home');assert window.selected==0 and window.list_top==0
        key('Page_Down');assert window.selected==5 and window.list_top==1
        key('End');key('Up');assert window.selected==10 and window.list_top==7
        checks.append('Physical End/Home/PageDown/Up select and reveal every connection, including last of12; long labels clipped inside viewport')
        key('Home');pointer(window,328,113,1,True);pointer(window,328,171);pointer(window,328,171,1,False)
        assert window.list_top==7 and window.selected==0,(window.list_top,window.selected)
        capture(window,'thumb-end-preserves-selection')
        key('Home');click(window,328,180);assert window.list_top==1 and window.selected==0
        pointer(window,110,120);click(window,110,120,5);assert window.list_top==2 and window.selected==0
        checks.append('Actual scrollbar thumb drag, arrow and wheel reach overflow rows while preserving selected connection')
        key('End');click(window,285,221);children=[w for w in Gtk.Window.list_toplevels()if isinstance(w,TCPIPWindow)and w.get_visible()]
        assert len(children)==1 and children[0].connection.uuid==backend.value.connections[-1].uuid
        focus(children[0]);key('Escape');assert not children[0].get_visible();focus(window);key('Escape');assert window.closed and not backend.calls
        checks.append('Last adapter Properties opens correct typed profile; physical child/parent Cancel writes no service settings')
        failed=Backend(True);failed.gate.set();window=NetworkWindow(shell,failed);windows.append(window);window.show_all();focus(window);wait(window);capture(window,'discovery-failed')
        assert window.load_error and not any(action==('ok',)for _,action in window.hits)
        key('Return');assert window.get_visible()and not failed.calls
        key('Escape');assert window.closed
        checks.append('Discovery failure shows explicit native-looking state, disabled OK and no Enter fallback mutation; Escape remains usable')
        report={'checks':checks,'construct_ms':construct_ms,'viewport':a.size,'actual_framebuffer':True,'real_pointer_keyboard':True,'failed':0,'scope':'Disposable fake discovery and profile fixtures; no network mutation/policy/native whole-page pixel acceptance.'}
        (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:
        for w in windows:
            if not w.closed:w.destroy()
        shell.destroy();x.XCloseDisplay(d)

def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--source',type=Path,default=ROOT/'src');p.add_argument('--size',default='800x600');p.add_argument('--assets',type=Path,default=ROOT/'private/shell-assets');p.add_argument('--output',type=Path,required=True);p.add_argument('--gi-path',default='/tmp/win95lx-sprint-tools.uouVbC/usr/lib/python3/dist-packages/gi');a=p.parse_args()
    sys.path.insert(0,str(a.source))
    if a.child:return child(a)
    with tempfile.TemporaryDirectory(prefix='w95uat-network-inventory-')as temporary:
        t=Path(temporary);r,w=os.pipe();server=subprocess.Popen([shutil.which('Xvfb')or'/tmp/win95lx-sprint-tools.uouVbC/usr/bin/Xvfb','-displayfd',str(w),'-screen','0',a.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);os.close(w)
        try:
            if not select.select([r],[],[],10)[0]:raise RuntimeError('Owned display did not start.')
            display=':'+os.read(r,32).decode().strip();env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None)
            for name in('HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME'):
                folder=t/name;folder.mkdir();env[name]=str(folder)
            env.update(DISPLAY=display,GDK_BACKEND='x11')
            subprocess.run([sys.executable,__file__,'--child','--pid',str(server.pid),'--source',str(a.source.resolve()),'--size',a.size,'--assets',str(a.assets.resolve()),'--output',str(a.output.resolve()),'--gi-path',a.gi_path],env=env,check=True,timeout=35)
        finally:os.close(r);server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
