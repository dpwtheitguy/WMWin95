#!/usr/bin/env python3
"""Real Wine plus new Display controls, in a disposable guest-owned Xvfb only."""
import json,os,select,subprocess,sys,tempfile,time
from pathlib import Path
assert os.uname().nodename=='win95lx-dev','Run only in the development guest.'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]
output=Path(sys.argv[1]);output.mkdir(exist_ok=False)
tmp=tempfile.TemporaryDirectory(prefix='win95lx-saver-ui-real-');folder=Path(tmp.name)
r,w=os.pipe();xvfb=Path('/home/developer/win95lx-ui-qa.eK9O7BgJ/Xvfb')
server=subprocess.Popen([str(xvfb),'-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();os.close(r);assert display!=':0'
os.environ.update(DISPLAY=display,GDK_BACKEND='x11',HOME=str(folder/'home'),XDG_CONFIG_HOME=str(folder/'config'),XDG_DATA_HOME=str(folder/'data'),XDG_CACHE_HOME=str(folder/'cache'));Path(os.environ['HOME']).mkdir()
daemon=None;observer=None;native_prefs=None
try:
 if '--existing-owner' in sys.argv:
  subprocess.run(['xfconf-query','-c','xfce4-screensaver','-p','/lock/enabled','-n','-t','bool','-s','false'],check=True,stdout=subprocess.DEVNULL)
  daemon=subprocess.Popen(['/usr/bin/xfce4-screensaver','--debug'],stdout=(output/'xfce-daemon.log').open('w'),stderr=subprocess.STDOUT)
  from win95lx.apps.screensaver_ownership import SessionBus
  observer=SessionBus(os.environ['DBUS_SESSION_BUS_ADDRESS']);deadline=time.monotonic()+5
  while observer.owner()is None and time.monotonic()<deadline:time.sleep(.05)
  assert observer.owner()is not None
  native_prefs=subprocess.check_output(['xfconf-query','-c','xfce4-screensaver','-lv'])
 import gi;gi.require_foreign('cairo')
 from win95lx.shell.app import Shell,Gtk,Gdk
 from check_menu_seams import flush_draws
 from gi.repository import GLib
 shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk);shell.open('display');shell.display_tab='screensaver';flush_draws(Gtk)
 from win95lx.apps.screensaver_host import host_for
 host=host_for(shell);assert host.runtime is not None
 heartbeat=[];GLib.timeout_add(20,lambda:(heartbeat.append(time.monotonic()),True)[1])
 import ctypes
 x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(display.encode());x.XFlush.argtypes=[ctypes.c_void_p]
 x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong;x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
 xt.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
 def key(name):
  code=x.XKeysymToKeycode(d,x.XStringToKeysym(name.encode()));xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0);x.XFlush(d);flush_draws(Gtk)
 def click(px,py):
  win=shell.state.active;xt.XTestFakeMotionEvent(d,-1,win.x+px,win.y+py,0);xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);flush_draws(Gtk)
 def wait_for(predicate,limit=60):
  end=time.monotonic()+limit
  while time.monotonic()<end:
   flush_draws(Gtk)
   if predicate():return
   time.sleep(.01)
  raise AssertionError('Timed out: '+host.status+' '+host.error)
 def capture(name):
  flush_draws(Gtk);Gdk.Display.get_default().sync();Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),0,0,800,600).savev(str(output/(name+'.png')),'png',[],[])
 identity='plus95-nature';index=host.ids.index(identity);click(114,270);key('Home')
 for _ in range(index):key('Down')
 start=time.monotonic();key('Return');assert host.pending.saver==identity
 wait_for(lambda:not host.busy);prepare_ms=(time.monotonic()-start)*1000;assert not host.error,host.error
 capture('selected-ready');click(355,426);assert host.applied==host.pending and host.applied.saver==identity
 assert json.loads(host.path.read_text())['saver']==identity
 start=time.monotonic();click(326,270);wait_for(lambda:host.runtime._process is not None,10)
 deadline=time.monotonic()+3
 while time.monotonic()<deadline:flush_draws(Gtk);time.sleep(.01)
 capture('nature-fullscreen-3s');assert host.runtime._process.poll() is None
 key('Escape');wait_for(lambda:not host.busy,10);assert host.runtime._process is None
 stop_ms=(time.monotonic()-deadline)*1000;capture('preview-dismissed')
 old_focus=host.focus
 x.XGetInputFocus.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_int)];focus=ctypes.c_ulong();revert=ctypes.c_int();x.XGetInputFocus(d,ctypes.byref(focus),ctypes.byref(revert))
 from gi.repository import GdkX11
 (output/'focus-before.json').write_text(json.dumps({'focus':focus.value,'shell':shell.get_window().get_xid()}))
 key('Tab')
 assert host.focus!=old_focus,'Keyboard focus was not restored after preview'
 # One genuine minute of server idle; no fabricated timer value.
 click(285,300);key('1');click(355,426);assert host.applied.wait_minutes==1
 idle_start=time.monotonic();wait_for(lambda:host.idle_runtime._process is not None,70)
 idle_elapsed=time.monotonic()-idle_start
 deadline=time.monotonic()+3
 while time.monotonic()<deadline:flush_draws(Gtk);time.sleep(.01)
 capture('nature-idle-activation')
 key('Escape');wait_for(lambda:host.idle_runtime._process is None and host.idle_runtime._lease is None,10)
 assert host.idle_runtime._lease is None
 assert any(w.kind=='display'for w in shell.state.windows),'Idle dismissal closed its owner'
 capture('idle-dismissed')
 host.cancel();assert host.pending==host.applied
 result={'runtime':'actual guest Wine','display':display,'saver':identity,'physical_input':['catalog popup keyboard selection','Apply persists real selection','Preview launches original Nature renderer','Escape dismisses andownedruntimecleansup','keyboardfocusrestored','genuine60secondserveridleactivatesselectedsaver','idleEscape releasesprefixlease'],'idle_activation_seconds':idle_elapsed,'prepare_ms':prepare_ms,'dismiss_cleanup_ms':stop_ms,'gtk_heartbeat_count':len(heartbeat),'max_gtk_heartbeat_gap_ms':max((b-a)*1000 for a,b in zip(heartbeat,heartbeat[1:])) if len(heartbeat)>1 else None,'snapshot':'disposableHOMEandownedXvfb; userdesktopuntouched'}
 (output/'report.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
 if observer:
  assert host.ownership.state.mode=='Inhibit'
  assert subprocess.check_output(['xfconf-query','-c','xfce4-screensaver','-lv'])==native_prefs
  result['existing_daemon']='running,scopedInhibit,configunchanged'
  (output/'report.json').write_text(json.dumps(result,indent=2))
 host.close();shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
 # Let bounded background cleanup finish before destroying the owned display.
 time.sleep(1)
 if observer:
  assert not observer.inhibitors(observer.owner()[0]);observer.close();observer=None
finally:
 if observer:observer.close()
 if daemon and daemon.poll()is None:daemon.terminate();daemon.wait(timeout=5)
 server.terminate();server.wait(timeout=10);tmp.cleanup()
