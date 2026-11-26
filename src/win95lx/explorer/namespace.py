"""Safe internal namespace shortcuts, without executing arbitrary desktop commands."""
from configparser import ConfigParser
from pathlib import Path

TARGETS={'(C:)':'drive','Control Panel':'control','My Computer':'computer'}


def create_shortcut(desktop, label):
    target=TARGETS[label]
    desktop=Path(desktop);desktop.mkdir(parents=True,exist_ok=True)
    name='Shortcut to '+label.replace(':','')
    contents=f'[Desktop Entry]\nType=Link\nName={name}\nURL=win95lx:{target}\n'
    index=1
    while True:
        path=desktop/(name+(f' ({index})' if index>1 else '')+'.desktop')
        try:
            with path.open('x') as stream:stream.write(contents)
            return path
        except FileExistsError:index+=1


def shortcut_target(path):
    parser=ConfigParser(interpolation=None)
    try:
        parser.read(path)
        entry=parser['Desktop Entry']
        if entry.get('Type')!='Link':return None
        url=entry.get('URL','')
        target=url.removeprefix('win95lx:')
        return target if url.startswith('win95lx:') and target in TARGETS.values() else None
    except (OSError,ValueError,KeyError):return None
