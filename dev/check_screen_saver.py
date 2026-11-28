#!/usr/bin/env python3
"""Owned-display physical-input UI checks; fake runtime explicitly not Wine proof."""
import argparse,json,os,select,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]
def child(a):
    import gi;gi.__path__.append(a.gi_path);gi.require_foreign('cairo')
    from check_accessibility import owned_display_guard
    assert owned_display_guard(os.environ['DISPLAY'],a.pid)
    from win95lx.control_panel import screensaver_runtime as backend
    import threading
    class Process:
        def __init__(self):self.done=threading.Event()
        def wait(self):self.done.wait(10);return 0
        def poll(self):return 0 if self.done.is_set() else None
    class FakeRuntime:
        instances=[]
        def __init__(self,*args,**kwargs):self.process=None;self.calls=[];self.__class__.instances.append(self)
        def prepare(self,identity):self.calls.append(('prepare',identity));time.sleep(.08)
        def ready(self,identity):return True
        def availability(self,identity,mode):return True,''
        def launch(self,identity,mode='fullscreen',**kwargs):self.calls.append(('launch',identity,mode));self.process=Process();return self.process
        def stop(self):
            self.calls.append(('stop',))
            if self.process:self.process.done.set();self.process=None
        def close(self):self.stop()
    backend.WineScreenSaverRuntime=FakeRuntime
    from win95lx.shell.app import Shell,Gtk,Gdk
    from check_menu_seams import flush_draws
    shell=Shell(a.assets);shell.show_all();flush_draws(Gtk);shell.open('display');shell.display_tab='screensaver';flush_draws(Gtk)
    from win95lx.apps.screensaver_host import host_for
    host=host_for(shell);host.daemon_running=lambda:False;host.owner_conflict=False;assert len(host.ids)>1
    a.output.mkdir(parents=True,exist_ok=False)
    def capture(name):
        shell.area.queue_draw();flush_draws(Gtk);Gdk.Display.get_default().sync();win=shell.state.active
        Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),win.x,win.y,win.width,win.height).savev(str(a.output/(name+'.png')),'png',[],[])
    capture('none')
    from dataclasses import replace
    # Match native capture state: None selected, Wait1 disabled, Apply enabled.
    host.pending=replace(host.pending,wait_minutes=1);capture('none-native-state');host.pending=host.applied
    from pixels import read
    from stage_command_button_assets import read_bmp
    rw,rh,reference=read_bmp(ROOT/'private/theme-customization-20261127/saver-ie4-native/STATE.BMP')
    aw,ah,actual=read(a.output/'none-native-state.png');assert(rw,rh)==(aw,ah)==(404,448)
    pixel_difference=sum(left!=right for left,right in zip(reference,actual));assert pixel_difference==0,pixel_difference
    (a.output/'pixel-diff.json').write_text(json.dumps({'profile':'ie4','state':'None focused,Wait1 disabled,Apply enabled','dimensions':[aw,ah],'differing_pixels':pixel_difference,'reference':'private/theme-customization-20261127/saver-ie4-native/STATE.BMP'},indent=2))
    import ctypes
    x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(os.environ['DISPLAY'].encode())
    x.XFlush.argtypes=[ctypes.c_void_p];x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong;x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
    xt.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    def key(name):
        code=x.XKeysymToKeycode(d,x.XStringToKeysym(name.encode()));xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0);x.XFlush(d);flush_draws(Gtk)
    def click(px,py):
        win=shell.state.active;xt.XTestFakeMotionEvent(d,-1,win.x+px,win.y+py,0);xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);flush_draws(Gtk)
    def wait_for(predicate):
        end=time.monotonic()+3
        while time.monotonic()<end:
            flush_draws(Gtk)
            if predicate():return
            time.sleep(.01)
        raise AssertionError('UI worker did not settle')
    click(115,271);key('Down');key('Return');assert host.pending.saver
    wait_for(lambda:not host.busy);capture('selected')
    for _ in range(5):click(309,294)
    assert host.pending.wait_minutes==15,host.pending.wait_minutes
    click(356,426);wait_for(lambda:host.applied==host.pending)
    assert json.loads(host.path.read_text())['wait_minutes']==15
    click(325,270);wait_for(lambda:host.runtime.process is not None)
    # Simulate switching tab while a saver process is waiting. UI remains live;
    # stopping happens off GTK and releases its owned child.
    click(45,40);assert shell.display_tab=='background';wait_for(lambda:host.runtime.process is None)
    click(112,40);assert shell.display_tab=='screensaver'
    click(248,270);wait_for(lambda:host.runtime.process is not None)
    host.runtime.process.done.set();wait_for(lambda:not host.busy);assert host.runtime.process is None
    capture('settings-returned')
    saved=host.path.read_bytes();click(285,300);key('2');key('0');assert host.pending.wait_minutes==20 and host.dirty
    from win95lx.apps.screensaver_ownership import OwnershipState
    from gi.repository import GLib
    previous_ownership=host.ownership.state;host.ownership.state=OwnershipState(error='The current screen saver service could not be coordinated. Your settings have not been changed.')
    native_errors=[]
    def close_owner_error():
        dialog=next((item for item in Gtk.Window.list_toplevels()if isinstance(item,Gtk.Dialog)and item.get_visible()),None)
        if dialog is None:return True
        assert not dialog.get_decorated()
        px,py=dialog.get_position();pw,ph=dialog.get_size();assert pw<=shell.get_screen().get_width()
        Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),px,py,pw,ph).savev(str(a.output/'owner-failure-native.png'),'png',[],[])
        native_errors.append(True);key('Return');return False
    GLib.timeout_add(100,close_owner_error);click(356,426);assert native_errors and host.path.read_bytes()==saved and host.pending.wait_minutes==20
    host.ownership.state=previous_ownership
    click(276,426);assert not any(w.kind=='display' for w in shell.state.windows);assert host.path.read_bytes()==saved
    shell.open('display');shell.display_tab='screensaver';flush_draws(Gtk);assert host.pending==host.applied
    capture('reopened')
    result={'runtime':'explicit fake runtime; no compatibility claim','viewport':a.size,'physical_input':['popup pointer/keyboard selection','wait spinner pointer increments','Apply persists selected saver and15minute wait','Preview does not block tab switch; tab departure stops owned process','Settings natural exit releases runtime','two-digit Wait keyboard input20','ownershipfailure showsnativeerror andpreservesapplied/pending/files','Cancel does not persist pending changes','reopen restores applied selection andwait'],'calls':host.runtime.calls}
    (a.output/'report.json').write_text(json.dumps(result,indent=2))
    shell.disconnect_by_func(Gtk.main_quit);shell.destroy();flush_draws(Gtk)
def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--assets',type=Path,default=ROOT/'private/shell-assets');p.add_argument('--output',type=Path,required=True);p.add_argument('--size',default='800x600');p.add_argument('--gi-path',default='/tmp/win95lx-sprint-tools.uouVbC/usr/lib/python3/dist-packages/gi');a=p.parse_args()
    if a.child:return child(a)
    with tempfile.TemporaryDirectory(prefix='win95lx-saver-ui-')as tmp:
        folder=Path(tmp);assets=folder/'assets';assets.mkdir()
        for source in a.assets.iterdir():(assets/source.name).symlink_to(source.resolve())
        if not(assets/'screensavers').exists():
            from stage_screensaver_assets import stage
            stage(assets/'screensavers')
        r,w=os.pipe();binary=shutil.which('Xvfb')or'/tmp/win95lx-sprint-tools.uouVbC/usr/bin/Xvfb';server=subprocess.Popen([binary,'-displayfd',str(w),'-screen','0',a.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
        try:
            assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None);env.update(DISPLAY=display,GDK_BACKEND='x11',HOME=str(folder/'home'),XDG_CONFIG_HOME=str(folder/'config'),XDG_CACHE_HOME=str(folder/'cache'),XDG_DATA_HOME=str(folder/'data'));Path(env['HOME']).mkdir()
            subprocess.run(['/usr/bin/python3',__file__,'--child','--pid',str(server.pid),'--assets',str(assets),'--output',str(a.output.resolve()),'--size',a.size,'--gi-path',a.gi_path],env=env,check=True,timeout=40)
        finally:os.close(r);server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()
