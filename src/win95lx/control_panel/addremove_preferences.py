"""Curated component inventory and transactional installer boundary.

The default implementation is read-only: no apt/sudo command is constructed.
Mutation requires a future typed guest service, not writable preferences that
pretend the desktop or installed packages changed.
"""
from dataclasses import dataclass,replace
from pathlib import Path
from functools import lru_cache
import hashlib,json,re,shutil,subprocess

ID=re.compile(r'[a-z][a-z0-9_.-]{0,95}')
PACKAGE=re.compile(r'[a-z0-9][a-z0-9+.-]{0,127}')
GROUP_LABELS={'presets':'Desktop Enhancements','explorer':'Explorer','desktop':'Desktop','taskbar':'Taskbar','fonts':'Fonts','sound':'Multimedia','startup':'Startup','menus':'Start Menu','controls':'Windows Controls','components':'Optional Components'}
class SetupError(RuntimeError):pass
class SetupCancelled(SetupError):pass

def identifier(value):
 if not isinstance(value,str) or not ID.fullmatch(value):raise ValueError('Invalid component identifier.')
 return value
@dataclass(frozen=True)
class Component:
 id:str
 label:str
 group:str
 description:str
 available:bool=False
 reason:str='The component setting is not connected to its runtime consumer.'
 implementation:str='planned'
 apply_mode:str='reopen_window'
 packages:tuple=()
 def __post_init__(self):object.__setattr__(self,'packages',tuple(self.packages))
 def validate(self):
  identifier(self.id);identifier(self.group)
  if not self.label or '\0' in self.label or '\n' in self.label:raise ValueError('Invalid component label.')
  if type(self.available) is not bool:raise ValueError('Invalid component capability.')
  if any(not isinstance(p,str) or not PACKAGE.fullmatch(p) for p in self.packages):raise ValueError('Invalid managed package name.')
  return self
@dataclass(frozen=True)
class Programme:
 id:str
 label:str
 packages:tuple=()
 builtin:bool=False
 def __post_init__(self):object.__setattr__(self,'packages',tuple(self.packages))
 def validate(self):
  identifier(self.id)
  if not self.label or '\0' in self.label or '\n' in self.label:raise ValueError('Invalid programme label.')
  if any(not isinstance(p,str) or not PACKAGE.fullmatch(p) for p in self.packages):raise ValueError('Invalid managed package name.')
  if type(self.builtin) is not bool:raise ValueError('Invalid built-in component flag.')
  if not self.builtin and not self.packages:raise ValueError('A managed programme requires registered packages.')
  return self
@dataclass(frozen=True)
class InstalledProgramme:
 id:str
 label:str
 installed:bool
 versions:tuple=()
 builtin:bool=False
 def __post_init__(self):object.__setattr__(self,'versions',tuple(tuple(v) for v in self.versions))
@dataclass(frozen=True)
class Catalogue:
 components:tuple
 programmes:tuple=(Programme('desktop-enhancements','Desktop Enhancements',(),True),)
 def __post_init__(self):
  object.__setattr__(self,'components',tuple(self.components));object.__setattr__(self,'programmes',tuple(self.programmes))
 def validate(self):
  if len({c.id for c in self.components})!=len(self.components) or len({p.id for p in self.programmes})!=len(self.programmes):raise ValueError('Duplicate registered component or programme.')
  for c in self.components:c.validate()
  for p in self.programmes:p.validate()
  return self
 @classmethod
 def from_data(cls,data,programmes=None):
  if type(data.get('schema_version')) is not int or data.get('schema_version')!=1:raise ValueError('Unsupported component catalogue.')
  components=[]
  for preset in data.get('presets',()):
   components.append(Component('preset.'+preset['id'],preset['label'],'presets','Compatibility preset: '+preset['label']+'. Shell generation and Plus! remain independent.',False,'This compatibility preset has not yet been connected and accepted as a working runtime profile.','catalogue_only','session_restart'))
  for f in data.get('features',()):
   # A catalogue flag alone never grants a working setting: a typed service
   # binding must also exist. Current root catalogue is intentionally read-only.
   available=f.get('user_selectable') is True and f.get('global_binding')=='accepted'
   reason='' if available else 'This setting is unavailable until its consumer binding and Apply/Cancel verification are implemented.'
   desc=f["label"]+'. '+('Existing implementation: '+f.get('implementation','planned').replace('_',' ')+'. Changes require '+f.get('apply_mode','reopen_window').replace('_',' ')+'.')
   components.append(Component(f['id'],f['label'],f['group'],desc,available,reason,f.get('implementation','planned'),f.get('apply_mode','reopen_window'),tuple(f.get('package_ids',()))))
  return cls(tuple(components),tuple(programmes) if programmes is not None else cls.__dataclass_fields__['programmes'].default).validate()
 @property
 def groups(self):return tuple(dict.fromkeys(c.group for c in self.components))
 def members(self,group):return tuple(c for c in self.components if c.group==group)

@lru_cache(maxsize=8)
def load_catalogue(path):
 """Explicit activation/refresh API; paint and input use the immutable result."""
 return Catalogue.from_data(json.loads(Path(path).read_text()))

@dataclass(frozen=True)
class SetupSnapshot:
 programmes:tuple
 features:tuple  # (component ID, bool|None): None means unknown, not installed=False.
 generation:str
 free_bytes:int=0
 def __post_init__(self):
  object.__setattr__(self,'programmes',tuple(self.programmes));object.__setattr__(self,'features',tuple(tuple(f) for f in self.features))
 def feature(self,key):return dict(self.features).get(key)
 def with_changes(self,features=(),programmes=()):
  values=dict(self.features);values.update(features);apps={p.id:p for p in self.programmes}
  for ident,installed in programmes:
   if ident not in apps:raise SetupError('Unknown registered programme.')
   apps[ident]=replace(apps[ident],installed=installed)
  return replace(self,programmes=tuple(apps.values()),features=tuple(values.items()))

def snapshot(programmes,features,free_bytes=0):
 raw=json.dumps({'programmes':[(p.id,p.installed,p.versions,p.builtin) for p in programmes],'features':sorted(features)},sort_keys=True,separators=(',',':')).encode()
 return SetupSnapshot(tuple(programmes),tuple(features),hashlib.sha256(raw).hexdigest(),free_bytes)

class ReadOnlyPackages:
 """Only query the curated package names; never show dependency inventory."""
 mutable=False
 reason='The scoped component installer service is not installed. No software has been changed.'
 def __init__(self,run=None):self.run=run or subprocess.run
 def snapshot(self,catalogue):
  names=tuple(sorted({p for app in catalogue.programmes for p in app.packages}));installed={}
  if names:
   try:
    result=self.run(['dpkg-query','-W','-f=${binary:Package}\\t${Version}\\t${db:Status-Status}\\n','--',*names],capture_output=True,text=True,stdin=subprocess.DEVNULL,timeout=8)
   except (OSError,subprocess.TimeoutExpired) as e:raise SetupError('Installed software information could not be read.') from e
   if result.returncode not in (0,1):raise SetupError('Installed software information could not be read.')
   for line in result.stdout.splitlines():
    fields=line.split('\t')
    if len(fields)==3 and fields[2]=='installed' and fields[0].split(':')[0] in names:installed[fields[0].split(':')[0]]=fields[1]
  apps=tuple(InstalledProgramme(p.id,p.label,p.builtin or all(name in installed for name in p.packages),tuple((name,installed[name]) for name in p.packages if name in installed),p.builtin) for p in catalogue.programmes)
  # No guessed global profile values: unbound settings have unknown state.
  return snapshot(apps,tuple((c.id,None) for c in catalogue.components),shutil.disk_usage('/').free)
 def execute(self,*args):raise SetupError(self.reason)
 def restore(self,*args):raise SetupError('No installer transaction was started.')

class SetupBackend:
 def __init__(self,catalogue,service=None):self.catalogue=catalogue.validate();self.service=service or ReadOnlyPackages();self.cached=None
 def preferences(self,refresh=False):
  if self.cached is None or refresh:self.cached=self.service.snapshot(self.catalogue)
  return self.cached
 @property
 def writable(self):return bool(self.service.mutable)
 def validate_changes(self,before,pending):
  defs={c.id:c for c in self.catalogue.components};apps={p.id:p for p in self.catalogue.programmes}
  oldfeatures=dict(before.features);newfeatures=dict(pending.features)
  if oldfeatures.keys()!=newfeatures.keys():raise SetupError('The registered component list changed. Refresh this window.')
  features=[]
  for key,value in newfeatures.items():
   if value==oldfeatures[key]:continue
   if key not in defs or not defs[key].available:raise SetupError(defs[key].reason if key in defs else 'Unknown component.')
   if type(value) is not bool:raise ValueError('Invalid component choice.')
   features.append((key,value))
  old={p.id:p for p in before.programmes};new={p.id:p for p in pending.programmes}
  if old.keys()!=new.keys():raise SetupError('The registered programme list changed.')
  changes=[]
  for key,p in new.items():
   if p.installed!=old[key].installed:
    if key not in apps or apps[key].builtin:raise SetupError('This built-in component cannot be removed individually.')
    if type(p.installed) is not bool:raise ValueError('Invalid installation choice.')
    changes.append((key,p.installed))
  return tuple(features),tuple(changes)
 def apply(self,pending,before,cancel=None):
  features,programmes=self.validate_changes(before,pending)
  if not features and not programmes:return before
  if not self.writable:raise SetupError(self.service.reason)
  if cancel is not None and cancel.is_set():raise SetupCancelled('The component change was cancelled before installation.')
  current=self.service.snapshot(self.catalogue)
  if current.generation!=before.generation:raise SetupError('Installed components changed while this window was open. Refresh and try again.')
  try:
   self.service.execute(features,programmes,before,cancel)
   after=self.service.snapshot(self.catalogue)
   if any(after.feature(k)!=v for k,v in features) or any(next((p.installed for p in after.programmes if p.id==k),None)!=v for k,v in programmes):raise SetupError('The installer did not retain the requested components.')
   if cancel is not None and cancel.is_set():raise SetupCancelled('The component change was cancelled.')
  except Exception as error:
   self.cached=None
   try:
    self.service.restore(before,features,programmes)
    restored=self.service.snapshot(self.catalogue)
    if any(restored.feature(k)!=before.feature(k) for k,_ in features) or any(next((p.installed for p in restored.programmes if p.id==k),None)!=next(p.installed for p in before.programmes if p.id==k) for k,_ in programmes) or any(next((p.versions for p in restored.programmes if p.id==k),None)!=next(p.versions for p in before.programmes if p.id==k) for k,_ in programmes):raise SetupError('Restore verification failed.')
    self.cached=restored
   except Exception as rollback:raise SetupError('The component change failed and could not be fully restored. Refresh to inspect the current components.') from rollback
   raise SetupError('The component change failed. Previous components were restored.') from error
  self.cached=after;return after

class SetupController:
 def __init__(self,backend):self.backend=backend;self.applied=self.pending=None
 def load(self,refresh=False):self.applied=self.pending=self.backend.preferences(refresh);return self.applied
 def cancel(self):self.pending=self.applied
 def set_feature(self,ident,value):
  c=next((c for c in self.backend.catalogue.components if c.id==ident),None)
  if c is None:raise SetupError('Unknown component.')
  if not c.available:raise SetupError(c.reason)
  if not self.backend.writable:raise SetupError(self.backend.service.reason)
  if self.pending is None:raise SetupError('Installed component information is still loading.')
  candidate=self.pending.with_changes(((ident,value),));self.backend.validate_changes(self.applied,candidate);self.pending=candidate
 def set_programme(self,ident,installed):
  if not self.backend.writable:raise SetupError(self.backend.service.reason)
  if self.pending is None:raise SetupError('Installed component information is still loading.')
  candidate=self.pending.with_changes(programmes=((ident,installed),));self.backend.validate_changes(self.applied,candidate);self.pending=candidate
 def apply(self,cancel=None):
  if self.pending is None:raise SetupError('Installed component information is still loading.')
  self.applied=self.pending=self.backend.apply(self.pending,self.applied,cancel)
