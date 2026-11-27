#!/usr/bin/env python3
"""Isolated fake-service Network GUI regression; never changes real networking."""
import argparse,json,sys,time
from pathlib import Path
from dataclasses import replace
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    gi.require_version("GdkX11","3.0")
    from gi.repository import GdkX11
    import os
    display=Gdk.Display.get_default()
    if not isinstance(display,GdkX11.X11Display) or display.get_name()!=os.environ.get("DISPLAY"):raise SystemExit("The requested isolated X11 display is required")
    from win95lx.apps.network import NetworkWindow,TCPIPWindow
    from win95lx.control_panel.network_preferences import NetworkState,Connection,IPv4Config
    from check_menu_seams import flush_draws
    from check_reference_ui import compare_region
    from pixels import read
    identifier='15f427dd-57f1-4a02-9c2f-3764d6230565'
    class Fixture:
        def __init__(self):self.value=NetworkState('win95lx-dev',(Connection(identifier,'Ethernet adapter','w95uat0','dummy',IPv4Config(),active=False),));self.calls=[]
        def preferences(self):return self.value
        def apply(self,pending,baseline):self.calls.append((pending,baseline));self.value=pending
        def restore(self,state):self.value=state
    backend=Fixture();checks=[];comparisons=[]
    with TemporaryDirectory() as temporary,patch('pathlib.Path.home',return_value=Path(temporary)):
        shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
        started=time.perf_counter();window=NetworkWindow(shell,backend);window.show_all();flush_draws(Gtk);open_ms=(time.perf_counter()-started)*1000
        def capture(win,name):
            flush_draws(Gtk);surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*win.size);win.caption_active=True;win.draw(win.area,cairo.Context(surface));path=args.output/(name+'.png');surface.write_to_png(str(path));return read(path)
        try:
            actual=capture(window,'network-configuration')
            source=read(ROOT/'private/shell-assets/network-configuration-frame.png')
            for label,rect in (('caption-tabs',(0,0,366,52)),('buttons',(0,420,366,40))):
                difference=compare_region(actual,source,rect,(rect[0],rect[1]));comparisons.append({'region':label,'differing_pixels':difference});assert difference==0,(label,difference)
            for tab,name in ((1,'identification'),(2,'access')):window.action(('tab',tab));capture(window,'network-'+name)
            window.action(('tab',0));child=TCPIPWindow(window,backend.value.connections[0]);child.show_all();flush_draws(Gtk)
            for tab,name in enumerate(child.tabs):child.action(('tab',tab));capture(child,'tcpip-'+name)
            # Native radio focus/mnemonic/pointer transitions stay pending-only.
            child.action(('tab',6));child.focus_action=('method','auto');capture(child,'radio-auto-focused')
            child.key(child,SimpleNamespace(keyval=Gdk.KEY_Right,state=0));assert child.pending.method=='manual'
            child.key(child,SimpleNamespace(keyval=Gdk.KEY_Right,state=0));assert child.pending.method=='auto'
            child.focus_action=('ip','address',0)
            child.key(child,SimpleNamespace(keyval=Gdk.KEY_s,state=Gdk.ModifierType.MOD1_MASK));assert child.pending.method=='manual' and child.focus_action==('method','manual')
            capture(child,'radio-manual-focused')
            child.press(child.area,SimpleNamespace(button=1,x=40,y=177));capture(child,'radio-auto-pressed')
            child.motion(child.area,SimpleNamespace(x=340,y=390));assert not child.press_inside
            child.release(child.area,SimpleNamespace(button=1,x=340,y=390));assert child.pending.method=='manual'
            child.press(child.area,SimpleNamespace(button=1,x=40,y=177));child.release(child.area,SimpleNamespace(button=1,x=40,y=177));assert child.pending.method=='auto'
            checks.append('Radio native focus/mnemonics, two-member arrow wrap, press-drag-out cancellation and click selection remain pending-only')
            child.action(('tab',6));child.action(('method','manual'))
            for name,value in (('address','192.0.2.10'),('netmask','255.255.255.0')):
                child.focus_action=('ip',name,0)
                for char in value:child.key(child,SimpleNamespace(keyval=Gdk.unicode_to_keyval(ord(char)),state=0))
                assert child.entries[name].text==value
            typed=capture(child,'tcpip-manual-address')
            reference=read(ROOT/'private/screenshots/network-native-reviewed-20261126/tcpip-ip-manual-typed-settled.png')
            # Independently captured native IPAddress interior, no caret/selection.
            difference=compare_region(typed,reference,(172,301,131,17),(143,234))
            comparisons.append({'region':'native System font typed IPAddress interior','differing_pixels':difference,'rectangle':[143,234,131,17]});assert difference==0,('IPAddress interior',difference)
            checks.append('Original vgasys.fon System font and typed IPv4 interior match native screenshot exactly')
            for label,native_rect,actual_origin in (('Specify-IP checked radio and complete label',(65,264,125,16),(36,197)),('Automatic-IP unchecked radio and complete label',(65,240,248,16),(36,173))):
                difference=compare_region(typed,reference,native_rect,actual_origin);comparisons.append({'region':label,'differing_pixels':difference});assert difference==0,(label,difference)
            child.focus_action=('ip','address',3);child.key(child,SimpleNamespace(keyval=Gdk.KEY_Tab,state=0));assert child.focus_action==('ip','netmask',0)
            clipboard=Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD);clipboard.set_text('999.1.2.3',-1)
            with patch.object(child,'error') as error:
                child.key(child,SimpleNamespace(keyval=Gdk.KEY_v,state=Gdk.ModifierType.CONTROL_MASK));error.assert_called_once()
            assert child.entries['netmask'].text=='255.255.255.0'

            child.action(('tab',4));child.entries['gateway'].key('','192.0.2.1');child.action(('gateway-add',));assert child.pending.gateway=='192.0.2.1'
            child.action(('tab',3));child.action(('dns-mode',True));child.entries['dns'].key('','192.0.2.53');child.action(('dns-add',))
            child.text_entries['suffix'].text='example.invalid';child.action(('search-add',));capture(child,'tcpip-dns-configured')
            assert child.pending.dns==('192.0.2.53',);assert child.pending.search==('example.invalid',)
            child.action(('ok',));assert not backend.calls;assert window.controller.pending.connections[0].ipv4.address=='192.0.2.10'
            window.controller.cancel();assert window.controller.pending==window.controller.applied
            checks.append('Typed segmented IPv4 and subnet mask, gateway add, manual DNS and suffix add; child OK updates only parent pending state; parent Cancel discards all changes without a service write')
            child=TCPIPWindow(window,backend.value.connections[0]);child.show_all();flush_draws(Gtk);child.action(('method','manual'));child.entries['address'].key('','192.0.2.22');child.entries['netmask'].key('','255.255.255.0');child.action(('ok',));window.action(('ok',))
            deadline=time.monotonic()+3
            while window.busy and time.monotonic()<deadline:flush_draws(Gtk);time.sleep(.01)
            assert len(backend.calls)==1;assert backend.value.connections[0].ipv4.address=='192.0.2.22'
            class FailingFixture(Fixture):
                def apply(self,pending,baseline):self.calls.append((pending,baseline));raise NetworkError('The network setting could not be applied; previous settings were retained.')
            from win95lx.control_panel.network_preferences import NetworkError
            failing=FailingFixture();failed_window=NetworkWindow(shell,failing);failed_window.show_all();flush_draws(Gtk)
            failed_window.controller.pending=failed_window.controller.pending.change_connection(identifier,ipv4=IPv4Config(method='manual',address='192.0.2.99',netmask='255.255.255.0'))
            with patch.object(failed_window,'error') as error:
                failed_window.action(('ok',));deadline=time.monotonic()+3
                while failed_window.busy and time.monotonic()<deadline:flush_draws(Gtk);time.sleep(.01)
                error.assert_called_once()
            assert not failed_window.busy and failed_window.get_visible() and failed_window.area.get_sensitive()
            assert failed_window.controller.applied==failing.value and failed_window.controller.pending!=failed_window.controller.applied
            capture(failed_window,'failed-apply-preserves-pending');failed_window.action(('cancel',));assert failing.value.connections[0].ipv4.method=='auto'
            checks.append('Failed asynchronous Apply retains previous fake service state, keeps pending edits/window, restores controls; Cancel discards pending state')
            display=[shell.get_screen().get_width(),shell.get_screen().get_height()]
            checks.append('Asynchronous parent OK calls fake service exactly once, verifies state and closes; no real network calls')
        finally:
            for top in list(Gtk.Window.list_toplevels()):
                if top is not shell:top.destroy()
            shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),[ROOT/'private/shell-assets/network-configuration-frame.png',ROOT/'private/shell-assets/network-ip-system.fnt',ROOT/'private/screenshots/network-native-reviewed-20261126/tcpip-ip-manual-typed-settled.png',ROOT/'private/shell-assets/network-radio-states.json']),'display':display,'fixture_open_and_settle_ms':round(open_ms,3),'checks':checks,'comparisons':comparisons,'failed':0,'service_scope':'Fake service only; actual NetworkManager effects and nonadmin policy NOT accepted.','pixel_scope':'Named caption/tab/button regions, typed IPv4 interior and same-state normal Network radios/labels accepted; independent16-state radio primitive checked separately; complete dynamic pages remain unaccepted.'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
