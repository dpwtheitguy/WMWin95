import tempfile
import json
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from win95lx.control_panel.theme_preferences import ThemeController, ThemeSelection, installed_names, parse_theme, WallpaperProvider, PreferenceProvider
from win95lx.control_panel.wallpaper import Wallpaper


class Provider:
    def __init__(self, value=0, fail=False):
        self.value, self.fail = value, fail
    def snapshot(self): return self.value
    def restore(self, value): self.value = value
    def apply(self, value):
        self.value = value
        if self.fail: raise RuntimeError('provider failed after mutation')


class ThemeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.providers = {name: Provider() for name in ('wallpaper', 'pointers', 'sounds')}
        self.themes = {'Nature': {name: name for name in self.providers}}
        self.path = self.root / 'theme.json'
        self.controller = ThemeController(self.themes, self.providers, self.path)

    def test_apply_all_and_persist(self):
        self.controller.select('Nature'); self.controller.apply()
        self.assertEqual([p.value for p in self.providers.values()], list(self.providers))
        self.assertIn('Nature', self.path.read_text())
        self.assertEqual(self.controller.applied, self.controller.pending)

    def test_cancel_never_applies(self):
        self.controller.select('Nature'); self.controller.cancel()
        self.assertIsNone(self.controller.pending)
        self.assertEqual([p.value for p in self.providers.values()], [0, 0, 0])
        self.assertFalse(self.path.exists())

    def test_reopen_loads_selection_without_reapplying(self):
        self.controller.select('Nature', ('sounds',));self.controller.apply()
        for provider in self.providers.values():provider.fail = True
        reopened = ThemeController(self.themes,self.providers,self.path)
        self.assertEqual(reopened.applied,ThemeSelection('Nature',('sounds',)))
        self.assertEqual(reopened.pending,reopened.applied)

    def test_external_edits_invalidate_theme_label_without_touching_history(self):
        self.controller.select('Nature',('wallpaper',));self.controller.apply()
        previous=self.path.read_bytes()
        calls=[]
        self.controller.reconcile_current({'wallpaper':lambda value:calls.append(value) or False})
        self.assertIsNone(self.controller.applied);self.assertIsNone(self.controller.pending)
        self.assertEqual(calls,['wallpaper']);self.assertEqual(self.path.read_bytes(),previous)
        self.assertEqual(self.providers['sounds'].value,0)

    def test_malformed_saved_selection_has_no_effect(self):
        for raw in ('null','[]','{"name":"Nature","components":"sounds"}', '{"name":"Missing","components":[]}', '{"name":"Nature","components":["colors"]}'):
            self.path.write_text(raw)
            reopened=ThemeController(self.themes,self.providers,self.path)
            self.assertIsNone(reopened.pending)
            self.assertEqual([p.value for p in self.providers.values()],[0,0,0])

    def test_subset_leaves_other_components_alone(self):
        self.controller.select('Nature', ('sounds',)); self.controller.apply()
        self.assertEqual([p.value for p in self.providers.values()], [0, 0, 'sounds'])

    def test_every_provider_failure_rolls_back_including_failed_provider(self):
        for name in self.providers:
            with self.subTest(component=name):
                self.providers[name].fail = True
                self.controller.select('Nature')
                with self.assertRaisesRegex(RuntimeError, 'provider failed'): self.controller.apply()
                self.assertEqual([p.value for p in self.providers.values()], [0, 0, 0])
                self.assertIsNone(self.controller.applied)
                self.assertFalse(self.path.exists())
                self.providers[name].fail = False

    def test_persistence_failure_restores_effects(self):
        self.path.mkdir()
        self.controller.select('Nature')
        with self.assertRaises(OSError): self.controller.apply()
        self.assertEqual([p.value for p in self.providers.values()], [0, 0, 0])

    def test_rollback_failure_is_not_suppressed(self):
        self.providers['sounds'].fail = True
        self.providers['wallpaper'].restore = lambda value: (_ for _ in ()).throw(RuntimeError('restore failed'))
        self.controller.select('Nature')
        with self.assertRaisesRegex(RuntimeError, 'wallpaper: restore failed'): self.controller.apply()

    def test_unknown_and_unsupported_components_rejected(self):
        with self.assertRaises(ValueError): self.controller.select('Missing')
        for components in (('colors',), ('sounds', 'sounds')):
            with self.assertRaises(ValueError): self.controller.select('Nature', components)

    def test_preflight_conflict_changes_no_provider_or_persistence(self):
        def reject(components):
            self.assertEqual(components,('wallpaper',))
            raise ValueError('Close Display Properties first.')
        self.controller.preflight=reject
        self.controller.select('Nature',('wallpaper',))
        with self.assertRaisesRegex(ValueError,'Close Display'):self.controller.apply()
        self.assertFalse(self.path.exists());self.assertIsNone(self.controller.applied)
        self.assertEqual(self.controller.pending.name,'Nature')
        self.assertEqual([provider.value for provider in self.providers.values()],[0,0,0])

    def test_unavailable_provider_rejected(self):
        del self.providers['sounds']
        with self.assertRaises(ValueError): self.controller.select('Nature')

    def test_manifest_audio_variants_are_explicit(self):
        inf = ' 1,NA.WAV<Nature beep.wav>\n 1,NA.WA8<Nature beep.wav>'
        self.assertEqual(installed_names(inf)['nature beep.wav'], 'NA.WAV')
        self.assertEqual(installed_names(inf, 8)['nature beep.wav'], 'NA.WA8')

    def test_manifest_ambiguous_non_audio_rejected(self):
        with self.assertRaises(ValueError): installed_names(' 1,A.BMP<X.bmp>\n 1,B.BMP<X.bmp>')

    def test_parse_resolves_original_names_without_execution(self):
        (self.root/'NA.JPG').write_bytes(b'fixture')
        source = self.root/'NATURE.THM'
        source.write_text('[Control Panel\\Desktop]\nWallpaper=%ThemeDir%Nature wallpaper.jpg\nTileWallpaper=1\n[boot]\nSCRNSAVE.EXE=evil.exe\n')
        value = parse_theme(source, {'nature wallpaper.jpg': 'NA.JPG'}, self.root)
        self.assertEqual(value['wallpaper'], {'file': str(self.root/'NA.JPG'), 'mode': 'tile'})
        self.assertNotIn('screensaver', value)

    def test_parse_rejects_traversal_and_external_paths(self):
        source = self.root/'TEST.THM'
        for value in ('%ThemeDir%../outside.jpg', 'file:///etc/passwd', '%ThemeDir%missing.jpg'):
            source.write_text('[Control Panel\\Desktop]\nWallpaper=' + value)
            with self.assertRaises(ValueError): parse_theme(source, {}, self.root)

    def test_wallpaper_provider_actual_model_persistence_and_restore(self):
        path = self.root/'wallpaper.json'; image = self.root/'nature.jpg'; image.write_bytes(b'fixture')
        w = Wallpaper([], path); calls = []
        provider = WallpaperProvider(w, lambda: calls.append(w.name))
        before = provider.snapshot()
        provider.apply({'file': str(image), 'mode': 'tile'})
        self.assertEqual(Wallpaper([], path).name, 'nature.jpg')
        self.assertEqual(w.mode, 'tile')
        provider.restore(before)
        self.assertEqual(w.name, '(None)'); self.assertFalse(path.exists())
        self.assertEqual(w.custom, {}); self.assertEqual(calls, ['nature.jpg', '(None)'])

    def test_wallpaper_existing_bytes_restored_on_later_component_failure(self):
        path = self.root/'wallpaper.json'; w = Wallpaper([], path); w.apply('(None)', 'center')
        previous = path.read_bytes(); image = self.root/'nature.jpg'; image.write_bytes(b'fixture')
        self.providers['wallpaper'] = WallpaperProvider(w, lambda: None)
        self.themes['Nature']['wallpaper'] = {'file': str(image), 'mode': 'tile'}
        self.providers['sounds'].fail = True
        self.controller.select('Nature')
        with self.assertRaises(RuntimeError): self.controller.apply()
        self.assertEqual(path.read_bytes(), previous); self.assertEqual(w.name, '(None)')

    def test_wallpaper_missing_rejected_without_persisting(self):
        w = Wallpaper([], self.root/'wallpaper.json')
        provider = WallpaperProvider(w, lambda: None)
        with self.assertRaises(ValueError): provider.apply({'file': str(self.root/'missing'), 'mode': 'center'})
        self.assertFalse(w.path.exists())

    def test_existing_sound_controller_effects_and_exact_file_rollback(self):
        from win95lx.control_panel.preferences import PreferenceController
        from win95lx.control_panel.sound_preferences import SoundPreferences, SoundBackend, KEYS
        backend = SoundBackend(self.root)
        path = self.root/'sounds.json'
        controller = PreferenceController(path, backend, SoundPreferences)
        provider = PreferenceProvider(controller, lambda value, previous: previous.select(value, {'Nature': {key:'' for key in KEYS}}))
        before = provider.snapshot()
        provider.apply('Nature')
        self.assertEqual(backend.preferences().scheme, 'Nature');self.assertTrue(path.exists())
        provider.restore(before)
        self.assertEqual(backend.preferences().scheme, 'Windows Default');self.assertFalse(path.exists())

    def test_preference_provider_restores_pending_and_old_bytes(self):
        from dataclasses import replace
        from win95lx.control_panel.preferences import PreferenceController
        from win95lx.control_panel.sound_preferences import SoundPreferences, SoundBackend, KEYS
        # No Sounds needs no actual audio device or WAV file.
        backend=SoundBackend(self.root);backend.value=SoundPreferences().select('No Sounds')
        path=self.root/'sounds.json';controller=PreferenceController(path,backend,SoundPreferences)
        controller.apply();old_bytes=path.read_bytes()
        controller.pending=replace(controller.applied,scheme='Pending')
        provider=PreferenceProvider(controller,lambda value, previous:replace(previous,scheme=value))
        before=provider.snapshot();provider.apply('Nature');provider.restore(before)
        self.assertEqual(path.read_bytes(),old_bytes)
        self.assertEqual(controller.pending.scheme,'Pending');self.assertEqual(controller.applied.scheme,'No Sounds')


class CurrentSoundThemeTests(unittest.TestCase):
    def test_external_scheme_saved_after_theme_open_survives_apply_and_rollback(self):
        from win95lx.control_panel.theme_preferences import CurrentPreferenceProvider
        from win95lx.control_panel.preferences import PreferenceController,save_preferences
        from win95lx.control_panel.sound_preferences import SoundPreferences,SoundBackend,KEYS
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);path=root/'sounds.json'
            c=PreferenceController(path,SoundBackend(root),SoundPreferences)
            mapping={key:'' for key in KEYS}
            provider=CurrentPreferenceProvider(c,lambda name,previous:previous.select(name,{'Nature':mapping}))
            externally_changed=SoundPreferences().select('No Sounds').save_scheme('My custom scheme')
            save_preferences(externally_changed,path);original=path.read_bytes()
            before=provider.snapshot();provider.apply('Nature')
            self.assertIn('My custom scheme',json.loads(path.read_text())['schemes'])
            provider.restore(before);self.assertEqual(path.read_bytes(),original)
            self.assertEqual(c.backend.preferences(),externally_changed)

class NativePaletteTests(unittest.TestCase):
    def test_vga6_profile_matches_independent_decoder_and_preserves_ui_components(self):
        from win95lx.control_panel.theme_preferences import native_256_component
        for original,expected in ((106,104),(92,95),(117,119),(86,87),(73,72),(90,88),(0,0),(128,128),(192,192),(255,255)):
            self.assertEqual(native_256_component(original),expected)
        for value in (-1,256,True,1.5):
            with self.assertRaises(ValueError):native_256_component(value)

class PointerThemeTests(unittest.TestCase):
    def test_artwork_apply_preserves_current_device_settings_and_rollback(self):
        from win95lx.control_panel.theme_preferences import PointerThemeProvider
        from win95lx.control_panel.mouse_preferences import MousePreferences
        from dataclasses import replace
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'mouse.json'
            state=[MousePreferences(left_handed=True,speed=9,double_click_ms=700)]
            provider=PointerThemeProvider(path,lambda:state[0],lambda value:state.__setitem__(0,value),('Plus! / Nature',))
            before=provider.snapshot();provider.apply('Plus! / Nature')
            self.assertEqual(state[0],replace(before[0],scheme='Plus! / Nature',overrides={}))
            # A later independent Mouse edit is retained by the next theme.
            state[0]=replace(state[0],speed=2,left_handed=False)
            provider.apply('Plus! / Nature');self.assertEqual(state[0].speed,2);self.assertFalse(state[0].left_handed)
            provider.restore(before);self.assertEqual(state[0],before[0]);self.assertFalse(path.exists())

    def test_missing_pointer_scheme_never_changes_state(self):
        from win95lx.control_panel.theme_preferences import PointerThemeProvider
        from win95lx.control_panel.mouse_preferences import MousePreferences
        calls=[]
        with tempfile.TemporaryDirectory() as folder:
            provider=PointerThemeProvider(Path(folder)/'mouse.json',MousePreferences,calls.append,())
            with self.assertRaises(ValueError):provider.apply('Missing')
            self.assertEqual(calls,[])

if __name__ == '__main__': unittest.main()
