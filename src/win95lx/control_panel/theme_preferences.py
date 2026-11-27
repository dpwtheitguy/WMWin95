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

COMPONENTS = ('wallpaper', 'pointers', 'sounds')
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
    return {'name': Path(path).stem, 'wallpaper': {'file': wallpaper,
            'mode': 'tile' if desktop.get('tilewallpaper', '0') == '1' else 'center'},
            'pointers': pointers, 'sounds': sounds}


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
            if not isinstance(stored, dict) or set(stored) != {'name', 'components'} or not isinstance(stored['components'], list):
                raise ValueError('Invalid saved theme selection.')
            self.select(stored['name'], stored['components'])
            self.applied = self.pending
        except (OSError, ValueError, TypeError):
            self.applied = self.pending = None

    def select(self, name, components=COMPONENTS):
        if name not in self.themes:
            raise ValueError('Unknown desktop theme.')
        value = ThemeSelection(name, tuple(components)).validate()
        if any(component not in self.providers for component in value.components):
            raise ValueError('A selected theme component is unavailable.')
        self.pending = value

    def reconcile_current(self, matches):
        """Treat saved metadata as history, not proof session settings match it."""
        if self.applied is not None:
            theme = self.themes[self.applied.name]
            if any(not matches[name](theme[name]) for name in self.applied.components):
                self.applied = self.pending = None

    def cancel(self):
        self.pending = self.applied

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
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temp = self.path.with_suffix('.tmp')
            temp.write_text(json.dumps({'name': self.pending.name, 'components': self.pending.components}) + '\n')
            temp.replace(self.path)
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
    def __init__(self, wallpaper, refresh):
        self.wallpaper, self.refresh = wallpaper, refresh

    def snapshot(self):
        w = self.wallpaper
        return deepcopy({key: value for key, value in vars(w).items() if key != 'path'}), w.path.read_bytes() if w.path.exists() else None

    def apply(self, value):
        w = self.wallpaper
        path = Path(value['file'])
        if not path.is_file():
            raise ValueError('The theme wallpaper cannot be found.')
        if value['mode'] not in ('center', 'tile'):
            raise ValueError('Unsupported wallpaper placement.')
        label = w.register(path)
        w.apply(label, value['mode'], '(None)', (0,) * 8)
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

    def apply(self, scheme):
        from dataclasses import replace
        if scheme not in self.schemes:
            raise ValueError('The theme pointer scheme is not installed.')
        value = replace(self.current(), scheme=scheme, overrides={}).validate()
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
