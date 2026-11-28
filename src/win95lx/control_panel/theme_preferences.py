"""Read original Plus! theme definitions without executing their components.

Providers expose snapshot/apply/restore. A transaction includes the provider
that failed: a provider may have changed part of its state before raising.
"""
from dataclasses import dataclass, field
from pathlib import Path
from copy import deepcopy
import configparser
import json
import re

COMPONENTS = ('wallpaper', 'pointers', 'sounds', 'icons', 'colors', 'fonts', 'metrics', 'screensaver')
UNSUPPORTED = {
    'screensaver': 'These screen saver programs are not supported in this version.',
    'icons': 'Theme desktop icon changes are not available in this version.',
    'colors': 'Theme system color changes are not available in this version.',
    'fonts': 'Theme font and window size changes are not available in this version.',
}


def installed_names(inf, audio_bits=16):
    """Map installed long names back to the CAB members that supply them."""
    if audio_bits not in (8, 16):
        raise ValueError('Choose 8-bit or 16-bit theme sound assets.')
    result = {}
    for short, long in re.findall(r'[,\s]([\w~.-]+)<([^<>\r\n]+)>', inf):
        key = long.casefold()
        if key in result and result[key] != short:
            previous = result[key]
            if {Path(previous).suffix.upper(), Path(short).suffix.upper()} == {'.WAV', '.WA8'}:
                result[key] = next(value for value in (previous, short)
                                   if value.upper().endswith('.WAV' if audio_bits == 16 else '.WA8'))
                continue
            raise ValueError('Ambiguous Plus! installation filename.')
        result[key] = short
    return result


# Original installed aliases resolve to IDs, never commands or executable paths.
SCREENSAVER_ALIASES = {
    'nature.scr':'plus95-nature', 'dangerous creatures.scr':'plus95-dangerous',
    'leonardo da vinci.scr':'plus95-davinci', 'the golden era.scr':'plus95-golden-era',
    'sports.scr':'plus95-sports', 'mystery.scr':'plus95-mystery',
    'inside your computer.scr':'plus95-inside-computer', 'travel.scr':'plus95-travel',
    'windows 95.scr':'plus95-windows95', "the 60's usa.scr":'plus95-sixties',
    'science.scr':'plus95-science',
    **{name+'.scr':'win95-'+name for name in ('bezier','scrnsave','ssflywin','ssmarque','ssmyst','ssstars','ss3dfo','ssflwbox','ssmaze','sspipes','sstext3d')},
}


def screensaver_association(value):
    if not isinstance(value,str):raise ValueError('Invalid theme screen saver association.')
    value=value.strip()
    if not value:return {'saver':''}
    if value.startswith('"') and value.endswith('"'):value=value[1:-1]
    match=re.fullmatch(r'%windir%\\?system\\([^\\/:"<>|?*]+)',value,re.I)
    if match is None or match[1].casefold() not in SCREENSAVER_ALIASES:
        raise ValueError('The theme screen saver is not in the installed catalog.')
    return {'saver':SCREENSAVER_ALIASES[match[1].casefold()]}


def original_screensaver(path):
    """Read only a known original association; do not import registry commands."""
    data=Path(path).read_bytes()
    if len(data)>256*1024:raise ValueError('The theme definition is too large.')
    # Original WIN95HC.THM contains a bare legacy line outside our association.
    parser=configparser.ConfigParser(interpolation=None,strict=True,allow_no_value=True)
    parser.read_string(data.decode('cp1252'))
    sections={name.casefold():parser[name] for name in parser.sections()}
    boot=sections.get('boot',{})
    if 'scrnsave.exe' not in boot:return None
    desktop=sections.get('control panel\\desktop',{})
    if desktop.get('screensaveactive','1')=='0':return {'saver':''}
    return screensaver_association(boot['scrnsave.exe'])


def parse_theme(path, names, root):
    root = Path(root).resolve()
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.read_string(Path(path).read_text(encoding='cp1252'))
    sections = {name.casefold(): parser[name] for name in parser.sections()}

    def asset(value):
        value = value.strip().strip('"')
        if not value:
            return ''
        if not value.casefold().startswith('%themedir%'):
            raise ValueError('Unsupported theme asset location: ' + value)
        name = value[len('%ThemeDir%'):]
        if '/' in name or '\\' in name or name in ('.', '..'):
            raise ValueError('Theme asset must be a filename.')
        source = names.get(name.casefold())
        if source is None:
            raise ValueError('Theme asset is absent from the installation manifest: ' + name)
        candidate = (root / source).resolve()
        if candidate.parent != root or not candidate.is_file():
            raise ValueError('Theme asset is missing or outside the library: ' + name)
        return str(candidate)

    desktop = sections.get('control panel\\desktop', {})
    pointers = {key: asset(value) for key, value in sections.get('control panel\\cursors', {}).items()
                if key != 'defaultvalue'}
    sounds = {}
    for section, values in sections.items():
        if section.startswith('appevents\\schemes\\apps\\') and section.endswith('\\.current'):
            parts = section.split('\\')
            sounds[parts[-2]] = asset(values.get('defaultvalue', ''))
    wallpaper = asset(desktop.get('wallpaper', ''))
    result = {'name': Path(path).stem, 'wallpaper': {'file': wallpaper,
            'mode': 'tile' if desktop.get('tilewallpaper', '0') == '1' else 'center'},
            'pointers': pointers, 'sounds': sounds}
    boot=sections.get('boot',{})
    if 'scrnsave.exe' in boot:
        try:result['screensaver']=screensaver_association(boot['scrnsave.exe'])
        except ValueError:pass  # Preserve safe visual components; never expose executable text.
        if desktop.get('screensaveactive','1')=='0':result['screensaver']={'saver':''}
    return result


@dataclass(frozen=True)
class ThemeSelection:
    name: str = ''
    components: tuple = field(default_factory=lambda: COMPONENTS)

    def validate(self):
        if not isinstance(self.name, str) or not self.name or len(self.name) > 100:
            raise ValueError('Choose a desktop theme.')
        if not isinstance(self.components, tuple) or len(set(self.components)) != len(self.components) or any(c not in COMPONENTS for c in self.components):
            raise ValueError('Unsupported theme component.')
        return self


class ThemeController:
    def __init__(self, themes, providers, path):
        self.themes, self.providers, self.path = themes, providers, Path(path)
        self.applied = None
        self.pending = None
        try:
            stored = json.loads(self.path.read_text())
            if not isinstance(stored, dict) or set(stored) not in ({'name', 'components'},{'name','components','directory'}) or not isinstance(stored['components'], list):
                raise ValueError('Invalid saved theme selection.')
            if 'directory' in stored:raise ValueError('An external theme needs its attached theme folder.')
            self.select(stored['name'], stored['components'])
            self.applied = self.pending
        except (OSError, ValueError, TypeError):
            self.applied = self.pending = None

    def select(self, name, components=None):
        if name not in self.themes:
            raise ValueError('Unknown desktop theme.')
        if components is None:
            components=tuple(component for component in COMPONENTS if component in self.themes[name] and (component in self.providers or component in ('wallpaper','pointers','sounds')))
        value = ThemeSelection(name, tuple(components)).validate()
        if any(component not in self.providers for component in value.components):
            raise ValueError('A selected theme component is unavailable.')
        if any(component not in self.themes[name] for component in value.components):
            raise ValueError('A selected component is not included in this theme.')
        self.pending = value

    def reconcile_current(self, matches):
        """Treat saved metadata as history, not proof session settings match it."""
        if self.applied is not None:
            theme = self.themes[self.applied.name]
            if any(not matches[name](theme[name]) for name in self.applied.components):
                self.applied = self.pending = None

    def cancel(self):
        self.pending = self.applied
        self.edited = None

    def attach_store(self, store):
        self.store=store
        self.refresh_catalog()
        # The saved selection may refer to a custom definition which was not
        # available when the controller initially read its metadata.
        if self.applied is None and self.pending is None:
            try:
                stored=json.loads(self.path.read_text())
                if not isinstance(stored,dict) or set(stored) not in ({'name','components'},{'name','components','directory'}) or not isinstance(stored['components'],list):
                    raise ValueError('Invalid saved theme selection.')
                if 'directory' in stored:
                    store.use_directory(stored['directory']);self.refresh_catalog()
                self.select(stored['name'],tuple(stored['components']))
                self.applied=self.pending
            except (OSError,ValueError,TypeError,KeyError):
                store.use_directory(store.default_directory);self.refresh_catalog()
        return self

    def refresh_catalog(self, builtins=None):
        if hasattr(self,'store'):
            if builtins is not None:self.store.builtins=deepcopy(builtins)
            values=self.store.catalog()
            self.themes.clear();self.themes.update(values)
        if self.pending is not None and self.pending.name not in self.themes:self.pending=None
        if self.applied is not None and self.applied.name not in self.themes:self.applied=None

    def capture_current(self):
        from win95lx.control_panel.theme_store import validate_definition
        value={}
        for name,provider in self.providers.items():
            if name not in COMPONENTS:continue
            capture=getattr(provider,'export_current',getattr(provider,'capture',None))
            if capture is None:raise ValueError('The current '+name+' settings cannot be saved.')
            value[name]=capture()
        return validate_definition(value)

    def _save_selection(self, selection):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp')
        try:
            value={'name':selection.name,'components':selection.components}
            if hasattr(self,'store') and not self.store.is_default_directory:value['directory']=str(self.store.directory)
            temp.write_text(json.dumps(value)+'\n')
            temp.replace(self.path)
        finally:temp.unlink(missing_ok=True)

    def save_current(self,name=None,*,path=None,overwrite=False,expected=None):
        if not hasattr(self,'store'):raise ValueError('The theme folder is unavailable.')
        value=self.capture_current()
        components=tuple(component for component in COMPONENTS if component in value)
        # Native Save As creates/selects a definition and enables Apply. It
        # does not apply the desktop or commit the current-theme registry value.
        if path is not None:name=self.store.save_path(path,value,overwrite=overwrite,expected=expected)
        else:name=self.store.save(name,value,overwrite=overwrite,expected=expected)
        self.refresh_catalog();self.pending=ThemeSelection(name,components);self.edited=True
        return name

    def open_theme(self,path):
        from win95lx.control_panel.theme_store import decode_theme,theme_name
        if not hasattr(self,'store'):raise ValueError('The theme folder is unavailable.')
        path=Path(path)
        if not path.is_absolute() or path.suffix.casefold()!='.theme':raise ValueError('Choose a theme file.')
        name,_value=self.store.decode_path(path)
        if name.casefold()!=theme_name(path.stem).casefold():raise ValueError('The theme definition has a conflicting name.')
        previous=self.store.directory,self.pending,self.applied
        try:
            self.store.use_directory(path.parent);self.refresh_catalog();self.select(name)
        except Exception:
            self.store.use_directory(previous[0]);self.refresh_catalog();self.pending,self.applied=previous[1:]
            raise
        return name

    def delete_theme(self,name,*,expected=None):
        if not hasattr(self,'store'):raise ValueError('The theme folder is unavailable.')
        self.store.delete(name,expected=expected)
        self.refresh_catalog()
        # Keep applied-history bytes as history. A missing definition resolves
        # to Current Windows settings on reopen; deletion must not rewrite the
        # current desktop's preference files or implicitly apply another theme.

    def apply(self):
        if self.pending is None:
            raise ValueError('Choose a desktop theme.')
        self.pending.validate()
        if hasattr(self, 'preflight'):
            self.preflight(self.pending.components)
        theme = self.themes[self.pending.name]
        snapshots = [(name, self.providers[name].snapshot()) for name in self.pending.components]
        touched = []
        try:
            for name, previous in snapshots:
                touched.append((name, previous))
                self.providers[name].apply(theme[name])
            self._save_selection(self.pending)
        except Exception as failure:
            errors = []
            for name, previous in reversed(touched):
                try:
                    self.providers[name].restore(previous)
                except Exception as error:
                    errors.append(name + ': ' + str(error))
            if errors:
                raise RuntimeError('Theme application failed and some settings could not be restored: ' + '; '.join(errors)) from failure
            raise
        self.applied = self.pending
        self.edited = None


class PreferenceProvider:
    """Adapt an existing preference controller without replacing its backend.

    Capture preference bytes as well as the active value: restoring only the
    active session would silently leave the failed theme applied after reboot.
    """
    def __init__(self, controller, convert):
        self.controller, self.convert = controller, convert

    def snapshot(self):
        c = self.controller
        return c.applied, c.pending, c.path.read_bytes() if c.path.exists() else None, c.backend.snapshot()

    def apply(self, value):
        c = self.controller
        c.pending = self.convert(value, c.applied)
        c.apply()

    def export_current(self):
        from dataclasses import asdict
        c=self.controller
        value=c.applied
        if c.path.exists():value=type(value)(**json.loads(c.path.read_text())).validate()
        data=asdict(value)
        return {key:deepcopy(data[key]) for key in ('scheme','events')}

    def restore(self, state):
        applied, pending, contents, backend_state = state
        c = self.controller
        c.backend.restore(backend_state)
        c.apply_session(applied)
        if contents is None:
            c.path.unlink(missing_ok=True)
        else:
            c.path.write_bytes(contents)
        c.applied, c.pending = applied, pending


class WallpaperProvider:
    """Use the existing Wallpaper persistence/render model and refresh hook."""
    def __init__(self, wallpaper, refresh, assets=None):
        self.wallpaper, self.refresh = wallpaper, refresh
        self.assets=Path(assets) if assets is not None else None

    def export_current(self):
        from win95lx.control_panel.wallpaper import BITMAPS
        w=self.wallpaper
        if w.name=='(None)':filename=''
        elif w.name in w.custom:filename=w.custom[w.name]
        elif self.assets is not None and w.name in BITMAPS:filename=str((self.assets/('wallpaper-'+BITMAPS[w.name])).resolve())
        else:raise ValueError('The current wallpaper cannot be saved.')
        return {'file':filename,'mode':w.mode,'pattern':w.pattern,'pattern_rows':list(w.pattern_rows)}

    def snapshot(self):
        w = self.wallpaper
        return deepcopy({key: value for key, value in vars(w).items() if key != 'path'}), w.path.read_bytes() if w.path.exists() else None

    def apply(self, value):
        w = self.wallpaper
        path = Path(value['file']) if value['file'] else None
        if path is not None and not path.is_file():
            raise ValueError('The theme wallpaper cannot be found.')
        if value['mode'] not in ('center', 'tile'):
            raise ValueError('Unsupported wallpaper placement.')
        rows=value.get('pattern_rows',(0,)*8)
        if len(rows)!=8 or any(type(n) is not int or not 0<=n<=255 for n in rows):raise ValueError('Invalid desktop pattern data.')
        label = w.register(path) if path is not None else '(None)'
        w.apply(label, value['mode'], value.get('pattern','(None)'), rows)
        self.refresh()

    def restore(self, state):
        values, contents = state
        w = self.wallpaper
        for key in tuple(vars(w)):
            if key != 'path':
                delattr(w, key)
        vars(w).update(deepcopy(values))
        if contents is None:
            w.path.unlink(missing_ok=True)
        else:
            w.path.write_bytes(contents)
        self.refresh()


class PointerThemeProvider:
    """Change only pointer artwork; never rewrite device acceleration/buttons."""
    def __init__(self, path, current, apply_session, schemes):
        self.path, self.current, self.apply_session = Path(path), current, apply_session
        self.schemes = schemes

    def snapshot(self):
        return self.current(), self.path.read_bytes() if self.path.exists() else None

    def export_current(self):
        value=self.current()
        return {'scheme':value.scheme,'overrides':deepcopy(value.overrides)}

    def apply(self, scheme):
        from dataclasses import replace
        overrides={}
        if isinstance(scheme,dict):
            overrides=deepcopy(scheme.get('overrides',{}));scheme=scheme.get('scheme')
        if scheme not in self.schemes:
            raise ValueError('The theme pointer scheme is not installed.')
        value = replace(self.current(), scheme=scheme, overrides=overrides).validate()
        from win95lx.assets.cursors import decode
        for filename in overrides.values():
            path=Path(filename)
            if not path.is_absolute():raise ValueError('The theme pointer file must be a complete path.')
            if path.stat().st_size>16*1024*1024:raise ValueError('The theme pointer file is too large.')
            decode(path.read_bytes())
        self.apply_session(value)
        value.save(self.path)

    def restore(self, state):
        value, contents = state
        self.apply_session(value)
        if contents is None:
            self.path.unlink(missing_ok=True)
        else:
            self.path.write_bytes(contents)


class CurrentPreferenceProvider(PreferenceProvider):
    """Refresh saved values at transaction time after another applet was closed."""
    def snapshot(self):
        c=self.controller
        value=type(c.applied)()
        if c.path.exists():
            value=type(c.applied)(**json.loads(c.path.read_text())).validate()
        c.applied=c.pending=value
        c.backend.restore(value)
        return super().snapshot()


def native_256_component(value):
    """The prepared QEMU VGA6 DAC profile; not an all-hardware color rule.

    Independently specified in QEMU8.2.2 hw/display/vga_int.h c6_to_8.
    """
    if type(value) is not int or not 0<=value<=255:
        raise ValueError('Invalid palette component.')
    six=value>>2
    return (six<<2)|(3 if six&1 else 0)


class ScreensaverThemeProvider:
    """Reuse the Display saver host; applying a theme never starts media code."""
    def __init__(self, host):
        self.host=host

    def export_current(self):
        from dataclasses import asdict
        return asdict(self.host.applied.validate())

    def snapshot(self):
        h=self.host
        return h.applied,h.pending,h.path.read_bytes() if h.path.exists() else None

    def _value(self, value):
        from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences
        if not isinstance(value,dict) or set(value) not in ({'saver'},{'saver','wait_minutes'}):
            raise ValueError('Invalid theme screen saver settings.')
        result=ScreenSaverPreferences(value['saver'],value.get('wait_minutes',self.host.applied.wait_minutes)).validate()
        if result.saver:
            if self.host.runtime is None or self.host.catalog is None:
                raise ValueError('The screen saver compatibility component is unavailable.')
            self.host.catalog.resolve(result.saver)
            available,reason=self.host.runtime.availability(result.saver,'fullscreen')
            if not available:raise ValueError(reason)
            if not self.host.runtime.ready(result.saver):
                raise ValueError('The screen saver must finish preparing before applying this theme.')
        return result

    def apply(self, value):
        h=self.host
        pending=h.pending
        try:
            h.pending=self._value(value)
            h.apply()
        finally:
            # Do not consume an independent pending Display selection.
            h.pending=pending

    def restore(self, state):
        applied,pending,contents=state
        h=self.host
        if not hasattr(h,'restore_theme'):
            raise RuntimeError('The screen saver host cannot restore a theme transaction.')
        h.restore_theme(applied,pending,contents)

    def matches(self, value):
        current=self.export_current()
        return isinstance(value,dict) and all(current.get(key)==item for key,item in value.items())
