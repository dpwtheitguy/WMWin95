"""Transactional, noninteractive NetworkManager IPv4 configuration.

Only explicitly edited connection properties are written. IPv6, credentials,
non-default routes, MTU and other unrelated settings remain under NM ownership.
"""
from dataclasses import dataclass,field,replace
from ipaddress import IPv4Address,IPv4Interface,IPv4Network
from pathlib import Path
import os,re,socket,subprocess,uuid

MODIFY='org.freedesktop.NetworkManager.settings.modify.system'
CONTROL='org.freedesktop.NetworkManager.network-control'
HOSTNAME='org.freedesktop.NetworkManager.settings.modify.hostname'
FIELDS=('connection.id','connection.uuid','connection.interface-name','connection.type','connection.autoconnect',
        'ipv4.method','ipv4.addresses','ipv4.gateway','ipv4.dns','ipv4.dns-search','ipv4.ignore-auto-dns',
        'ipv4.never-default','ipv4.routes','ipv4.dhcp-hostname')
IP_FIELDS=FIELDS[5:]

class NetworkError(RuntimeError):pass

def split_escaped(value,separator=':'):
    rows=[];part=[];escaped=False
    for char in value:
        if escaped:part.append(char);escaped=False
        elif char=='\\':escaped=True
        elif char==separator:rows.append(''.join(part));part=[]
        else:part.append(char)
    if escaped:part.append('\\')
    rows.append(''.join(part));return rows

def boolean(value):return value.strip().lower() in ('yes','true','1','on')
def items(value):return tuple(part.strip() for part in value.split(',') if part.strip())
def unescape(value):return split_escaped(value,'\0')[0]

def ipv4(value,label='IP address'):
    try:address=IPv4Address(value)
    except ValueError as error:raise ValueError(f'Enter a valid {label}.') from error
    if address.is_unspecified or address.is_multicast or int(address)==0xffffffff:raise ValueError(f'Enter a unicast {label}.')
    return str(address)

def prefix_from_mask(mask):
    try:prefix=IPv4Network('0.0.0.0/'+mask).prefixlen
    except (ValueError,TypeError) as error:raise ValueError('Enter a valid, contiguous subnet mask.') from error
    if prefix<1:raise ValueError('The subnet mask cannot be zero.')
    return prefix

def valid_hostname(value):
    # The native Identification page has the original 15-character name limit.
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,13}[A-Za-z0-9])?',value):
        raise ValueError('The computer name must contain 1 to 15 letters, digits or hyphens, and must begin and end with a letter or digit.')
    return value

def domain(value):
    if not isinstance(value,str) or len(value)>253:raise ValueError('Enter a valid domain name.')
    if value and any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?',part) for part in value.rstrip('.').split('.')):raise ValueError('Enter a valid domain name.')
    return value

@dataclass(frozen=True)
class IPv4Config:
    method:str='auto'
    address:str=''
    netmask:str=''
    gateway:str=''
    dns:tuple=()
    search:tuple=()
    route_search:tuple=()
    manual_dns:bool=False
    never_default:bool=False
    extra_addresses:tuple=()
    routes:str=''
    dhcp_hostname:str=''
    def __post_init__(self):
        for name in ('dns','search','route_search','extra_addresses'):object.__setattr__(self,name,tuple(getattr(self,name)))
    def validate(self):
        if self.method not in ('auto','manual','disabled','shared','link-local'):raise ValueError('Unsupported address assignment method.')
        if self.method=='manual' and (not self.address or not self.netmask):raise ValueError('Specify an IP address and subnet mask.')
        if self.address:
            ipv4(self.address);prefix_from_mask(self.netmask)
        elif self.netmask:raise ValueError('Specify an IP address before entering its subnet mask.')
        if self.gateway:ipv4(self.gateway,'gateway address')
        if len(self.dns)>6 or len(self.search)>6:raise ValueError('Use at most six servers or search domains.')
        for value in self.dns:ipv4(value,'DNS server address')
        for value in self.search:domain(value)
        for value in self.route_search:
            if not value.startswith('~'):raise ValueError('Invalid existing DNS route domain.')
            if value!='~.':domain(value[1:])
        for value in self.extra_addresses:
            try:IPv4Interface(value)
            except ValueError as error:raise ValueError('An existing additional IP address is invalid.') from error
        if self.dhcp_hostname:domain(self.dhcp_hostname)
        if type(self.manual_dns) is not bool or type(self.never_default) is not bool:raise ValueError('Invalid network option.')
        if not isinstance(self.routes,str) or '\n' in self.routes or '\0' in self.routes:raise ValueError('Invalid existing route data.')
        return self
    def set_method(self,method):
        return replace(self,method=method,address='' if method=='auto' else self.address,netmask='' if method=='auto' else self.netmask,extra_addresses=() if method=='auto' else self.extra_addresses)
    def properties(self):
        self.validate();addresses=tuple(([f'{self.address}/{prefix_from_mask(self.netmask)}'] if self.address else [])+list(self.extra_addresses))
        return {'ipv4.method':self.method,'ipv4.addresses':','.join(addresses),'ipv4.gateway':self.gateway,
            'ipv4.dns':','.join(self.dns),
            'ipv4.dns-search':','.join((*self.search,*self.route_search)),
            # Win95 Disable DNS means disable the manual override, not DHCP DNS.
            'ipv4.ignore-auto-dns':'yes' if self.manual_dns else 'no',
            'ipv4.never-default':'yes' if self.never_default else 'no',
            'ipv4.routes':self.routes,'ipv4.dhcp-hostname':self.dhcp_hostname}

@dataclass(frozen=True)
class Connection:
    uuid:str
    name:str
    device:str
    kind:str
    ipv4:IPv4Config=field(default_factory=IPv4Config)
    autoconnect:bool=True
    active:bool=False
    def validate(self):
        try:uuid.UUID(self.uuid)
        except (ValueError,AttributeError) as error:raise ValueError('Invalid connection identifier.') from error
        if not isinstance(self.name,str) or not self.name or '\0' in self.name or '\n' in self.name:raise ValueError('Invalid connection name.')
        if self.device and not re.fullmatch(r'[A-Za-z0-9_.:-]{1,64}',self.device):raise ValueError('Invalid network adapter.')
        self.ipv4.validate();return self

@dataclass(frozen=True)
class NetworkState:
    hostname:str
    connections:tuple=()
    description:str=''
    workgroup:str=''
    def __post_init__(self):object.__setattr__(self,'connections',tuple(self.connections))
    def validate(self):
        # Existing hostnames may be longer than Win95's UI name limit. Validate
        # only an edited name at the transaction boundary; never reject opening.
        if not isinstance(self.hostname,str) or not self.hostname or '\0' in self.hostname or '\n' in self.hostname:raise ValueError('Invalid computer name.')
        if len({c.uuid for c in self.connections})!=len(self.connections):raise ValueError('Duplicate connection identifiers.')
        for connection in self.connections:connection.validate()
        if not isinstance(self.description,str) or len(self.description)>256 or '\0' in self.description or '\n' in self.description:raise ValueError('Invalid computer description.')
        if not isinstance(self.workgroup,str) or len(self.workgroup)>15:raise ValueError('Use at most 15 characters for the workgroup.')
        return self
    def change_connection(self,identifier,**values):
        if identifier not in {c.uuid for c in self.connections}:raise ValueError('The connection is no longer available.')
        return replace(self,connections=tuple(replace(c,**values) if c.uuid==identifier else c for c in self.connections))

@dataclass(frozen=True)
class Adapter:
    device:str
    kind:str
    state:str
    connection:str
    uuid:str
    name:str=''


def parse_connection(value,active=False,fallback_device=''):
    values=value.splitlines()
    if len(values)<len(FIELDS):values+=['']*(len(FIELDS)-len(values))
    data=dict(zip(FIELDS,map(unescape,values)))
    addresses=items(data['ipv4.addresses']);first=IPv4Interface(addresses[0]) if addresses else None
    ipv=IPv4Config(method=data['ipv4.method'] or 'disabled',address=str(first.ip) if first else '',netmask=str(first.netmask) if first else '',
        gateway=data['ipv4.gateway'],dns=items(data['ipv4.dns']),search=tuple(x for x in items(data['ipv4.dns-search']) if not x.startswith('~')),
        route_search=tuple(x for x in items(data['ipv4.dns-search']) if x.startswith('~')),manual_dns=boolean(data['ipv4.ignore-auto-dns']),never_default=boolean(data['ipv4.never-default']),
        extra_addresses=addresses[1:],routes=data['ipv4.routes'],dhcp_hostname=data['ipv4.dhcp-hostname'])
    return Connection(data['connection.uuid'],data['connection.id'],data['connection.interface-name'] or fallback_device,data['connection.type'],ipv,boolean(data['connection.autoconnect']),active).validate()

class NetworkManager:
    def __init__(self,run=None,guard=None):
        self.run=run or self._run;self.guard=guard or self._guest_guard;self.adapters=();self.identity_editable=False
    @staticmethod
    def _guest_guard():
        # Root will switch the project guard to an immutable guest marker.
        from win95lx.guest_identity import is_development_guest
        return is_development_guest()
    @staticmethod
    def _run(*args):
        try:
            return subprocess.run(['nmcli','--wait','12','--colors','no',*args],check=True,capture_output=True,text=True,
                stdin=subprocess.DEVNULL,timeout=17,env={**os.environ,'LC_ALL':'C'}).stdout.rstrip('\n')
        except subprocess.TimeoutExpired as error:raise NetworkError('The network service did not respond in time. The previous settings will be restored.') from error
        except (FileNotFoundError,subprocess.CalledProcessError) as error:
            detail=(getattr(error,'stderr','') or '').casefold()
            if any(word in detail for word in ('not authorized','permission','not permitted','authentication')):raise NetworkError('The network setting is not available because the required guest service policy is missing. No password prompt is used.') from error
            raise NetworkError('The network service could not complete this change. The previous settings will be restored.') from error
    def permissions(self):
        text=self.run('-t','--escape','yes','-f','PERMISSION,VALUE','general','permissions')
        return {row[0]:row[1] for line in text.splitlines() if len(row:=split_escaped(line))==2}
    def inventory(self):
        text=self.run('-t','--escape','yes','-f','DEVICE,TYPE,STATE,CONNECTION,CON-UUID','device','status');rows=[]
        for line in text.splitlines():
            fields=split_escaped(line)
            if len(fields)!=5:continue
            device,kind,state,name,identifier=fields
            if kind=='loopback':continue
            rows.append(Adapter(device,kind,state,name,identifier))
        self.adapters=tuple(rows);return self.adapters
    def connection(self,identifier,active=False,device=''):
        return parse_connection(self.run('-g',','.join(FIELDS),'connection','show','uuid',identifier),active,device)
    def preferences(self):
        self.inventory();active={a.uuid:a.device for a in self.adapters if a.uuid and a.state.startswith('connected')}
        listing=self.run('-t','--escape','yes','-f','UUID,NAME,TYPE,DEVICE,ACTIVE','connection','show');rows=[]
        for line in listing.splitlines():
            fields=split_escaped(line)
            if len(fields)!=5:continue
            identifier,name,kind,device,is_active=fields
            if kind=='loopback':continue
            try:rows.append(self.connection(identifier,boolean(is_active),active.get(identifier,device)))
            except ValueError:continue
        hostname=self.run('general','hostname') or socket.gethostname()
        return NetworkState(hostname,tuple(rows)).validate()
    def snapshot(self):return self.preferences()
    def _write(self,connection):
        old=self.connection(connection.uuid,connection.active,connection.device)
        values=connection.ipv4.properties();args=[]
        for key,value in values.items():
            if value!=old.ipv4.properties()[key]:args.extend((key,value))
        if connection.autoconnect!=old.autoconnect:args+=['connection.autoconnect','yes' if connection.autoconnect else 'no']
        if args:self.run('connection','modify','uuid',connection.uuid,*args)
        if args and connection.active:self.run('connection','up','uuid',connection.uuid,'ifname',connection.device)
    def _restore_connections(self,connections):
        failures=[]
        for c in reversed(tuple(connections)):
            try:
                self._write(c)
                restored=self.connection(c.uuid,c.active,c.device)
                if restored.ipv4!=c.ipv4 or restored.autoconnect!=c.autoconnect:raise NetworkError('Restored connection settings could not be verified.')
            except (NetworkError,ValueError) as error:failures.append(str(error))
        return failures
    def apply(self,pending,baseline):
        pending.validate();baseline.validate()
        if not self.guard():raise NetworkError('Network changes are available inside the installed Win95LX guest.')
        old={c.uuid:c for c in baseline.connections};new={c.uuid:c for c in pending.connections}
        if old.keys()!=new.keys():raise NetworkError('Adding and removing connection profiles is not implemented in this property sheet.')
        changed=[c for c in pending.connections if c.ipv4!=old[c.uuid].ipv4 or c.autoconnect!=old[c.uuid].autoconnect]
        identity=pending.hostname!=baseline.hostname
        if pending.workgroup!=baseline.workgroup or pending.description!=baseline.description:raise NetworkError('File and printer sharing service integration is not installed. Workgroup and description have not been changed.')
        if identity:
            valid_hostname(pending.hostname)
            if not self.identity_editable:raise NetworkError('Computer-name changes are not enabled until the guest identity service is installed.')
        if not changed and not identity:return
        required={MODIFY}|({CONTROL} if any(c.active for c in changed) else set())|({HOSTNAME} if identity else set())
        permissions=self.permissions()
        if any(permissions.get(name)!='yes' for name in required):raise NetworkError('The network setting is not available because the required guest service policy is missing. No password prompt is used.')
        snapshots=[]
        for c in changed:
            current=self.connection(c.uuid,old[c.uuid].active,c.device)
            if current.ipv4!=old[c.uuid].ipv4 or current.autoconnect!=old[c.uuid].autoconnect:raise NetworkError('This connection changed while the window was open. Reopen Network and try again.')
            snapshots.append(current)
        attempted=[];identity_attempted=False
        try:
            for c,before in zip(changed,snapshots):attempted.append(before);self._write(c)
            if identity:
                identity_attempted=True;self.run('general','hostname',pending.hostname)
        except (NetworkError,ValueError) as error:
            failures=self._restore_connections(attempted)
            if identity_attempted:
                try:self.run('general','hostname',baseline.hostname)
                except NetworkError as restore:failures.append(str(restore))
            if failures:raise NetworkError('The network change failed and could not be fully restored. Reopen Network to check the current connection.') from error
            raise
    def restore(self,before):
        if not self.guard():raise NetworkError('Network changes are available inside the installed Win95LX guest.')
        failures=self._restore_connections(before.connections)
        if self.identity_editable:
            try:
                if self.run('general','hostname')!=before.hostname:self.run('general','hostname',before.hostname)
            except NetworkError as error:failures.append(str(error))
        if failures:raise NetworkError('The previous network settings could not be fully restored.')

class NetworkController:
    def __init__(self,backend):self.backend=backend;self.applied=self.pending=backend.preferences()
    def cancel(self):self.pending=self.applied
    def apply(self):
        self.pending.validate();before=self.applied
        self.backend.apply(self.pending,before)
        changed={c.uuid for c in self.pending.connections
                 if c.uuid in {old.uuid for old in before.connections}
                 and next(old for old in before.connections if old.uuid==c.uuid)!=c}
        rollback=replace(before,connections=tuple(c for c in before.connections if c.uuid in changed))
        try:
            current=self.backend.preferences()
            actual={c.uuid:c for c in current.connections}
            for expected in self.pending.connections:
                if expected.uuid in changed:
                    observed=actual.get(expected.uuid)
                    if observed is None or observed.ipv4!=expected.ipv4 or observed.autoconnect!=expected.autoconnect:
                        raise NetworkError('The network service did not retain the requested settings.')
            if self.pending.hostname!=before.hostname and current.hostname!=self.pending.hostname:
                raise NetworkError('The network service did not retain the requested computer name.')
        except (NetworkError,ValueError,OSError) as error:
            try:self.backend.restore(rollback)
            except (NetworkError,ValueError,OSError) as rollback:
                raise NetworkError('The changed network settings could not be verified or fully restored. Reopen Network to check the current connection.') from rollback
            raise NetworkError('The changed network settings could not be verified. The previous connection settings were restored.') from error
        self.applied=self.pending=current

class IPv4Entry:
    """Four bounded edit fields for the native IPAddress control.

    A whole-address paste is atomic. Empty fields remain empty until validation;
    the editor never silently substitutes zero or guesses a subnet mask.
    """
    def __init__(self,value=''):
        from win95lx.shell.text_entry import TextEntry
        parts=value.split('.') if value else ['']*4
        if len(parts)!=4:raise ValueError('An IP address has four fields.')
        self.fields=[TextEntry(text=part) for part in parts];self.index=0;self.just_advanced=False
    @property
    def text(self):return '.'.join(field.text for field in self.fields) if any(f.text for f in self.fields) else ''
    def focus(self,index):
        self.index=max(0,min(3,index));self.fields[self.index].select_all();self.just_advanced=False
    def key(self,name,text='',ctrl=False,shift=False):
        field=self.fields[self.index]
        if text=='.' or name in ('period','KP_Decimal'):
            if self.just_advanced:self.just_advanced=False;return True
            if self.index<3:self.focus(self.index+1)
            return True
        if name in ('Left','BackSpace') and field.cursor==0 and field.selection[0]==field.selection[1] and self.index>0:
            self.index-=1;previous=self.fields[self.index];previous.cursor=len(previous.text);previous.anchor=previous.cursor;self.just_advanced=False;return True
        if name=='Right' and field.cursor==len(field.text) and self.index<3:
            self.focus(self.index+1);return True
        if text:
            if '.' in text:
                parts=text.split('.')
                if len(parts)!=4 or any(not p.isascii() or not p.isdigit() or len(p)>3 or int(p)>255 for p in parts):return False
                for item,value in zip(self.fields,parts):item.text=value;item.cursor=len(value);item.anchor=item.cursor
                self.index=3;self.just_advanced=False;return True
            if not text.isascii() or not text.isdigit():return False
            a,b=field.selection;candidate=field.text[:a]+text+field.text[b:]
            if len(candidate)>3 or int(candidate)>255:return False
            field.replace(text);self.just_advanced=False
            if len(field.text)==3 and self.index<3:self.focus(self.index+1);self.just_advanced=True
            return True
        self.just_advanced=False;return field.key(name,ctrl=ctrl,shift=shift)
