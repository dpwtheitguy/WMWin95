"""Per-user Plus-style theme definitions; media are referenced, never deleted.

The readable INI sections document supported settings. The versioned
Win95LX section preserves exact supported values without interpreting commands,
screen savers, DLLs, or arbitrary registry sections from a theme file.
"""
from copy import deepcopy
import configparser
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import unicodedata

MAX_DEFINITION = 256 * 1024
COMPONENTS = ('wallpaper', 'pointers', 'sounds', 'icons', 'colors', 'fonts', 'metrics', 'screensaver')


class ThemeExistsError(FileExistsError):
    def __init__(self, name, token):
        self.name, self.token = name, token
        super().__init__('A theme with this name already exists.')


class ThemeChangedError(RuntimeError):
    pass


def theme_name(value):
    if not isinstance(value, str):
        raise ValueError('Type a name for the theme.')
    value = unicodedata.normalize('NFC', value.strip())
    while value.casefold().endswith('.theme'):
        value = value[:-6].rstrip()
    if (not value or len(value) > 100 or value in ('.', '..')
            or value[-1] in '. ' or any(ord(c) < 32 or c in '<>:"/\\|?*' for c in value)):
        raise ValueError('The theme name contains characters that cannot be used in a file name.')
    if len(value.encode('utf-8'))>249:raise ValueError('The theme name is too long.')
    if value.casefold() == 'current windows settings':
        raise ValueError('Choose a different theme name.')
    if value.split('.')[0].casefold() in {'con', 'prn', 'aux', 'nul',
            *(f'com{i}' for i in range(1, 10)), *(f'lpt{i}' for i in range(1, 10))}:
        raise ValueError('Choose a different theme name.')
    return value


def validate_definition(value):
    """Validate supported values without opening/launching external resources."""
    from win95lx.control_panel.mouse_preferences import MousePreferences
    from win95lx.control_panel.sound_preferences import SoundPreferences
    if not isinstance(value, dict) or not set(('wallpaper','pointers','sounds')) <= set(value) or set(value) - set(COMPONENTS):
        raise ValueError('The theme definition is incomplete or unsupported.')
    wall = value['wallpaper']
    if not isinstance(wall, dict) or set(wall) - {'file', 'mode', 'pattern', 'pattern_rows'}:
        raise ValueError('Invalid theme wallpaper settings.')
    filename = wall.get('file')
    if not isinstance(filename, str) or '\0' in filename or len(filename) > 4096 or filename and not Path(filename).is_absolute():
        raise ValueError('Invalid theme wallpaper filename.')
    if wall.get('mode') not in ('center', 'tile'):
        raise ValueError('Unsupported wallpaper placement.')
    pattern = wall.get('pattern', '(None)')
    rows = wall.get('pattern_rows', [0] * 8)
    if not isinstance(pattern, str) or len(pattern) > 100 or '\0' in pattern:
        raise ValueError('Invalid desktop pattern.')
    if not isinstance(rows, (tuple, list)) or len(rows) != 8 or any(type(n) is not int or not 0 <= n <= 255 for n in rows):
        raise ValueError('Invalid desktop pattern data.')
    pointer = value['pointers']
    if not isinstance(pointer, dict) or set(pointer) != {'scheme', 'overrides'}:
        raise ValueError('Invalid theme pointer settings.')
    MousePreferences(scheme=pointer['scheme'], overrides=pointer['overrides']).validate()
    for filename in pointer['overrides'].values():
        if '\0' in filename or len(filename) > 4096 or not Path(filename).is_absolute():
            raise ValueError('Invalid theme pointer filename.')
    sounds = value['sounds']
    if not isinstance(sounds, dict) or set(sounds) != {'scheme', 'events'}:
        raise ValueError('Invalid theme sound settings.')
    SoundPreferences(**sounds).validate()
    if 'icons' in value:
        icons = value['icons']
        if not isinstance(icons, dict) or set(icons) - {'computer','network','recycle-empty','recycle-full'}:
            raise ValueError('Invalid theme icon settings.')
        for pair in icons.values():
            if not isinstance(pair, dict) or set(pair) != {'large','small'}:
                raise ValueError('Invalid theme icon images.')
            for filename in pair.values():
                if not isinstance(filename,str) or '\0' in filename or len(filename)>4096 or not Path(filename).is_absolute():
                    raise ValueError('Invalid theme icon filename.')
    if 'screensaver' in value:
        from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences
        saver=value['screensaver']
        if not isinstance(saver,dict) or set(saver) not in ({'saver'},{'saver','wait_minutes'}):
            raise ValueError('Invalid theme screen saver settings.')
        ScreenSaverPreferences(saver['saver'],saver.get('wait_minutes',10)).validate()
        if saver['saver'] and any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-._' for c in saver['saver']):
            raise ValueError('Invalid theme screen saver identity.')
    appearance={}
    if any(component in value for component in ('colors','fonts','metrics')):
        from win95lx.control_panel.theme_appearance import validate_colors,validate_fonts,validate_metrics
        for component,validator in (('colors',validate_colors),('fonts',validate_fonts),('metrics',validate_metrics)):
            if component in value:appearance[component]=validator(value[component])
    result = deepcopy(value)
    result.update(appearance)
    result['wallpaper'].update(pattern=pattern, pattern_rows=list(rows))
    # Ensure the serialized object is plain bounded JSON data, not a caller's
    # mutable dictionaries or dataclass-specific objects.
    return json.loads(json.dumps(result, ensure_ascii=False, allow_nan=False))


def encode_theme(name, value):
    value = validate_definition(value)
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    wall = value['wallpaper']
    parser['Control Panel\\Desktop'] = {'Wallpaper': wall['file'],
        'TileWallpaper': '1' if wall['mode'] == 'tile' else '0',
        'Pattern': ' '.join(map(str, wall['pattern_rows']))}
    parser['Control Panel\\Cursors'] = dict(value['pointers']['overrides'])
    for event, filename in sorted(value['sounds']['events'].items()):
        parser['AppEvents\\Schemes\\Apps\\.Default\\' + event + '\\.Current'] = {'DefaultValue': filename}
    if 'screensaver' in value:
        parser['Win95LX.ScreenSaver'] = {key:str(item) for key,item in value['screensaver'].items()}
    parser['Win95LX.Theme'] = {'Schema': '1', 'Name': theme_name(name),
        'Settings': json.dumps(value, ensure_ascii=False, separators=(',', ':'))}
    stream = io.StringIO(); parser.write(stream, space_around_delimiters=False)
    data = stream.getvalue().encode('utf-8')
    if len(data) > MAX_DEFINITION:
        raise ValueError('The theme definition is too large.')
    return data


def decode_theme(data):
    if not isinstance(data, bytes) or len(data) > MAX_DEFINITION:
        raise ValueError('The theme definition is too large or invalid.')
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    try:
        parser.read_string(data.decode('utf-8-sig'))
        section = parser['Win95LX.Theme']
        if section.get('schema') != '1' or set(section) != {'schema', 'name', 'settings'}:
            raise ValueError('Unsupported theme definition version.')
        return theme_name(section['name']), validate_definition(json.loads(section['settings']))
    except (UnicodeError, configparser.Error, KeyError, TypeError) as error:
        raise ValueError('The theme definition cannot be read.') from error


class ThemeStore:
    """A private user catalog layered over immutable shipped definitions.

    Save As and Delete touch definitions only. Removing a shipped definition
    records a per-user tombstone; original distribution assets stay immutable.
    External edits are detected by content tokens before overwrite/deletion.
    """
    def __init__(self, directory, builtins, *, default_directory=None, legacy_loader=None):
        self.directory = Path(directory)
        self.default_directory=Path(default_directory) if default_directory is not None else self.directory
        self.builtins = deepcopy(builtins)
        self.errors = {}
        self.legacy_loader=legacy_loader

    @property
    def is_default_directory(self):
        return self.directory.resolve()==self.default_directory.resolve()

    def use_directory(self,directory):
        directory=Path(directory)
        if not directory.is_absolute():raise ValueError('Choose a complete theme folder path.')
        if directory.resolve()!=self.default_directory.resolve() and not directory.is_dir():
            raise ValueError('The selected theme folder is unavailable.')
        if directory.is_symlink():directory=directory.resolve()
        self.directory=directory

    def _prepare(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise ValueError('The theme folder is not available.')

    def _lock(self):
        self._prepare()
        flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0)
        descriptor = os.open(self.directory / '.win95lx-themes.lock', flags, 0o600)
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor); raise ValueError('The theme catalog is not available.')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        return os.fdopen(descriptor, 'rb')

    @staticmethod
    def _read(path):
        descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
        with os.fdopen(descriptor, 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise ValueError('The theme definition is not a regular file.')
            data = stream.read(MAX_DEFINITION + 1)
        if len(data) > MAX_DEFINITION:
            raise ValueError('The theme definition is too large.')
        return data

    def decode_path(self,path):
        data=self._read(path)
        try:return decode_theme(data)
        except ValueError:
            if self.legacy_loader is None:raise
            return self.legacy_loader(data,Path(path))

    def _hidden(self):
        path = self.directory / '.hidden.json'
        if not path.exists() and not path.is_symlink():
            return set()
        data = json.loads(self._read(path))
        if not isinstance(data, list) or any(not isinstance(n, str) for n in data):
            raise ValueError('The theme catalog cannot be read.')
        return set(data)

    def _custom(self):
        result = {}; errors = {}; ambiguous=set()
        if not self.directory.exists():
            self.errors={}
            return result
        if self.directory.is_symlink():
            raise ValueError('The theme folder is redirected.')
        for path in sorted(self.directory.iterdir()):
            if path.suffix.casefold() != '.theme':
                continue
            try:
                name, value = self.decode_path(path)
                key = name.casefold()
                if key != theme_name(path.stem).casefold():
                    raise ValueError('Conflicting theme definition names.')
                if key in result:
                    errors[result[key][2].name]='Conflicting theme definition names.'
                    del result[key];ambiguous.add(key)
                    raise ValueError('Conflicting theme definition names.')
                if key in ambiguous:raise ValueError('Conflicting theme definition names.')
                result[key] = (name, value, path)
            except (OSError, ValueError, TypeError) as error:
                errors[path.name] = str(error)
        self.errors = errors
        return result

    def catalog(self):
        if self.directory.is_symlink():raise ValueError('The theme folder is redirected.')
        hidden = self._hidden() if self.directory.exists() and self.is_default_directory else set()
        values = {name: deepcopy(value) for name, value in self.builtins.items() if name.casefold() not in hidden} if self.is_default_directory else {}
        for key, (name, value, _path) in self._custom().items():
            for old in tuple(values):
                if old.casefold() == key: del values[old]
            values[name] = value
        return values

    def names(self):
        return tuple(sorted(self.catalog(), key=str.casefold))

    def _builtin(self, name):
        if not self.is_default_directory:return None
        return next((key for key in self.builtins if key.casefold() == name.casefold()), None)

    def is_custom(self, name):
        try:key=theme_name(name).casefold()
        except ValueError:return False
        return key in self._custom()

    def exists(self, name):
        try:key = theme_name(name).casefold()
        except ValueError:return False
        return any(n.casefold() == key for n in self.catalog())

    contains = exists

    def path_for(self, name):
        name = theme_name(name); record = self._custom().get(name.casefold())
        return record[2] if record else self.directory / (name + '.theme')

    def token(self, name):
        try:name = theme_name(name)
        except ValueError:return None
        record = self._custom().get(name.casefold())
        if record:
            return hashlib.sha256(self._read(record[2])).hexdigest()
        original = self._builtin(name)
        if original is not None and self.exists(original):
            return 'builtin:' + hashlib.sha256(json.dumps(self.builtins[original], sort_keys=True).encode()).hexdigest()
        return None

    def _atomic(self, path, data, *, exclusive=False):
        temporary = None;committed=False
        try:
            try:
                with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.theme-', delete=False) as stream:
                    temporary = Path(stream.name); stream.write(data); stream.flush(); os.fsync(stream.fileno())
                if exclusive:
                    os.link(temporary, path)
                else:
                    if path.is_symlink(): raise ValueError('The theme definition is redirected.')
                    temporary.replace(path)
                committed=True
                descriptor = os.open(path.parent, os.O_DIRECTORY)
                try: os.fsync(descriptor)
                finally: os.close(descriptor)
            finally:
                if temporary is not None: temporary.unlink(missing_ok=True)
        except Exception as error:
            error.theme_write_committed=committed
            raise

    def save(self, name, value, *, overwrite=False, expected=None, commit=None):
        name = theme_name(name); data = encode_theme(name, value)
        with self._lock():
            matches=[]
            for candidate in self.directory.iterdir():
                if candidate.suffix.casefold()=='.theme':
                    try:key=theme_name(candidate.stem).casefold()
                    except ValueError:continue
                    if key==name.casefold():matches.append(candidate)
            if len(matches)>1:raise ValueError('The theme folder contains conflicting file names.')
            current = self.token(name)
            if current is not None and not overwrite:
                raise ThemeExistsError(name, current)
            if expected is not None and current != expected:
                raise ThemeChangedError('This theme changed while the dialog was open. Try again.')
            record = self._custom().get(name.casefold())
            if matches and record is None:
                raise ValueError('The existing theme definition cannot be replaced because it cannot be read.')
            if record: name, _value, path = record; data = encode_theme(name, value)
            else: path = self.directory / (name + '.theme')
            previous = self._read(path) if record else None
            written=False
            try:
                self._atomic(path, data, exclusive=record is None)
                written=True
                if commit is not None: commit(name)
            except Exception as error:
                # A failed metadata commit must not lose an overwritten theme.
                # Never roll back a file which another editor replaced meanwhile.
                if (written or getattr(error,'theme_write_committed',False)) and path.exists() and not path.is_symlink() and self._read(path) == data:
                    try:
                        if previous is None: path.unlink()
                        else: self._atomic(path, previous)
                    except Exception as rollback:
                        raise RuntimeError('The theme could not be saved and its previous definition could not be restored.') from rollback
                raise error
        return name

    def save_path(self,path,value,*,overwrite=False,expected=None):
        path=Path(path)
        if not path.is_absolute():raise ValueError('Choose a complete theme file path.')
        if path.suffix.casefold()!='.theme':path=path.with_name(path.name+'.theme')
        if not path.parent.is_dir() and path.parent.resolve()!=self.default_directory.resolve():
            raise ValueError('The selected theme folder is unavailable.')
        target=ThemeStore(path.parent,self.builtins,default_directory=self.default_directory,legacy_loader=self.legacy_loader)
        name=target.save(path.stem,value,overwrite=overwrite,expected=expected)
        self.use_directory(path.parent)
        return name

    def token_path(self,path):
        path=Path(path)
        if not path.is_absolute():raise ValueError('Choose a complete theme file path.')
        if path.suffix.casefold()!='.theme':path=path.with_name(path.name+'.theme')
        return ThemeStore(path.parent,self.builtins,default_directory=self.default_directory,legacy_loader=self.legacy_loader).token(path.stem)

    def exists_path(self,path):
        path=Path(path)
        if path.suffix.casefold()!='.theme':path=path.with_name(path.name+'.theme')
        return path.exists() or self.token_path(path) is not None

    def delete(self, name, *, expected=None):
        name = theme_name(name)
        with self._lock():
            current = self.token(name)
            if current is None: raise FileNotFoundError('This theme is no longer available.')
            if expected is not None and current != expected:
                raise ThemeChangedError('This theme changed while the dialog was open. Try again.')
            record = self._custom().get(name.casefold()); builtin = self._builtin(name)
            hidden = self._hidden(); state = self.directory / '.hidden.json'
            previous = self._read(state) if state.exists() else None
            if builtin:
                hidden.add(builtin.casefold())
                self._atomic(state, (json.dumps(sorted(hidden)) + '\n').encode())
            try:
                if record: record[2].unlink()
            except Exception:
                if builtin:
                    if previous is None: state.unlink(missing_ok=True)
                    else: self._atomic(state, previous)
                raise
        return name
