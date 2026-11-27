#!/usr/bin/python3
"""Guest-only create-printer service: fixed socket, peer UID and CUPS endpoint.

No shell commands, package installation, deletion, arbitrary files, server
settings, existing-destination changes or credentials are accepted over RPC.
"""
import argparse,json,multiprocessing,os,socket,socketserver,struct,sys
from dataclasses import asdict
from pathlib import Path


def operation(request,cups_socket,journal):
    import cups
    from win95lx.control_panel.printer_installation import PrinterInstallPlan,PrinterInstaller,discover_installation,encode_discovery,write_installation_record,PartialInstallation,PrinterError
    cups.setPasswordCB(lambda _:'')
    connection=cups.Connection(host=cups_socket)
    try:
        if request=={'operation':'discover'}:value=encode_discovery(discover_installation(connection))
        elif set(request)=={'operation','plan'}and request['operation']=='install':
            if not isinstance(request['plan'],dict):raise PrinterError('The printer installation request is not valid.')
            plan=PrinterInstallPlan(**request['plan'])
            if type(plan.print_test_page)is not bool or type(plan.make_user_default)is not bool:raise PrinterError('The printer options are not valid.')
            value=asdict(PrinterInstaller(connection,lambda record:write_installation_record(journal,record)).install(plan))
        else:raise PrinterError('The printer operation is not supported.')
        return {'ok':True,'value':value}
    except PartialInstallation as error:return {'ok':False,'queue':error.queue,'error':'its final state could not be confirmed'}
    except PrinterError as error:return {'ok':False,'error':str(error)}
    except(TypeError,ValueError):return {'ok':False,'error':'The printer operation could not be completed. Check the name, driver and address, then try again.'}


def worker(pipe,request,cups_socket,journal):
    try:pipe.send(operation(request,cups_socket,journal))
    except Exception:pipe.send({'ok':False,'error':'The printing service is unavailable or access was denied. Check Printers before retrying an installation.'})
    finally:pipe.close()


def bounded_operation(request,cups_socket,journal,timeout=20):
    # Discovery and IPP negotiation can block inside libcups. A disposable
    # process provides an actual deadline; canceling a Python thread cannot.
    context=multiprocessing.get_context('fork');reader,writer=context.Pipe(False)
    process=context.Process(target=worker,args=(writer,request,cups_socket,journal));process.start();writer.close()
    try:
        if reader.poll(timeout):return reader.recv()
        return {'ok':False,'error':'The printer did not respond in time. Check Printers before retrying; an installation may have completed.'}
    finally:
        reader.close()
        if process.is_alive():process.terminate()
        process.join(timeout=2)
        if process.is_alive():process.kill();process.join(timeout=2)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--peer-uid',type=int,required=True);parser.add_argument('--socket',type=Path,default=Path('/run/win95lx-printers/control.sock'));parser.add_argument('--cups-socket',default='/run/cups/cups.sock');parser.add_argument('--journal',type=Path,default=Path('/var/lib/win95lx/printer-installations'));parser.add_argument('--owned-test-service',action='store_true');args=parser.parse_args()
    if not args.owned_test_service:
        if os.geteuid()!=0 or socket.gethostname()!='win95lx-dev':parser.error('Production printer helper must run as root in the dedicated guest.')
        if args.socket!=Path('/run/win95lx-printers/control.sock')or args.cups_socket!='/run/cups/cups.sock'or args.journal!=Path('/var/lib/win95lx/printer-installations'):parser.error('Production paths are fixed.')
    else:
        root=args.socket.parent.resolve()
        if not root.name.startswith('w95uat-')or not str(Path(args.cups_socket).resolve()).startswith(str(root)+'/')or not str(args.journal.resolve()).startswith(str(root)+'/'):parser.error('Owned test paths must share a disposable w95uat directory.')
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(3)
            _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=args.peer_uid:return
            try:
                data=self.rfile.readline(8193)
                if len(data)>8192 or not data.endswith(b'\n'):return
                request=json.loads(data)
                if not isinstance(request,dict):return
                reply=bounded_operation(request,args.cups_socket,args.journal)
                self.wfile.write(json.dumps(reply,separators=(',',':')).encode()+b'\n')
            except(OSError,ValueError,EOFError):return
    args.socket.parent.mkdir(mode=0o755,parents=True,exist_ok=True)
    if args.socket.exists():raise SystemExit('Refusing to replace an existing service socket.')
    server=socketserver.UnixStreamServer(str(args.socket),Handler)
    os.chmod(args.socket,0o666) # SO_PEERCRED is authoritative; no other peer UID accepted.
    try:server.serve_forever()
    finally:server.server_close();args.socket.unlink(missing_ok=True)

if __name__=='__main__':main()
