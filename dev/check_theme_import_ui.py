#!/usr/bin/env python3
"""Physical Open/Cancel/Apply of a legacy file in an owned Xvfb/private HOME."""
import argparse,ctypes,hashlib,json,os,re,select,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]
def child(a):
 import gi
 if a.gi_path:gi.__path__.append(a.gi_path)
 gi.require_foreign('cairo')
 from check_accessibility import owned_display_guard
 assert owned_display_guard(os.environ['DISPLAY'],a.pid)
 from win95lx.shell.app import Shell,Gtk,Gdk
 from gi.repository import GLib
 from win95lx.apps.desktop_themes import DesktopThemesWindow,controller_for
 from win95lx.apps.theme_dialogs import ThemeFileDialog
 from check_menu_seams import flush_draws
 shell=Shell(a.assets);shell.show_all();flush_draws(Gtk);window=DesktopThemesWindow(shell);window.show_all();flush_draws(Gtk)
 a.output.mkdir(parents=True,exist_ok=False);definition=a.fixture/'Original.theme'
 originals={path.name:hashlib.sha256(path.read_bytes()).hexdigest()for path in a.fixture.iterdir()if path.is_file()}
 config=Path.home()/'.config/win95lx';before={str(path.relative_to(config)):path.read_bytes()for path in config.glob('*.json')}
 input_settings=(shell.mouse_preferences.speed,shell.mouse_preferences.left_handed,shell.mouse_preferences.double_click_ms)
 x=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(os.environ['DISPLAY'].encode());x.XFlush.argtypes=[ctypes.c_void_p]
 x.XStringToKeysym.argtypes=[ctypes.c_char_p];x.XStringToKeysym.restype=ctypes.c_ulong;x.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];x.XKeysymToKeycode.restype=ctypes.c_uint
 xt.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
 def key(name,down=None):
  code=x.XKeysymToKeycode(d,x.XStringToKeysym(name.encode()));assert code,name
  if down is None:xt.XTestFakeKeyEvent(d,code,1,0);xt.XTestFakeKeyEvent(d,code,0,0)
  else:xt.XTestFakeKeyEvent(d,code,int(down),0)
  x.XFlush(d);flush_draws(Gtk)
 def type_text(text):
  for char in text:
   shift=char.isupper()or char=='_';name={'.':'period','/':'slash','-':'minus','_':'minus',' ':'space'}.get(char,char.lower())
   if shift:key('Shift_L',True)
   key(name)
   if shift:key('Shift_L',False)
 def click(widget,px,py):
  left,top=widget.get_position();offset=getattr(widget,'body_offset',0)if py>=22 else 0
  xt.XTestFakeMotionEvent(d,-1,left+px,top+py+offset,0);xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);flush_draws(Gtk)
 def wait_for(predicate):
  end=time.monotonic()+60
  while time.monotonic()<end:
   flush_draws(Gtk)
   if predicate():return
   time.sleep(.01)
  raise AssertionError('Legacy import did not settle')
 def capture(name):
  flush_draws(Gtk);Gdk.Display.get_default().sync();left,top=window.get_position();width,height=window.get_size();Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),left,top,width,height).savev(str(a.output/(name+'.png')),'png',[],[])
 def open_original(path=definition,expect=True):
  def fill():
   dialog=next((item for item in Gtk.Window.list_toplevels()if isinstance(item,ThemeFileDialog)and item.get_visible()),None)
   if dialog is None:return True
   type_text(str(path));GLib.timeout_add(100,lambda:(click(dialog,373,212),False)[1]);return False
  GLib.timeout_add(100,fill);click(window,110,42);key('End');key('Return')
  if expect:
   assert window.controller.pending.name=='Original';wait_for(lambda:not window.saver_preparing())
 errors=[]
 def close_import_error():
  dialog=next((item for item in Gtk.Window.list_toplevels()if isinstance(item,Gtk.Dialog)and not isinstance(item,ThemeFileDialog)and item.get_visible()),None)
  if dialog is None:return True
  left,top=dialog.get_position();width,height=dialog.get_size();assert not dialog.get_decorated();assert width<=shell.get_screen().get_width()
  Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),left,top,width,height).savev(str(a.output/'missing-asset-native-error.png'),'png',[],[])
  errors.append(True);key('Return');return False
 bad=Path.home()/'Missing.theme';bad.write_bytes(re.sub(rb'(?im)^Wallpaper=[^\r\n]*',b'Wallpaper=%ThemeDir%missing.bmp',definition.read_bytes(),count=1))
 GLib.timeout_add(100,close_import_error);open_original(bad,False);assert errors and window.controller.pending is None
 assert {str(path.relative_to(config)):path.read_bytes()for path in config.glob('*.json')}==before
 open_original();capture('opened-not-applied');assert {str(path.relative_to(config)):path.read_bytes()for path in config.glob('*.json')}==before
 click(window,456,423);assert not window.get_visible();assert {str(path.relative_to(config)):path.read_bytes()for path in config.glob('*.json')}==before
 window=DesktopThemesWindow(shell);window.show_all();flush_draws(Gtk);assert window.controller.pending is None
 open_original();value=window.controller.themes['Original'];click(window,538,423);assert window.controller.applied.name=='Original'
 reopened=controller_for(shell);assert reopened.applied==window.controller.applied
 assert shell.mouse_preferences.scheme=='(None)'and len(shell.mouse_preferences.overrides)==14
 assert (shell.mouse_preferences.speed,shell.mouse_preferences.left_handed,shell.mouse_preferences.double_click_ms)==input_settings
 from win95lx.control_panel.theme_appearance import appearance
 assert appearance.values['colors']==value['colors'];assert appearance.values['fonts']==value['fonts'];assert appearance.values['metrics']==value['metrics']
 assert shell.theme_icon_values==value['icons'];capture('applied-legacy')
 assert {path.name:hashlib.sha256(path.read_bytes()).hexdigest()for path in a.fixture.iterdir()if path.is_file()}==originals
 components=window.controller.applied.components
 (a.output/'report.json').write_text(json.dumps({'viewport':a.size,'actual_input':['missing asset native error preserves current selection and preference bytes','Other popup and native OpenTheme filename','Open changes preview only','Cancel leaves all preference bytes unchanged','reopen returns CurrentWindowsSettings','repeated Other/Open and physical Apply','independent reopen reconciles imported definition'],'actual_components':components,'original_media_unchanged':True,'icon_cache_files':len(list((config/'theme-icon-cache').glob('*.png'))),'pixel_acceptance':'functional import check only; imported full-theme preview not pixel accepted'},indent=2))
 window.destroy();shell.disconnect_by_func(Gtk.main_quit);shell.destroy();flush_draws(Gtk)
def main():
 p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--assets',type=Path,default=ROOT/'private/shell-assets');p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--size',default='800x600');p.add_argument('--gi-path',default='/tmp/win95lx-sprint-tools.uouVbC/usr/lib/python3/dist-packages/gi');p.add_argument('--xvfb',default='/tmp/win95lx-sprint-tools.uouVbC/usr/bin/Xvfb');a=p.parse_args()
 if a.child:return child(a)
 with tempfile.TemporaryDirectory(prefix='win95lx-import-')as tmp:
  root=Path(tmp);r,w=os.pipe();server=subprocess.Popen([shutil.which('Xvfb')or a.xvfb,'-displayfd',str(w),'-screen','0',a.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w)
  try:
   assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None);env.update(DISPLAY=display,GDK_BACKEND='x11',HOME=str(root/'home'),XDG_CONFIG_HOME=str(root/'config'),XDG_CACHE_HOME=str(root/'cache'),XDG_DATA_HOME=str(root/'data'));Path(env['HOME']).mkdir()
   subprocess.run(['/usr/bin/python3',__file__,'--child','--pid',str(server.pid),'--assets',str(a.assets.resolve()),'--fixture',str(a.fixture.resolve()),'--output',str(a.output.resolve()),'--size',a.size,'--gi-path',a.gi_path],env=env,check=True,timeout=90)
  finally:os.close(r);server.terminate();server.wait(timeout=10)
if __name__=='__main__':main()
