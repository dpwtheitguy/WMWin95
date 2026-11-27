"""Persistent namespace/file links using safe Linux desktop Link entries."""
from configparser import ConfigParser,Error as ConfigError
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse,unquote

from win95lx.control_panel.catalog import targets
TARGETS={'(C:)':'drive','Control Panel':'control','My Computer':'computer',**targets()}

@dataclass(frozen=True)
class Shortcut:
    kind:str
    target:str


def read_shortcut(path):
    parser=ConfigParser(interpolation=None)
    try:
        with Path(path).open(encoding='utf-8') as stream:parser.read_file(stream)
        entry=parser['Desktop Entry']
        if entry.get('Type')!='Link':return None
        url=entry.get('URL','');parts=urlparse(url)
        if parts.scheme=='win95lx' and parts.path in TARGETS.values() and not parts.netloc:
            return Shortcut('namespace',parts.path)
        if parts.scheme=='file' and parts.netloc in ('','localhost') and parts.path.startswith('/') and not parts.query and not parts.fragment:
            return Shortcut('path',unquote(parts.path))
    except (OSError,UnicodeError,ValueError,KeyError,ConfigError):pass
    return None


def write_shortcut(directory,name,link):
    directory=Path(directory)
    if not directory.is_dir():raise NotADirectoryError("The shortcut destination is no longer available.")
    name=name.replace('/','_').replace(':','').replace('\n',' ').replace('\r',' ')
    url='win95lx:'+link.target if link.kind=='namespace' else Path(link.target).absolute().as_uri()
    index=1
    existing={path.name.casefold() for path in directory.iterdir()}
    while True:
        filename=('Shortcut to '+name if index==1 else f'Shortcut ({index}) to '+name)+'.desktop'
        if filename.casefold() in existing:
            index+=1
            continue
        path=directory/filename
        parser=ConfigParser(interpolation=None);parser.optionxform=str
        parser['Desktop Entry']={'Type':'Link','Name':path.stem,'URL':url}
        created=False
        try:
            with path.open('x',encoding='utf-8') as stream:
                created=True;parser.write(stream)
            return path
        except FileExistsError:
            if created:
                path.unlink(missing_ok=True);raise
            index+=1
        except BaseException:
            if created:path.unlink(missing_ok=True)
            raise


def create_shortcut(desktop,label):
    return write_shortcut(desktop,' '+label if label=='(C:)' else label,Shortcut('namespace',TARGETS[label]))


def create_file_shortcut(directory,target):
    target=Path(target).absolute()
    if not target.exists():raise FileNotFoundError(f'The target {target.name} cannot be found.')
    link=read_shortcut(target) if target.suffix.casefold()=='.desktop' else None
    return write_shortcut(directory,target.stem if target.suffix.casefold()=='.desktop' else target.name,
                          link or Shortcut('path',str(target)))


def shortcut_target(path):
    link=read_shortcut(path)
    return link.target if link and link.kind=='namespace' else None


def resolve_shortcut(path,limit=32):
    seen=set();path=Path(path).absolute()
    for _ in range(limit):
        if path in seen:raise ValueError('The shortcut contains a circular target.')
        seen.add(path);link=read_shortcut(path)
        if link is None:raise ValueError('The shortcut target is invalid or unsupported.')
        if link.kind=='namespace':return link
        target=Path(link.target)
        if not target.exists():raise FileNotFoundError(f'The item {target.name} that this shortcut refers to cannot be found.')
        if target.suffix.casefold()!='.desktop':return Shortcut('path',str(target))
        path=target
    raise ValueError('The shortcut target chain is too long.')


def display_name(name):return Path(name).stem if str(name).casefold().endswith('.desktop') else str(name)


def folder_shortcut_destination(path,root):
    """Resolve a bounded folder Link for virtual-item drops, never execute it."""
    root=Path(root).resolve();link=resolve_shortcut(path)
    target=root if link.kind=='namespace' and link.target=='drive' else Path(link.target) if link.kind=='path' else None
    if target is None or not target.is_dir():raise ValueError('The shortcut does not refer to an available folder.')
    target=target.resolve(strict=True);target.relative_to(root)
    return target
