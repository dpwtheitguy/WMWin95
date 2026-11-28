#!/usr/bin/env python3
"""Real Theme UI + actual saver provider in a disposable guest display only."""
import ctypes,json,os,select,subprocess,sys,tempfile,time
from pathlib import Path
assert os.uname().nodename=='win95lx-dev'
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]
out=Path(sys.argv[1]);out.mkdir(exist_ok=False)
with tempfile.TemporaryDirectory(prefix='win95lx-theme-saver-')as tmp:
 folder=Path(tmp);r,w=os.pipe();server=subprocess.Popen(['/home/developer/win95lx-ui-qa.eK9O7BgJ/Xvfb','-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
 try:
  assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();os.close(r);assert display!=':0'
  os.environ.update(DISPLAY=display,GDK_BACKEND='x11',HOME=str(folder/'home'),XDG_CONFIG_HOME=str(folder/'config'),XDG_DATA_HOME=str(folder/'data'),XDG_CACHE_HOME=str(folder/'cache'));Path(os.environ['HOME']).mkdir()
  import gi;gi.require_foreign('cairo')
  from win95lx.shell.app import Shell,Gtk,Gdk
  from gi.repository import GLib
  from win95lx.apps.desktop_themes import DesktopThemesWindow,controller_for
  from check_menu_seams import flush_draws
  shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk);window=DesktopThemesWindow(shell);window.show_all();flush_draws(Gtk);controller=window.controller
  host=controller.providers['screensaver'].host;assert host.runtime is not None
  x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(display.encode());x.XFlush.argtypes=[ctypes.c_void_p];x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong;x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
  xt.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
  def key(name):
   code=x.XKeysymToKeycode(d,x.XStringToKeysym(name.encode()));xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0);x.XFlush(d);flush_draws(Gtk)
  def click(px,py):
   wx,wy=window.get_position();xt.XTestFakeMotionEvent(d,-1,wx+px,wy+py,0);xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);flush_draws(Gtk)
  def wait_for(predicate,limit=60):
   end=time.monotonic()+limit
   while time.monotonic()<end:
    flush_draws(Gtk)
    if predicate():return
    time.sleep(.01)
   raise AssertionError('Theme saver operation timed out')
  def capture(name):
   flush_draws(Gtk);Gdk.Display.get_default().sync();Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),0,0,800,600).savev(str(out/(name+'.png')),'png',[],[])
  def choose(name):
   click(115,42);key('Home')
   for _ in range(window.names.index(name)):key('Down')
   key('Return');assert controller.pending.name==name
   wait_for(lambda:not window.saver_preparing());flush_draws(Gtk)
  choose('Nature (high color)');assert 'screensaver'in controller.pending.components
  capture('nature-prepared');click(537,423);assert host.applied.saver=='plus95-nature';assert controller.applied.name=='Nature (high color)'
  fresh=controller_for(shell);assert fresh.applied==controller.applied
  capture('nature-applied');click(502,61);wait_for(lambda:host.runtime._process is not None,10)
  deadline=time.monotonic()+3
  while time.monotonic()<deadline:flush_draws(Gtk);time.sleep(.01)
  capture('theme-preview');key('Escape');wait_for(lambda:not host.busy,10);assert window.get_visible()
  before={path.name:path.read_bytes()for path in host.path.parent.glob('*.json')};saved_applied=host.applied;saved_pending=host.pending
  choose('Travel (high color)');provider=controller.providers['screensaver'];apply=provider.apply
  def fail_after(value):apply(value);raise RuntimeError('Injected post-saver failure')
  provider.apply=fail_after;closed=[]
  def close_error():
   dialog=next((item for item in Gtk.Window.list_toplevels()if isinstance(item,Gtk.Dialog)and item.get_visible()),None)
   if dialog is None:return True
   closed.append(True);key('Return');return False
  GLib.timeout_add(100,close_error);click(537,423);provider.apply=apply;assert closed
  assert host.applied==saved_applied and host.pending==saved_pending
  assert {path.name:path.read_bytes()for path in host.path.parent.glob('*.json')}==before
  wait_for(lambda:host.idle.preferences==saved_applied)
  capture('rollback-pending-retained')
  (out/'report.json').write_text(json.dumps({'display':display,'runtime':'actual Wine','checks':['physical theme selection warms original typed saver','physical Apply changes actual ScreenSaverHost preferences','independent theme reopen reconciles saver','native Themes ScreenSaver button launches original renderer','Escape preserves theme window','failure after actual saver apply restores all exact JSON bytes and Display pending state','scheduler generation converges to restored saver']},indent=2))
  window.destroy();shell.disconnect_by_func(Gtk.main_quit);shell.destroy();time.sleep(1)
 finally:server.terminate();server.wait(timeout=10)
