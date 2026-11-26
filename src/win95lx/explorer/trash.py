"""Recycle Bin backed by the freedesktop home Trash layout."""

from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote
import shutil

from win95lx.explorer.file_operations import move_entry


class TrashStore:
    def __init__(self, root=None):
        self.root = root or Path.home()/'.local'/'share'/'Trash'
        self.files,self.info = self.root/'files',self.root/'info'

    def entries(self):
        result = []
        if not self.info.is_dir():
            return result
        for info in self.info.glob('*.trashinfo'):
            name = info.name[:-10]
            source = self.files/name
            if not source.exists() and not source.is_symlink():
                continue
            parser = ConfigParser(interpolation=None)
            try:
                parser.read(info)
                original = Path(unquote(parser['Trash Info']['Path']))
                if not original.is_absolute():
                    continue
            except (KeyError,ValueError):
                continue
            result.append((name,original,source.is_dir() and not source.is_symlink()))
        return sorted(result,key=lambda entry:(entry[1].name.casefold(),entry[0]))

    def put(self, source):
        source = Path(source).absolute()
        self.files.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.info.mkdir(parents=True,exist_ok=True,mode=0o700)
        for index in range(10000):
            name = source.name+(f'.{index}' if index else '')
            target = self.files/name
            if target.exists() or target.is_symlink():
                continue
            info = self.info/(name+'.trashinfo')
            try:
                metadata = info.open('x')
            except FileExistsError:
                continue
            try:
                with metadata:
                    metadata.write('[Trash Info]\nPath='+quote(str(source),safe='/')+
                                   '\nDeletionDate='+datetime.now().isoformat(timespec='seconds')+'\n')
                move_entry(source,target)
            except (OSError,ValueError):
                info.unlink()
                raise
            return name
        raise OSError('Could not allocate a Recycle Bin entry.')

    def restore(self, name):
        original = next(entry[1] for entry in self.entries() if entry[0]==name)
        move_entry(self.files/name,original)
        (self.info/(name+'.trashinfo')).unlink()

    def delete(self, name):
        if name not in {entry[0] for entry in self.entries()}:
            return
        source = self.files/name
        if source.is_dir() and not source.is_symlink():
            shutil.rmtree(source)
        else:
            source.unlink()
        (self.info/(name+'.trashinfo')).unlink()
