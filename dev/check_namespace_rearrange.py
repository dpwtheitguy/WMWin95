#!/usr/bin/env python3
"""Namespace rearrangement using actual X11 pointer events on an owned Xvfb."""
import os,sys,argparse,tempfile,json,subprocess,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
import gi;gi.require_foreign('cairo');import cairo
from win95lx.shell.app import Shell,Gtk,Gdk
from check_menu_seams import flush_draws
D=Gdk.Display.get_default()
if os.environ.get('GDK_BACKEND')!='x11' or os.environ.get('WAYLAND_DISPLAY') or 'X11' not in type(D).__name__ or D.get_name()!=os.environ.get('DISPLAY') or D.get_name().split('.')[0] in (':0',':1'):raise RuntimeError('Isolated X11 required')
import ctypes,ctypes.util
X=ctypes.CDLL(ctypes.util.find_library('X11'));T=ctypes.CDLL(ctypes.util.find_library('Xtst'))
X.XOpenDisplay.restype=ctypes.c_void_p;XD=X.XOpenDisplay(None)
X.XFlush.argtypes=[ctypes.c_void_p];X.XKeysymToKeycode.argtypes=[ctypes.c_void_p,ctypes.c_ulong];X.XKeysymToKeycode.restype=ctypes.c_uint
T.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong]
T.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
T.XTestFakeKeyEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
def xdo(*args):
 if args[0]=='mousemove':T.XTestFakeMotionEvent(XD,-1,int(args[-2]),int(args[-1]),0)
 elif args[0] in ('mousedown','mouseup'):T.XTestFakeButtonEvent(XD,int(args[1]),args[0]=='mousedown',0)
 elif args[0]=='key':
  code=X.XKeysymToKeycode(XD,Gdk.keyval_from_name(args[1]));T.XTestFakeKeyEvent(XD,code,True,0);T.XTestFakeKeyEvent(XD,code,False,0)
 X.XFlush(XD);flush_draws(Gtk)
checks=[]
with tempfile.TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
 shell=Shell(ROOT/'private/shell-assets');shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk)
 try:
  def render(name):
   flush_draws(Gtk);im=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw(shell.area,cairo.Context(im));im.write_to_png(str(a.output/(name+'.png')))
  def item(win,label):return next((x+min(w-1,10),y+min(h-1,10)) for x,y,w,h,act in shell.hits if act[0]=='item' and act[1] is win and act[3]==label)
  def drag(start,end,via=None):
   xdo('mousemove','--sync',*start);xdo('mousedown',1)
   if via:xdo('mousemove','--sync',*via)
   xdo('mousemove','--sync',*end);xdo('mouseup',1)
  with patch.object(shell,'transfer_files',side_effect=AssertionError('namespace must not transfer files')):
   for kind,label in (('computer','(C:)'),('control','Mouse')):
    shell.open(kind);win=shell.state.active;win.x=win.y=20;win.width=640;win.height=450;render(kind+'-before')
    if kind=='computer':assert win.namespace_auto is False,'New My Computer must allow native-style manual placement by default'
    if win.namespace_auto:shell.action(('namespace-auto',win));render(kind+'-manual')
    start=item(win,label);origin=next(act[4] for *_,act in shell.hits if act[0]=='item' and act[1] is win and act[3]==label)
    drag(start,(start[0]+31,start[1]+24));render(kind+'-moved');actual=shell.shortcut_icons.position('namespace:'+kind+':large',label,None);assert actual==(origin[0]+31,origin[1]+24),(kind,actual,origin)
    # Threshold latches after moving out then returning below initial threshold.
    start=item(win,label);drag(start,(start[0]+1,start[1]+1),(start[0]+15,start[1]+15));render(kind+'-latched');assert shell.shortcut_icons.position('namespace:'+kind+':large',label,None)==(actual[0]+1,actual[1]+1)
    saved=shell.shortcut_icons.path.read_bytes();start=item(win,label);xdo('mousemove','--sync',*start);xdo('mousedown',1);xdo('mousemove','--sync',start[0]+20,start[1]+20);xdo('key','Escape');xdo('mouseup',1);render(kind+'-cancelled');assert shell.shortcut_icons.path.read_bytes()==saved
    start=item(win,label);drag(start,(shell.width-1,shell.height-1));assert shell.shortcut_icons.path.read_bytes()==saved
    checks.append(kind+': actual pointer move, release endpoint, threshold latch, Escape, outside-client cancellation and zero filesystem transfer')
    shell.action(('namespace-auto',win));render(kind+'-auto');start=item(win,label);drag(start,(start[0]+15,start[1]+15));assert shell.namespace_item_drag is None;render(kind+'-auto-release')
    checks.append(kind+': Auto Arrange prevents free-position drag')
    shell.action(('namespace-auto',win));shell.action(('namespace-view',win,'small'));render(kind+'-small');start=item(win,label);drag(start,(start[0]+9,start[1]+9));render(kind+'-small-moved');assert shell.shortcut_icons.position('namespace:'+kind+':small',label,None) is not None
    for mode in ('list','details'):
     shell.action(('namespace-view',win,mode));render(kind+'-'+mode);start=item(win,label);drag(start,(start[0]+9,start[1]+9));assert shell.namespace_item_drag is None
    checks.append(kind+': Small Icons can move; List and Details remain ordered')
    shell.action(('namespace-view',win,'large'));render(kind+'-reloaded')
    for x,y,w,h,act in shell.hits:
     if act[0]=='item' and act[1] is win:
      vx,vy,vw,vh=win.namespace_viewport;assert vx<=x and vy<=y and x+w<=vx+vw and y+h<=vy+vh
   from win95lx.shell.desktop_icons import ShortcutIcons
   reopened=ShortcutIcons();assert reopened.position('namespace:computer:large','(C:)',None) is not None;assert reopened.position('namespace:control:large','Mouse',None) is not None
   checks.append('Stable namespace/view/label keys survive independent store reopen; all rendered item hits are client-clipped')
  (a.output/'report.json').write_text(json.dumps({'status':'pass','display':D.get_name(),'screen':[shell.width,shell.height],'checks':checks,'real_pointer':True},indent=2)+'\n');print(json.dumps(checks))
 finally:shell.destroy()
