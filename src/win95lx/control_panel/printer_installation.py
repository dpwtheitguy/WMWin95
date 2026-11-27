"""Typed printer discovery and create-only installation transactions.

An IPP backend advertisement is not a discovered device. Queue creation is
restricted to fresh unpredictable internal identifiers; display names are kept
separately. Existing destinations are never Add-Modified by this executor.
"""
from dataclasses import dataclass,replace
import re
from urllib.parse import urlsplit,parse_qsl,unquote
from win95lx.control_panel.printer_preferences import PrinterError,queue_name

@dataclass(frozen=True)
class PrinterDriver:
    ident:str
    manufacturer:str
    label:str
    driverless:bool=False

@dataclass(frozen=True)
class PrinterEndpoint:
    uri:str
    label:str
    model:str=''

@dataclass(frozen=True)
class InstallationDiscovery:
    drivers:tuple[PrinterDriver,...]
    endpoints:tuple[PrinterEndpoint,...]
    transports:tuple[str,...]
    existing_names:tuple[str,...]

@dataclass(frozen=True)
class PrinterInstallPlan:
    name:str
    endpoint:str
    driver:str
    description:str
    print_test_page:bool=False
    make_user_default:bool=False
    def validate(self,discovery):
        try:queue_name(self.name)
        except ValueError as error:raise PrinterError(str(error))from error
        if self.name.casefold()in {name.casefold()for name in discovery.existing_names}:raise PrinterError('A printer with this name already exists. Type a different printer name.')
        target=validate_endpoint(self.endpoint)
        if urlsplit(target).scheme=='usb'and target not in {endpoint.uri for endpoint in discovery.endpoints}:raise PrinterError('Select an attached USB printer found by the printing service.')
        driver=next((driver for driver in discovery.drivers if driver.ident==self.driver),None)
        if driver is None:raise PrinterError('The selected printer driver is no longer available. Select another driver.')
        if driver.driverless and urlsplit(target).scheme not in('ipp','ipps'):raise PrinterError('IPP Everywhere requires an ipp:// or ipps:// printer address.')
        if not isinstance(self.description,str)or not self.description.strip()or len(self.description)>127 or any(ord(c)<32 for c in self.description):raise PrinterError('The printer description contains unsupported characters.')
        return replace(self,endpoint=target)


def validate_endpoint(value):
    if not isinstance(value,str)or not value or any(ord(c)<33 for c in value):raise PrinterError('Type a complete printer address.')
    try:
        uri=urlsplit(value);port=uri.port
    except ValueError as error:raise PrinterError('The printer address is not valid.')from error
    if uri.scheme not in('ipp','ipps','socket','lpd','usb'):raise PrinterError('Choose an IPP, AppSocket, LPD or detected USB printer address.')
    if uri.username is not None or uri.password is not None:raise PrinterError('Passwords cannot be stored in the printer address.')
    if uri.fragment or(uri.query and uri.scheme!='usb'):raise PrinterError('The printer address cannot contain a query or fragment.')
    if any(ord(c)<32 for c in unquote(value)):raise PrinterError('The printer address contains unsupported characters.')
    if uri.scheme=='usb'and uri.query:
        parts=parse_qsl(uri.query,keep_blank_values=True)
        if not parts or len({key for key,_ in parts})!=len(parts)or any(key not in('serial','interface')or not value or len(value)>256 for key,value in parts):raise PrinterError('The detected USB printer address is not supported.')
    if not uri.hostname:raise PrinterError('The printer address must include a device or host name.')
    if port is not None and not 1<=port<=65535:raise PrinterError('The printer port is not valid.')
    if uri.scheme in('ipp','ipps','lpd')and not uri.path.strip('/'):raise PrinterError('The printer address must include its queue path.')
    return value


def discover_installation(connection):
    """Read-only scheduler query; call on an isolated service worker.

    getDevices can take seconds and may require authorization. Do not call
    this function on the GTK thread or infer write access from its success.
    """
    try:
        existing=tuple(connection.getPrinters())
        rows=connection.getDevices(limit=100,include_schemes=['ipp','ipps','dnssd','usb','socket','lpd'])
        ppds=connection.getPPDs(limit=10000)
    except Exception as error:raise PrinterError('Printer discovery could not be completed. The printing service may require authorization.')from error
    endpoints=[];transports=set()
    for address,attrs in rows.items():
        # CUPS reports "ipp" / "ipps" backend advertisements with no device.
        # They are transport capabilities, never fabricated hardware entries.
        if ':'not in address:transports.add(address);continue
        try:validate_endpoint(address)
        except PrinterError:continue
        endpoints.append(PrinterEndpoint(address,str(attrs.get('device-info')or address),str(attrs.get('device-make-and-model')or'')))
    drivers=[PrinterDriver('everywhere','Generic','IPP Everywhere',True)]
    for ident,attrs in ppds.items():
        drivers.append(PrinterDriver(str(ident),str(attrs.get('ppd-make')or'Other'),str(attrs.get('ppd-make-and-model')or ident)))
    return InstallationDiscovery(tuple(sorted(drivers,key=lambda d:(d.manufacturer.casefold(),d.label.casefold()))),tuple(sorted(endpoints,key=lambda e:e.label.casefold())),tuple(sorted(transports)),existing)

WIZARD_PAGES=('welcome','driver','port','name','testpage')
@dataclass(frozen=True)
class PrinterWizardState:
    page:int=0
    driver:str='everywhere'
    endpoint:str=''
    name:str=''
    print_test_page:bool=False
    make_user_default:bool=False
    def previous(self):return replace(self,page=max(0,self.page-1))
    def next(self,discovery):
        if self.page==1 and self.driver not in{d.ident for d in discovery.drivers}:raise PrinterError('Select a printer driver.')
        if self.page==2:validate_endpoint(self.endpoint)
        if self.page>=3:self.plan().validate(discovery)
        return replace(self,page=min(len(WIZARD_PAGES)-1,self.page+1))
    def plan(self):
        ident=re.sub(r'[\s/#]+','_',self.name.strip())
        if ident.startswith('-'):ident='Printer_'+ident
        return PrinterInstallPlan(ident,self.endpoint,self.driver,self.name,self.print_test_page,self.make_user_default)

INSTALLATION_BLOCKER='The printer installation service is unavailable. Install the printing component and try again.'


@dataclass(frozen=True)
class PrinterInstallResult:
    queue:str
    description:str
    test_job:int|None=None

class PartialInstallation(PrinterError):
    """A known newly created queue exists; never disguise this as rollback."""
    def __init__(self,queue,detail):
        self.queue=queue
        super().__init__('The printer was added, but '+detail+'. The new printer has been kept. Open Printers to check it before trying again.')

class PrinterInstaller:
    """Create-only adapter; caller serializes requests through a narrow service.

    Never pass user input as an existing CUPS destination. The random identity
    is generated inside this executor, and a durable intent is saved before the
    first mutation. On uncertain failure we retain the owned queue and report
    partial completion rather than deleting externally changed data. A server
    administrator remains authoritative; this is not a lock against root.
    """
    def __init__(self,connection,journal,*,token=None):
        import secrets
        self.connection=connection;self.journal=journal;self.token=token or(lambda:secrets.token_hex(16))
    def install(self,plan):
        from dataclasses import asdict
        import time
        discovery=discover_installation(self.connection);plan=plan.validate(discovery)
        # descriptions also collide: random identifiers must not hide duplicate
        # user-facing names on reopening the wizard.
        rows=self.connection.getPrinters()
        if any(plan.description.casefold()in(n.casefold(),str(a.get('printer-info')or n).casefold())for n,a in rows.items()):
            raise PrinterError('A printer with this name already exists. Type a different printer name.')
        token=self.token()
        if not re.fullmatch('[0-9a-f]{32}',token):raise PrinterError('The printer identity could not be allocated.')
        name='w95lx_'+token
        if any(n.casefold()==name.casefold()for n in rows):raise PrinterError('The printer identity is already in use. Try again.')
        record={'version':1,'queue':name,'description':plan.description,'endpoint':plan.endpoint,'driver':plan.driver,'phase':'intent','created':time.time()}
        self.journal(record)
        try:
            self.connection.addPrinter(name,device=plan.endpoint,ppdname=plan.driver,info=plan.description,location='')
        except Exception as error:
            # Add-Modify can time out after its server-side success. Read back
            # only our unpredictable name; never claim no changes without it.
            try:exists=name in self.connection.getPrinters()
            except Exception:exists=None
            record['phase']='uncertain'if exists is None else'created'if exists else'failed'
            try:self.journal(record)
            except OSError:pass
            if exists is not False:raise PartialInstallation(name,'the printing service did not confirm completion')from error
            raise PrinterError('The printer could not be added. Check its address, connection and driver, then try again.')from error
        try:
            record['phase']='created';self.journal(record)
            actual=self.connection.getPrinterAttributes(name,requested_attributes=['printer-info','device-uri','printer-state','printer-is-accepting-jobs','printer-is-shared'])
            if actual is None or str(actual.get('printer-info'))!=plan.description or str(actual.get('device-uri'))!=plan.endpoint:
                raise PrinterError('the printer settings could not be verified')
            self.connection.setPrinterShared(name,False)
            self.connection.enablePrinter(name);self.connection.acceptJobs(name)
            until=time.monotonic()+2
            while True:
                actual=self.connection.getPrinterAttributes(name,requested_attributes=['printer-info','device-uri','printer-state','printer-is-accepting-jobs','printer-is-shared'])
                if actual and actual.get('printer-is-accepting-jobs',False)and int(actual.get('printer-state',5))!=5 and actual.get('printer-is-shared')is False:break
                if time.monotonic()>=until:raise PrinterError('the printer could not be started')
                time.sleep(.02)
        except Exception as error:
            record['phase']='partial'
            try:self.journal(record)
            except OSError:pass
            raise PartialInstallation(name,'its ready state could not be verified')from error
        record['phase']='ready'
        try:self.journal(record)
        except OSError as error:raise PartialInstallation(name,'its installation record could not be saved')from error
        return PrinterInstallResult(name,plan.description)


def write_installation_record(directory,record):
    """Atomic durable journal in a root-owned service directory."""
    import json,os,tempfile
    from pathlib import Path
    directory=Path(directory)
    if not re.fullmatch('w95lx_[0-9a-f]{32}',record.get('queue','')):raise PrinterError('The printer journal identity is not valid.')
    directory.mkdir(mode=0o700,parents=True,exist_ok=True)
    if directory.is_symlink():raise PrinterError('The printer journal is redirected.')
    target=directory/(record['queue']+'.json');temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=directory,prefix='.install-',delete=False)as stream:
            temporary=Path(stream.name);stream.write((json.dumps(record,sort_keys=True)+'\n').encode());stream.flush();os.fsync(stream.fileno())
        temporary.replace(target)
        descriptor=os.open(directory,os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)


def encode_discovery(discovery):
    from dataclasses import asdict
    return asdict(discovery)


def decode_discovery(value):
    return InstallationDiscovery(tuple(PrinterDriver(**row)for row in value['drivers']),tuple(PrinterEndpoint(**row)for row in value['endpoints']),tuple(value['transports']),tuple(value['existing_names']))

class PrinterInstallationClient:
    """Bounded AF_UNIX service calls, intended for a background UI worker."""
    def __init__(self,path='/run/win95lx-printers/control.sock',timeout=25):self.path=path;self.timeout=timeout
    def request(self,operation,**values):
        import json,socket
        request=json.dumps({'operation':operation,**values},separators=(',',':')).encode()+b'\n'
        if len(request)>8192:raise PrinterError('The printer request is too large.')
        try:
            with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)as stream:
                stream.settimeout(self.timeout);stream.connect(self.path);stream.sendall(request);data=b''
                while not data.endswith(b'\n'):
                    chunk=stream.recv(65536)
                    if not chunk:raise PrinterError('The printer service closed the connection.')
                    data+=chunk
                    if len(data)>4*1024*1024:raise PrinterError('The printer service reply is too large.')
            reply=json.loads(data)
        except(OSError,ValueError)as error:raise PrinterError('The printer installation service is unavailable or did not respond. Check Printers before retrying an installation.')from error
        if not reply.get('ok'):
            if reply.get('queue'):raise PartialInstallation(reply['queue'],reply.get('error','completion was not confirmed'))
            raise PrinterError(reply.get('error','The printer operation could not be completed.'))
        return reply['value']
    def discover(self):return decode_discovery(self.request('discover'))
    def install(self,plan):
        from dataclasses import asdict
        # Per-user defaults and documents are intentionally applied by the
        # non-admin client, not the privileged service identity.
        value=self.request('install',plan=asdict(plan));return PrinterInstallResult(**value)
