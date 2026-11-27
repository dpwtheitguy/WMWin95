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
 with (a.output/'events.log').open('a') as log:log.write(' '.join(map(str,args))+'\n')
 if args[0]=='mousemove':T.XTestFakeMotionEvent(XD,-1,int(args[-2]),int(args[-1]),0)
 elif args[0] in ('mousedown','mouseup'):T.XTestFakeButtonEvent(XD,int(args[1]),args[0]=='mousedown',0)
 elif args[0]=='key':
  code=X.XKeysymToKeycode(XD,Gdk.keyval_from_name(args[1]));T.XTestFakeKeyEvent(XD,code,True,0);T.XTestFakeKeyEvent(XD,code,False,0)
 X.XFlush(XD);flush_draws(Gtk)
import faulthandler;faulthandler.dump_traceback_later(90,exit=True)
checks=[]
with tempfile.TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
 from win95lx.explorer.drive_browser import DriveBrowser
 shell=Shell(ROOT/'private/shell-assets');shell._drive=DriveBrowser(Path(home));assert shell._drive.view.root==Path(home).resolve()
 shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk)
 try:
  def render(name):
   flush_draws(Gtk);im=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw(shell.area,cairo.Context(im));im.write_to_png(str(a.output/(name+'.png')))
  def item(win,label):return next((x+min(w-1,10),y+min(h-1,10)) for x,y,w,h,act in shell.hits if act[0]=='item' and act[1] is win and act[3]==label)
  def drag(start,end,via=None,button=1):
   xdo('mousemove','--sync',*start);xdo('mousedown',button)
   if via:xdo('mousemove','--sync',*via)
   xdo('mousemove','--sync',*end);xdo('mouseup',button)
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
   from win95lx.explorer.namespace import read_shortcut
   shell.desktop_folder.mkdir(parents=True,exist_ok=True)
   shell.open('computer');win=shell.state.active;win.x=win.y=20;win.width=640;win.height=450
   for mode in ('large','small','list','details'):
    shell.action(('namespace-view',win,mode));render('cross-'+mode)
    if not win.namespace_auto:shell.action(('namespace-auto',win));render('cross-'+mode+'-auto')
    start=item(win,'(C:)');end=(shell.width-20,shell.height-65);before=set(shell.desktop_folder.iterdir())
    with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.NO) as prompt:
     drag(start,end);prompt.assert_called_once();assert prompt.call_args.kwargs['profile']=='namespace-drop'
    assert set(shell.desktop_folder.iterdir())==before
    with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):drag(start,end)
    created=set(shell.desktop_folder.iterdir())-before;assert len(created)==1;created_path=created.pop();assert read_shortcut(created_path).target=='drive';shell.desktop_icons.move('file:'+created_path.name,(80,20+('large','small','list','details').index(mode)*75))
    render('cross-'+mode+'-created')
   checks.append('All four source views and AutoArrangeON permit external shortcut drops; native-profile No writes nothing and Yes creates typed namespace Link')
   shell.action(('namespace-view',win,'large'));render('ghost-before');start=item(win,'(C:)');end=(shell.width-30,shell.height-80)
   xdo('mousemove','--sync',*start);xdo('mousedown',1);xdo('mousemove','--sync',*end);render('ghost-outside-source');assert shell.namespace_pointer_point==end and shell.namespace_item_drag is not None
   xdo('key','Escape');xdo('mouseup',1);assert shell.namespace_item_drag is None
   checks.append('Actual pointer outside source retains global drag ghost until release; Escape cancels without prompt or write')
   before=set(shell.desktop_folder.iterdir());positions=shell.shortcut_icons.path.read_bytes();start=item(win,'(C:)')
   with patch('win95lx.apps.dialogs.message_box',side_effect=[Gtk.ResponseType.YES,Gtk.ResponseType.OK]) as prompt,patch('win95lx.explorer.namespace.create_shortcut',side_effect=PermissionError('/private/unwanted/path')):
    drag(start,end);assert prompt.call_count==2 and '/private/' not in prompt.call_args.args[2]
   assert set(shell.desktop_folder.iterdir())==before and shell.shortcut_icons.path.read_bytes()==positions
   with patch.object(shell,'file_drop_destination',return_value=(None,Path('loop'))),patch.object(shell._drive.view,'resolve',side_effect=RuntimeError('symlink loop')),patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.OK) as prompt:
    drag(start,end);prompt.assert_called_once();assert 'no longer available' in prompt.call_args.args[2]
   assert set(shell.desktop_folder.iterdir())==before
   checks.append('Permission and looping-destination failures show native concise errors without private paths, new files, source movement or changes to existing positions/files')
   start=item(win,'Control Panel')
   with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):drag(start,end)
   assert any(read_shortcut(path) and read_shortcut(path).target=='control' for path in shell.desktop_folder.iterdir())
   for path in shell.desktop_folder.iterdir():
    if read_shortcut(path) and read_shortcut(path).target=='control':shell.desktop_icons.move('file:'+path.name,(80,320))
   checks.append('Control Panel virtual root also creates its own typed namespace shortcut')
   start=item(win,'(C:)');before=set(shell.desktop_folder.iterdir())
   drag(start,start,button=3);assert shell.start_context and not any(row and row[0] in ('Close','My Computer','Work Offline') for row in shell.start_context.rows),(shell.start_context.rows if shell.start_context else None,shell.popup,shell.namespace_item_drag);xdo('key','Escape');assert shell.start_context is None
   drag(start,(start[0]+1,start[1]+1),via=(start[0]+15,start[1]+15),button=3);assert shell.start_context is None
   for cancel in ('escape','outside','cancel'):
    drag(start,end,button=3);menu=shell.start_context;assert menu and menu.rows[0][0]=='Create Shortcut(s) Here'
    if cancel=='escape':
     # Some multimedia/unmapped keyvals have no symbolic GDK name.
     event=Gdk.Event.new(Gdk.EventType.KEY_PRESS);event.keyval=0;event.state=Gdk.ModifierType(0)
     with patch.object(Gdk,'keyval_name',return_value=None):shell.key(shell,event)
     assert shell.start_context is menu
     xdo('key','Escape')
    elif cancel=='outside':xdo('mousemove','--sync',2,shell.height-40);xdo('mousedown',1);xdo('mouseup',1)
    else:xdo('mousemove','--sync',menu.x+30,menu.y+menu.height-10);xdo('mousedown',1);xdo('mouseup',1)
    assert shell.start_context is None and set(shell.desktop_folder.iterdir())==before
   drag(start,end,button=3);menu=shell.start_context
   with patch('win95lx.apps.dialogs.message_box',side_effect=AssertionError('Explicit right-drop link action must not reprompt')):
    xdo('mousemove','--sync',menu.x+35,menu.y+10);xdo('mousedown',1);xdo('mouseup',1)
   assert len(set(shell.desktop_folder.iterdir())-before)==1
   checks.append('Logical rightclick uses distinct item context; latched return avoids context; rightdrop Cancel/Escape/outside writesnothing; explicit CreateShortcutHere writes Link without reprompt')
   # Same virtual link can target a real folder, never move the source object.
   target=shell._drive.view.root/'Drop Target';target.mkdir();shell.open('drive',target.relative_to(shell._drive.view.root));folder=shell.state.active;folder.x=shell.width-230;folder.y=280;folder.width=220;folder.height=250
   render('folder-target');start=item(win,'(C:)');end=(folder.x+180,folder.y+100)
   with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):drag(start,end)
   links=list(target.iterdir());assert len(links)==1 and read_shortcut(links[0]).target=='drive';render('folder-created')
   checks.append('Actual folder-window drop writes a Link in that folder without moving virtual drive; existing files preserved')
   render('source-activation-before');start=item(win,'(C:)');assert shell.state.active is win
   # An exposed background source activates before its drag; covered items do not.
   empty=shell._drive.view.root/'Empty Cover';empty.mkdir();shell.open('drive',empty.relative_to(shell._drive.view.root));cover=shell.state.active;cover.x=start[0]+90;cover.y=30;cover.width=220;cover.height=250
   render('source-exposed-background');xdo('mousemove','--sync',*start);xdo('mousedown',1);assert shell.state.active is win and shell.namespace_item_drag is not None;xdo('key','Escape');xdo('mouseup',1)
   shell.state.windows.remove(cover);shell.state.windows.append(cover);cover.x=start[0]-100;cover.y=start[1]-140;render('source-covered-empty-client');xdo('mousemove','--sync',*start);xdo('mousedown',1);assert shell.namespace_item_drag is None and shell.icon_drag is None and shell.state.active is cover;xdo('mouseup',1)
   point=shell.desktop_icons.position('file:'+next(iter(shell.desktop_folder.iterdir())).name,shell.width,shell.height,shell.desktop_file_defaults.get('file:'+next(iter(shell.desktop_folder.iterdir())).name));desktop_point=(point[0]+25,point[1]+10);cover.x=desktop_point[0]-100;cover.y=desktop_point[1]-140;render('desktop-covered-empty-client');xdo('mousemove','--sync',*desktop_point);xdo('mousedown',1);assert shell.icon_drag is None and shell.namespace_item_drag is None;xdo('mouseup',1)
   checks.append('Partly exposed background namespace source activates and starts drag; empty foreground client blocks covered namespace and desktop icon click-through')
   from win95lx.shell.desktop_icons import ShortcutIcons
   reopened=ShortcutIcons();assert reopened.position('namespace:computer:large','(C:)',None) is not None;assert reopened.position('namespace:control:large','Mouse',None) is not None
   checks.append('Stable namespace/view/label keys survive independent store reopen; all rendered item hits are client-clipped')
  (a.output/'report.json').write_text(json.dumps({'status':'pass','display':D.get_name(),'screen':[shell.width,shell.height],'checks':checks,'real_pointer':True},indent=2)+'\n');print(json.dumps(checks))
 finally:shell.destroy();faulthandler.cancel_dump_traceback_later()
