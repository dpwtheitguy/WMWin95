#!/usr/bin/env python3
"""Render real scrollbar consumers and inspect exposed tracks, not just thumbs."""
import argparse,json,os,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
import gi;gi.require_foreign('cairo');import cairo
from win95lx.shell.app import Shell,Gtk,Gdk
from win95lx.shell.widgets import Painter
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.apps.system import SystemWindow
from win95lx.apps.fonts import FontsWindow,FontPreview
from win95lx.apps.choice_dialog import ChoicePopup
from win95lx.control_panel.font_catalog import fontconfig
from check_menu_seams import flush_draws
from pixels import read
assert 'X11' in type(Gdk.Display.get_default()).__name__ and Gdk.Display.get_default().get_name()==os.environ.get('DISPLAY'),'Use the requested isolated X11 display'
checks=[];windows=[]
def capture(window,name,size=None):
    flush_draws(Gtk);size=size or window.get_size();surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*size);window.draw(window.area,cairo.Context(surface));file=a.output/(name+'.png');surface.write_to_png(str(file));return read(file)
def track(image,rect,style,label):
    w,h,pixels=image;x,y,rw,rh=rect
    colors={pixels[yy*w+xx][:3] for yy in range(y,y+rh) for xx in range(x,x+rw)}
    expected={(192,192,192),(255,255,255)} if style=='classic' else {(255,255,255)}
    assert colors==expected,(label,colors)
    checks.append({'consumer':label,'region':rect,'style':style,'colors':sorted(colors)})
with TemporaryDirectory() as folder,patch('pathlib.Path.home',return_value=Path(folder)):
    shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
    try:
        system=SystemWindow(shell);windows.append(system);system.devices=[type('Device',(),{'name':'Device '+str(i),'category':'System devices'})() for i in range(60)];system.tab=1;system.show_all()
        for label,value in [('top',0),('middle',20),('bottom',1000)]:
            system.scroll=value;image=capture(system,'system-devices-'+label,system.size)
            bar=system.device_bar();top=bar.thumb_top(system.scroll)
            begin,end=max(((16,top),(top+bar.thumb,bar.height-16)),key=lambda span:span[1]-span[0])
            y=92+begin
            track(image,(363,y,16,16),'window','Device Manager '+label)
        from types import SimpleNamespace
        system.scroll=0;bar=system.device_bar();system.press(system.area,SimpleNamespace(x=370,y=92+bar.thumb_top(0)+5,button=1))
        system.motion(system.area,SimpleNamespace(x=370,y=10000));assert system.scroll==bar.maximum
        system.release(system.area,SimpleNamespace(button=1));assert system.device_drag is None
        system.press(system.area,SimpleNamespace(x=370,y=92+bar.thumb_top(system.scroll)+5,button=1));system.motion(system.area,SimpleNamespace(x=370,y=-10000));system.release(system.area,SimpleNamespace(button=1));assert system.scroll==0
        system.wheel(system.area,SimpleNamespace(x=370,y=150,direction=Gdk.ScrollDirection.DOWN));assert system.scroll==3
        # Entire independently captured native bars, including frame, arrows,
        # thumb proportion and exposed white track; four real GetScrollInfo cases.
        from win95lx.assets.bitmap import BitmapFont
        for name,total,value in [('systop',21,0),('sysall',31,0),('sysmiddle',31,7),('sysend',31,15)]:
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,16,263);bar=VerticalScrollbar.for_page(263,total-16,16)
            bar.draw(Painter(cairo.Context(surface),shell.font),0,0,value,track='window');file=a.output/(name+'-native-bar.png');surface.write_to_png(str(file))
            actual=read(file);reference=read(ROOT/'private/system-scroll-20261126/reviewed-v2'/(name+'-scrollbar.png'))
            diff=sum(x[:3]!=y[:3] for x,y in zip(actual[2],reference[2]));assert actual[:2]==reference[:2] and diff==0,(name,diff)
            checks.append({'consumer':'Native Device Manager '+name,'differing_pixels':diff,'thumb_height':bar.thumb,'thumb_top':bar.thumb_top(value)})
        face=fontconfig().query(ROOT/'private/shell-assets/fonts-source-arial.ttf')[0]
        class Fixture:
            def inventory(self):return tuple(replace(face,path=Path(folder)/f'font{i}.ttf',family=f'Font {i:03}') for i in range(100))
            def removal_reason(self,path):return 'Read-only test fixture'
        fonts=FontsWindow(shell,Fixture());windows.append(fonts);fonts.show_all();flush_draws(Gtk)
        for label,value in [('top',0),('bottom',1000)]:
            fonts.scroll=value;image=capture(fonts,'fonts-'+label);w,h=fonts.get_size();bar=VerticalScrollbar(fonts.metrics()[4],fonts.metrics()[3]);top=44+bar.thumb_top(fonts.scroll);y=100 if not top<=100<top+21 else 140
            track(image,(w-22,y,16,16),'classic','Fonts '+label)
        preview=FontPreview(fonts,face);windows.append(preview);preview.show_all();image=capture(preview,'font-preview');w,h=preview.get_size();track(image,(w-22,h-110,16,16),'classic','Font preview')
        popup=ChoicePopup(system,(33,100,240,21),tuple('Choice '+str(i) for i in range(30)),0,lambda _:None);windows.append(popup);image=capture(popup,'choice-popup',(popup.width,popup.height));track(image,(popup.width-17,70,16,16),'classic','Shared ChoicePopup');popup.finish(None);windows.remove(popup)
        # Native white exceptions are checked against independent captured
        # frame pixels, not accepted merely because our renderer is white.
        for name,rect in [('system-devices-frame.png',(363,288,16,48)),('mouse-pointers-frame.png',(362,248,16,80)),('sounds-sounds-frame.png',(324,120,16,60)),('background-frame-clean.png',(265,326,16,36))]:
            track(read(shell.assets/name),rect,'window','Native exception '+name)
    finally:
        for window in reversed(windows):window.destroy()
        shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
report={'checks':checks,'failed':0,'scope':'Exposed track colors and real caller integration; not whole-control/native-pixel acceptance','resolution':[Gdk.Screen.get_default().get_width(),Gdk.Screen.get_default().get_height()]}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
