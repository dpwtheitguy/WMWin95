"""Verified, content-based cache for sequential private asset-building stages.

Builders own their declared inputs. A hit restores this stage's intermediate
bytes, even when a later stage rewrote the same catalog during the prior run.
Input mtimes never establish validity; stat changes only discover output owners.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import time

SCHEMA=1
MAX_METADATA=16*1024*1024


def _json(value,*,sort_keys=True):
    return json.dumps(value,sort_keys=sort_keys,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def _digest(path):
    value=hashlib.sha256()
    with path.open('rb')as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):value.update(chunk)
    return value.hexdigest()


def _safe_directory(path,create=False):
    path=Path(path)
    for parent in (path,*path.parents):
        if parent.is_symlink():raise ValueError('Asset cache directories cannot be redirected.')
    if create:path.mkdir(parents=True,exist_ok=True)
    if not path.is_dir():raise ValueError('Asset cache directory is unavailable.')
    return path


def _relative(value):
    if not isinstance(value,str)or not value or '\\'in value or '\0'in value:
        raise ValueError('Invalid stage artifact path.')
    path=Path(value)
    if path.is_absolute()or any(part in ('','.','..')for part in value.split('/')):
        raise ValueError('Stage artifacts must stay inside the output directory.')
    return path.as_posix()


def _atomic(path,writer,mode=0o600):
    _safe_directory(path.parent,True)
    if path.is_symlink():raise ValueError('A stage artifact is redirected.')
    if path.exists()and not path.is_file():raise ValueError('A stage artifact is not a regular file.')
    descriptor,name=tempfile.mkstemp(prefix='.asset-',dir=path.parent);temporary=Path(name)
    try:
        with os.fdopen(descriptor,'wb')as stream:
            writer(stream);stream.flush();os.fsync(stream.fileno());os.fchmod(stream.fileno(),mode)
        temporary.replace(path)
        directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:temporary.unlink(missing_ok=True)


def _copy(source,destination,mode):
    def writer(stream):
        with source.open('rb')as incoming:
            for chunk in iter(lambda:incoming.read(1024*1024),b''):stream.write(chunk)
    _atomic(destination,writer,mode)


def _tree(path):
    """Flatten exact input names/types/content, including absent input roots."""
    path=Path(path).absolute();result=[]
    def visit(item,ancestors):
        if item.is_symlink():
            target=os.readlink(item);resolved=item.resolve(strict=True)
            if resolved in ancestors:raise ValueError('An asset input contains a symbolic-link cycle.')
            result.append((str(item),'symlink',target))
            visit(resolved,ancestors|{resolved});return
        try:info=item.stat()
        except FileNotFoundError:
            result.append((str(item),'absent'));return
        mode=stat.S_IMODE(info.st_mode)
        if stat.S_ISREG(info.st_mode):result.append((str(item),'file',mode,_digest(item)))
        elif stat.S_ISDIR(info.st_mode):
            result.append((str(item),'directory',mode))
            for child in sorted(item.iterdir(),key=lambda value:value.name):visit(child,ancestors|{item})
        else:raise ValueError('Asset inputs must be regular files or directories.')
    visit(path,set());return result


class StageCache:
    def __init__(self,output,cache_dir,force=False):
        self.output=Path(os.path.abspath(output));self.cache_dir=Path(os.path.abspath(cache_dir));self.force=bool(force)
        if self.output.is_relative_to(self.cache_dir)or self.cache_dir.is_relative_to(self.output):
            raise ValueError('The artifact store must be outside the output bundle.')
        _safe_directory(self.output,True);_safe_directory(self.cache_dir,True)
        for name in ('blobs','entries','locks'):_safe_directory(self.cache_dir/name,True)
        self.report=[];self.stage_outputs={};self.stage_deleted={}

    @contextmanager
    def _lock(self):
        name=hashlib.sha256(str(self.output).encode()).hexdigest()+'.lock'
        descriptor=os.open(self.cache_dir/'locks'/name,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):raise ValueError('Invalid asset cache lock.')
            fcntl.flock(descriptor,fcntl.LOCK_EX);yield
        finally:os.close(descriptor)

    def _path(self,name):
        path=self.output/_relative(name)
        _safe_directory(path.parent,True)
        if path.is_symlink():raise ValueError('A stage artifact is redirected.')
        return path

    def _snapshot(self):
        result={}
        def visit(folder):
            _safe_directory(folder)
            for path in sorted(folder.iterdir(),key=lambda value:value.name):
                if path.is_symlink():raise ValueError('The asset bundle contains a redirected artifact.')
                info=path.stat()
                if stat.S_ISDIR(info.st_mode):visit(path)
                elif stat.S_ISREG(info.st_mode):
                    if info.st_mode&0o7000:raise ValueError('Special artifact permissions are not supported.')
                    result[path.relative_to(self.output).as_posix()]=(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns,stat.S_IMODE(info.st_mode))
                else:raise ValueError('The asset bundle contains a non-file artifact.')
        visit(self.output);return result

    def _declared(self,result):
        names=set()
        def visit(value):
            if isinstance(value,dict):
                if 'output'in value:
                    filename=value['output']
                    if isinstance(filename,str):
                        candidate=Path(filename)
                        if candidate.is_absolute():
                            try:filename=candidate.relative_to(self.output).as_posix()
                            except ValueError:raise ValueError('A declared artifact leaves the output bundle.')from None
                        names.add(_relative(filename))
                for item in value.values():visit(item)
            elif isinstance(value,list):
                for item in value:visit(item)
        visit(result);return names

    @staticmethod
    def _inputs(paths):
        return [(str(path),_tree(path))for path in sorted({Path(os.path.abspath(value))for value in paths},key=str)]

    def _upstream_unchanged(self,before,after,owned):
        ignored={str(self.output/name)for name in owned}
        def filtered(rows):
            return [(root,[tuple(item)for item in tree if item[0]not in ignored])for root,tree in rows]
        return filtered(before)==filtered(after)

    def _entry(self,name,fingerprint):
        folder=self.cache_dir/'entries'/name;_safe_directory(folder,True)
        return folder/(fingerprint+'.json')

    def _load(self,path,name,fingerprint):
        if path.is_symlink()or not path.is_file()or path.stat().st_size>MAX_METADATA:raise ValueError('Invalid stage metadata.')
        document=json.loads(path.read_bytes())
        if not isinstance(document,dict)or set(document)!={'schema','name','fingerprint','result','artifacts','deleted'}or document['schema']!=SCHEMA or document['name']!=name or document['fingerprint']!=fingerprint:
            raise ValueError('Invalid stage metadata.')
        if not isinstance(document['artifacts'],dict)or not isinstance(document['deleted'],list):raise ValueError('Invalid stage outputs.')
        for relative,record in document['artifacts'].items():
            _relative(relative)
            if not isinstance(record,dict)or set(record)!={'sha256','size','mode'}or re.fullmatch(r'[a-f0-9]{64}',str(record['sha256']))is None or type(record['size'])is not int or record['size']<0 or type(record['mode'])is not int or not 0<=record['mode']<=0o777:
                raise ValueError('Invalid cached artifact.')
            blob=self.cache_dir/'blobs'/record['sha256']
            if blob.is_symlink()or not blob.is_file()or blob.stat().st_size!=record['size']or _digest(blob)!=record['sha256']:raise ValueError('A cached artifact has changed.')
        for relative in document['deleted']:_relative(relative)
        if set(document['deleted'])&set(document['artifacts']):raise ValueError('Conflicting cached outputs.')
        _json(document['result'])
        if not self._declared(document['result'])<=set(document['artifacts']):raise ValueError('Cached output records do not match their artifacts.')
        return document

    def _restore(self,document):
        restored=0
        # Validate all destination types before making any output change.
        for relative in (*document['artifacts'],*document['deleted']):
            path=self._path(relative)
            if path.exists()and not path.is_file():raise ValueError('A cached artifact destination is not a file.')
        for relative in document['deleted']:
            self._path(relative).unlink(missing_ok=True)
        for relative,record in document['artifacts'].items():
            path=self._path(relative)
            if not(path.is_file()and path.stat().st_size==record['size']and stat.S_IMODE(path.stat().st_mode)==record['mode']and _digest(path)==record['sha256']):
                _copy(self.cache_dir/'blobs'/record['sha256'],path,record['mode']);restored+=1
            if not path.is_file()or _digest(path)!=record['sha256']:raise ValueError('A restored artifact could not be verified.')
        return restored

    def _capture(self,names):
        artifacts={}
        for relative in sorted(names):
            path=self._path(relative)
            if not path.is_file():raise ValueError('A declared stage output is missing.')
            info=path.stat();digest=_digest(path);blob=self.cache_dir/'blobs'/digest
            if not(blob.is_file()and not blob.is_symlink()and blob.stat().st_size==info.st_size and _digest(blob)==digest):
                # A corrupt regular blob is safely replaced; never follow links.
                if blob.is_symlink():raise ValueError('A cached blob is redirected.')
                _copy(path,blob,0o600)
            if _digest(blob)!=digest or _digest(path)!=digest or path.stat().st_size!=info.st_size or stat.S_IMODE(path.stat().st_mode)!=stat.S_IMODE(info.st_mode):raise ValueError('A stage artifact changed while being cached.')
            artifacts[relative]={'sha256':digest,'size':info.st_size,'mode':stat.S_IMODE(info.st_mode)}
        return artifacts

    def run(self,name,builder,dependencies=(),upstream=(),conditions=None):
        if not isinstance(name,str)or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',name)is None:raise ValueError('Invalid asset stage name.')
        if not callable(builder):raise TypeError('An asset stage needs a builder.')
        if conditions is not None and not isinstance(conditions,dict):raise ValueError('Stage conditions must be a JSON object.')
        dependencies=tuple(dependencies);upstream=tuple(upstream)
        started=time.monotonic()
        with self._lock():
            deps=self._inputs(dependencies);prior=self._inputs(upstream)
            payload={'schema':SCHEMA,'name':name,'dependencies':deps,'upstream':prior,'conditions':conditions or{},'cache_code':_digest(Path(__file__))}
            fingerprint=hashlib.sha256(_json(payload)).hexdigest();entry=self._entry(name,fingerprint)
            reason='forced'if self.force else'not-cached'
            if not self.force and entry.exists():
                try:
                    document=self._load(entry,name,fingerprint);restored=self._restore(document)
                    expected=set(document['artifacts'])|set(document['deleted'])
                    if deps!=self._inputs(dependencies)or not self._upstream_unchanged(prior,self._inputs(upstream),expected)or _digest(Path(__file__))!=payload['cache_code']:
                        raise ValueError('Asset inputs changed while restoring the cache.')
                except (OSError,ValueError,TypeError,KeyError):reason='cache-corrupt'
                else:
                    self.stage_outputs[name]=[self.output/value for value in sorted(document['artifacts'])]
                    self.stage_deleted[name]=[self.output/value for value in document['deleted']]
                    self.report.append({'name':name,'status':'hit','seconds':round(time.monotonic()-started,6),'outputs':len(document['artifacts']),'restored':restored,'fingerprint':fingerprint})
                    return document['result']
            before=self._snapshot()
            try:
                result=json.loads(_json(builder(),sort_keys=False))
                after=self._snapshot()
                owned={path for path,info in after.items()if before.get(path)!=info}|self._declared(result)
                deleted=set(before)-set(after)
                artifacts=self._capture(owned)
                unchanged=deps==self._inputs(dependencies)and self._upstream_unchanged(prior,self._inputs(upstream),owned|deleted)and _digest(Path(__file__))==payload['cache_code']
                document={'schema':SCHEMA,'name':name,'fingerprint':fingerprint,'result':result,'artifacts':artifacts,'deleted':sorted(deleted)}
                data=_json(document,sort_keys=False)
                if len(data)>MAX_METADATA:raise ValueError('Stage cache metadata is too large.')
                if unchanged:_atomic(entry,lambda stream:stream.write(data))
                else:reason='inputs-changed'
            except BaseException:
                self.stage_outputs.pop(name,None);self.stage_deleted.pop(name,None)
                self.report.append({'name':name,'status':'failed','seconds':round(time.monotonic()-started,6),'reason':reason,'fingerprint':fingerprint})
                raise
            self.stage_outputs[name]=[self.output/value for value in sorted(artifacts)]
            self.stage_deleted[name]=[self.output/value for value in sorted(deleted)]
            self.report.append({'name':name,'status':'miss','seconds':round(time.monotonic()-started,6),'outputs':len(artifacts),'deleted':len(deleted),'cached':unchanged,'reason':reason,'fingerprint':fingerprint})
            return result
