"""Real Fontconfig inventory and transactional per-user font management."""
from dataclasses import dataclass
from pathlib import Path
from functools import lru_cache
import ctypes as C,ctypes.util,hashlib,json,os,shutil,stat,subprocess,tempfile

EXTENSIONS=frozenset(('.ttf','.otf','.ttc','.otc','.pfa','.pfb','.pcf','.bdf','.fon','.fnt'))
MAX_FONT_BYTES=128*1024*1024

@dataclass(frozen=True)
class FontFace:
    path:Path
    index:int
    family:str
    style:str
    format:str
    version:int=0
    @property
    def label(self):return self.family+(' '+self.style if self.style.casefold() not in ('regular','normal','book','') else '')
    @property
    def key(self):return (str(self.path),self.index)

class _FontSet(C.Structure):
    _fields_=[('nfont',C.c_int),('sfont',C.c_int),('fonts',C.POINTER(C.c_void_p))]

class Fontconfig:
    def __init__(self):
        name=ctypes.util.find_library('fontconfig')
        if not name:raise RuntimeError('The font library is unavailable.')
        self.lib=C.CDLL(name)
        specs={
            'FcInit':([],C.c_int),'FcConfigCreate':([],C.c_void_p),'FcConfigBuildFonts':([C.c_void_p],C.c_int),'FcConfigDestroy':([C.c_void_p],None),'FcInitReinitialize':([],C.c_int),'FcConfigGetCurrent':([],C.c_void_p),
            'FcPatternCreate':([],C.c_void_p),'FcPatternDestroy':([C.c_void_p],None),
            'FcObjectSetCreate':([],C.c_void_p),'FcObjectSetAdd':([C.c_void_p,C.c_char_p],C.c_int),'FcObjectSetDestroy':([C.c_void_p],None),
            'FcFontList':([C.c_void_p,C.c_void_p,C.c_void_p],C.POINTER(_FontSet)),
            'FcFontSetDestroy':([C.POINTER(_FontSet)],None),
            'FcPatternGetString':([C.c_void_p,C.c_char_p,C.c_int,C.POINTER(C.c_char_p)],C.c_int),
            'FcPatternGetInteger':([C.c_void_p,C.c_char_p,C.c_int,C.POINTER(C.c_int)],C.c_int),
            'FcFreeTypeQuery':([C.c_char_p,C.c_int,C.c_void_p,C.POINTER(C.c_int)],C.c_void_p),
            'FcConfigAppFontAddFile':([C.c_void_p,C.c_char_p],C.c_int),
            'FcDirCacheRescan':([C.c_char_p,C.c_void_p],C.c_void_p),
            'FcDirCacheUnload':([C.c_void_p],None),
        }
        for key,(args,result) in specs.items():fn=getattr(self.lib,key);fn.argtypes=args;fn.restype=result
        if not self.lib.FcInit():raise RuntimeError('The font library could not be initialized.')
    def string(self,pattern,key,fallback=''):
        value=C.c_char_p()
        if self.lib.FcPatternGetString(pattern,key.encode(),0,C.byref(value))!=0:return fallback
        return (value.value or b'').decode('utf-8',errors='replace')
    def integer(self,pattern,key,default=0):
        value=C.c_int()
        return value.value if self.lib.FcPatternGetInteger(pattern,key.encode(),0,C.byref(value))==0 else default
    def face(self,pattern,path=None,index=None):
        path=Path(path or self.string(pattern,'file'))
        return FontFace(path,self.integer(pattern,'index') if index is None else index,self.string(pattern,'family',path.stem),self.string(pattern,'style','Regular'),self.string(pattern,'fontformat','Unknown'),self.integer(pattern,'fontversion'))
    def query(self,path):
        path=Path(path);count=C.c_int();pattern=self.lib.FcFreeTypeQuery(os.fsencode(path),0,None,C.byref(count))
        if not pattern:raise ValueError('This file is not a supported font, or its font data is damaged.')
        try:faces=[self.face(pattern,path,0)]
        finally:self.lib.FcPatternDestroy(pattern)
        if not 1<=count.value<=256:raise ValueError('This font collection contains an unsupported number of faces.')
        for index in range(1,count.value):
            pattern=self.lib.FcFreeTypeQuery(os.fsencode(path),index,None,C.byref(count))
            if not pattern:raise ValueError('One of the font collection faces could not be read.')
            try:faces.append(self.face(pattern,path,index))
            finally:self.lib.FcPatternDestroy(pattern)
        return tuple(faces)
    def inventory(self):
        pattern=self.lib.FcPatternCreate();objects=self.lib.FcObjectSetCreate();fonts=None
        if not pattern or not objects:raise MemoryError('Could not read the font list.')
        try:
            for key in (b'file',b'family',b'style',b'fontformat',b'fontversion',b'index'):self.lib.FcObjectSetAdd(objects,key)
            fonts=self.lib.FcFontList(self.lib.FcConfigGetCurrent(),pattern,objects)
            if not fonts:raise RuntimeError('The installed font list could not be read.')
            if not 0<=fonts.contents.nfont<=50000:raise ValueError('The installed font list is too large.')
            return tuple(self.face(fonts.contents.fonts[i]) for i in range(fonts.contents.nfont))
        finally:
            if fonts:self.lib.FcFontSetDestroy(fonts)
            self.lib.FcObjectSetDestroy(objects);self.lib.FcPatternDestroy(pattern)
    def visible(self,path):
        expected=Path(path).resolve()
        return any(face.path.resolve()==expected for face in self.inventory())
    def refresh(self):
        if not self.lib.FcInitReinitialize():raise RuntimeError('The font list could not be refreshed.')
    def refresh_directory(self,path):
        # fc-cache's command-line grace delay stalls an interactive import.
        # Use its library operation, then reload and verify actual visibility.
        self.refresh();config=self.lib.FcConfigGetCurrent()
        cache=self.lib.FcDirCacheRescan(os.fsencode(path),config)
        if not cache:raise RuntimeError('The font cache could not be updated.')
        self.lib.FcDirCacheUnload(cache);self.refresh()
    def preview_config(self,paths):
        config=self.lib.FcConfigCreate()
        if not config:raise MemoryError('The font preview could not be created.')
        try:
            for path in paths:
                if not self.lib.FcConfigAppFontAddFile(config,os.fsencode(path)):raise ValueError('This font could not be loaded for preview.')
            if not self.lib.FcConfigBuildFonts(config):raise RuntimeError('The preview font list could not be built.')
            return config
        except Exception:self.lib.FcConfigDestroy(config);raise
    def destroy_config(self,config):self.lib.FcConfigDestroy(config)

@lru_cache(maxsize=1)
def fontconfig():return Fontconfig()

def digest(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

class FontCatalog:
    def __init__(self,root=None,manifest=None,home=None,scanner=None,cache=None):
        self.home=Path(home or Path.home()).resolve()
        self.root=Path(root or self.home/'.local/share/fonts/Win95LX')
        self.manifest=Path(manifest or self.home/'.config/win95lx/fonts.json')
        self.scanner=scanner or fontconfig();self.cache=cache or self.update_cache
        from win95lx.control_panel.bitmap_font_policy import BitmapFontPolicy
        self.bitmap_policy=BitmapFontPolicy(self.home,self.root)
        self.check_paths()
    def check_paths(self):
        for path in (self.root,self.manifest):
            if path.is_symlink() or not path.resolve().is_relative_to(self.home):raise ValueError('The font location must be an ordinary path inside your user folder.')
    def ledger(self):
        self.check_paths()
        try:
            value=json.loads(self.manifest.read_text())
            if not isinstance(value,dict) or any(not isinstance(k,str) or Path(k).name!=k or not isinstance(v,str) or len(v)!=64 for k,v in value.items()):raise ValueError('The personal font installation record is damaged.')
            return value
        except FileNotFoundError:return {}
        except (json.JSONDecodeError,UnicodeError) as error:raise ValueError('The personal font installation record is damaged.') from error
    def save_ledger(self,value):
        self.check_paths();self.manifest.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(prefix='.fonts-',dir=self.manifest.parent)
        try:
            with os.fdopen(fd,'w') as stream:json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
            os.replace(temp,self.manifest)
        finally:Path(temp).unlink(missing_ok=True)
    def update_cache(self):
        if hasattr(self.scanner,'refresh_directory'):self.scanner.refresh_directory(self.root)
        else:
            subprocess.run(['fc-cache','-f',str(self.root)],check=True,capture_output=True,text=True,timeout=30)
            self.scanner.refresh()
    def inventory(self):
        self.check_paths();rows={face.key:face for face in self.scanner.inventory() if face.path.is_file()}
        known={str(face.path.resolve()) for face in rows.values()}
        if self.root.exists():
            for path in sorted(self.root.rglob('*')):
                if path.is_symlink() or not path.is_file() or path.suffix.casefold() not in EXTENSIONS or str(path.resolve()) in known:continue
                try:
                    for face in self.scanner.query(path):rows[face.key]=face
                except (OSError,ValueError):continue
        return tuple(sorted(rows.values(),key=lambda face:(face.label.casefold(),str(face.path),face.index)))
    def candidates(self,directory):
        directory=Path(directory)
        return tuple(path for path in sorted(directory.rglob('*')) if path.is_file() and not path.is_symlink() and path.suffix.casefold() in EXTENSIONS)
    def install(self,source):
        self.check_paths();source=Path(source)
        if source.is_symlink() or not source.is_file():raise ValueError('Choose an ordinary font file.')
        if source.suffix.casefold() not in EXTENSIONS or source.name.startswith('.'):raise ValueError('Choose a TrueType, OpenType, Type 1 or supported bitmap font file.')
        if source.stat().st_size>MAX_FONT_BYTES:raise ValueError('This font file is too large.')
        self.scanner.query(source)
        self.root.mkdir(parents=True,exist_ok=True);self.check_paths();destination=self.root/source.name
        if any(p.name.casefold()==source.name.casefold() for p in self.root.iterdir()):raise FileExistsError('A font with this filename is already installed. No files were replaced.')
        previous=self.ledger();temp=None;installed=False;identity=None;policy_state=None
        try:
            fd,temp=tempfile.mkstemp(prefix='.install-',dir=self.root)
            with os.fdopen(fd,'wb') as output,source.open('rb') as input:
                shutil.copyfileobj(input,output);output.flush();os.fsync(output.fileno())
            faces=self.scanner.query(Path(temp));sha=digest(temp)
            info=Path(temp).stat();identity=(info.st_dev,info.st_ino)
            os.link(temp,destination);installed=True;Path(temp).unlink();temp=None
            policy_state=self.bitmap_policy.update(previous,{**previous,destination.name:sha})
            self.cache()
            if not self.scanner.visible(destination):raise ValueError('This font is recognized, but it is not enabled by the system font configuration. No font was installed.')
            self.save_ledger({**previous,destination.name:sha})
            return tuple(FontFace(destination,f.index,f.family,f.style,f.format,f.version) for f in faces)
        except Exception:
            if installed and destination.exists():
                info=destination.lstat()
                if (info.st_dev,info.st_ino)==identity:destination.unlink()
            self.bitmap_policy.restore(policy_state)
            try:self.cache()
            except (OSError,RuntimeError,subprocess.SubprocessError):pass
            raise
        finally:
            if temp:Path(temp).unlink(missing_ok=True)
    def removal_reason(self,path):
        self.check_paths();path=Path(path)
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()) or path.parent.resolve()!=self.root.resolve():return 'System fonts and fonts outside this personal installation folder cannot be removed here.'
        record=self.ledger().get(path.name)
        if not record:return 'This font was not installed by Fonts. Remove it using its original installer.'
        if not path.is_file():return 'This font file is no longer available.'
        if path.stat().st_uid!=os.geteuid() or digest(path)!=record:return 'This font changed outside Fonts and cannot be removed without review.'
        return None
    def remove(self,path):
        path=Path(path);reason=self.removal_reason(path)
        if reason:raise PermissionError(reason)
        previous=self.ledger();fd,backup=tempfile.mkstemp(prefix='.remove-',dir=self.root);os.close(fd)
        os.replace(path,backup);policy_state=None
        try:
            if Path(backup).is_symlink() or digest(backup)!=previous[path.name]:raise PermissionError('This font changed while the operation was starting. No font was removed.')
            updated=dict(previous);updated.pop(path.name)
            policy_state=self.bitmap_policy.update(previous,updated)
            self.cache();self.save_ledger(updated)
        except Exception:
            try:os.link(backup,path)
            except FileExistsError:raise RuntimeError('The font could not be restored because another file occupies its location. The original font is retained in '+str(backup))
            Path(backup).unlink();self.bitmap_policy.restore(policy_state)
            try:self.cache()
            except (OSError,RuntimeError,subprocess.SubprocessError):pass
            raise
        else:Path(backup).unlink()


def font_metadata(path,index=0):
    """Read bounded SFNT name-table metadata without executing font files."""
    import struct
    with Path(path).open('rb') as stream:
        size=stream.seek(0,2);stream.seek(0);header=stream.read(12);base=0
        if header[:4]==b'ttcf':
            if len(header)!=12:return {}
            count=struct.unpack_from('>I',header,8)[0]
            if not 0<=index<count<=256:return {}
            stream.seek(12+index*4);offset=stream.read(4)
            if len(offset)!=4:return {}
            base=struct.unpack('>I',offset)[0];stream.seek(base);header=stream.read(12)
        if len(header)!=12 or header[:4] not in (b'\x00\x01\x00\x00',b'OTTO',b'true'):return {}
        count=struct.unpack_from('>H',header,4)[0]
        if count>4096 or base+12+count*16>size:return {}
        table=None
        for _ in range(count):
            entry=stream.read(16)
            if entry[:4]==b'name':table=struct.unpack_from('>II',entry,8)
        if table is None:return {}
        offset,length=table
        if length>8*1024*1024 or offset+length>size or length<6:return {}
        stream.seek(offset);data=stream.read(length)
    version,count,strings=struct.unpack_from('>HHH',data)
    if version>1 or count>8192 or 6+count*12>len(data) or strings>len(data):return {}
    keys={0:'copyright',1:'family',2:'style',4:'full_name',5:'version',8:'manufacturer'};result={};scores={}
    for i in range(count):
        platform,encoding,language,name,length,start=struct.unpack_from('>HHHHHH',data,6+i*12)
        if name not in keys or strings+start+length>len(data) or length>8192:continue
        if platform in (0,3):codec='utf-16-be'
        elif platform==1:codec='mac_roman'
        else:continue
        try:value=data[strings+start:strings+start+length].decode(codec)
        except UnicodeError:continue
        score=(platform==3,language==0x409,encoding in (1,10))
        if name not in scores or score>scores[name]:scores[name]=score;result[keys[name]]=value[:4096]
    return result
