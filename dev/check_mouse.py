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

COMMAND_LABELS=('OK','Cancel','&Apply','&Browse...','Use De&fault','Sa&ve As...','&Delete','&Change...')

def stage_command_references(source,output):
 from stage_command_button_assets import read_bmp
 from pixels import write
 import hashlib
 metadata=source/'captures/STATES.JSN';catalog=json.loads(metadata.read_text());rows=[]
 if len(catalog['states'])!=64:raise ValueError('Incomplete native Mouse command matrix')
 output.mkdir(parents=True,exist_ok=True)
 for case in catalog['states']:
  label,state=case['label_index'],case['state_index']
  if case['width']!=75 or case['height']!=23 or case['font_height']!=13 or not case['saved']:raise ValueError('Unexpected native Mouse command profile')
  bmp=source/'captures'/f'B0{label}{state}.BMP';w,h,pixels=read_bmp(bmp)
  if (w,h)!=(79,27):raise ValueError('Native command margins differ')
  name=f'mouse-command-native-{label}-{state}.png';write(output/name,w,h,pixels)
  rows.append({**case,'raw_label':COMMAND_LABELS[label],'file':name,'png_sha256':hashlib.sha256((output/name).read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(bmp.read_bytes()).hexdigest()})
 result={'profile':'Original IE4 Win95 OSR2.5 USER BUTTON,96dpi,256colors,13px MS Sans Serif,75x23 HWND with2pxparentmargin','cases':rows,'metadata_sha256':hashlib.sha256(metadata.read_bytes()).hexdigest(),'harness_source_sha256':hashlib.sha256((source/'command-buttons.c').read_bytes()).hexdigest(),'harness_binary_sha256':hashlib.sha256((source/'W95BTNS.EXE').read_bytes()).hexdigest()}
 (output/'mouse-command-references.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'staged_native_command_cases':len(rows)}))

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--stage-command-references',type=Path);a=p.parse_args()
 if a.stage_command_references:
  if not a.output.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Native assets must remain private')
  stage_command_references(a.stage_command_references,a.output);return
 a.output.mkdir(parents=True,exist_ok=False)
 custom=ROOT/'private/cabsets/windows95/arrow_m.cur'
 assert custom.is_file(), 'Stage the original custom-pointer fixture before starting this interactive check.'
 import gi;gi.require_foreign('cairo');import cairo
 from win95lx.shell.app import Shell,Gtk,Gdk
 gi.require_version("GdkX11","3.0")
 from gi.repository import GdkX11
 import os
 display=Gdk.Display.get_default()
 if not isinstance(display,GdkX11.X11Display) or display.get_name()!=os.environ.get("DISPLAY"):raise SystemExit("Requested isolated X11 display required")
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
   # Compare actual Mouse command-pass output, not only the shared primitive.
   import hashlib
   catalog=json.loads((ROOT/'private/shell-assets/mouse-command-references.json').read_text())
   matrix={(case['raw_label'],case['state_index']):case for case in catalog['cases']}
   def command_exact(image,name,action):
    label,rect,_,enabled=next(spec for spec in window.button_specs if spec[2]==action)
    focused=window.caption_active and window.focus_action==action
    pressed=window.pressed==action and window.press_inside
    default=window.default_command==action
    state=(7 if default else 6) if not enabled else 5 if pressed and focused else 4 if pressed else 3 if focused and default else 2 if focused else 1 if default else 0
    case=matrix[label,state];source=ROOT/'private/shell-assets'/case['file'];assert hashlib.sha256(source.read_bytes()).hexdigest()==case['png_sha256']
    x,y,w,h=rect;difference=compare_region(image,read(source),(0,0,79,27),(x-2,y-2))
    comparisons.append({'name':name,'raw_label':label,'state_index':state,'differing_pixels':difference});assert not difference,(name,label,state,difference)
   for tab in range(4):
    window.action(('tab',tab));window.focus_action=('body',);image=capture(f'commands-page-{tab}-default')
    for label,rect,action,enabled in window.button_specs:command_exact(image,f'page{tab} default '+label,action)
   checks.append('Actual command pass across all four tabs matches native full HWND plus parent margins; intentional capability-disabled states use native disabled BUTTON')
   window.update(speed=7)
   for tab in range(4):
    window.action(('tab',tab));capture(f'commands-page-{tab}-pending')
    actions=[action for label,rect,action,enabled in window.button_specs if enabled]
    for index,action in enumerate(actions):
     window.focus_action=action;window.pressed=None;window.press_inside=True
     image=capture(f'command-{tab}-{index}-focused');command_exact(image,f'page{tab} focused',action)
     assert window.default_command==action
     window.pressed=action;image=capture(f'command-{tab}-{index}-pressed');command_exact(image,f'page{tab} pressed',action)
     window.press_inside=False;image=capture(f'command-{tab}-{index}-held-outside');command_exact(image,f'page{tab} held outside',action)
     window.pressed=None
   window.action(('tab',1));window.role=0;window.update(overrides={'arrow':str(custom)});window.focus_action=('scheme',)
   image=capture('use-default-enabled');command_exact(image,'Use Default enabled',('default',));assert ('default',) in window.command_actions and window.command_mnemonics.get('f')==('default',)
   for state in ('focused','pressed','held-outside'):
    window.focus_action=('default',);window.pressed=('default',) if state!='focused' else None;window.press_inside=state!='held-outside'
    image=capture('use-default-'+state);command_exact(image,'Use Default '+state,('default',))
   window.pressed=None
   checks.append('Every enabled actual command transfers the unique default and matches native focused/pressed/held-outside states')
   window.controller.cancel();window.action(('tab',0));capture('commands-reset')
   assert ('apply',) not in window.command_actions and 'a' not in window.command_mnemonics
   # Actual event handlers: cancellation when released at the half-open edge.
   pointer=lambda x,y:SimpleNamespace(x=x,y=y,button=1,type=Gdk.EventType.BUTTON_PRESS)
   with patch.object(window,'action') as invoked:
    window.press(window.area,pointer(250,425));capture('cancel-command-pressed')
    window.motion(window.area,pointer(315,425));assert not window.press_inside
    window.motion(window.area,pointer(313,425));assert window.press_inside
    window.release(window.area,pointer(314,425));invoked.assert_not_called()
    window.press(window.area,pointer(250,425));window.release(window.area,pointer(313,437));invoked.assert_called_once_with(('cancel',))
   window.focus_action=('cancel',)
   with patch.object(window,'action') as invoked:
    window.key(window,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));invoked.assert_called_once_with(('cancel',))
   window.update(speed=7);capture('apply-mnemonic-enabled')
   with patch.object(window,'action') as invoked:
    window.key(window,SimpleNamespace(keyval=Gdk.KEY_a,state=Gdk.ModifierType.MOD1_MASK));invoked.assert_called_once_with(('apply',))
   window.controller.cancel();window.action(('tab',0));capture('commands-reset-final')
   checks.append('Actual press leave/reenter/release-out cancels, release-in invokes once; focused Cancel Enter and enabled Apply mnemonic route correctly')
   pending=window.controller.pending
   with patch.object(shell,'key') as start,patch.object(window,'destroy') as destroy:
    key=SimpleNamespace(keyval=Gdk.KEY_Escape,state=Gdk.ModifierType.CONTROL_MASK)
    assert window.key(window,key);start.assert_called_once_with(shell,key);destroy.assert_not_called()
   assert window.controller.pending==pending
   checks.append('Ctrl+Esc forwards Start without cancelling Mouse Properties pending edits')
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
 report={**identity(ROOT,Path(__file__).resolve(),[ROOT/'private/screenshots/start-development-20261110/native-mouse-buttons-clean.png',ROOT/'private/shell-assets/mouse-command-references.json']),'viewport':[shell.width,shell.height],'checks':checks,'comparisons':comparisons,'failed':0};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
