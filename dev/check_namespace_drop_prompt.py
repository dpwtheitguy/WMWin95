"""Isolated native drop prompt pixels and Yes/No (no Escape/Close) contract."""
import argparse,os,sys,json,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
import gi;gi.require_foreign('cairo');import cairo
from win95lx.shell.app import Shell,Gtk,Gdk
from win95lx.apps import dialogs
from pixels import read
from check_reference_ui import compare_region
from check_menu_seams import flush_draws
D=Gdk.Display.get_default()
if os.environ.get('GDK_BACKEND')!='x11' or os.environ.get('WAYLAND_DISPLAY') or 'X11' not in type(D).__name__ or D.get_name()!=os.environ.get('DISPLAY') or D.get_name().split('.')[0] in (':0',':1'):raise RuntimeError('Isolated X11 required')
with tempfile.TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
 shell=Shell(ROOT/'private/shell-assets');shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk);checks=[]
 try:
  def inspect(dialog):
   dialog.show_all();dialog.present();dialog.get_window().focus(Gdk.CURRENT_TIME);flush_draws(Gtk);fixed=dialog.get_content_area().get_children()[0];canvas=next(c for c in fixed.get_children() if isinstance(c,Gtk.DrawingArea));surface=cairo.ImageSurface(cairo.FORMAT_RGB24,326,119);canvas.draw(cairo.Context(surface));file=a.output/'namespace-drop-prompt.png';surface.write_to_png(str(file));difference=compare_region(read(file),read(ROOT/'private/shell-assets/namespace-drop-prompt.png'),(0,0,326,119),(0,0));assert difference==0,difference
   import ctypes as C,ctypes.util
   X=C.CDLL(ctypes.util.find_library('X11'));T=C.CDLL(ctypes.util.find_library('Xtst'));X.XOpenDisplay.restype=C.c_void_p;xd=X.XOpenDisplay(None);X.XSync.argtypes=[C.c_void_p,C.c_int]
   T.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong];T.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
   dx,dy=dialog.get_position()
   def pointer(x,y,down=None):
    T.XTestFakeMotionEvent(xd,-1,dx+x,dy+y,0)
    if down is not None:T.XTestFakeButtonEvent(xd,1,down,0)
    X.XSync(xd,False);flush_draws(Gtk)
   buttons=sorted((c for c in fixed.get_children() if isinstance(c,Gtk.Button)),key=lambda c:c.get_allocation().x)
   assert [(b.get_allocation().x,b.get_allocation().y,b.get_allocation().width,b.get_allocation().height) for b in buttons]==[(84,82,75,23),(165,82,75,23)]
   responses=[];dialog.connect('response',lambda _,response:responses.append(response));event=Gdk.Event.new(Gdk.EventType.KEY_PRESS);event.keyval=Gdk.KEY_Escape;event.state=Gdk.ModifierType(0);dialog.emit('key-press-event',event);assert not responses
   event.keyval=Gdk.KEY_F4;event.state=Gdk.ModifierType.MOD1_MASK;dialog.emit('key-press-event',event);assert not responses
   event.state=Gdk.ModifierType(0);delete=Gdk.Event.new(Gdk.EventType.DELETE);handled=dialog.emit('delete-event',delete);assert handled and not responses,(type(dialog).__name__,handled,responses)
   assert len([c for c in fixed.get_children() if isinstance(c,Gtk.Button)])==2
   for name,button,x in [('yes',buttons[0],84),('no',buttons[1],165)]:
    pointer(x+30,90,True);assert button.get_state_flags()&Gtk.StateFlags.ACTIVE
    image=cairo.ImageSurface(cairo.FORMAT_RGB24,326,119);canvas.draw(cairo.Context(image));image.write_to_png(str(a.output/(name+'-held.png')))
    pointer(50,70);assert not button.get_state_flags()&Gtk.StateFlags.ACTIVE
    pointer(x+30,90);assert button.get_state_flags()&Gtk.StateFlags.ACTIVE
    pointer(50,70,False);assert not responses
   buttons[0].grab_focus();flush_draws(Gtk);X.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];X.XKeysymToKeycode.restype=C.c_uint;T.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong];code=X.XKeysymToKeycode(xd,Gdk.KEY_Tab);T.XTestFakeKeyEvent(xd,code,True,0);T.XTestFakeKeyEvent(xd,code,False,0);X.XSync(xd,False);flush_draws(Gtk);assert buttons[1].has_focus()
   image=cairo.ImageSurface(cairo.FORMAT_RGB24,326,119);canvas.draw(cairo.Context(image));image.write_to_png(str(a.output/'no-tab-focus.png'))
   checks.append('Actual XTest Yes/No press-held, leave/reenter and outside-release cancellation; exact hit rectangles; Tab transfers default/focus toNo')
   event.keyval=Gdk.KEY_n;dialog.emit('key-press-event',event);assert responses==[Gtk.ResponseType.NO];responses.clear();event.keyval=Gdk.KEY_Return;dialog.emit('key-press-event',event);assert responses==[Gtk.ResponseType.NO]
   checks.extend(['Original326×119 complete static prompt pixels:0 differences','Escape has no response; no active caption Close button; native No mnemonic returnsNo']);return Gtk.ResponseType.NO
  with patch.object(dialogs,'run_dialog',side_effect=inspect):
   answer=dialogs.message_box(shell,'Shortcut','You cannot move or copy this item to this location.\nDo you want to create a shortcut to the item instead?',Gtk.MessageType.QUESTION,dialogs.YES_NO,Gtk.ResponseType.YES,profile='namespace-drop')
  assert answer==Gtk.ResponseType.NO
  (a.output/'report.json').write_text(json.dumps({'status':'pass','checks':checks},indent=2)+'\n');print(json.dumps(checks))
 finally:shell.destroy()
