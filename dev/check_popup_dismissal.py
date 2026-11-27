#!/usr/bin/env python3
"""Real X11 pointer regression for shared dropdown grabs and event replay."""
import argparse,ctypes as C,ctypes.util,json,os,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests'),str(ROOT/'dev')]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False)
import gi;gi.require_foreign('cairo')
from win95lx.shell.app import Shell,Gtk,Gdk
from win95lx.apps.multimedia import MultimediaWindow
from win95lx.control_panel.audio_preferences import PulseAudio
from test_audio_preferences import FakePulse
from check_menu_seams import flush_draws
assert 'X11' in type(Gdk.Display.get_default()).__name__ and Gdk.Display.get_default().get_name()==os.environ.get('DISPLAY'),'Use isolated matching X11 display'
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p;x.XSync.argtypes=[C.c_void_p,C.c_int];x.XCloseDisplay.argtypes=[C.c_void_p]
xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong];xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
display=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert display
checks=[]
def click(px,py):
    xt.XTestFakeMotionEvent(display,0,px,py,0);xt.XTestFakeButtonEvent(display,1,1,0);xt.XTestFakeButtonEvent(display,1,0,0);x.XSync(display,False);flush_draws(Gtk)
with TemporaryDirectory() as folder,patch('pathlib.Path.home',return_value=Path(folder)):
    shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
    window=MultimediaWindow(shell,PulseAudio(FakePulse().run));window.show_all();flush_draws(Gtk)
    def open_popup():
        window.present();window.action(('tab',0));flush_draws(Gtk);window.action(('device','sinks'));flush_draws(Gtk)
        popup=window.popup_window;assert popup.get_visible() and Gtk.grab_get_current() is popup;return popup
    try:
        popup=open_popup();left,top=window.get_position();click(left+100,top+38)
        assert popup.finished and Gtk.grab_get_current() is None,'Outside tab click stranded grab'
        assert window.tab==1,('Initiating outside click did not switch tab',window.tab)
        checks.append('Open playback dropdown then click Video tab: popup dismissed and same click switched tab')
        popup=open_popup();popup.key(popup,type('Key',(),{'keyval':Gdk.KEY_Escape})());flush_draws(Gtk)
        assert popup.finished and Gtk.grab_get_current() is None;checks.append('Escape releases grab')
        popup=open_popup();popup.key(popup,type('Key',(),{'keyval':Gdk.KEY_Return})());flush_draws(Gtk)
        assert popup.finished and Gtk.grab_get_current() is None;checks.append('Return commits selection and releases grab')
        popup=open_popup();px,py=popup.get_position();click(px+10,py+7)
        assert popup.finished and Gtk.grab_get_current() is None;checks.append('Actual pointer selection commits and releases grab')
        popup=open_popup();other=Gtk.Window();other.set_decorated(False);other.set_default_size(80,60);other.move(5,30)
        area=Gtk.DrawingArea();area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK);other.add(area);hits=[];area.connect('button-press-event',lambda *_:hits.append(1) or True);other.show_all();window.present();popup.present();flush_draws(Gtk)
        click(25,50);assert popup.finished and Gtk.grab_get_current() is None;assert len(hits)==1,('Outside click should reach another window exactly once',hits)
        other.destroy();checks.append('Outside click reaches another GTK window exactly once without a stuck grab')
        popup=open_popup();popup.key(popup,type('Key',(),{'keyval':Gdk.KEY_Tab,'state':0})());flush_draws(Gtk)
        assert popup.finished and Gtk.grab_get_current() is None;checks.append('Tab closes dropdown and transfers keyboard focus')
        popup=open_popup();other=Gtk.Window();other.show_all();other.present();other.get_window().focus(Gdk.CURRENT_TIME);flush_draws(Gtk)
        assert popup.finished and Gtk.grab_get_current() is None;other.destroy();checks.append('Focus transfer closes popup without stealing focus back')
        from win95lx.apps.fonts import FontsWindow
        class EmptyFonts:
            def inventory(self):return ()
            def removal_reason(self,path):return 'Read-only fixture'
        fonts=FontsWindow(shell,EmptyFonts());fonts.show_all();flush_draws(Gtk);fonts.command(('menu','File'));flush_draws(Gtk)
        menu=fonts.menu_popup;assert menu and Gtk.grab_get_current() is menu
        fx,fy=fonts.get_position();click(fx+78,fy+30)
        assert menu.closed and fonts.menu_popup is not None and fonts.menu_popup is not menu
        assert Gtk.grab_get_current() is fonts.menu_popup;fonts.menu_popup.finish();assert Gtk.grab_get_current() is None
        checks.append('Font File menu switches to View with the initiating outside click')
        fonts.command(('menu','File'));flush_draws(Gtk);menu=fonts.menu_popup;fonts.destroy();flush_draws(Gtk)
        assert menu.closed and Gtk.grab_get_current() is None;checks.append('Font menu releases grab when its parent is destroyed')
        popup=open_popup();window.destroy();flush_draws(Gtk);assert popup.finished and Gtk.grab_get_current() is None;window=None;checks.append('Destroying parent closes popup and releases grab')
    finally:
        if window:window.destroy()
        shell.disconnect_by_func(Gtk.main_quit);shell.destroy();x.XCloseDisplay(display)
report={'checks':checks,'failed':0,'display':os.environ['DISPLAY']};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
