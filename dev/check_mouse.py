#!/usr/bin/env python3
"""Mouse property-sheet native pixels, input, persistence and real X11 mapping."""
import argparse,json,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch,Mock
from types import SimpleNamespace
from dataclasses import replace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]
from pixels import read
from check_reference_ui import compare_region

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 import gi;gi.require_foreign('cairo');import cairo
 from win95lx.shell.app import Shell,Gtk,Gdk
 from win95lx.apps.mouse import MouseWindow
 from win95lx.control_panel.mouse_preferences import MousePreferences,X11Mouse,SCHEMES
 from check_menu_seams import flush_draws
 checks=[];comparisons=[]
 with TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
  shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
  backend=X11Mouse();original=backend.snapshot();backend.apply(MousePreferences());before=backend.snapshot()
  try:
   window=MouseWindow(shell,backend);window.show_all();flush_draws(Gtk)
   def capture(name):
    image=cairo.ImageSurface(cairo.FORMAT_RGB24,404,448);window.draw(window.area,cairo.Context(image));path=a.output/(name+'.png');image.write_to_png(str(path));return read(path)
   actual=capture('buttons-default')
   ref=ROOT/'private/screenshots/start-development-20261110/native-mouse-buttons-clean.png'
   difference=compare_region(actual,read(ref),(44,44,404,448),(0,0));comparisons.append({'name':'complete default Buttons sheet','differing_pixels':difference});assert not difference,difference
   # A real pointer release, not press, commits the button action.
   event=lambda x,y:SimpleNamespace(x=x,y=y,button=1,type=Gdk.EventType.BUTTON_PRESS)
   window.press(window.area,event(150,94));window.release(window.area,event(150,94));assert window.controller.pending.left_handed
   assert backend.snapshot()==before
   window.press(window.area,event(208,296));window.release(window.area,event(208,296));assert window.controller.pending.double_click_ms==100
   window.action(('tab',2));window.key(window,SimpleNamespace(keyval=Gdk.KEY_Right,state=0));assert window.controller.pending.speed==6
   window.action(('apply',));prefs=MousePreferences.load(window.controller.path);assert prefs.left_handed and prefs.double_click_ms==100 and prefs.speed==6
   assert Gtk.Settings.get_default().get_property('gtk-double-click-time')==100
   state=backend.snapshot();assert state[0].index(1)>state[0].index(3);assert state[1:3]==(6,5)
   checks.append('pointer radios slider keyboard Apply persisted and real X11 mapping/acceleration plus GTK timing')
   window.action(('tab',0));capture('before-test')
   for time_ms in (1000,1050):
    e=event(300,330);e.time=time_ms;window.press(window.area,e);window.release(window.area,e)
   assert window.animation_frame==0
   window.animation_frame=16;capture('native-jack-animation-middle')
   checks.append('test area uses pending double-click timing and original 32-frame MAIN.CPL animation')

   window.update(left_handed=False);window.controller.cancel();assert window.controller.pending.left_handed;assert backend.snapshot()==state
   checks.append('Cancel discards pending edits without reverting previously applied settings')
   for index,name in enumerate(('buttons','pointers','motion','general')):
    window.action(('tab',index));capture(name+'-working')
   window.action(('tab',1));window.action(('scheme',));assert window.combo.expanded
   window.press(window.area,event(80,85+22+13));assert window.controller.pending.scheme==SCHEMES[1]
   window.key(window,SimpleNamespace(keyval=Gdk.KEY_Down,state=0));assert window.controller.pending.scheme==SCHEMES[2]
   for role,_ in __import__('win95lx.control_panel.mouse_preferences',fromlist=['ROLES']).ROLES:assert window.pointer_image(role).get_width()>0
   capture('pointers-before-scroll')
   window.press(window.area,event(370,190));window.motion(window.area,event(370,345));window.release(window.area,event(370,345))
   assert window.scroll==8;capture('pointers-thumb-bottom')
   window.press(window.area,event(370,300));window.motion(window.area,event(370,174));window.release(window.area,event(370,174))
   assert window.scroll==0
   checks.append('pointer list thumb dragging clamps at both ends and redraws actual rows')
   window.action(('apply',));assert shell.cursor_for('arrow') is not None
   checks.append('scheme dropdown pointer and keyboard selection all fourteen cursor roles and actual cursor application')
   custom=ROOT/'private/cabsets/windows95/arrow_m.cur'
   window.role=0
   with patch('win95lx.apps.dialogs.choose_file',return_value=custom):window.action(('browse',))
   assert window.controller.pending.overrides['arrow']==str(custom)
   capture('pointers-before-scroll')
   window.press(window.area,event(370,190));window.motion(window.area,event(370,345));window.release(window.area,event(370,345))
   assert window.scroll==8;capture('pointers-thumb-bottom')
   window.press(window.area,event(370,300));window.motion(window.area,event(370,174));window.release(window.area,event(370,174))
   assert window.scroll==0
   checks.append('pointer list thumb dragging clamps at both ends and redraws actual rows')
   window.action(('apply',));assert shell.cursor_for('arrow') is not None and window.pointer_image('arrow').get_width()>0
   window.action(('default',));assert 'arrow' not in window.controller.pending.overrides
   window.action(('apply',))
   checks.append('Browse valid CUR file Apply original hotspot and Use Default')
   window.action(('scheme',));previous=window.controller.pending.scheme
   window.key(window,SimpleNamespace(keyval=Gdk.KEY_Up,state=0))
   window.key(window,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0))
   assert window.controller.pending.scheme==previous
   checks.append('Escape dismisses provisional dropdown selection without applying it')
   # Normal Control Panel Open and Properties route to the same sheet instance.
   shell.open('control');panel=shell.state.active;shell.item_selection=(panel,'Mouse')
   shell.action(('computer-menu',panel,'open'));assert 'mouse' in shell.accessory_windows
   actual_window=shell.accessory_windows['mouse'];shell.action(('computer-menu',panel,'properties'))
   assert shell.accessory_windows['mouse'] is actual_window
   actual_window.update(speed=1);actual_window.action(('cancel',))
   assert MousePreferences.load(window.controller.path).speed==6
   shell.item_selection=(panel,'Mouse');shell.key(shell,SimpleNamespace(keyval=Gdk.KEY_Return,state=0))
   assert 'mouse' in shell.accessory_windows
   shell.accessory_windows['mouse'].action(('cancel',))
   from win95lx.explorer.namespace import create_shortcut,resolve_shortcut
   shortcut=create_shortcut(Path(home)/'Desktop','Mouse');assert resolve_shortcut(shortcut).target=='mouse'
   checks.append('Control Panel Open Properties reuse Cancel and namespace shortcut')

   window.update(speed=10);window.controller.cancel();assert window.controller.pending.speed==6
   window.destroy()
   # MouseWindow closes its display; use a fresh connection to restore the test X server.
   backend=X11Mouse();backend.restore(before)
   # All committed options survive a new controller/window instance.
   reopened=MouseWindow(shell,backend);assert reopened.controller.pending==prefs.__class__.load(reopened.controller.path);reopened.destroy();backend=None
   checks.append('reopened sheet loads applied values')
  finally:
   if backend is not None:backend.close()
   restore=X11Mouse();restore.restore(original);restore.close()
   shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
 from evidence import identity
 report={**identity(ROOT,Path(__file__).resolve(),[ROOT/'private/screenshots/start-development-20261110/native-mouse-buttons-clean.png']),'viewport':[shell.width,shell.height],'checks':checks,'comparisons':comparisons,'failed':0};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
