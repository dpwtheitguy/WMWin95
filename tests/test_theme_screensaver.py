import json
from dataclasses import asdict
from pathlib import Path
import sys,tempfile,unittest
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.theme_preferences import ScreensaverThemeProvider, screensaver_association, SCREENSAVER_ALIASES, parse_theme, ThemeController
from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences

class Host:
    def __init__(self,path):
        self.path=path;self.applied=ScreenSaverPreferences('',10);self.pending=ScreenSaverPreferences('',12);self.scheduler=self.applied;self.prepared=True;self.usable=True;self.applies=0
        self.catalog=SimpleNamespace(resolve=self.resolve)
        self.runtime=SimpleNamespace(ready=lambda _:self.prepared,availability=lambda *a:(self.usable,'Unavailable.'))
    def resolve(self,identity):
        if identity not in ('plus95-nature','plus95-science'):raise ValueError('Missing package.')
    def apply(self):
        self.applied=self.pending;self.scheduler=self.applied;self.applies+=1;self.path.write_text(json.dumps(asdict(self.applied)))
    def restore_theme(self,applied,pending,contents):
        self.applied,self.pending,self.scheduler=applied,pending,applied
        if contents is None:self.path.unlink(missing_ok=True)
        else:self.path.write_bytes(contents)

class ThemeScreensaverTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.host=Host(self.root/'saver.json');self.provider=ScreensaverThemeProvider(self.host)
    def test_all_aliases_map_to_typed_ids(self):
        for alias,identity in SCREENSAVER_ALIASES.items():self.assertEqual(screensaver_association('%Windir%System\\'+alias),{'saver':identity})
    def test_optional_windows_slash_and_case(self):self.assertEqual(screensaver_association('%WINDIR%\\SYSTEM\\NATURE.SCR'),{'saver':'plus95-nature'})
    def test_quoted_spaces(self):self.assertEqual(screensaver_association('"%Windir%System\\The 60\'s USA.scr"'),{'saver':'plus95-sixties'})
    def test_empty_is_none(self):self.assertEqual(screensaver_association(''),{'saver':''})
    def test_unsafe_paths_and_commands_rejected(self):
        for value in ('evil.exe','%Windir%System\\Nature.scr /s','%Windir%System\\..\\Nature.scr','/tmp/Nature.scr','C:\\Windows\\System\\Nature.scr','%Other%Nature.scr','%Windir%System\\Nature.scr;echo x'):
            with self.subTest(value=value),self.assertRaises(ValueError):screensaver_association(value)
    def test_parse_original_boot_association(self):
        path=self.root/'Nature.THM';path.write_text('[boot]\nSCRNSAVE.EXE=%WinDir%System\\Nature.SCR')
        self.assertEqual(parse_theme(path,{},self.root)['screensaver'],{'saver':'plus95-nature'})
    def test_parse_unknown_preserves_safe_components(self):
        path=self.root/'Mixed.THM';path.write_text('[boot]\nSCRNSAVE.EXE=evil.exe')
        self.assertNotIn('screensaver',parse_theme(path,{},self.root))
    def test_parse_inactive_preserves_no_execution(self):
        path=self.root/'Off.THM';path.write_text('[Control Panel\\Desktop]\nScreenSaveActive=0\n[boot]\nSCRNSAVE.EXE=%WinDir%System\\Nature.SCR')
        self.assertEqual(parse_theme(path,{},self.root)['screensaver'],{'saver':''})
    def test_apply_keeps_existing_timeout_if_absent(self):self.provider.apply({'saver':'plus95-nature'});self.assertEqual(self.host.applied,ScreenSaverPreferences('plus95-nature',10))
    def test_apply_explicit_timeout(self):self.provider.apply({'saver':'plus95-nature','wait_minutes':20});self.assertEqual(self.host.scheduler.wait_minutes,20)
    def test_apply_preserves_display_pending(self):
        pending=self.host.pending;self.provider.apply({'saver':'plus95-nature'});self.assertEqual(self.host.pending,pending)
    def test_apply_does_not_launch_process(self):self.provider.apply({'saver':'plus95-nature'});self.assertEqual(self.host.applies,1)
    def test_unprepared_does_not_persist(self):
        self.host.prepared=False
        with self.assertRaises(ValueError):self.provider.apply({'saver':'plus95-nature'})
        self.assertEqual(self.host.applies,0);self.assertFalse(self.host.path.exists())
    def test_unavailable_component_does_not_persist(self):
        self.host.usable=False
        with self.assertRaises(ValueError):self.provider.apply({'saver':'plus95-nature'})
        self.assertFalse(self.host.path.exists())
    def test_missing_catalog_package_rejected(self):
        with self.assertRaises(ValueError):self.provider.apply({'saver':'missing'})
    def test_none_needs_no_runtime(self):
        self.host.runtime=None;self.host.catalog=None;self.provider.apply({'saver':''});self.assertEqual(self.host.applied.saver,'')
    def test_invalid_timeout_rejected(self):
        for n in (0,61,True,'10'):
            with self.subTest(n=n),self.assertRaises(ValueError):self.provider.apply({'saver':'plus95-nature','wait_minutes':n})
    def test_extra_commands_rejected(self):
        with self.assertRaises(ValueError):self.provider.apply({'saver':'plus95-nature','command':'evil'})
    def test_rollback_exact_bytes_pending_and_scheduler(self):
        self.host.path.write_bytes(b'{"saver":"", "wait_minutes":10}\n');state=self.provider.snapshot();self.provider.apply({'saver':'plus95-nature'});self.provider.restore(state)
        self.assertEqual(self.provider.snapshot(),state);self.assertEqual(self.host.scheduler,state[0])
    def test_rollback_absent_preferences(self):
        state=self.provider.snapshot();self.provider.apply({'saver':'plus95-nature'});self.provider.restore(state);self.assertFalse(self.host.path.exists())
    def test_export_is_actual_not_display_pending(self):self.assertEqual(self.provider.export_current(),{'saver':'','wait_minutes':10})
    def test_matches_optional_timeout(self):self.provider.apply({'saver':'plus95-nature'});self.assertTrue(self.provider.matches({'saver':'plus95-nature'}));self.assertFalse(self.provider.matches({'saver':'plus95-nature','wait_minutes':11}))
    def test_later_provider_failure_restores_saver(self):
        class Failure:
            def snapshot(self):return None
            def apply(self,value):raise ValueError('later failure')
            def restore(self,state):pass
        themes={'Test':{'screensaver':{'saver':'plus95-nature'},'icons':{}}};controller=ThemeController(themes,{'screensaver':self.provider,'icons':Failure()},self.root/'theme.json');controller.select('Test',('screensaver','icons'))
        with self.assertRaises(ValueError):controller.apply()
        self.assertEqual(self.host.scheduler.saver,'');self.assertFalse(self.host.path.exists())

    def test_targeted_original_reader_ignores_unrelated_legacy_bare_line(self):
        from win95lx.control_panel.theme_preferences import original_screensaver
        path=self.root/'Original.THM';path.write_text('[Other]\nav\n[boot]\nSCRNSAVE.EXE=%WinDir%System\\Science.scr')
        self.assertEqual(original_screensaver(path),{'saver':'plus95-science'})
    def test_targeted_original_reader_missing_association(self):
        from win95lx.control_panel.theme_preferences import original_screensaver
        path=self.root/'Original.THM';path.write_text('[Other]\nA=B')
        self.assertIsNone(original_screensaver(path))
    def test_custom_theme_roundtrip_includes_typed_saver(self):
        from win95lx.control_panel.theme_store import encode_theme,decode_theme
        from win95lx.control_panel.sound_preferences import SoundPreferences
        value={'wallpaper':{'file':'','mode':'center'},'pointers':{'scheme':'(None)','overrides':{}},'sounds':{'scheme':'Windows Default','events':dict(SoundPreferences().events)},'screensaver':{'saver':'plus95-nature','wait_minutes':23}}
        self.assertEqual(decode_theme(encode_theme('Owned',value))[1]['screensaver'],value['screensaver'])
    def test_custom_theme_rejects_command_as_identity(self):
        from win95lx.control_panel.theme_store import validate_definition
        from win95lx.control_panel.sound_preferences import SoundPreferences
        value={'wallpaper':{'file':'','mode':'center'},'pointers':{'scheme':'(None)','overrides':{}},'sounds':{'scheme':'Windows Default','events':dict(SoundPreferences().events)},'screensaver':{'saver':'wine evil.scr /s'}}
        with self.assertRaises(ValueError):validate_definition(value)

    def test_optional_unavailable_saver_omitted_on_default_selection(self):
        controller=ThemeController({'Custom':{'screensaver':{'saver':'plus95-nature'},'icons':{}}},{'icons':object()},self.root/'metadata.json')
        controller.select('Custom');self.assertEqual(controller.pending.components,('icons',))
    def test_optional_unavailable_saver_explicit_selection_rejected(self):
        controller=ThemeController({'Custom':{'screensaver':{'saver':'plus95-nature'},'icons':{}}},{'icons':object()},self.root/'metadata.json')
        with self.assertRaises(ValueError):controller.select('Custom',('screensaver',))

if __name__=='__main__':unittest.main()
