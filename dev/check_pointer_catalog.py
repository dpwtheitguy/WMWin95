#!/usr/bin/env python3
"""Compare every basic pointer role with independent native list captures."""
import argparse,json,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
from pixels import read,write
from check_reference_ui import compare_region

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 import gi;gi.require_foreign('cairo');import cairo
 from win95lx.shell.app import Shell,Gtk,Gdk
 from win95lx.apps.mouse import MouseWindow
 from win95lx.control_panel.mouse_preferences import ROLES,MousePreferences
 from check_menu_seams import flush_draws
 comparisons=[];inventory=[]
 with TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
  shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk);window=MouseWindow(shell);window.show_all();flush_draws(Gtk)
  initial_backend=window.controller.backend.snapshot()
  window.action(('tab',1));assert window.controller.pending.scheme=='(None)'
  def capture(name):
   im=cairo.ImageSurface(cairo.FORMAT_RGB24,404,448);window.draw(window.area,cairo.Context(im));file=a.output/(name+'.png');im.write_to_png(str(file));return read(file)
  for name,scroll,selection in (('top',0,0),('middle',4,9),('bottom',8,13),('cross-selected',0,4)):
   window.scroll=scroll;window.role=selection;actual=capture('ours-basic-'+name)
   reference=read(ROOT/'private/screenshots/start-development-20261110'/('native-basic-pointers-'+name+'.png'))
   full=compare_region(actual,reference,(70,201,336,204),(26,157))
   comparisons.append({'role':'complete six-row list including labels','viewport':name,'differing_pixels':full,'native_rect':[70,201,336,204],'ours_origin':[26,157]})
   preview=compare_region(actual,reference,(344,113,80,78),(300,69))
   comparisons.append({'role':'preview well including cursor','viewport':name,'differing_pixels':preview,'native_rect':[344,113,80,78],'ours_origin':[300,69]})
   for row,(role,label) in enumerate(ROLES[scroll:scroll+6]):
    native=(369,202+row*34,32,32);count=compare_region(actual,reference,native,(325,158+row*34))
    comparisons.append({'role':label,'viewport':name,'differing_pixels':count,'native_rect':native,'ours_origin':[325,158+row*34]})
  for scheme in window.scheme_choices:
   window.update(scheme=scheme,overrides={});window.combo.value=window.scheme_choices.index(scheme);window.role=0;window.scroll=0
   frames=0
   for role,label in ROLES:
    d=shell.pointer_library.definition(scheme,role)
    assert d['sequence'] and len(d['sequence'])==len(d['durations_ms'])
    for frame in d['frames']:
     file=shell.assets/frame['file'];w,h,pixels=read(file);assert [w,h]==frame['dimensions'];assert 0<=frame['hotspot'][0]<w and 0<=frame['hotspot'][1]<h
    window.pointer_image(role);frames+=len(d['frames'])
   window.action(('apply',));assert shell.mouse_preferences.scheme==scheme
   for role,label in ROLES:assert shell.cursor_for(role) is not None
   capture('scheme-'+str(len(inventory)).zfill(2));inventory.append({'name':scheme,'roles':14,'referenced_frames':frames,'animated':shell.pointer_library.animated(scheme)})
  # Runtime animation changes the actual GDK cursor, not just the preview picture.
  scheme='Plus! / Animated / Apple';window.update(scheme=scheme,overrides={});window.action(('apply',))
  definition=shell.pointer_library.definition(scheme,'arrow');assert len(definition['frames'])>1
  with patch('win95lx.shell.app.GLib.get_monotonic_time',return_value=shell.cursor_animation_epoch):first=shell.cursor_for('arrow')
  with patch('win95lx.shell.app.GLib.get_monotonic_time',return_value=shell.cursor_animation_epoch+int(definition['durations_ms'][0]*1000)+1):second=shell.cursor_for('arrow')
  assert first is not second
  # The Plus theme preview is an independent native screenshot.
  native=read(ROOT/'private/screenshots/start-development-20261110/native-plus-dangerous-arrow-preview.png')
  entry=shell.pointer_library.frame('Plus! / Dangerous Creatures (256 color)','arrow',0)
  w,h,pixels=read(shell.assets/entry['file']);composite=[p[:3]+(255,) if p[3] else (192,192,192,255) for p in pixels]
  output=a.output/'ours-plus-dangerous-arrow.png';write(output,w,h,composite)
  different=compare_region(read(output),native,(167,376,32,32),(0,0))
  comparisons.append({'role':'Plus Dangerous Creatures Normal Select','viewport':'native theme preview','differing_pixels':different,'native_rect':[167,376,32,32],'ours_origin':[0,0]})
  # A native Plus animated preview must match at least one independently timed frame.
  native=read(ROOT/'private/screenshots/start-development-20261110/native-plus-dangerous-background-preview-settled.png')
  definition=shell.pointer_library.definition('Plus! / Dangerous Creatures (256 color)','busy');candidates=[]
  for index,frame in enumerate(definition['frames']):
   w,h,pixels=read(shell.assets/frame['file']);composite=[p[:3]+(255,) if p[3] else (192,192,192,255) for p in pixels]
   file=a.output/('ours-plus-bee-'+str(index)+'.png');write(file,w,h,composite)
   candidates.append((compare_region(read(file),native,(167,376,32,32),(0,0)),index))
  best,index=min(candidates);comparisons.append({'role':'Plus Dangerous Creatures Working In Background animated frame','viewport':'native theme preview','differing_pixels':best,'matched_frame':index,'native_rect':[167,376,32,32],'ours_origin':[0,0]})
  # Every item remains reachable through a bounded list, including the final Plus entry.
  window.combo.value=0;window.open_schemes()
  from types import SimpleNamespace
  for _ in range(len(window.scheme_choices)-1):window.key(window,SimpleNamespace(keyval=Gdk.KEY_Down,state=0))
  assert window.scheme_scroll>0;capture('all-schemes-dropdown-last-page');window.key(window,SimpleNamespace(keyval=Gdk.KEY_Return,state=0))
  assert window.controller.pending.scheme==window.scheme_choices[-1]
  window.controller.backend.restore(initial_backend)
  window.destroy();shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
 from evidence import identity
 refs=list((ROOT/'private/screenshots/start-development-20261110').glob('native-basic-pointers-*.png'))+[ROOT/'private/screenshots/start-development-20261110/native-plus-dangerous-arrow-preview.png',ROOT/'private/screenshots/start-development-20261110/native-plus-dangerous-background-preview-settled.png']
 report={**identity(ROOT,Path(__file__).resolve(),refs),'viewport':[shell.width,shell.height],'comparisons':comparisons,'inventory':inventory,'failed':sum(bool(c['differing_pixels']) for c in comparisons)}
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return bool(report['failed'])
if __name__=='__main__':raise SystemExit(main())
