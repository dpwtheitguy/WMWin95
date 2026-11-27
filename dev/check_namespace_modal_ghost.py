#!/usr/bin/env python3
"""Actual X11 framebuffer: release must remove the ghost behind a nested modal."""
import argparse,ctypes,ctypes.util,json,os,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--source',type=Path,default=ROOT/'src');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
sys.path[:0]=[str(a.source),str(ROOT/'dev')]
from win95lx.shell.app import Shell,Gtk,Gdk,GLib
from win95lx.explorer.drive_browser import DriveBrowser
from win95lx.shell.namespace_drop import drag_image_origin
from check_menu_seams import flush_draws
d=Gdk.Display.get_default()
assert os.environ.get('GDK_BACKEND')=='x11' and not os.environ.get('WAYLAND_DISPLAY') and d and 'X11'in type(d).__name__ and d.get_name()==os.environ['DISPLAY'] and d.get_name().split('.')[0]not in(':0',':1'),'Owned isolated X11 required'
x=ctypes.CDLL(ctypes.util.find_library('X11'));t=ctypes.CDLL(ctypes.util.find_library('Xtst'));x.XOpenDisplay.restype=ctypes.c_void_p;x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p];handle=x.XOpenDisplay(None);assert handle
t.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];t.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
def move(px,py):t.XTestFakeMotionEvent(handle,-1,int(px),int(py),0);x.XFlush(handle);flush_draws(Gtk)
def button(down):t.XTestFakeButtonEvent(handle,1,down,0);x.XFlush(handle);flush_draws(Gtk)
def pixels(window,rect,name):
 xx,yy,w,h=map(int,rect);pb=Gdk.pixbuf_get_from_window(window.get_window(),xx,yy,w,h);assert pb;pb.savev(str(a.output/(name+'.png')),'png',[],[]);data=pb.get_pixels();stride=pb.get_rowstride();channels=pb.get_n_channels();return [tuple(data[j*stride+i*channels:j*stride+i*channels+3])for j in range(h)for i in range(w)]
observations=[];errors=[];seen=[]
with tempfile.TemporaryDirectory(prefix='w95uat-modal-ghost-')as directory,patch('pathlib.Path.home',return_value=Path(directory)):
 shell=Shell(ROOT/'private/shell-assets');shell._drive=DriveBrowser(Path(directory));shell.disconnect_by_func(Gtk.main_quit);shell.show_all();shell.open('computer');win=shell.state.active;win.x=win.y=20;win.width=500;win.height=450;flush_draws(Gtk)
 try:
  hit=next(hit for hit in shell.hits if hit[4][0]=='item'and hit[4][1]is win and hit[4][3]=='(C:)');start=(hit[0]+32,hit[1]+17);point=hit[4][4];end=(shell.width-60,200)
  move(*start);button(True);move(*end)
  origin=drag_image_origin(win.namespace_viewport,point,start,end,win.namespace_scroll,image_x=15);rect=(*origin,32,32)
  before=pixels(shell,rect,'before-release-ghost');assert any(rgb!=(0,128,128)for rgb in before),'Fixture did not paint a visible ghost'
  deadline=time.monotonic()+5
  def inspect():
   dialogs=[window for window in Gtk.Window.list_toplevels()if isinstance(window,Gtk.Dialog)and window.get_visible()]
   if not dialogs:
    if time.monotonic()<deadline:return True
    errors.append('Drop question did not open');return False
   dialog=dialogs[0]
   try:
    after=pixels(shell,rect,'modal-open-ghost-region');wrong=sum(rgb!=(0,128,128)for rgb in after);observations.append({'ghost_rectangle':rect,'stale_pixels':wrong,'question':dialog.get_title()});seen.append(True)
    if wrong:errors.append(f'{wrong} stale ghost pixels remain during the modal')
    Gdk.pixbuf_get_from_window(shell.get_window(),0,0,shell.width,shell.height).savev(str(a.output/'modal-open-parent.png'),'png',[],[])
   finally:dialog.response(Gtk.ResponseType.NO)
   return False
  # Allow queued GTK draws to settle inside the nested GtkDialog.run loop.
  GLib.timeout_add(250,inspect);button(False);assert seen,'No modal inspection occurred'
  assert not tuple(shell.desktop_folder.iterdir()),'No must not create a shortcut'
  report={'source':str(a.source),'screen':[shell.width,shell.height],'actual_x11_pixels':True,'observations':observations,'errors':errors,'passed':not errors};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));assert not errors,errors
 finally:
  for window in Gtk.Window.list_toplevels():
   if isinstance(window,Gtk.Dialog):window.destroy()
  shell.destroy();x.XCloseDisplay(handle)
