#!/usr/bin/env python3
"""Guest-only fresh-queue RPC proof using owned CUPS + IPP Everywhere emulator."""
import argparse,getpass,json,os,socket,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src')]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--owned-guest-service',action='store_true');args=parser.parse_args()
    if not args.owned_guest_service or socket.gethostname()!='win95lx-dev':parser.error('Owned development guest only; host CUPS never modified.')
    import cups
    from win95lx.control_panel.printer_installation import PrinterInstallationClient,PrinterInstallPlan,PrinterError
    args.output.mkdir(parents=True,exist_ok=False);checks=[];processes=[];logs=[]
    def baseline():
        code='import cups,json; c=cups.Connection(host="/run/cups/cups.sock");print(json.dumps({"printers":c.getPrinters(),"default":c.getDefault()},sort_keys=True))'
        return subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,text=True,timeout=5).stdout
    before=baseline()
    with tempfile.TemporaryDirectory(prefix='w95uat-install-')as directory:
        root=Path(directory)
        for part in('state','spool','cache','tmp','config','home','ipp-spool'):(root/part).mkdir()
        socketpath=root/'cups.sock';rpcpath=root/'control.sock';journal=root/'journal'
        files=root/'cups-files.conf';config=root/'cupsd.conf'
        files.write_text('\n'.join(['User '+getpass.getuser(),'Group '+getpass.getuser(),'SystemGroup '+getpass.getuser(),'Printcap '+str(root/'printcap'),'ServerRoot '+str(root/'config'),'StateDir '+str(root/'state'),'RequestRoot '+str(root/'spool'),'CacheDir '+str(root/'cache'),'TempDir '+str(root/'tmp'),'AccessLog '+str(root/'access.log'),'ErrorLog '+str(root/'error.log'),'PageLog '+str(root/'page.log')])+'\n')
        config.write_text('Listen '+str(socketpath)+'\nBrowsing Off\nWebInterface No\nLogLevel info\n<Location />\nOrder allow,deny\nAllow all\n</Location>\n<Policy default>\n<Limit All>\nOrder allow,deny\nAllow all\n</Limit>\n</Policy>\n')
        def launch(name,command):
            log=(args.output/(name+'.log')).open('w');logs.append(log);process=subprocess.Popen(command,stdout=log,stderr=log,env={**os.environ,'PYTHONPATH':str(ROOT/'src')});processes.append(process);return process
        def wait(path,process):
            until=time.monotonic()+7
            while not path.exists()and process.poll()is None and time.monotonic()<until:time.sleep(.02)
            assert path.exists()and process.poll()is None,(path,process.poll())
        try:
            daemon=launch('cups',['/usr/sbin/cupsd','-f','-c',str(config),'-s',str(files)]);wait(socketpath,daemon)
            listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1];listener.close()
            emulator=launch('ipp',['/usr/sbin/ippeveprinter','-r','off','-n','localhost','-p',str(port),'-d',str(root/'ipp-spool'),'-f','application/postscript,image/pwg-raster','-k','Owned Win95LX IPP'])
            until=time.monotonic()+7
            while time.monotonic()<until:
                try:
                    with socket.create_connection(('127.0.0.1',port),.2):break
                except OSError:time.sleep(.05)
            assert emulator.poll()is None,'IPP emulator failed'
            helper=launch('service',[sys.executable,'-m','win95lx.control_panel.printer_service','--owned-test-service','--peer-uid',str(os.getuid()),'--socket',str(rpcpath),'--cups-socket',str(socketpath),'--journal',str(journal)]);wait(rpcpath,helper)
            client=PrinterInstallationClient(str(rpcpath));started=time.perf_counter();discovery=client.discover();discovery_ms=(time.perf_counter()-started)*1000
            assert any(d.driverless for d in discovery.drivers);checks.append('Actual bounded RPC discovery returns IPP Everywhere separately from backend advertisements')
            endpoint='ipp://127.0.0.1:'+str(port)+'/ipp/print';plan=PrinterInstallPlan('Owned_Printer',endpoint,'everywhere','Owned Printer')
            started=time.perf_counter()
            try:result=client.install(plan)
            except Exception:
                connection=cups.Connection(host=str(socketpath));(args.output/'failed-state.json').write_text(json.dumps(connection.getPrinters(),indent=2));raise
            install_ms=(time.perf_counter()-started)*1000
            connection=cups.Connection(host=str(socketpath));printer=connection.getPrinterAttributes(result.queue,requested_attributes=['printer-info','device-uri','printer-is-accepting-jobs','printer-state','printer-is-shared'])
            assert printer['printer-info']=='Owned Printer'and printer['device-uri']==endpoint and printer['printer-is-accepting-jobs']and printer['printer-state']!=5 and printer['printer-is-shared']is False
            # Confirm actual PPD negotiated with the emulator, not a fabricated
            # destination or substituted raw queue.
            ppd=root/'config/ppd'/(result.queue+'.ppd');assert ppd.is_file(),list(root.rglob('*.ppd'));data=ppd.read_bytes();assert b'*PPD-Adobe:'in data and(b'PWG'in data or b'IPP'in data)
            checks.append('Finish RPC actually creates a ready driverless queue and negotiated PPD against owned IPP emulator')
            records=[json.loads(path.read_text())for path in journal.glob('*.json')];assert len(records)==1 and records[0]['phase']=='ready'
            checks.append('Durable ownership journal reads ready after create/readback; human name separate from random stable queue identity')
            from win95lx.control_panel.printer_preferences import Printers
            job=Printers(connection).print_test_page(result.queue)
            until=time.monotonic()+8;captured=[]
            while time.monotonic()<until:
                captured=[p for p in(root/'ipp-spool').iterdir()if p.is_file()and p.stat().st_size>1800 and p.read_bytes()[:4]in(b'RaS2',b'RaSt',b'RaS3')]
                if captured:break
                time.sleep(.05)
            assert captured,'Test page did not reach IPP emulator'
            checks.append('Actual optional PostScript test page converted to PWG raster through CUPS and reached owned IPP spool')
            try:client.install(plan)
            except PrinterError:pass
            else:raise AssertionError('Duplicate description installed')
            assert len(connection.getPrinters())==1;checks.append('Repeated Finish/name collision does not add or overwrite another queue')
            # Retain a fixture printer and fail unreachable IPP negotiation.
            old=dict(connection.getPrinters());bad=PrinterInstallPlan('Missing','ipp://127.0.0.1:1/ipp/print','everywhere','Missing Printer')
            try:client.install(bad)
            except PrinterError:pass
            else:raise AssertionError('Unreachable IPP endpoint accepted')
            assert connection.getPrinters()[result.queue]==old[result.queue];checks.append('Unreachable endpoint fails without changing existing owned printer')
            # Test authentication rejection from the real listening socket.
            helper.terminate();helper.wait(timeout=3);rpcpath.unlink(missing_ok=True)
            denied=launch('denied-service',[sys.executable,'-m','win95lx.control_panel.printer_service','--owned-test-service','--peer-uid',str(os.getuid()+10000),'--socket',str(rpcpath),'--cups-socket',str(socketpath),'--journal',str(journal)]);wait(rpcpath,denied)
            try:client.discover()
            except PrinterError:pass
            else:raise AssertionError('Foreign peer UID accepted')
            assert connection.getPrinters()[result.queue]==old[result.queue];checks.append('SO_PEERCRED mismatch denied by actual socket with queues unchanged')
            denied.terminate();denied.wait(timeout=3);rpcpath.unlink(missing_ok=True)
            try:client.discover()
            except PrinterError:pass
            else:raise AssertionError('Unavailable service accepted')
            checks.append('Unavailable helper produces explicit native-model error')
        finally:
            for process in reversed(processes):
                if process.poll()is None:
                    process.terminate()
                    try:process.wait(timeout=3)
                    except subprocess.TimeoutExpired:process.kill();process.wait()
            for log in logs:log.close()
            if(root/'error.log').exists():(args.output/'scheduler-error.log').write_bytes((root/'error.log').read_bytes())
    assert baseline()==before,'Normal guest queues/default changed'
    report={'checks':checks,'discovery_ms':discovery_ms,'install_ms':install_ms,'queue':result.queue,'existing_guest_state_unchanged':True,'all_owned_processes_exited':all(p.poll()is not None for p in processes),'failed':0,'scope':'Real private CUPS and IPP Everywhere emulator + authenticated RPC. Not physical printer or root/system service UI proof.'}
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
