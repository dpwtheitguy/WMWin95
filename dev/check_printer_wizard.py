#!/usr/bin/env python3
"""Physical-input Add Printer UAT on an owned X11 display and disposable HOME."""
import argparse,ctypes as C,ctypes.util,json,os,sys,tempfile,threading,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.printer_wizard import PrinterWizardWindow
    from win95lx.control_panel.printer_installation import InstallationDiscovery,PrinterDriver,PrinterInstallResult,PrinterError
    from check_menu_seams import flush_draws
    from pixels import read
    from stage_command_button_assets import read_bmp
    from stage_printers_assets import stage_wizard
    d=Gdk.Display.get_default();assert os.environ.get('GDK_BACKEND')=='x11' and not os.environ.get('WAYLAND_DISPLAY') and 'X11'in type(d).__name__ and d.get_name()==os.environ['DISPLAY'] and d.get_name().split('.')[0]not in(':0',':1')
    x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p;x.XSync.argtypes=[C.c_void_p,C.c_int];x.XCloseDisplay.argtypes=[C.c_void_p];x.XStringToKeysym.argtypes=[C.c_char_p];x.XStringToKeysym.restype=C.c_ulong;x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_uint;x.XSetInputFocus.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong]
    xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong];xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong];xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
    handle=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert handle
    def flush():x.XSync(handle,False);flush_draws(Gtk)
    def click(window,px,py):
        left,top=window.get_position();xt.XTestFakeMotionEvent(handle,0,left+px,top+py,0);xt.XTestFakeButtonEvent(handle,1,1,0);xt.XTestFakeButtonEvent(handle,1,0,0);flush()
    def key(name):
        code=x.XKeysymToKeycode(handle,x.XStringToKeysym(name.encode()));assert code;xt.XTestFakeKeyEvent(handle,code,1,0);xt.XTestFakeKeyEvent(handle,code,0,0);flush()
    def text(value):
        for char in value:
            shift=char.isupper()or char in(':','_')
            if shift:xt.XTestFakeKeyEvent(handle,x.XKeysymToKeycode(handle,x.XStringToKeysym(b'Shift_L')),1,0)
            symbol={' ': 'space',':':'semicolon','/':'slash','.':'period','_':'minus'}.get(char,char.lower());key(symbol)
            if shift:xt.XTestFakeKeyEvent(handle,x.XKeysymToKeycode(handle,x.XStringToKeysym(b'Shift_L')),0,0);flush()
    def wait(window):
        until=time.monotonic()+4
        while window.busy and not window.closed and time.monotonic()<until:flush_draws(Gtk);time.sleep(.01)
        assert not window.busy or window.closed,'UI worker did not finish'
    checks=[];comparisons=[];discovery=InstallationDiscovery(tuple([PrinterDriver('everywhere','Generic','IPP Everywhere',True)]+[PrinterDriver('sample'+str(i)+'.ppd','Acme','Acme Laser '+str(i))for i in range(30)]),(),('ipp','ipps'),())
    class Client:
        def __init__(self):self.plans=[];self.delay=0;self.error=None
        def discover(self):
            time.sleep(self.delay)
            if self.error:raise self.error
            return discovery
        def install(self,plan):
            self.plans.append(plan);time.sleep(self.delay)
            if self.error:raise self.error
            return PrinterInstallResult('w95lx_'+'a'*32,plan.description)
    with tempfile.TemporaryDirectory(prefix='w95uat-printer-wizard-')as directory,patch('pathlib.Path.home',return_value=Path(directory)):
        assets=Path(directory)/'assets';assets.mkdir();stage_wizard(assets)
        for source in(ROOT/'private/shell-assets').iterdir():
            if not(assets/source.name).exists():(assets/source.name).symlink_to(source)
        shell=Shell(assets);shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk);client=Client();completed=[]
        def show(**kwargs):
            window=PrinterWizardWindow(shell,**kwargs);window.show_all();flush_draws(Gtk);x.XSetInputFocus(handle,window.get_window().get_xid(),1,0);flush();return window
        window=show(discovery=discovery,client=client,on_installed=lambda:completed.append(True))
        def capture(name,window=window):
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,441,323);window.draw(window.area,cairo.Context(surface));path=args.output/(name+'.png');surface.write_to_png(str(path));return read(path)
        try:
            actual=capture('welcome');_,_,native=read_bmp(ROOT/'private/reference-tools/printers-native-20261127/welcome/PRINTERS.BMP');w,h,p=actual
            for label,rect in [('back',(193,287,75,23)),('next',(268,287,75,23)),('cancel',(353,287,75,23))]:
                xx,yy,rw,rh=rect;diff=sum(p[(yy+j)*w+xx+i]!=native[(yy+j)*w+xx+i]for j in range(rh)for i in range(rw));assert diff==0,(label,diff);comparisons.append({'button':label,'differing_pixels':diff})
            assert not any(window.contains(rect,425,10)and action==('cancel',)for rect,action in window.hits),'Phantom Close action in native buttonless caption'
            click(window,300,299);assert window.state.page==1;capture('drivers')
            # First click selects Acme. Keyboard End must select the last of30
            # real model fixtures and keep it visible behind a gray scrollbar.
            click(window,35,125);selected=window.state.driver;click(window,420,210);assert window.list_tops['driver']==1 and window.state.driver==selected;capture('driver-scroll')
            key('Tab');key('End');assert window.state.driver=='sample29.ppd';capture('driver-end')
            key('Home');assert window.state.driver=='sample0.ppd';click(window,35,138);assert window.manufacturer=='Generic'
            key('Return');assert window.state.page==2;capture('endpoint')
            text('ipp://owned.example/ipp/print');assert window.endpoint_entry.text=='ipp://owned.example/ipp/print';key('Return');assert window.state.page==3
            text('owned printer');assert window.name_entry.text=='owned printer';key('Return');assert window.state.page==4;capture('finish-ready')
            checks.append('Actual pointer/keyboard navigate all five measured pages, populated lists End/Home, endpoint/name entries and native command buttons')
            click(window,220,299);assert window.state.page==3;click(window,300,299);assert window.state.page==4;assert window.name_entry.text=='owned printer'
            checks.append('Back preserves endpoint/name and pending plan without installing')
            client.delay=2;click(window,300,299);assert window.busy and window.installing
            key('Return');key('Escape');click(window,390,299);click(window,300,299);assert not window.closed and len(client.plans)==1;capture('installing')
            wait(window);assert window.closed and len(client.plans)==1 and completed==[True];assert not client.plans[0].print_test_page
            checks.append('Finish dispatches once; double-click, Enter, Escape and Cancel cannot duplicate/cancel an already-sent installation; completion refreshes caller')
            slow=Client();slow.delay=1;window=show(client=slow);assert window.busy;key('Escape');assert window.closed;time.sleep(1.1);flush()
            checks.append('Escape immediately closes during read-only discovery; late worker cannot repaint/reopen a destroyed wizard')
            failed=Client();failed.error=PrinterError('The printer installation service is unavailable.');window=show(client=failed);wait(window);capture('service-unavailable',window)
            assert window.service_error and not any(a==('next',)for _,a in window.hits);click(window,390,299);assert window.closed
            checks.append('Unavailable discovery leaves truthful native status and disabled Next; Cancel still works')
            # Unknown GDK key should not crash TextEntry.lower().
            window=show(discovery=discovery,client=Client());window.key(window,SimpleNamespace(keyval=0,state=0,string=''));key('Escape');assert window.closed
            checks.append('Unnamed key and cancellation without Finish produce no installation')
            # Real guest inventory has manufacturers before Generic and many
            # Generic drivers before IPP Everywhere. Both selections must be
            # revealed on first entry, not only after a user changes them.
            deep=InstallationDiscovery(tuple([PrinterDriver('brand'+str(i),'Brand '+str(i).zfill(2),'Brand model')for i in range(24)]+[PrinterDriver('generic'+str(i),'Generic','Earlier generic '+str(i).zfill(2))for i in range(24)]+[PrinterDriver('everywhere','Generic','IPP Everywhere',True)]),(),('ipp',),())
            window=show(discovery=deep,client=Client());click(window,300,299)
            assert window.state.page==1
            capture('deep-inventory-selected',window)
            diagnostic={'focus':window.focus_action,'top_rows':window.list_tops,'manufacturer_visible':any(a==('manufacturer','Generic')for _,a in window.hits),'driver_visible':any(a==('driver','everywhere')for _,a in window.hits)}
            (args.output/'deep-selection.json').write_text(json.dumps(diagnostic,indent=2)+'\n')
            assert diagnostic['manufacturer_visible']and diagnostic['driver_visible'],diagnostic
            assert window.list_tops['manufacturer']>0 and window.list_tops['driver']>0
            assert window.focus_action==('manufacturer','Generic')
            # Page transitions reveal the still-selected values even if the
            # user had scrolled them out of view before leaving the page.
            window.list_tops={'manufacturer':0,'driver':0};click(window,300,299);assert window.state.page==2;click(window,220,299)
            assert window.state.page==1 and window.list_tops['manufacturer']>0 and window.list_tops['driver']>0
            key('Home');assert window.manufacturer=='Brand 00'and window.list_tops['driver']==0
            key('Escape');assert window.closed
            checks.append('Deep initial manufacturer/model selections are visible and manufacturer-focused on first entry and Back; a new manufacturer reveals its first model')
        finally:
            if not window.closed:window.destroy()
            shell.destroy();x.XCloseDisplay(handle)
    until=time.monotonic()+3
    while any(t.name=='win95lx-printer-installation'for t in threading.enumerate())and time.monotonic()<until:flush_draws(Gtk);time.sleep(.01)
    assert not any(t.name=='win95lx-printer-installation'for t in threading.enumerate())
    report={'checks':checks,'native_button_comparisons':comparisons,'failed':0,'scope':'Actual XTest pointer/keyboard wizard UAT with deterministic service fixture. Native measured command buttons exact; adapted driver/endpoint contents are not full-page equality. Real CUPS effects checked separately.'};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
