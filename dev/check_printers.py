#!/usr/bin/env python3
"""Guest-only printer backend validation with disposable CUPS and byte sink."""
import argparse,getpass,hashlib,json,os,socket,subprocess,sys,tempfile,threading,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev'),str(ROOT/'tools')]

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);parser.add_argument('--owned-guest-service',action='store_true');parser.add_argument('--ui',action='store_true');parser.add_argument('--queue-ui',action='store_true');parser.add_argument('--assets',type=Path);args=parser.parse_args()
    if args.ui:return check_ui(args.output)
    if not args.owned_guest_service or socket.gethostname()!='win95lx-dev':parser.error('Run only in the Win95LX development guest with --owned-guest-service; host scheduler probes are prohibited.')
    import cups
    from win95lx.control_panel.printer_preferences import Printers,PrinterError
    from evidence import identity
    args.output.mkdir(parents=True,exist_ok=False)
    def baseline():
        # libcups caches the user's configuration directory on first use.
        # Observe the real guest scheduler in a separate read-only process,
        # so this worker can use its disposable HOME without sharing globals.
        code='import cups,json; c=cups.Connection(host="/run/cups/cups.sock"); print(json.dumps({"printers":c.getPrinters(),"default":c.getDefault()}))'
        result=subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,text=True,timeout=5)
        return json.loads(result.stdout)
    before=baseline();checks=[];daemon=None;listener=None;thread=None
    with tempfile.TemporaryDirectory(prefix='w95uat-cups-')as directory:
        root=Path(directory);name='w95uat_'+uuid.uuid4().hex[:10];assert name.startswith('w95uat_')
        for component in('state','spool','cache','tmp','config','home'):(root/component).mkdir()
        previous_home=os.environ.get('HOME');previous_xdg=os.environ.pop('XDG_CONFIG_HOME',None);os.environ['HOME']=str(root/'home')
        output=root/'captured.ps';listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(5);received=[]
        def capture():
            try:
                client,address=listener.accept();assert address[0]=='127.0.0.1'
                with client,output.open('wb')as stream:
                    client.settimeout(5)
                    while True:
                        data=client.recv(65536)
                        if not data:break
                        stream.write(data)
                received.append(output.stat().st_size)
            except Exception as error:received.append(type(error).__name__)
        thread=threading.Thread(target=capture,name='w95uat-print-capture',daemon=True);thread.start()
        files=root/'cups-files.conf';config=root/'cupsd.conf';endpoint=root/'cups.sock'
        files.write_text('\n'.join(['User '+getpass.getuser(),'Group '+getpass.getuser(),'SystemGroup '+getpass.getuser(),'Printcap '+str(root/'printcap'),'ServerRoot '+str(root/'config'),'StateDir '+str(root/'state'),'RequestRoot '+str(root/'spool'),'CacheDir '+str(root/'cache'),'TempDir '+str(root/'tmp'),'AccessLog '+str(root/'access.log'),'ErrorLog '+str(root/'error.log'),'PageLog '+str(root/'page.log')])+'\n')
        config.write_text('Listen '+str(endpoint)+'\nBrowsing Off\nWebInterface No\nLogLevel info\n<Location />\nOrder allow,deny\nAllow all\n</Location>\n<Policy default>\n<Limit All>\nOrder allow,deny\nAllow all\n</Limit>\n</Policy>\n')
        log=(args.output/'daemon.log').open('w');job=held=None
        try:
            daemon=subprocess.Popen(['/usr/sbin/cupsd','-f','-c',str(config),'-s',str(files)],stdout=log,stderr=log)
            until=time.monotonic()+5
            while not endpoint.exists()and daemon.poll()is None and time.monotonic()<until:time.sleep(.02)
            if daemon.poll()is not None or not endpoint.exists():raise RuntimeError('Owned guest printing service did not start.')
            connection=cups.Connection(host=str(endpoint));connection.addPrinter(name,device='socket://127.0.0.1:'+str(listener.getsockname()[1]),ppdname='raw',info='Owned disposable printer');connection.enablePrinter(name);connection.acceptJobs(name)
            backend=Printers(connection,user=getpass.getuser(),administration=True);printer=backend.printer(name);assert printer.name==name and printer.accepting
            server_default=connection.getDefault();backend.set_default(name);assert backend.printer(name).default;assert connection.getDefault()==server_default
            checks.append('Actual inventory and per-user default readback; owned server default unchanged')
            job=backend.print_test_page(name);thread.join(timeout=6);assert received and type(received[0])is int,received
            page=output.read_bytes();assert b'Windows Printer Test Page'in page;subprocess.run(['gs','-q','-dBATCH','-dNOPAUSE','-sDEVICE=nullpage','-'],input=page,check=True,capture_output=True,timeout=5);checks.append('Actual test-page bytes reached owned loopback printer simulator')
            document=root/'held.ps';document.write_text('%!PS\nshowpage\n');held=connection.printFile(name,str(document),'Owned held document',{'job-hold-until':'indefinite','document-format':'application/postscript'})
            rows=backend.jobs(name);assert any(row.ident==held and row.state==4 for row in rows)
            if args.queue_ui:real_queue_ui(backend,name,held,args.output,args.assets or ROOT/'private/printers-assets');checks.append('Physical queue selection/menu cancellation reached actual isolated CUPS and read back empty')
            else:backend.cancel(name,held)
            assert not any(row.ident==held for row in backend.jobs(name));checks.append('Held document listed through actual privacy-filtered API and canceled by owner')
            backend.pause(name,True);assert backend.printer(name).state==5;backend.pause(name,False)
            until=time.monotonic()+3
            while backend.printer(name).state!=3 and time.monotonic()<until:time.sleep(.02)
            assert backend.printer(name).state==3;checks.append('Owned queue pause/resume readback')
            connection.deletePrinter(name)
            try:backend.printer(name)
            except PrinterError:pass
            else:raise AssertionError('Deleted owned queue remained visible')
            checks.append('Vanished owned queue reports native-model error')
            daemon.terminate();daemon.wait(timeout=3)
            try:backend.inventory()
            except PrinterError:pass
            else:raise AssertionError('Stopped private service remained available')
            checks.append('Stopped owned printing service reports failure')
        finally:
            listener.close();thread.join(timeout=6)
            if daemon is not None and daemon.poll()is None:
                daemon.terminate()
                try:daemon.wait(timeout=3)
                except subprocess.TimeoutExpired:daemon.kill();daemon.wait()
            log.close()
            if(root/'error.log').exists():(args.output/'error.log').write_bytes((root/'error.log').read_bytes())
            if previous_home is None:os.environ.pop('HOME',None)
            else:os.environ['HOME']=previous_home
            if previous_xdg is not None:os.environ['XDG_CONFIG_HOME']=previous_xdg
        assert not thread.is_alive()and daemon.poll()is not None
    after=baseline();assert after==before,'Existing guest queues/default changed'
    report={**identity(ROOT,Path(__file__).resolve()),'checks':checks,'owned_queue':name,'test_job':job,'held_job':held,'captured_bytes':len(page),'captured_sha256':hashlib.sha256(page).hexdigest(),'baseline_queue_count':len(before['printers']),'existing_state_unchanged':True,'private_daemon_exited':True,'capture_thread_exited':True,'failed':0,'scope':'Owned guest scheduler, interpreter-validated test page and loopback byte receiver; physical real queue UI tested when queue-ui enabled; no physical printer or complete pixel acceptance.'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
def real_queue_ui(backend,name,ident,output,assets):
    import ctypes as C,ctypes.util
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.printers import PrinterQueueWindow
    from check_menu_seams import flush_draws
    display=Gdk.Display.get_default();assert display and 'X11'in type(display).__name__ and display.get_name()==os.environ.get('DISPLAY')
    x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
    x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p;x.XSync.argtypes=[C.c_void_p,C.c_int];x.XCloseDisplay.argtypes=[C.c_void_p]
    xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong];xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
    handle=x.XOpenDisplay(os.environ['DISPLAY'].encode());assert handle
    def click(px,py):
        xt.XTestFakeMotionEvent(handle,0,px,py,0);xt.XTestFakeButtonEvent(handle,1,1,0);xt.XTestFakeButtonEvent(handle,1,0,0);x.XSync(handle,False);flush_draws(Gtk)
    def wait(window):
        until=time.monotonic()+5
        while window.busy and time.monotonic()<until:flush_draws(Gtk);time.sleep(.01)
        assert not window.busy,'Real queue UI service timeout'
    shell=Shell(assets);shell.show_all();flush_draws(Gtk);window=PrinterQueueWindow(shell,name,backend);window.show_all();wait(window);flush_draws(Gtk)
    try:
        assert any(job.ident==ident for job in window.jobs)
        left,top=window.get_position();click(left+35,top+70);assert window.selected==ident
        click(left+65,top+32);popup=window.menu_popup;assert popup and Gtk.grab_get_current()is popup
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,*window.get_size());window.draw(window.area,cairo.Context(surface));surface.write_to_png(str(output/'real-queue-selected.png'))
        px,py=popup.get_position();click(px+50,py+10);wait(window)
        assert window.menu_popup is None and Gtk.grab_get_current()is None
        assert not any(job.ident==ident for job in backend.jobs(name)) and not window.jobs
        # Actual pointer opening and outside dismissal must release its grab.
        click(left+20,top+32);popup=window.menu_popup;assert popup
        click(left+250,top+95);assert popup.closed and Gtk.grab_get_current()is None
    finally:
        window.destroy();shell.disconnect_by_func(Gtk.main_quit);shell.destroy();x.XCloseDisplay(handle)
    until=time.monotonic()+3
    while any(t.name.startswith('win95lx-printer')for t in threading.enumerate())and time.monotonic()<until:flush_draws(Gtk);time.sleep(.01)
    assert not any(t.name.startswith('win95lx-printer')for t in threading.enumerate())

def check_ui(output):
    """Original queue regions plus background work and context ownership."""
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.apps.printers import PrinterQueueWindow,PrinterNamespace
    from win95lx.control_panel.printer_preferences import Printer,PrintJob,PrinterCapabilities
    from check_menu_seams import flush_draws
    from stage_printers_assets import stage
    from stage_command_button_assets import read_bmp
    from pixels import read
    from unittest.mock import patch
    display=Gdk.Display.get_default()
    assert display and 'X11'in type(display).__name__ and display.get_name()==os.environ.get('DISPLAY'),'Requires isolated X11 display'
    output.mkdir(parents=True,exist_ok=False);checks=[];comparisons=[]
    class Backend:
        user='w95uat'
        def __init__(self):self.rows=();self.actions=[];self.failed=False
        def inventory(self):
            time.sleep(.08)
            if self.failed:
                from win95lx.control_panel.printer_preferences import PrinterError
                raise PrinterError('The printing service is unavailable.')
            return(Printer('w95uatreference','Owned fixture'),)
        def printer(self,name):return self.inventory()[0]
        def jobs(self,name):return self.rows
        def capabilities(self):return PrinterCapabilities(False,'Access is denied.')
        def cancel(self,name,ident):self.actions.append(('cancel',name,ident));self.rows=tuple(j for j in self.rows if j.ident!=ident)
    def wait(window):
        until=time.monotonic()+3
        while window.busy and time.monotonic()<until:flush_draws(Gtk);time.sleep(.005)
        assert not window.busy,'Printer worker timed out'
    with tempfile.TemporaryDirectory(prefix='w95uat-printer-ui-')as directory:
        assets=Path(directory);stage(assets)
        for path in(ROOT/'private/shell-assets').iterdir():
            if not(assets/path.name).exists():(assets/path.name).symlink_to(path)
        backend=Backend();shell=Shell(assets);shell.show_all();flush_draws(Gtk)
        started=time.perf_counter();window=PrinterQueueWindow(shell,'w95uatreference',backend);paint=[]
        window.area.connect_after('draw',lambda *_:paint.append((time.perf_counter()-started)*1000)if not paint else False)
        window.show_all();wait(window);assert paint and paint[0]<80,paint
        checks.append('First paint before deliberately delayed80ms printer inventory completes')
        flush_draws(Gtk);window.caption_active=True
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,562,185);window.draw(window.area,cairo.Context(surface));surface.write_to_png(str(output/'queue-native.png'))
        w,h,actual=read(output/'queue-native.png');_,_,native=read_bmp(ROOT/'private/reference-tools/printers-native-20261127/queue-real/PRINTERS.BMP')
        for name,rect in [('caption',(0,0,562,23)),('menubar',(4,23,554,19)),('header',(6,44,550,17)),('empty-list',(6,61,550,100)),('status',(4,161,554,20))]:
            x,y,rw,rh=rect;difference=sum(actual[(y+yy)*w+x+xx]!=native[(y+yy)*w+x+xx]for yy in range(rh)for xx in range(rw));assert difference==0,(name,difference);comparisons.append({'region':name,'rect':rect,'differing_pixels':difference})
        backend.rows=(PrintJob(1,'w95uatreference','Own document','w95uat',4,1),PrintJob(2,'w95uatreference','Other document','other',3,2));window.refresh();wait(window)
        window.selected=2;assert not window.rows('Document')[0][2];window.selected=1;assert window.rows('Document')[0][2];window.command('cancel');wait(window)
        assert backend.actions==[('cancel','w95uatreference',1)] and len(window.jobs)==1;checks.append('Other-user document disabled; own cancellation/readback')
        provider=PrinterNamespace(backend);provider.publish(provider.load());assert provider.entries()[1][2]==('printer-queue','w95uatreference');checks.append('Explorer provider returns structured destination target')
        window.jobs=tuple(PrintJob(i,'w95uatreference','Document '+str(i),'w95uat',4,1)for i in range(1,101));window.set_scroll(999);assert window.scroll==100-window.visible_rows();window.set_scroll(-1);assert window.scroll==0
        from types import SimpleNamespace
        window.selected=1
        for _ in range(12):window.key(window,SimpleNamespace(keyval=Gdk.KEY_Down,state=0))
        assert window.selected==13 and window.scroll>0;checks.append('Long queue scroll bounds and keyboard selection keep selected document visible')
        backend.failed=True;window.refresh();wait(window);assert not window.jobs and window.printer is None and window.selected is None;assert not window.rows('Printer')[0][2];checks.append('Failed refresh clears stale jobs and selection; service actions disabled')
        backend.failed=False;window.refresh();wait(window)
        window.command(('menu','Printer',6));flush_draws(Gtk);assert window.menu_popup;window.menu_popup.finish();window.refresh();window.destroy()
        until=time.monotonic()+3
        while any(t.name.startswith('win95lx-printer')for t in threading.enumerate())and time.monotonic()<until:flush_draws(Gtk);time.sleep(.01)
        assert not any(t.name.startswith('win95lx-printer')for t in threading.enumerate());checks.append('Close while worker running releases popup and exits serialized worker')
        shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),[ROOT/'private/reference-tools/printers-native-20261127/queue-real/PRINTERS.BMP',ROOT/'private/reference-tools/printers-native-20261127/queue-real/PRINTERS.JSN']),'checks':checks,'comparisons':comparisons,'first_paint_ms':paint[0],'failed':0,'scope':'Queue empty native geometry and fixture backend context/lifecycle only; not physical input, wizard or real UI/CUPS integration.'}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
