"""Explorer clipboard and filesystem operations on the presented drive."""

from dataclasses import dataclass
import ctypes
import os
from pathlib import Path
import shutil
import stat


@dataclass(frozen=True)
class FileClipboard:
    sources: tuple[Path, ...] = ()
    move: bool = False

    def transfer(self, view, folder):
        destination = view.resolve(folder)
        failures = []
        remaining = []
        for relative in self.sources:
            try:
                parent = view.resolve(relative.parent)
                source = parent/relative.name
                if self.move and source == destination/source.name:
                    continue
                if not self.move and parent == destination:
                    copy_with_new_name(source,destination)
                else:
                    transfer = move_entry if self.move else copy_entry
                    transfer(source, destination/source.name)
            except (OSError, RuntimeError, ValueError) as error:
                message = error.strerror if isinstance(error, OSError) else None
                failures.append(f"{relative.name}: {message or error}")
                remaining.append(relative)
        clipboard = FileClipboard(tuple(remaining), True) if self.move else self
        return clipboard, failures


def copy_with_new_name(source, destination):
    existing = {path.name.casefold() for path in destination.iterdir()}
    for index in range(1,10001):
        prefix = 'Copy of ' if index == 1 else f'Copy ({index}) of '
        name = prefix+source.name
        if name.casefold() in existing:
            continue
        try:
            copy_entry(source,destination/name)
            return destination/name
        except FileExistsError:
            existing.add(name.casefold())
    raise OSError('Could not allocate a name for the copy.')


def move_entry(source, target):
    # renameat2 preserves the original on failure and never replaces a target.
    libc = ctypes.CDLL(None, use_errno=True)
    rename = libc.renameat2
    rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    if rename(-100, os.fsencode(source), -100, os.fsencode(target), 1):
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), target.name)


def copy_entry(source, target):
    mode = source.lstat().st_mode
    if stat.S_ISLNK(mode):
        target.symlink_to(source.readlink())
    elif stat.S_ISDIR(mode):
        if target.parent.is_relative_to(source):
            raise ValueError('A folder cannot be copied into itself.')
        target.mkdir()
        try:
            shutil.copytree(source, target, symlinks=True, dirs_exist_ok=True)
        except (OSError, RuntimeError):
            shutil.rmtree(target)
            raise
    elif stat.S_ISREG(mode):
        with source.open('rb') as original, target.open('xb') as copied:
            try:
                shutil.copyfileobj(original, copied)
                shutil.copystat(source, target)
            except OSError:
                target.unlink()
                raise
    else:
        raise OSError('This file type cannot be copied.')


def child_name(name):
    if not name or name in ('.', '..') or '/' in name or chr(92) in name or chr(0) in name:
        raise ValueError('Enter a valid file or folder name.')
    return name
