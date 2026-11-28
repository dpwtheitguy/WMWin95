"""Scoped existing-profile NetworkManager service; never a shell/privilege proxy.

Production policy is a root-owned UUID/interface/type allowlist. A socket peer
must belong to the authorized active local graphical login. No service is
installed or enabled merely by importing this module.
"""
from dataclasses import asdict, replace
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import socketserver
import signal
import stat
import struct
import threading
import tempfile
import time
from collections import OrderedDict
from win95lx.control_panel.network_preferences import NetworkManager, NetworkController, NetworkState, Connection, IPv4Config, NetworkError

MAX_REQUEST=64*1024
SOCKET=Path('/run/win95lx-network/control.sock')
POLICY=Path('/etc/win95lx/network-policy.json')
EDITABLE=frozenset(('method','address','netmask','gateway','dns','search','manual_dns','dhcp_hostname'))


def encode_state(value):
    return json.loads(json.dumps(asdict(value.validate())))


def decode_state(value):
    if not isinstance(value,dict) or set(value)!={'hostname','connections','description','workgroup'} or not isinstance(value['connections'],list) or len(value['connections'])>32:
        raise ValueError('Invalid network update document.')
    rows=[]
    for row in value['connections']:
        if not isinstance(row,dict) or set(row)!={'uuid','name','device','kind','ipv4','autoconnect','active'} or not isinstance(row['ipv4'],dict):
            raise ValueError('Invalid connection update document.')
        if type(row['autoconnect'])is not bool or type(row['active'])is not bool:
            raise ValueError('Invalid connection options.')
        rows.append(Connection(**{**row,'ipv4':IPv4Config(**row['ipv4'])}).validate())
    return NetworkState(value['hostname'],tuple(rows),value['description'],value['workgroup']).validate()


def validate_policy(value):
    if not isinstance(value,dict) or set(value)!={'schema','peer_uid','profiles'} or value['schema']!=1 or type(value['peer_uid'])is not int or value['peer_uid']<=0 or not isinstance(value['profiles'],list) or len(value['profiles'])>32:
        raise ValueError('Invalid network service policy.')
    profiles={}
    for row in value['profiles']:
        if not isinstance(row,dict) or set(row)!={'uuid','device','kind','qa_only'} or type(row['qa_only'])is not bool:
            raise ValueError('Invalid network profile policy.')
        Connection(row['uuid'],'Policy',row['device'],row['kind']).validate()
        if not row['device'] or row['kind']not in ('dummy','802-3-ethernet','802-11-wireless') or row['uuid']in profiles:
            raise ValueError('Invalid network profile policy.')
        if row['qa_only'] and (row['kind']!='dummy' or not row['device'].startswith('w95uat')):
            raise ValueError('QA policy requires an owned dummy interface.')
        profiles[row['uuid']]=dict(row)
    return value['peer_uid'],profiles


def load_policy(path=POLICY):
    path=Path(path);info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid!=0 or info.st_mode&0o022 or info.st_size>MAX_REQUEST:
        raise ValueError('The network service policy is not protected.')
    return validate_policy(json.loads(path.read_text()))


def active_local_peer(connection, expected_uid):
    """Kernel credentials plus logind's actual peer login, with no uid payload."""
    _,uid,_=struct.unpack('3i',connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    if uid!=expected_uid:return False
    library=ctypes.CDLL('libsystemd.so.0')
    library.sd_peer_get_session.argtypes=[ctypes.c_int,ctypes.POINTER(ctypes.c_void_p)];library.sd_peer_get_session.restype=ctypes.c_int
    library.sd_session_is_active.argtypes=[ctypes.c_char_p];library.sd_session_is_active.restype=ctypes.c_int
    library.sd_session_is_remote.argtypes=[ctypes.c_char_p];library.sd_session_is_remote.restype=ctypes.c_int
    library.sd_session_get_uid.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_uint)];library.sd_session_get_uid.restype=ctypes.c_int
    library.sd_session_get_type.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_void_p)];library.sd_session_get_type.restype=ctypes.c_int
    libc=ctypes.CDLL(None);libc.free.argtypes=[ctypes.c_void_p]
    name=ctypes.c_void_p();kind=ctypes.c_void_p()
    try:
        if library.sd_peer_get_session(connection.fileno(),ctypes.byref(name))<0:return False
        session=ctypes.string_at(name);owner=ctypes.c_uint()
        if library.sd_session_get_uid(session,ctypes.byref(owner))<0 or owner.value!=uid:return False
        if library.sd_session_is_active(session)!=1 or library.sd_session_is_remote(session)!=0:return False
        if library.sd_session_get_type(session,ctypes.byref(kind))<0:return False
        return ctypes.string_at(kind)in (b'x11',b'wayland')
    finally:
        if name.value:libc.free(name)
        if kind.value:libc.free(kind)


class GuestNetworkManager(NetworkManager):
    """Forward deadline with a separate bounded recovery command budget."""
    def __init__(self):
        self.deadline=None
        super().__init__(run=self._command)
    def _command(self,*args):
        import subprocess
        remaining=17 if self.deadline is None else min(17,self.deadline-time.monotonic())
        if remaining<=0:raise NetworkError('The network operation timed out. Recovery will be attempted.')
        try:
            result=subprocess.run(['/usr/bin/nmcli','--wait',str(max(1,min(12,int(remaining)))),'--colors','no',*args],check=True,capture_output=True,text=True,stdin=subprocess.DEVNULL,timeout=remaining,env={'PATH':'/usr/bin:/bin','LC_ALL':'C'})
            if len(result.stdout)>1024*1024:raise NetworkError('The network service returned too much information.')
            return result.stdout.rstrip('\n')
        except (subprocess.TimeoutExpired,subprocess.CalledProcessError,OSError)as error:
            raise NetworkError('The network service could not complete the operation. Recovery will be attempted.')from error
    def _restore_connections(self,connections):
        previous=self.deadline;self.deadline=time.monotonic()+35
        try:return super()._restore_connections(connections)
        finally:self.deadline=previous


def _journal_write(path,request):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if path.is_symlink()or any(parent.is_symlink()for parent in path.parents):raise NetworkError('The network recovery journal is unavailable.')
    descriptor,temporary=tempfile.mkstemp(prefix='.network-',dir=path.parent)
    try:
        with os.fdopen(descriptor,'w')as stream:
            json.dump(request,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        folder=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(folder)
        finally:os.close(folder)
    finally:
        Path(temporary).unlink(missing_ok=True)


class NetworkService:
    def __init__(self,manager,policy,*,guard=lambda:False,journal=None):
        self.peer_uid,self.profiles=validate_policy(policy)
        self.manager,self.guard=manager,guard
        self.journal=Path(journal)if journal is not None else None
        self.lock=threading.Lock();self.requests=OrderedDict()

    def _validate_update(self,pending,baseline):
        if (pending.hostname,pending.description,pending.workgroup)!=(baseline.hostname,baseline.description,baseline.workgroup):
            raise NetworkError('Computer identity and sharing are not supported by this network service.')
        old={c.uuid:c for c in baseline.connections};new={c.uuid:c for c in pending.connections}
        if not old or old.keys()!=new.keys():raise NetworkError('This service edits existing connections only.')
        for identity,c in new.items():
            before=old[identity];policy=self.profiles.get(identity)
            if policy is None or any(getattr(c,key)!=policy[key] or getattr(before,key)!=policy[key] for key in ('device','kind')):
                raise NetworkError('This connection is not enabled in the installed network service policy.')
            if any(getattr(c,key)!=getattr(before,key) for key in ('name','active')):
                raise NetworkError('The connection identity cannot be changed here.')
            for key in asdict(c.ipv4):
                if key not in EDITABLE and getattr(c.ipv4,key)!=getattr(before.ipv4,key):
                    raise NetworkError('This update includes an unsupported routing setting.')
            if c.ipv4.method not in ('auto','manual','disabled'):
                raise NetworkError('This address assignment mode is not supported here.')
            if policy['qa_only']:
                if not before.ipv4.never_default or not c.ipv4.never_default or c.ipv4.gateway or before.ipv4.gateway or c.autoconnect or before.autoconnect or c.ipv4.search or before.ipv4.search or '~win95lx-uat.invalid'not in before.ipv4.route_search:
                    raise NetworkError('The QA connection must remain isolated from default networking.')
        return old,new

    def operation(self,request):
        with self.lock:
            if not self.guard():raise NetworkError('Network changes are available only in the installed Win95LX guest.')
            if not isinstance(request,dict) or set(request)!={'operation','request_id','baseline','pending'} or request['operation']!='apply' or not isinstance(request['request_id'],str) or not re.fullmatch(r'[a-f0-9]{32}',request['request_id']):
                raise ValueError('Invalid network service request.')
            digest=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest();identifier=request['request_id']
            if identifier in self.requests:
                previous,reply=self.requests[identifier]
                if previous!=digest:raise NetworkError('A network request identifier was reused with different settings.')
                return reply
            if self.journal is not None and self.journal.exists():
                raise NetworkError('A previous network change was interrupted. Recovery must be checked before changing settings again.')
            if hasattr(self.manager,'deadline'):self.manager.deadline=time.monotonic()+45
            baseline=decode_state(request['baseline']);pending=decode_state(request['pending'])
            self._validate_update(pending,baseline)
            # Authoritative identity/adapter fields are reread on the service,
            # never trusted just because the request is well-formed.
            actual=self.manager.preferences()
            if (actual.hostname,actual.description,actual.workgroup)!=(baseline.hostname,baseline.description,baseline.workgroup):
                raise NetworkError('The computer identity changed while this window was open.')
            actual_rows={row.uuid:row for row in actual.connections}
            for before in baseline.connections:
                current=actual_rows.get(before.uuid)
                if current!=before:raise NetworkError('This connection changed while the window was open. Reopen Network and try again.')
                if self.profiles[before.uuid]['qa_only']:
                    isolated=self.manager.run('-g','ipv4.route-table,ipv4.dns-priority,ipv6.method','connection','show','uuid',before.uuid).splitlines()
                    if isolated!=['49995','32760','disabled']:
                        raise NetworkError('The QA connection isolation settings are missing.')
            controller=NetworkController(self.manager,initial_state=baseline)
            controller.pending=pending
            if self.journal is not None:_journal_write(self.journal,request)
            try:
                controller.apply()
            except BaseException:
                # Remove a failed transaction journal only when authoritative
                # state proves its entire edited baseline was restored.
                try:
                    if hasattr(self.manager,'deadline'):self.manager.deadline=time.monotonic()+10
                    recovered={c.uuid:c for c in self.manager.preferences().connections}
                    if all(recovered.get(c.uuid)==c for c in baseline.connections) and self.journal is not None:
                        self.journal.unlink(missing_ok=True)
                except Exception:pass
                raise
            if self.journal is not None:self.journal.unlink(missing_ok=True)
            reply={'ok':True,'value':encode_state(controller.applied)}
            self.requests[identifier]=(digest,reply)
            while len(self.requests)>64:self.requests.popitem(last=False)
            return reply


class NetworkServiceClient:
    def __init__(self,path=SOCKET):self.path=Path(path)
    def call(self,request):
        data=json.dumps(request,separators=(',',':')).encode()+b'\n'
        if len(data)>MAX_REQUEST:raise NetworkError('The network update is too large.')
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)as stream:
                stream.settimeout(100);stream.connect(str(self.path));stream.sendall(data)
                with stream.makefile('rb')as reader:response=reader.readline(MAX_REQUEST+1)
            if len(response)>MAX_REQUEST or not response.endswith(b'\n'):raise ValueError('Invalid service response.')
            reply=json.loads(response)
            if not isinstance(reply,dict) or type(reply.get('ok'))is not bool:raise ValueError('Invalid service response.')
            if not reply['ok']:raise NetworkError(reply.get('error','The network operation could not be completed.'))
            return decode_state(reply['value'])
        except (OSError,ValueError,KeyError,TypeError)as error:
            raise NetworkError('The network service is unavailable or did not confirm the change. Reopen Network before retrying.')from error


class ServiceNetworkManager:
    """Unprivileged inventory; existing-profile writes use the scoped service."""
    def __init__(self,reader=None,client=None):
        self.reader=reader or NetworkManager();self.client=client or NetworkServiceClient();self.identity_editable=False
    @property
    def adapters(self):return self.reader.adapters
    def preferences(self):return self.reader.preferences()
    def _apply(self,pending,baseline):
        import uuid
        return self.client.call({'operation':'apply','request_id':uuid.uuid4().hex,'baseline':encode_state(baseline),'pending':encode_state(pending)})
    def apply(self,pending,baseline):
        old={c.uuid:c for c in baseline.connections};new={c.uuid:c for c in pending.connections}
        if old.keys()!=new.keys():raise NetworkError('Adding and removing connections is not supported by this service.')
        if (pending.hostname,pending.workgroup,pending.description)!=(baseline.hostname,baseline.workgroup,baseline.description):raise NetworkError('Computer identity and sharing changes are not supported by this service.')
        changed=tuple(c for c in pending.connections if c!=old[c.uuid])
        if changed:self._apply(replace(pending,connections=changed),replace(baseline,connections=tuple(old[c.uuid]for c in changed)))
    def restore(self,before):
        current=self.reader.preferences();actual={c.uuid:c for c in current.connections}
        try:baseline=replace(current,connections=tuple(actual[c.uuid]for c in before.connections))
        except KeyError:raise NetworkError('A changed connection disappeared before recovery.')from None
        if before.connections:self._apply(before,baseline)


def installed_backend():
    """Prefer the reviewed helper only when its protected guest socket exists."""
    from win95lx.guest_identity import is_development_guest
    try:
        info=SOCKET.lstat();directory=SOCKET.parent.lstat()
        if (is_development_guest() and stat.S_ISSOCK(info.st_mode) and info.st_uid==0
                and stat.S_ISDIR(directory.st_mode) and directory.st_uid==0 and not directory.st_mode&0o022):
            return ServiceNetworkManager()
    except OSError:pass
    return NetworkManager()


def main():
    from win95lx.guest_identity import is_development_guest
    parser=argparse.ArgumentParser();args=parser.parse_args()
    if os.geteuid()!=0 or not Path('/etc/win95lx/guest-id').is_file() or not is_development_guest():parser.error('This service is restricted to the installed guest.')
    uid,profiles=load_policy()
    policy={'schema':1,'peer_uid':uid,'profiles':list(profiles.values())}
    service=NetworkService(GuestNetworkManager(),policy,guard=lambda:Path('/etc/win95lx/guest-id').is_file()and is_development_guest(),journal=Path('/var/lib/win95lx/network/pending.json'))
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.request.settimeout(3)
            try:
                if not active_local_peer(self.request,uid):return
                line=self.rfile.readline(MAX_REQUEST+1)
                if len(line)>MAX_REQUEST or not line.endswith(b'\n'):return
                request=json.loads(line)
                try:reply=service.operation(request)
                except(NetworkError,ValueError,TypeError)as error:reply={'ok':False,'error':str(error)}
                self.wfile.write(json.dumps(reply,separators=(',',':')).encode()+b'\n')
            except(OSError,ValueError,TypeError):return
    SOCKET.parent.mkdir(parents=True,exist_ok=True,mode=0o755)
    directory=SOCKET.parent.lstat()
    if not stat.S_ISDIR(directory.st_mode)or directory.st_uid!=0 or directory.st_mode&0o022:
        raise SystemExit('The network service directory is not protected.')
    if SOCKET.exists()or SOCKET.is_symlink():raise SystemExit('Refusing to replace an existing service socket.')
    server=socketserver.UnixStreamServer(str(SOCKET),Handler);os.chmod(SOCKET,0o666)
    def terminate(*_):raise SystemExit(0)
    signal.signal(signal.SIGTERM,terminate)
    try:server.serve_forever()
    finally:server.server_close();SOCKET.unlink(missing_ok=True)

if __name__=='__main__':main()
