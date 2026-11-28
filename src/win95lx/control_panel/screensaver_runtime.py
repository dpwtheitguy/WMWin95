"""Typed private screensaver packages; prefix preparation belongs on a worker."""
import hashlib
import fcntl
import json
import os
import shutil
import subprocess
import threading
import tempfile
import struct
from win95lx.control_panel.theme_appearance import DEFAULT_COLORS, validate_colors
from pathlib import Path

PROFILE_RECIPE = 1
RUNTIME_RECIPE = 2
TRUSTED_GROUP = 'trusted95'
MODES = {'fullscreen': '/s', 'configure': '/c', 'preview': '/p'}


def _relative(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('Invalid package path.')
    path = Path(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('Invalid package path.')
    return path


class ScreenSaverCatalog:
    def __init__(self, root, document):
        self.root = Path(root).resolve()
        if not isinstance(document,dict):raise ValueError('Unsupported screensaver catalog.')
        if document.get('schema') != 1 or not isinstance(document.get('presentations'), dict):
            raise ValueError('Unsupported screensaver catalog.')
        self.groups=json.loads(json.dumps(document.get('runtime_groups',{})))
        self.profiles=json.loads(json.dumps(document.get('font_profiles',{})))
        if not isinstance(self.groups,dict)or not isinstance(self.profiles,dict):raise ValueError('Invalid screensaver runtime profile.')
        for name,group in self.groups.items():
            if name!=TRUSTED_GROUP or group!={'trust':'builtin95','profile':'classic95'}:raise ValueError('Unsupported shared screensaver trust group.')
        for name,profile in self.profiles.items():
            if name!='classic95' or not isinstance(profile,dict) or set(profile)!={'directory','files','colors','recipe'} or (type(profile['recipe'])is not int or profile['recipe']!=PROFILE_RECIPE):raise ValueError('Invalid screensaver font profile.')
            _relative(profile['directory']);validate_colors(profile['colors'])
            if not isinstance(profile['files'],dict)or set(profile['files'])!={'sserife.fon','vgasys.fon'}:raise ValueError('Original screensaver fonts are missing.')
            for digest in profile['files'].values():
                if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):raise ValueError('Invalid screensaver font digest.')
        for group in self.groups.values():
            if group['profile']not in self.profiles:raise ValueError('Shared screensaver appearance profile is missing.')
        self.presentations = json.loads(json.dumps(document['presentations']))
        for identity, row in self.presentations.items():
            if not isinstance(identity, str) or not identity or identity in ('.','..') or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-._' for c in identity):
                raise ValueError('Invalid screensaver identity.')
            if not isinstance(row,dict):raise ValueError('Invalid screensaver presentation.')
            if row.get('architecture') != 'win32' or not isinstance(row.get('files'), dict):
                raise ValueError('Unsupported screensaver architecture.')
            group=row.get('runtime_group')
            if group is not None and (group not in self.groups or row.get('product')not in ('Windows95','Plus95')):raise ValueError('Only trusted original95 packages may share a runtime.')
            executable = _relative(row.get('executable'))
            if str(executable) not in row['files'] or not row['files']:
                raise ValueError('Screensaver executable is missing.')
            seen = set()
            for name, digest in row['files'].items():
                _relative(name)
                if name.casefold() in seen or not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
                    raise ValueError('Invalid screensaver file manifest.')
                seen.add(name.casefold())
            _relative(row.get('directory'))
            if not set(row.get('modes', ())) <= set(MODES):
                raise ValueError('Invalid screensaver modes.')

    def group(self,identity):return self.resolve(identity).get('runtime_group')

    def profile(self,identity,*,validate=False):
        group=self.group(identity)
        if group is None:return None
        value=json.loads(json.dumps(self.profiles[self.groups[group]['profile']]))
        if validate:
            validate_colors(value['colors'])
            for name,digest in value['files'].items():
                file=self.root/value['directory']/name
                if file.is_symlink()or not file.is_file()or not file.resolve().is_relative_to(self.root):raise ValueError('A screensaver font is missing.')
                if not 64<=file.stat().st_size<=2*1024*1024:raise ValueError('Invalid original screensaver font size.')
                data=file.read_bytes()
                if len(data)<64 or len(data)>2*1024*1024 or data[:2]!=b'MZ' or hashlib.sha256(data).hexdigest()!=digest:raise ValueError('An original screensaver font has changed.')
                offset=struct.unpack_from('<I',data,60)[0]
                if data[offset:offset+2]!=b'NE':raise ValueError('An original screensaver font is not an NE font container.')
        return value

    @classmethod
    def load(cls, path):
        path = Path(path)
        if path.stat().st_size > 1024 * 1024:
            raise ValueError('Screensaver catalog is too large.')
        return cls(path.parent, json.loads(path.read_text()))

    def resolve(self, identity):
        try:
            return json.loads(json.dumps(self.presentations[identity]))
        except KeyError:
            raise ValueError('The screensaver package is unavailable.') from None

    def validate(self, identity):
        row = self.resolve(identity)
        folder = self.root / row['directory']
        for name, digest in row['files'].items():
            path = folder / name
            if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(self.root):
                raise ValueError('A screensaver package file is missing.')
            if path.stat().st_size > 64 * 1024 * 1024 or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError('A screensaver package file has changed.')
        return row


class WineScreenSaverRuntime:
    def __init__(self,catalog,state_dir,*,wine='wine',wineserver='wineserver',wineboot='wineboot',runner_version='wine9-classic-profile1',popen=subprocess.Popen,run=subprocess.run):
        self.catalog,self.state_dir=catalog,Path(state_dir).absolute()
        self.wine,self.wineserver,self.wineboot=wine,wineserver,wineboot
        self.runner_version=runner_version;self._lease=None;self._popen,self._run=popen,run
        self._lock=threading.RLock();self._process=None;self._active=None;self._closed=False

    def prefix(self,identity):
        group=self.catalog.group(identity)
        return (self.state_dir/'groups'/group/'prefix')if group else(self.state_dir/identity/'prefix')

    def _destination(self,identity):
        base=self.prefix(identity)/'drive_c'/'Win95LX'
        return base/'Savers'/identity if self.catalog.group(identity)else base/'Saver'

    def _environment(self,identity):
        return {**os.environ,'WINEPREFIX':str(self.prefix(identity)),'WINEARCH':'win32','WINEDEBUG':'-all','WINEDLLOVERRIDES':'winemenubuilder.exe=d;mscoree,mshtml='}

    def _preparation_environment(self,identity):
        environment=self._environment(identity)
        for name in('DISPLAY','WAYLAND_DISPLAY'):environment.pop(name,None)
        return environment

    def environment(self,identity):
        """No lease is acquired here. Companion hosts require future operation ownership."""
        return self._environment(identity)

    def _binary(self):
        resolved=shutil.which(self.wine)
        if resolved:
            try:
                path=Path(resolved).resolve();info=path.stat();metadata=[[str(path),info.st_size,info.st_mtime_ns]]
                for resource in(path.parent.parent/'share/wine/wine.inf',Path('/usr/lib/wine/wine'),Path('/usr/lib/i386-linux-gnu/wine/i386-unix/ntdll.so')):
                    if resource.is_file():
                        item=resource.stat();metadata.append([str(resource),item.st_size,item.st_mtime_ns])
                return metadata
            except OSError:pass
        return None

    def _runtime_fingerprint(self,identity):
        value={'group':self.catalog.group(identity),'profile':self.catalog.profile(identity),'wine':self.wine,'binary':self._binary(),'runner_version':self.runner_version,'recipe':RUNTIME_RECIPE}
        return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

    def _fingerprint(self,identity):
        return hashlib.sha256(json.dumps({'package':self.catalog.resolve(identity),'runtime':self._runtime_fingerprint(identity)},sort_keys=True).encode()).hexdigest()

    def _marker(self,identity):
        root=self.prefix(identity).parent
        return root/'presentations'/(identity+'.json')if self.catalog.group(identity)else root/'prepared.json'

    def _runtime_marker(self,identity):return self.prefix(identity).parent/'prepared-runtime.json'

    @staticmethod
    def _matches(path,fingerprint):
        try:return not path.is_symlink()and json.loads(path.read_text())=={'fingerprint':fingerprint}
        except (OSError,ValueError):return False

    def _profile_ready(self,identity):
        profile=self.catalog.profile(identity)
        if profile is None:return True
        prefix=self.prefix(identity);folder=prefix/'drive_c'/'windows'/'Fonts'
        try:
            for name,digest in profile['files'].items():
                path=folder/name
                if path.is_symlink()or folder.is_symlink()or not path.resolve().is_relative_to(prefix.resolve())or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:return False
            return True
        except OSError:return False

    def _runtime_ready(self,identity):
        return self._matches(self._runtime_marker(identity),self._runtime_fingerprint(identity))and self._profile_ready(identity)

    def _quiet_ready(self,identity):
        path=self.prefix(identity)/'.update-timestamp'
        try:return not path.is_symlink()and path.read_text()=='disable\n'
        except (OSError,UnicodeError):return False

    def _quiet_guard(self,identity):
        prefix=self.prefix(identity);target=prefix/'.update-timestamp'
        if target.is_symlink():raise ValueError('Invalid screensaver runtime update guard.')
        descriptor,name=tempfile.mkstemp(prefix='.update-',dir=prefix);temporary=Path(name)
        try:
            with os.fdopen(descriptor,'w')as output:output.write('disable\n')
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)

    def ready(self,identity):
        prefix=self.prefix(identity)
        return prefix.is_dir()and not any(part.is_symlink()for part in(prefix,*prefix.parents))and self._quiet_ready(identity)and(self._runtime_ready(identity)if self.catalog.group(identity)else True)and self._matches(self._marker(identity),self._fingerprint(identity))

    def availability(self,identity,mode='fullscreen'):
        try:
            row=self.catalog.resolve(identity)
            if mode not in MODES or mode not in row.get('modes',()):return False,'This screensaver does not support that operation.'
            if any(shutil.which(command)is None for command in(self.wine,self.wineboot,self.wineserver)):return False,'The Windows screensaver compatibility component is not installed.'
            self.catalog.validate(identity);self.catalog.profile(identity,validate=True)
            return True,''
        except (OSError,ValueError)as error:return False,str(error)

    @staticmethod
    def _folder(path,root):
        if not path.absolute().is_relative_to(root.absolute())or any(p.is_symlink()for p in(path,*path.parents)):raise ValueError('Invalid screensaver installation directory.')
        path.mkdir(parents=True,exist_ok=True,mode=0o700)
        return path

    def _acquire(self,identity):
        folder=self._folder(self.prefix(identity).parent,self.state_dir)
        descriptor=os.open(folder/'runtime.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600);lease=os.fdopen(descriptor,'a')
        try:fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            lease.close();raise RuntimeError('This screensaver runtime is already in use.')from None
        return lease

    @staticmethod
    def _copy(source,target,root,digest):
        WineScreenSaverRuntime._folder(target.parent,root)
        if target.is_symlink()or not target.resolve().is_relative_to(root.resolve()):raise ValueError('Invalid screensaver installation path.')
        descriptor,name=tempfile.mkstemp(prefix='.saver-',dir=target.parent)
        temporary=Path(name)
        try:
            with os.fdopen(descriptor,'wb')as output,source.open('rb')as incoming:shutil.copyfileobj(incoming,output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest()!=digest:raise ValueError('A screensaver source changed during preparation.')
            temporary.replace(target)
        finally:temporary.unlink(missing_ok=True)

    @staticmethod
    def _write_marker(path,fingerprint,root):
        WineScreenSaverRuntime._folder(path.parent,root)
        if path.is_symlink():raise ValueError('Invalid screensaver preparation marker.')
        descriptor,name=tempfile.mkstemp(prefix='.prepared-',dir=path.parent)
        temporary=Path(name)
        try:
            with os.fdopen(descriptor,'w')as output:json.dump({'fingerprint':fingerprint},output)
            temporary.replace(path)
        finally:temporary.unlink(missing_ok=True)

    def _server_stop(self,identity):
        for flag in('-k','-w'):
            result=self._run([self.wineserver,flag],env=self._environment(identity),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5,check=False)
            if result.returncode:raise RuntimeError('The screensaver compatibility session could not be closed.')

    def _appearance(self,identity,profile):
        prefix=self.prefix(identity);fonts=prefix/'drive_c'/'windows'/'Fonts'
        self._folder(fonts,prefix)
        for name,digest in profile['files'].items():self._copy(self.catalog.root/profile['directory']/name,fonts/name,prefix,digest)
        lines=['Windows Registry Editor Version 5.00','',r'[HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\Fonts]',r'"MS Sans Serif (Win95 original)"="sserife.fon"',r'"System (Win95 original)"="vgasys.fon"','',r'[HKEY_LOCAL_MACHINE\Software\Microsoft\Windows NT\CurrentVersion\FontSubstitutes]',r'"MS Shell Dlg"="MS Sans Serif"',r'"MS Shell Dlg 2"="MS Sans Serif"','',r'[HKEY_CURRENT_USER\Control Panel\Colors]']
        for name,rgb in profile['colors'].items():lines.append('"'+name+'"="'+' '.join(map(str,rgb))+'"')
        descriptor,name=tempfile.mkstemp(prefix='.classic-',suffix='.reg',dir=prefix.parent);registry=Path(name)
        try:
            with os.fdopen(descriptor,'w',encoding='utf-16')as output:output.write('\n'.join(lines)+'\n')
            result=self._run([self.wine,'regedit','/S',str(registry)],env=self._preparation_environment(identity),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=30,check=False)
            if result.returncode:raise RuntimeError('The original screensaver appearance could not be prepared.')
        finally:registry.unlink(missing_ok=True)

    def prepare(self,identity):
        """Worker-only; shared baseline once, then small per-presentation copies."""
        with self._lock:
            if self._closed:raise RuntimeError('Screensaver runtime is closed.')
            row=self.catalog.validate(identity);profile=self.catalog.profile(identity,validate=True)
            if self.ready(identity):return
            if self._process is not None:
                if self._process.poll()is None:raise RuntimeError('Close the running screensaver before preparation.')
                self.stop()
            lease=self._acquire(identity)
            try:
                # Another worker may have prepared the same package before us.
                if self.ready(identity):return
                prefix=self._folder(self.prefix(identity),self.state_dir)
                marker=self._marker(identity)
                if marker.is_symlink():raise ValueError('Invalid screensaver preparation marker.')
                marker.unlink(missing_ok=True)
                initialize=not self.catalog.group(identity)or not self._runtime_ready(identity)or not self._quiet_ready(identity)
                if initialize:
                    update_guard=prefix/'.update-timestamp'
                    if update_guard.is_symlink()or(update_guard.exists()and update_guard.stat().st_nlink!=1):raise ValueError('Invalid screensaver runtime update guard.')
                    runtime_marker=self._runtime_marker(identity)
                    if runtime_marker.is_symlink():raise ValueError('Invalid screensaver runtime marker.')
                    runtime_marker.unlink(missing_ok=True)
                    result=self._run([self.wineboot,'-u'],env=self._preparation_environment(identity),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=90,check=False)
                    if result.returncode:raise RuntimeError('The Windows screensaver compatibility component could not initialize.')
                    if profile is not None:self._appearance(identity,profile)
                    self._server_stop(identity)
                    self._quiet_guard(identity)
                    if self.catalog.group(identity):self._write_marker(runtime_marker,self._runtime_fingerprint(identity),self.state_dir)
                destination=self._destination(identity)
                for name,digest in row['files'].items():self._copy(self.catalog.root/row['directory']/name,destination/name,prefix,digest)
                self._write_marker(marker,self._fingerprint(identity),self.state_dir)
            finally:lease.close()

    def launch(self,identity,mode='fullscreen',*,parent_hwnd=None):
        with self._lock:
            if self._closed:raise RuntimeError('Screensaver runtime is closed.')
            row=self.catalog.validate(identity)
            if mode not in MODES or mode not in row.get('modes',()):raise ValueError('Unsupported screensaver operation.')
            if mode=='preview'and(type(parent_hwnd)is not int or not 0<parent_hwnd<=0xffffffffffffffff):raise ValueError('Preview requires a Win32 parent window handle.')
            if mode!='preview'and parent_hwnd is not None:raise ValueError('A parent window is only valid for preview.')
            if self._process is not None:
                if self._process.poll()is None:raise RuntimeError('A screensaver is already running.')
                self.stop()
            lease=self._acquire(identity)
            try:
                if not self.ready(identity):raise RuntimeError('Prepare the screensaver compatibility component first.')
                self.catalog.profile(identity,validate=True)
                folder=self._destination(identity)
                for name,digest in row['files'].items():
                    path=folder/name
                    if path.is_symlink()or not path.is_file()or not path.resolve().is_relative_to(folder.resolve())or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('The prepared screensaver package has changed.')
                command=[self.wine,str(folder/row['executable']),MODES[mode]]
                if mode=='preview':command.append(str(parent_hwnd))
                process=self._popen(command,cwd=folder,env=self._environment(identity),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
            except BaseException:lease.close();raise
            self._lease=lease;self._process,self._active=process,identity
            return process

    def stop(self):
        """Bounded cleanup while retaining group ownership; idle instances never kill."""
        with self._lock:
            process,identity=self._process,self._active
            if process is None:return
            if process.poll()is None:
                try:
                    process.terminate()
                    try:process.wait(timeout=2)
                    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=2)
                except ProcessLookupError:pass
            # If cleanup fails, retain process/lease so another owner cannot be
            # admitted into a possibly live session. A later stop can retry.
            self._server_stop(identity)
            self._process,self._active=None,None
            if self._lease is not None:self._lease.close();self._lease=None

    def close(self):
        with self._lock:self._closed=True;self.stop()
