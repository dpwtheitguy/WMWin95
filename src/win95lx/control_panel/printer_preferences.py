"""CUPS printer namespace and per-user defaults; no implicit administration."""
from dataclasses import dataclass
from pathlib import Path
import getpass,os,shlex,subprocess,tempfile,urllib.parse

class PrinterError(RuntimeError):pass

def queue_name(value):
    if not isinstance(value,str)or not value or len(value)>127 or value.startswith('-')or any(c.isspace()or c in '/#'or ord(c)<32 for c in value):raise ValueError('The printer name is not valid.')
    return value

def public_uri(value):
    try:
        uri=urllib.parse.urlsplit(str(value));host=uri.hostname or''
        if ':'in host:host='['+host+']'
        if uri.port:host+=':'+str(uri.port)
        return urllib.parse.urlunsplit((uri.scheme,host,uri.path,uri.query,''))
    except ValueError:return ''

@dataclass(frozen=True)
class Printer:
    name:str
    description:str
    location:str=''
    model:str=''
    state:int=3
    accepting:bool=True
    default:bool=False
    uri:str=''
    @property
    def status(self):return {3:'Ready',4:'Printing',5:'Paused'}.get(self.state,'Unavailable')

@dataclass(frozen=True)
class PrintJob:
    ident:int
    printer:str
    title:str
    owner:str
    state:int
    kilobytes:int=0
    @property
    def status(self):return {3:'Waiting',4:'Held',5:'Printing',6:'Stopped',7:'Canceled',8:'Error',9:'Printed'}.get(self.state,'Unknown')

@dataclass(frozen=True)
class PrinterCapabilities:
    administration:bool
    reason:str=''

class Printers:
    def __init__(self,connection=None,*,run=None,options_path=None,user=None,administration=False):
        self._administration=administration is True;self._provided=connection;self.run=run or self.command;self.options_path=options_path or Path.home()/'.cups/lpoptions';self.user=user or getpass.getuser()
    @staticmethod
    def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=10,env={**os.environ,'LC_ALL':'C'}).stdout
    def connection(self):
        if self._provided is not None:return self._provided
        try:
            import cups
            # Product commands never prompt on an invisible terminal or retain
            # credentials. The server's ordinary session policy decides access.
            cups.setPasswordCB(lambda _prompt:'')
            return cups.Connection()
        except (ImportError,RuntimeError,OSError)as error:raise PrinterError('The printing service is unavailable. Check the printer connection and try again.')from error
    @staticmethod
    def failure(error):
        code=error.args[0]if error.args else None
        if code in(0x401,0x402,0x403):return PrinterError('Access is denied. This session is not authorized to change that printer.')
        if code==0x406:return PrinterError('The printer or document is no longer available. Choose Refresh and try again.')
        return PrinterError('The printer operation could not be completed. Check the printer and try again.')
    def inventory(self):
        connection=self.connection()
        try:
            rows=connection.getPrinters();destinations=connection.getDests();default=destinations.get((None,None));default=getattr(default,'name',None)
        except Exception as error:raise self.failure(error)from error
        result=[]
        for name,attrs in rows.items():
            queue_name(name);result.append(Printer(name,str(attrs.get('printer-info')or name),str(attrs.get('printer-location')or''),str(attrs.get('printer-make-and-model')or''),int(attrs.get('printer-state',3)),bool(attrs.get('printer-is-accepting-jobs',True)),name==default,public_uri(attrs.get('device-uri',''))))
        return tuple(sorted(result,key=lambda p:p.name.casefold()))
    def printer(self,name):
        queue_name(name)
        value=next((p for p in self.inventory()if p.name==name),None)
        if value is None:raise PrinterError('The printer is no longer available. Choose Refresh and try again.')
        return value
    def capabilities(self):
        # Reading server settings does not prove permission to change queues.
        # Production sessions remain own-document-only. The explicit opt-in
        # is reserved for an independently proven owned scheduler/policy.
        return PrinterCapabilities(self._administration,'' if self._administration else 'This session can manage its own documents. Printer installation, deletion and queue administration require separately verified authorization.')
    def jobs(self,name):
        self.printer(name);connection=self.connection()
        fields=['job-printer-uri','job-name','job-originating-user-name','job-state','job-k-octets']
        try:
            rows=connection.getJobs(which_jobs='not-completed',my_jobs=False)
            own=connection.getJobs(which_jobs='not-completed',my_jobs=True)
        except Exception as error:raise self.failure(error)from error
        result=[]
        for ident,summary in rows.items():
            attrs=dict(summary)
            # CUPS privacy policy can make Get-Jobs return only job-uri.
            # Get-Job-Attributes exposes destination/state separately; do not
            # incorrectly turn a real queue into an empty list.
            if not all(field in attrs for field in fields):
                try:attrs.update(connection.getJobAttributes(int(ident)))
                except Exception as error:
                    if error.args and error.args[0]==0x406:continue
                    raise self.failure(error)from error
            target=urllib.parse.unquote(urllib.parse.urlsplit(attrs.get('job-printer-uri',attrs.get('printer-uri',''))).path.rsplit('/',1)[-1])
            state=int(attrs.get('job-state',3))
            if target==name and state not in(7,8,9):
                owner=str(attrs.get('job-originating-user-name')or(self.user if ident in own else''))
                result.append(PrintJob(int(ident),name,str(attrs.get('job-name')or'Untitled'),owner,state,max(0,int(attrs.get('job-k-octets',0)))))
        return tuple(sorted(result,key=lambda j:j.ident))
    def cancel(self,name,ident):
        if type(ident)is not int or ident<=0:raise ValueError('The document number is not valid.')
        job=next((job for job in self.jobs(name)if job.ident==ident),None)
        if job is None:raise PrinterError('The document is no longer in this printer queue.')
        if job.owner!=self.user and not self.capabilities().administration:raise PrinterError('Access is denied. Only your own documents can be canceled in this session.')
        try:self.connection().cancelJob(ident,purge_job=False)
        except Exception as error:raise self.failure(error)from error
    def set_default(self,name):
        self.printer(name);path=self.options_path
        if path.is_symlink()or path.parent.is_symlink():raise PrinterError('The printer preference location is redirected and cannot be changed safely.')
        before=path.read_bytes()if path.exists()else None
        lines=(before or b'').decode('utf-8').splitlines();result=[];found=False
        for line in lines:
            try:parts=shlex.split(line,comments=True)
            except ValueError as error:raise PrinterError('The printer preferences contain an invalid entry and were kept unchanged.')from error
            if len(parts)>=2 and parts[0]in('Dest','Default'):
                first,rest=line.lstrip().split(None,1)
                if parts[1]==name:line='Default '+rest;found=True
                elif first=='Default':line='Dest '+rest
            result.append(line)
        if not found:result.append('Default '+name)
        encoded=('\n'.join(result)+'\n').encode('utf-8');path.parent.mkdir(parents=True,exist_ok=True)
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.lpoptions-',delete=False)as stream:temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
            temporary.replace(path)
            if not self.printer(name).default:raise PrinterError('The default printer could not be retained. The previous preference was restored.')
        except Exception:
            # Restore only while the file is still our exact write. Do not undo
            # an external preference edit discovered during readback.
            if path.exists()and path.read_bytes()==encoded:
                if before is None:path.unlink()
                else:
                    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.lpoptions-',delete=False)as stream:rollback=Path(stream.name);stream.write(before)
                    rollback.replace(path)
            raise
        finally:
            if temporary is not None:temporary.unlink(missing_ok=True)
    def print_test_page(self,name):
        printer=self.printer(name)
        if not printer.accepting:raise PrinterError('The printer is not accepting documents.')
        title=printer.description.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
        document=('%!PS-Adobe-3.0\n%%Pages:1\n/Helvetica findfont 18 scalefont setfont\n72 720 moveto(Windows Printer Test Page)show\n/Helvetica findfont 12 scalefont setfont\n72 680 moveto('+title+')show\n72 650 moveto(This page confirms that the printer can receive documents.)show\nshowpage\n%%EOF\n').encode('latin-1','replace')
        with tempfile.NamedTemporaryFile(suffix='.ps')as stream:
            stream.write(document);stream.flush()
            try:
                ident=int(self.connection().printFile(name,stream.name,'Windows Printer Test Page',{'document-format':'application/postscript'}))
                if ident<=0:raise PrinterError('The test page could not be sent to the printer.')
                return ident
            except Exception as error:raise self.failure(error)from error
    def pause(self,name,paused):
        if type(paused)is not bool:raise ValueError('The printer state is not valid.')
        self.printer(name)
        if not self.capabilities().administration:raise PrinterError(self.capabilities().reason)
        try:
            if paused:self.connection().disablePrinter(name,reason='Paused by user')
            else:self.connection().enablePrinter(name)
        except Exception as error:raise self.failure(error)from error
