#!/usr/bin/env python3
"""Isolated rendered Control Panel resize/view/scroll regression evidence."""
import argparse,json,sys,tempfile,hashlib,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
import gi
gi.require_foreign('cairo');gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
from gi.repository import Gtk,Gdk,GdkX11
display=Gdk.Display.get_default()
if not isinstance(display,GdkX11.X11Display) or display.get_name()!=os.environ.get('DISPLAY'):raise SystemExit('The requested isolated X11 display is required')
import cairo
from win95lx.shell.app import Shell
from win95lx.shell import computer_view
from win95lx.explorer.namespace_layout import reveal
from win95lx.control_panel import catalog
from win95lx.shell.widgets import Painter
from check_menu_seams import flush_draws
checks=[];screens=[]
with tempfile.TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
 shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk);shell.open('control');win=shell.state.active
 def render(name):
  im=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw(shell.area,cairo.Context(im));path=a.output/(name+'.png');im.write_to_png(str(path));screens.append(name)
  x,y,w,h=win.namespace_viewport
  for hx,hy,hw,hh,action in shell.hits:
   if not name.startswith('before-') and action[0]=='item' and action[1] is win:
    assert x<=hx and y<=hy and hx+hw<=x+w and hy+hh<=y+h,(name,(hx,hy,hw,hh),(x,y,w,h))
  return im
 for width in (760,450,290):
  win.x,win.y,win.width,win.height=20,30,width,390
  for mode in ('large','small','list','details'):
   shell.action(('namespace-view',win,mode));render(f'{width}-{mode}')
   win.namespace_scroll=reveal(win.namespace_layout,len(catalog.entries())-1);render(f'{width}-{mode}-last')
   assert any(act[0]=='item' and act[1] is win and act[3]==catalog.entries()[-1][1] for *_,act in shell.hits)
 checks.append('24 resize/view/last-item states have bounded icon hit targets and reachable last item')
 # Historical before image is archived evidence, not generated from moving Git HEAD.
 # Keep the ongoing regression runnable in staged releases without a .git directory.
 win.x,win.y,win.width,win.height=100,65,450,310;win.namespace_view='large';win.namespace_scroll=(0,0)
 render('after-wrapped-clipped')
 win.width,win.height=500,350;render('restored-500x350');win.namespace_scroll=reveal(win.namespace_layout,len(catalog.entries())-1);render('restored-500x350-last')
 shell.item_selection=(win,'Regional Settings');render('regional-description-wrapped')
 win.namespace_scroll=(0,0);render('thumb-start');thumb=next(h for h in shell.hits if h[-1][0]=='namespace-thumb');hx,hy,hw,hh,act=thumb
 shell.action(act,SimpleNamespace(x=hx+2,y=hy+2));shell.motion(shell.area,SimpleNamespace(x=hx+2,y=hy+300));assert win.namespace_scroll[1]>0;shell.release(shell.area,SimpleNamespace(button=1,x=hx+2,y=hy+300));render('thumb-drag-bottom');checks.append('scrollbar thumb drag reaches overflow rows')
 # A namespace-only layer must leave every pixel outside its client viewport intact.
 from win95lx.shell.namespace_view import draw as draw_namespace
 win.namespace_view='large';win.namespace_scroll=(0,0)
 im=cairo.ImageSurface(cairo.FORMAT_RGB24,400,300);cr=cairo.Context(im);cr.set_source_rgb(0,0.5,0.5);cr.paint();before=bytes(im.get_data());shell.hits=[]
 draw_namespace(shell,Painter(cr,shell.font),win,catalog.entries(),50,40,120,120);im.flush();after=bytes(im.get_data());stride=im.get_stride()
 for yy in range(300):
  for xx in range(400):
   if not (50<=xx<170 and 40<=yy<160):assert before[yy*stride+xx*4:yy*stride+xx*4+4]==after[yy*stride+xx*4:yy*stride+xx*4+4],(xx,yy)
 checks.append('namespace layer changes zero pixels outside client rectangle including scrollbars')
 # Move after shrink: transformed hits must follow the new origin.
 win.x,win.y,win.width,win.height=330,180,290,300;render('moved-shrunk')
 shell.key(shell,SimpleNamespace(keyval=Gdk.KEY_End,state=0));render('keyboard-end-revealed');assert win.focus_item==catalog.labels()[-1]
 shell.key(shell,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));render('keyboard-home-revealed');assert win.focus_item==catalog.labels()[0]
 checks.append('keyboard End/Home select and reveal after shrink/move')
 # Preserving manual positions when Auto Arrange is disabled.
 win.width=760;render('manual-wide');positions=win.namespace_positions;shell.action(('namespace-auto',win));win.width=290;render('manual-narrow');assert win.namespace_positions==positions;assert win.namespace_layout.horizontal
 shell.action(('namespace-auto',win));render('auto-narrow');assert win.namespace_positions!=positions
 checks.append('manual arrangement freezes on resize; Auto Arrange reflows and provides overflow access')
 # All toolbar/address/Web toggles off still use bounded responsive renderer.
 win.toolbar=win.address_bar=win.web_view=False;render('classic-no-bands')
 checks.append('all bands disabled retains responsive clipped namespace view')
 shell.hide()
(a.output/'report.json').write_text(json.dumps({'checks':checks,'screenshots':screens,'scope':'Rendered isolated shell and input/model regression, not complete native pixel equality','sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in a.output.glob('*.png')}},indent=2)+'\n')
print(json.dumps({'checks':checks,'screenshots':len(screens)},indent=2))
