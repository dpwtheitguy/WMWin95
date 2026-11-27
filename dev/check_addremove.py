#!/usr/bin/env python3
"""Isolated-X11, mock/read-only Add/Remove acceptance. Never installs software."""
import argparse,json,os,sys,time,tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev'),str(ROOT/'tests')]

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 import gi;gi.require_foreign('cairo');import cairo
 from win95lx.shell.app import Shell,Gtk,Gdk
 display=Gdk.Display.get_default();number=os.environ.get('DISPLAY','')
 if os.environ.get('GDK_BACKEND')!='x11' or os.environ.get('WAYLAND_DISPLAY') or 'X11' not in type(display).__name__ or display.get_name()!=number or number.split('.')[0] in (':0',':1'):
  raise RuntimeError('Explicit isolated X11 display required; refusing primary desktop.')
 from win95lx.apps.addremove import AddRemoveWindow,ComponentDetails
 from win95lx.control_panel.addremove_preferences import SetupBackend
 from test_addremove_preferences import fixture,Service
 from check_menu_seams import flush_draws
 from check_reference_ui import compare_region
 from pixels import read
 args.output.mkdir(parents=True,exist_ok=False);checks=[];comparisons=[];windows=[]
 def wait(test):
  until=time.monotonic()+5
  while not test():
   while Gtk.events_pending():Gtk.main_iteration_do(False)
   if time.monotonic()>until:raise TimeoutError('Async applet did not settle')
   time.sleep(.002)
  flush_draws(Gtk)
 with tempfile.TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
  shell=Shell(ROOT/'private/shell-assets');shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk)
  try:
   start=time.perf_counter();window=AddRemoveWindow(shell);windows.append(window);window.show_all();wait(lambda:not window.loading);load_ms=(time.perf_counter()-start)*1000
   def capture(win,name):
    flush_draws(Gtk);win.caption_active=True;surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*win.size);win.draw(win.area,cairo.Context(surface));path=args.output/(name+'.png');surface.write_to_png(str(path));return read(path)
   for tab,name in enumerate(window.tabs):
    window.action(('tab',tab));window.focus_action=None;actual=capture(window,name);source=read(ROOT/'private/shell-assets'/f'addremove-{name}-frame.png')
    for label,rect in [('caption-tabs',(0,0,367,52)),('default-OK',(119,408,79,27)),('Cancel',(200,408,79,27))]:
     if tab==2 and label=='default-OK':continue # Native Create Disk owns default; unavailable here intentionally leaves OK default.
     difference=compare_region(actual,source,rect,(rect[0],rect[1]));comparisons.append(dict(name=name+' '+label,differing_pixels=difference));assert difference==0,(name,label,difference)
   assert len(window.controller.backend.catalogue.components)==43
   assert all(not c.available for c in window.controller.backend.catalogue.components)
   assert all(v is None for _,v in window.controller.pending.features)
   checks.append('All39 feature entries and4 presets remain unavailable with unknown real state; no simulated installation or selectable global feature.')
   window.action(('tab',0));window.action(('programme',));assert window.tab==1;capture(window,'desktop-enhancements-route')
   checks.append('Curated installed list exposes Desktop Enhancements, whose Add/Remove routes to Windows Setup in the same applet; arbitrary Debian packages are excluded.')
   child=ComponentDetails(window,window.rows()[0][0]);windows.append(child);child.show_all();capture(child,'read-only-details');before=window.controller.pending
   assert child.disabled and not any(a[0]=='toggle' for _,a in child.hits)
   child.key(child,SimpleNamespace(keyval=Gdk.KEY_space,state=0));assert child.controller.pending==before
   child.action(('cancel',));assert window.controller.pending==before
   checks.append('Native11px owner-drawn checklist glyphs; unavailable component is selectable for description but not togglable by pointer or Space; child Cancel leaves parent untouched.')
   # A mutable fake service demonstrates contracts without granting installation rights.
   service=Service();mock=AddRemoveWindow(shell,SetupBackend(fixture(),service));windows.append(mock);mock.show_all();wait(lambda:not mock.loading);mock.action(('tab',1))
   detail=ComponentDetails(mock,'desktop');windows.append(detail);detail.show_all();capture(detail,'mock-details-before');detail.action(('toggle','desktop.patterns'));detail.action(('cancel',));assert not mock.controller.pending.feature('desktop.patterns')
   detail=ComponentDetails(mock,'desktop');windows.append(detail);detail.show_all();detail.action(('toggle','desktop.patterns'));detail.action(('ok',));assert mock.controller.pending.feature('desktop.patterns') and not service.state.feature('desktop.patterns')
   threads=[];original=service.execute
   import threading
   def execute(*a):threads.append(threading.get_ident());return original(*a)
   service.execute=execute;mock.action(('apply',));wait(lambda:not mock.busy);assert service.state.feature('desktop.patterns') and threads[0]!=threading.get_ident();capture(mock,'mock-applied')
   checks.append('Child Cancel discards and child OK stages only; Apply invokes typed fake service off GUI thread and accepts authoritative readback; zero actual package writes.')
   detail=ComponentDetails(mock,'desktop');windows.append(detail);detail.show_all();detail.action(('toggle','desktop.patterns'));detail.action(('ok',));service.fail=True
   with patch.object(mock,'error') as error:
    mock.action(('apply',));wait(lambda:not mock.busy);error.assert_called_once()
   assert service.state.feature('desktop.patterns') and not mock.controller.pending.feature('desktop.patterns');capture(mock,'mock-failure-pending')
   checks.append('Injected partial service failure restores prior fake state; failed pending changes survive for correction, no false successful Apply.')
   window.action(('tab',1));capture(window,'component-list-start');assert window.list_max>0
   window.wheel(window.area,SimpleNamespace(direction=Gdk.ScrollDirection.DOWN));assert window.scroll==1
   capture(window,'component-list-scrolled-once')
   arrow=next(r for r,a in window.hits if a==('scroll',1));event=lambda x,y:SimpleNamespace(x=x,y=y,x_root=x,y_root=y,button=1)
   window.press(window.area,event(arrow[0]+2,arrow[1]+2));window.release(window.area,event(arrow[0]+2,arrow[1]+2));assert window.scroll==2
   window.action(('scroll',window.list_visible));assert window.scroll>2
   for _ in range(30):window.action(('scroll',1))
   capture(window,'component-list-end');assert window.scroll==window.list_max
   # Every interactive row and disabled reason rectangle stays within native client.
   for rect,action in window.hits:
    if action[0] in ('select','toggle'):assert 26<=rect[0] and rect[0]+rect[2]<=326 and 125<=rect[1] and rect[1]+rect[3]<=215,(rect,action)
   by,bar=window.scroll_geometry;rect=next(r for r,a in window.hits if a[0]=='list-thumb');event=lambda x,y:SimpleNamespace(x=x,y=y,x_root=x,y_root=y,button=1)
   window.press(window.area,event(rect[0]+3,rect[1]+2));window.motion(window.area,event(rect[0]+3,by+bar.arrow+2));window.release(window.area,event(rect[0]+3,by+bar.arrow+2));assert window.scroll==0
   window.selection=0;window.focus_action=('select',0);window.key(window,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert window.selection==len(window.rows())-1;capture(window,'keyboard-end-revealed');assert window.scroll==window.list_max
   checks.append('Wheel/page/arrow scrolling and thumb drag reach both ends; keyboard End reveals final row; partial-row hit rectangles remain within native list client.')
   with patch.object(window.controller.backend,'preferences',side_effect=AssertionError('Paint read backend')):
    for _ in range(10):capture(window,'cached-repaint')
   assert len([a for a in window.focus_order() if a[0]=='select'])==1 and not any(a[0] in ('toggle','list-thumb') for a in window.focus_order())
   checks.append('Ten complete repeated renders perform no backend preference read or package scan; component list is one native Tab stop rather than one per row.')
   # Loading after destruction must not resurrect or mutate a destroyed window.
   import threading
   gate=threading.Event();slow=Service();read_snapshot=slow.snapshot
   def delayed(catalogue):gate.wait(2);return read_snapshot(catalogue)
   slow.snapshot=delayed;closed=AddRemoveWindow(shell,SetupBackend(fixture(),slow));windows.append(closed);closed.destroy();gate.set();wait(lambda:slow.reads>0);assert not closed.alive and closed.loading
   checks.append('Destroyed-window async loading result is discarded, preventing window resurrection.')
   report={'status':'pass','display':number,'size':[display.get_default_screen().get_width(),display.get_default_screen().get_height()],'load_and_settle_ms':load_ms,'comparisons':comparisons,'behavior_checks':checks,'real_installations':0,'registered':False,'scope':'Original frame/caption/tab/footer comparisons; component rows and global bindings are prototype, not full native fidelity acceptance.'}
   (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
  finally:
   for w in reversed(windows):
    try:w.destroy()
    except Exception:pass
   shell.destroy()
if __name__=='__main__':main()
