#!/usr/bin/env python3
"""Physical isolated-X11 Printers namespace integration; never installs queues."""
import argparse,ctypes as C,ctypes.util,json,os,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.printers import PrinterNamespace
    from win95lx.control_panel.printer_preferences import Printer,PrinterCapabilities,PrinterError
    from check_menu_seams import flush_draws
    from stage_printers_assets import stage
    d=Gdk.Display.get_default();assert os.environ.get('GDK_BACKEND')=='x11' and not os.environ.get('WAYLAND_DISPLAY') and 'X11'in type(d).__name__ and d.get_name()==os.environ['DISPLAY'] and d.get_name().split('.')[0]not in(':0',':1')
    x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p;x.XSync.argtypes=[C.c_void_p,C.c_int];x.XCloseDisplay.argtypes=[C.c_void_p];x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_uint
    xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong];xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong];xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
    handle=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert handle
    def click(px,py):
        xt.XTestFakeMotionEvent(handle,0,int(px),int(py),0);xt.XTestFakeButtonEvent(handle,1,1,0);xt.XTestFakeButtonEvent(handle,1,0,0);x.XSync(handle,False);flush_draws(Gtk)
    def key(name):
        code=x.XKeysymToKeycode(handle,Gdk.keyval_from_name(name));xt.XTestFakeKeyEvent(handle,code,True,0);xt.XTestFakeKeyEvent(handle,code,False,0);x.XSync(handle,False);flush_draws(Gtk)
    class Backend:
        user='w95uat'
        def __init__(self):self.calls=0;self.failed=False;self.empty=False
        def inventory(self):
            self.calls+=1
            if self.failed:raise PrinterError('The printing service is unavailable.')
            return()if self.empty else(Printer('Fixture','Injected fixture; not installed'),)
        def capabilities(self):return PrinterCapabilities(False,'Administrative authorization is not established.')
        def printer(self,name):return self.inventory()[0]
        def jobs(self,name):return()
    checks=[]
    with tempfile.TemporaryDirectory(prefix='w95uat-printers-shell-')as directory,patch('pathlib.Path.home',return_value=Path(directory)):
        assets=Path(directory)/'assets';stage(assets)
        for source in(ROOT/'private/shell-assets').iterdir():
            if not(assets/source.name).exists():(assets/source.name).symlink_to(source)
        shell=Shell(assets);assert shell.desktop_folder.is_dir(),'Fresh profile must initialize Desktop before creating shortcuts';shell.disconnect_by_func(Gtk.main_quit);backend=Backend();shell.printer_provider=PrinterNamespace(backend);shell.show_all();flush_draws(Gtk)
        def render(name):
            flush_draws(Gtk);surface=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw(shell.area,cairo.Context(surface));surface.write_to_png(str(args.output/(name+'.png')))
        def item(win,label):return next((xx+min(ww-1,10),yy+min(hh-1,10))for xx,yy,ww,hh,action in shell.hits if action[0]=='item'and action[1]is win and action[3]==label)
        def wait():
            until=time.monotonic()+3
            while getattr(shell,'printer_loading',False)and time.monotonic()<until:flush_draws(Gtk);time.sleep(.005)
            assert not getattr(shell,'printer_loading',False);flush_draws(Gtk)
        try:
            shell.open('control');win=shell.state.active;win.x=win.y=20;win.width=640;win.height=450;render('control-before')
            px,py=item(win,'Printers');click(px,py);click(px,py);wait();assert shell.state.active.kind=='printers';win=shell.state.active;render('printers-folder')
            assert win.title=='Printers' and shell.images['cpl-printers'].get_width()==32 and shell.small_images['cpl-printers'].get_width()==16
            assert shell.printer_namespace().entries()==(('printer-add','Add Printer',('printer-add',)),('printer','Fixture',('printer-queue','Fixture')))
            checks.append('Actual Control Panel Printers double-click navigates existing Explorer window to discovered queues')
            px,py=item(win,'Fixture');click(px,py);click(px,py);flush_draws(Gtk);assert 'printer:Fixture'in shell.accessory_windows;queue=shell.accessory_windows['printer:Fixture'];queue.destroy();flush_draws(Gtk);checks.append('Actual queue icon double-click opens independent real queue class using injected backend, not an installed mock printer')
            shell.present();shell.get_window().focus(Gdk.CURRENT_TIME);render('printers-return');px,py=item(win,'Fixture');click(px,py);key('Return');assert 'printer:Fixture'in shell.accessory_windows;shell.accessory_windows['printer:Fixture'].destroy();flush_draws(Gtk)
            shell.present();shell.get_window().focus(Gdk.CURRENT_TIME);before=backend.calls;key('F5');wait();assert backend.calls>before;checks.append('Physical Return opens selected queue and F5 refreshes backend inventory')
            backend.failed=True;key('F5');wait();render('printers-service-error');assert shell.printer_namespace().error and not shell.printer_namespace().printers;assert not any(a[0]=='item'and a[1]is win and a[3]=='Fixture'for *_,a in shell.hits);checks.append('Service failure removes stale queue entry and renders explicit error')
            backend.failed=False;backend.empty=True;key('F5');wait();render('printers-empty');assert not shell.printer_namespace().error and not shell.printer_namespace().printers;assert [label for _,label,_ in shell.printer_namespace().entries()]==['Add Printer'];checks.append('Actual empty inventory shows no fake installed printers')
            from win95lx.control_panel.printer_installation import InstallationDiscovery,PrinterDriver
            class InstallationClient:
                installs=0
                def discover(self):return InstallationDiscovery((PrinterDriver('everywhere','Generic','IPP Everywhere',True),),(),('ipp',),())
                def install(self,plan):self.installs+=1;raise AssertionError('Cancel must never install a printer.')
            client=InstallationClient()
            with patch('win95lx.apps.printer_wizard.PrinterInstallationClient',return_value=client):
                px,py=item(win,'Add Printer');click(px,py);click(px,py)
                assert 'printer-wizard'in shell.accessory_windows
                wizard=shell.accessory_windows['printer-wizard'];assert wizard.get_title()=='Add Printer Wizard'
                deadline=time.monotonic()+3
                while wizard.busy and time.monotonic()<deadline:flush_draws(Gtk);time.sleep(.005)
                assert not wizard.busy;key('Escape');flush_draws(Gtk)
                assert 'printer-wizard'not in shell.accessory_windows and client.installs==0
            checks.append('Physical Add Printer opens actual wizard through registered factory; Escape removes task and performs no installation')
            cached=Printer('w95lx_'+'a'*32,'Cached Human Printer')
            provider=PrinterNamespace(backend);provider.printers=(cached,)
            with patch.object(backend,'printer',return_value=cached):
                queue=provider.open(shell,cached.name)
                assert queue.get_title()=='Cached Human Printer','Initial paint must use the known display name without waiting for CUPS.'
                queue.destroy();flush_draws(Gtk)
            checks.append('New queue uses cached human caption immediately, before asynchronous service readback')
            from win95lx.shell.widgets import Painter
            observed=[];surface=cairo.ImageSurface(cairo.FORMAT_RGB24,100,100);painter=Painter(cairo.Context(surface),shell.font);original=painter.image
            from win95lx.shell.widgets import BLACK,LIGHT
            label_colors=[];original_text=painter.text
            def record_text(text,x,y,color=BLACK,**kwargs):
                if text=='Add Printer':label_colors.append(color)
                return original_text(text,x,y,color,**kwargs)
            painter.text=record_text
            for selected in (False,True):shell.icon(painter,'printer-add','Add Printer',0,0,('test',),selected)
            assert label_colors==[BLACK,LIGHT],label_colors
            painter.text=original_text
            checks.append('Working Add Printer uses native black normal label and white selected label, never unfinished-control gray')
            painter.image=lambda image,*a,**k:(observed.append(image),original(image,*a,**k))[-1]
            shell.icon(painter,4,'Fixture.desktop',0,0,('test',));assert shell.images[30]in observed and shell.images[29]not in observed;checks.append('Actual Explorer icon renderer uses shell32 GROUP_ICON30 shortcut arrow, never29')
            from win95lx.shell import computer_view
            observed.clear();computer_view.draw(shell,painter,win)
            assert shell.images['explorer-printers-web-heading']in observed and shell.images['explorer-printers-web-computer']in observed;checks.append('Actual namespace renderer uses staged original Printers heading and circle, with registered32/16icons and structured targets')
            from win95lx.explorer.namespace import write_shortcut,Shortcut
            write_shortcut(shell.desktop_folder,'Control Panel',Shortcut('namespace','control'));shell.refresh_desktop_files();observed.clear();shell.draw_desktop(painter,shell.width,shell.height);assert shell.images[30]in observed and shell.images[29]not in observed;checks.append('Actual desktop shortcut renderer also uses original GROUP_ICON30 overlay')
        finally:
            for window in tuple(shell.accessory_windows.values()):window.destroy()
            shell.destroy();x.XCloseDisplay(handle)
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve()),'checks':checks,'screen':[shell.width,shell.height],'real_pointer':True,'failed':0,'scope':'Injected fixture discovery/context only; no queue installation or real printer effects. Real isolated CUPS effect proof is separate.'};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
