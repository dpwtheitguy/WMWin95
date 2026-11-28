"""Distinct CRUD, current-state and rollback cases; not repeated preset counts."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.theme_store import ThemeStore, ThemeExistsError, ThemeChangedError, theme_name, encode_theme, decode_theme, validate_definition
from win95lx.control_panel.theme_preferences import ThemeController, WallpaperProvider, PointerThemeProvider, CurrentPreferenceProvider
from win95lx.control_panel.wallpaper import Wallpaper
from win95lx.control_panel.mouse_preferences import MousePreferences
from win95lx.control_panel.sound_preferences import SoundPreferences, SoundBackend, KEYS
from win95lx.control_panel.preferences import PreferenceController, save_preferences


def definition(path='',mode='center'):
    return {'wallpaper':{'file':path,'mode':mode,'pattern':'(None)','pattern_rows':[0]*8},
            'pointers':{'scheme':'(None)','overrides':{}},
            'sounds':{'scheme':'No Sounds','events':{key:''for key in KEYS}}}


class ThemeStoreCases(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.directory=self.root/'themes'
        self.media=self.root/'keep.bmp';self.media.write_bytes(b'original media')
        self.value=definition(str(self.media));self.builtin={'Factory':deepcopy(self.value)}
        self.store=ThemeStore(self.directory,self.builtin)

    def test_open_catalog_does_not_create_profile_files(self):
        self.assertEqual(self.store.names(),('Factory',));self.assertFalse(self.directory.exists())

    def test_save_is_readable_ini_with_exact_typed_roundtrip(self):
        self.store.save('My theme',self.value)
        raw=self.store.path_for('My theme').read_bytes()
        self.assertIn(b'[Control Panel\\Desktop]',raw)
        name,value=decode_theme(raw);self.assertEqual((name,value),('My theme',self.value))

    def test_reopen_recovers_custom_definition(self):
        self.store.save('Custom',self.value)
        reopened=ThemeStore(self.directory,self.builtin)
        self.assertEqual(reopened.catalog()['Custom'],self.value)

    def test_save_has_immutable_caller_snapshot(self):
        value=deepcopy(self.value);self.store.save('Snapshot',value);value['wallpaper']['mode']='tile'
        self.assertEqual(self.store.catalog()['Snapshot']['wallpaper']['mode'],'center')

    def test_catalog_return_cannot_mutate_store(self):
        self.store.save('Copy',self.value);catalog=self.store.catalog();catalog['Copy']['sounds']['events']['Close']='bad'
        self.assertEqual(self.store.catalog()['Copy'],self.value)

    def test_unicode_and_normalized_name_collision(self):
        self.store.save('Café',self.value)
        with self.assertRaises(ThemeExistsError):self.store.save('Cafe\u0301',self.value)
        self.assertEqual(self.store.names(),('Café','Factory'))

    def test_extension_and_whitespace_normalize_idempotently(self):
        name=self.store.save('  Custom.Theme.THEME  ',self.value)
        self.assertEqual(name,'Custom');self.assertTrue((self.directory/'Custom.theme').exists())
        self.assertEqual(theme_name(theme_name('Custom.Theme.Theme')),'Custom')

    def test_case_insensitive_overwrite_requires_confirmation(self):
        self.store.save('Mixed',self.value)
        with self.assertRaises(ThemeExistsError)as found:self.store.save('MIXED',definition())
        self.assertTrue(found.exception.token)
        self.assertEqual(self.store.catalog()['Mixed'],self.value)

    def test_confirmed_overwrite_preserves_existing_display_case(self):
        self.store.save('Mixed',self.value);token=self.store.token('mixed')
        self.assertEqual(self.store.save('MIXED',definition(),overwrite=True,expected=token),'Mixed')
        self.assertEqual(self.store.catalog()['Mixed'],definition());self.assertEqual(len(list(self.directory.glob('*.theme'))),1)

    def test_external_edit_invalidates_overwrite_confirmation(self):
        self.store.save('Changed',self.value);token=self.store.token('Changed')
        self.store.path_for('Changed').write_bytes(encode_theme('Changed',definition(mode='tile')))
        with self.assertRaises(ThemeChangedError):self.store.save('Changed',definition(),overwrite=True,expected=token)
        self.assertEqual(self.store.catalog()['Changed']['wallpaper']['mode'],'tile')

    def test_delete_only_definition_keeps_media_bytes(self):
        self.store.save('Delete me',self.value);self.store.delete('Delete me',expected=self.store.token('Delete me'))
        self.assertFalse(self.store.exists('Delete me'));self.assertEqual(self.media.read_bytes(),b'original media')

    def test_changed_definition_is_not_deleted(self):
        self.store.save('Changed',self.value);token=self.store.token('Changed')
        self.store.save('Changed',definition(),overwrite=True)
        with self.assertRaises(ThemeChangedError):self.store.delete('Changed',expected=token)
        self.assertTrue(self.store.exists('Changed'))

    def test_missing_definition_delete_is_explicit(self):
        with self.assertRaises(FileNotFoundError):self.store.delete('Missing')

    def test_delete_builtin_tombstones_without_mutating_source(self):
        original=deepcopy(self.builtin);self.store.delete('Factory')
        self.assertFalse(self.store.exists('Factory'));self.assertEqual(self.builtin,original)
        self.assertNotIn('Factory',ThemeStore(self.directory,self.builtin).catalog())

    def test_builtin_override_and_delete_do_not_resurrect_original(self):
        self.store.save('Factory',definition(),overwrite=True,expected=self.store.token('Factory'))
        self.assertTrue(self.store.is_custom('factory'));self.store.delete('Factory')
        self.assertFalse(self.store.exists('Factory'));self.assertEqual(self.builtin['Factory'],self.value)

    def test_deleted_builtin_name_can_be_saved_as_custom_again(self):
        self.store.delete('Factory');self.store.save('Factory',self.value)
        self.assertTrue(self.store.is_custom('Factory'));self.assertTrue(self.store.exists('Factory'))

    def test_invalid_names_write_no_definition(self):
        for name in ('','../Escape','C:\\bad','a/b','name.','Current Windows settings','CON','A\0B','x'*101):
            with self.subTest(name=name),self.assertRaises(ValueError):self.store.save(name,self.value)
        self.assertFalse(self.directory.exists())

    def test_failed_create_leaves_no_temp_or_definition(self):
        with patch('win95lx.control_panel.theme_store.os.link',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):self.store.save('No write',self.value)
        self.assertEqual(list(self.directory.glob('*.theme')),[]);self.assertEqual(list(self.directory.glob('.theme-*')),[])

    def test_failed_overwrite_keeps_previous_definition(self):
        self.store.save('Keep',self.value);old=self.store.path_for('Keep').read_bytes()
        with patch.object(Path,'replace',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):self.store.save('Keep',definition(),overwrite=True)
        self.assertEqual(self.store.path_for('Keep').read_bytes(),old)

    def test_commit_failure_rolls_back_new_definition(self):
        with self.assertRaisesRegex(RuntimeError,'metadata'):
            self.store.save('No metadata',self.value,commit=lambda _:(_ for _ in ()).throw(RuntimeError('metadata')))
        self.assertFalse(self.store.exists('No metadata'))

    def test_commit_failure_restores_overwritten_bytes(self):
        self.store.save('Keep',self.value);old=self.store.path_for('Keep').read_bytes()
        with self.assertRaises(RuntimeError):
            self.store.save('Keep',definition(),overwrite=True,commit=lambda _:(_ for _ in ()).throw(RuntimeError('metadata')))
        self.assertEqual(self.store.path_for('Keep').read_bytes(),old)

    def test_redirected_definition_never_overwrites_target(self):
        self.directory.mkdir();foreign=self.root/'foreign';foreign.write_text('precious')
        (self.directory/'Redirect.theme').symlink_to(foreign)
        with self.assertRaises(ValueError):self.store.save('Redirect',self.value,overwrite=True)
        self.assertEqual(foreign.read_text(),'precious')

    def test_redirected_catalog_folder_rejected(self):
        foreign=self.root/'foreign';foreign.mkdir();self.directory.symlink_to(foreign,target_is_directory=True)
        with self.assertRaises(ValueError):self.store.catalog()
        with self.assertRaises(ValueError):self.store.save('Bad',self.value)
        self.assertEqual(list(foreign.iterdir()),[])

    def test_malformed_definition_reported_without_executing_sections(self):
        self.directory.mkdir();(self.directory/'Broken.theme').write_text('[Shell]\nCommand=rm -rf something\n')
        self.assertEqual(self.store.names(),('Factory',));self.assertIn('Broken.theme',self.store.errors)
        with self.assertRaises(ValueError):self.store.save('Broken',self.value,overwrite=True)

    def test_case_duplicate_files_are_ambiguous_not_arbitrarily_loaded(self):
        self.directory.mkdir();(self.directory/'DUP.theme').write_bytes(encode_theme('DUP',self.value));(self.directory/'dup.Theme').write_bytes(encode_theme('dup',definition()))
        self.assertFalse(self.store.exists('dup'));self.assertEqual(len(self.store.errors),2)
        with self.assertRaises(ValueError):self.store.save('Dup',self.value,overwrite=True)

    def test_oversize_and_future_schema_rejected(self):
        with self.assertRaises(ValueError):decode_theme(b'x'*(256*1024+1))
        data=encode_theme('Valid',self.value).replace(b'Schema=1',b'Schema=2')
        with self.assertRaises(ValueError):decode_theme(data)

    def test_bad_component_payload_does_not_create_file(self):
        bad=deepcopy(self.value);bad['wallpaper']['pattern_rows']=[1]*7
        with self.assertRaises(ValueError):self.store.save('Bad',bad)
        bad=deepcopy(self.value);bad['sounds']['events']={'Unknown':''}
        with self.assertRaises(ValueError):self.store.save('Bad',bad)
        self.assertFalse(self.directory.exists())

    def test_empty_wallpaper_and_nonempty_pattern_round_trip(self):
        value=definition();value['wallpaper'].update(pattern='Custom',pattern_rows=[255,0]*4)
        self.store.save('Pattern only',value);self.assertEqual(self.store.catalog()['Pattern only'],value)

    def test_icon_paths_round_trip_without_copying_or_deleting_assets(self):
        value=deepcopy(self.value);value['icons']={'computer':{'large':str(self.media),'small':str(self.media)}}
        self.store.save('Icons',value);self.assertEqual(self.store.catalog()['Icons'],value);self.store.delete('Icons')
        self.assertTrue(self.media.exists())


    def test_external_save_changes_directory_scope_without_merging_builtins(self):
        external=self.root/'External';external.mkdir()
        self.store.save_path(external/'Outside.Theme',self.value)
        self.assertEqual(self.store.names(),('Outside',));self.assertFalse(self.store.is_default_directory)
        self.assertEqual(self.store.path_for('Outside'),external/'Outside.theme')
        self.assertEqual(ThemeStore(self.directory,self.builtin).names(),('Factory',))

    def test_external_folder_delete_keeps_all_assets_and_other_definitions(self):
        external=self.root/'External';external.mkdir()
        self.store.save_path(external/'One.theme',self.value);self.store.save('Two',definition())
        self.store.delete('One');self.assertEqual(self.store.names(),('Two',));self.assertTrue(self.media.exists())

    def test_switch_back_to_managed_folder_recovers_factory_catalog(self):
        external=self.root/'External';external.mkdir();self.store.save_path(external/'Other.theme',self.value)
        self.store.use_directory(self.store.default_directory);self.assertEqual(self.store.names(),('Factory',))

    def test_failed_external_save_does_not_change_catalog_scope(self):
        with self.assertRaises(ValueError):self.store.save_path(self.root/'missing'/'Bad.theme',self.value)
        self.assertTrue(self.store.is_default_directory);self.assertEqual(self.store.names(),('Factory',))

    def test_external_overwrite_token_addresses_target_folder(self):
        external=self.root/'External';external.mkdir()
        other=ThemeStore(external,{}) ;other.save('Saved',self.value)
        token=self.store.token_path(external/'Saved.theme');self.assertEqual(token,other.token('Saved'))
        self.store.save_path(external/'Saved.theme',definition(),overwrite=True,expected=token)
        self.assertEqual(self.store.catalog()['Saved'],definition())

    def test_foreign_exclusive_create_with_identical_bytes_is_never_removed(self):
        import os
        original=os.link
        def race(source,target):
            Path(target).write_bytes(encode_theme('Race',self.value));return original(source,target)
        with patch('win95lx.control_panel.theme_store.os.link',side_effect=race):
            with self.assertRaises(FileExistsError):self.store.save('Race',self.value)
        self.assertEqual(self.store.catalog()['Race'],self.value)

    def test_post_commit_fsync_failure_restores_previous_definition(self):
        self.store.save('Keep',self.value);old=self.store.path_for('Keep').read_bytes()
        with patch('win95lx.control_panel.theme_store.os.fsync',side_effect=[None,OSError('disk'),None,None]):
            with self.assertRaises(OSError):self.store.save('Keep',definition(),overwrite=True)
        self.assertEqual(self.store.path_for('Keep').read_bytes(),old)

    def test_concurrent_app_saves_have_one_winner_and_one_collision(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        barrier=threading.Barrier(2)
        def attempt(mode):
            barrier.wait()
            try:ThemeStore(self.directory,self.builtin).save('Concurrent',definition(mode=mode));return 'saved'
            except ThemeExistsError:return 'collision'
        with ThreadPoolExecutor(2)as pool:
            first=pool.submit(attempt,'center');second=pool.submit(attempt,'tile');results=[first.result(),second.result()]
        self.assertCountEqual(results,['saved','collision']);self.assertIn(self.store.catalog()['Concurrent']['wallpaper']['mode'],('center','tile'))


    def test_appearance_values_are_saved_as_canonical_semantic_data(self):
        from win95lx.control_panel.theme_appearance import DEFAULT_COLORS,DEFAULT_FONTS,DEFAULT_METRICS
        value=deepcopy(self.value);value.update(colors=deepcopy(DEFAULT_COLORS),fonts={role:{'family':font['family'],'height':font['height']}for role,font in DEFAULT_FONTS.items()},metrics=deepcopy(DEFAULT_METRICS))
        self.store.save('Appearance',value);saved=self.store.catalog()['Appearance']
        self.assertEqual(saved['fonts']['menu']['weight'],400);self.assertEqual(saved['fonts']['menu']['width'],0)
        self.assertEqual(saved['colors'],DEFAULT_COLORS);self.assertEqual(saved['metrics'],DEFAULT_METRICS)

    def test_invalid_appearance_is_rejected_before_creating_definition(self):
        from win95lx.control_panel.theme_appearance import DEFAULT_COLORS,DEFAULT_FONTS,DEFAULT_METRICS
        for component,mutate in [('colors',lambda v:v['Window'].__setitem__(0,True)),('fonts',lambda v:v['menu'].__setitem__('height',0)),('metrics',lambda v:v.__setitem__('scroll_width',0))]:
            value=deepcopy(self.value);value[component]=deepcopy({'colors':DEFAULT_COLORS,'fonts':DEFAULT_FONTS,'metrics':DEFAULT_METRICS}[component]);mutate(value[component])
            with self.subTest(component=component),self.assertRaises(ValueError):self.store.save('Invalid',value)
        self.assertFalse(self.directory.exists())


class ActualCurrentProviderCases(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.config=self.root/'config';self.config.mkdir();self.assets=self.root/'assets';self.assets.mkdir()
        self.wallfile=self.root/'wall.bmp';self.wallfile.write_bytes(b'picture')
        self.wave=self.root/'tone.wav'
        with wave.open(str(self.wave),'wb')as stream:stream.setparams((1,1,8000,0,'NONE','none'));stream.writeframes(b'\x80\x80')
        self.cur=self.root/'arrow.cur'
        dib=struct.pack('<IiiHHIIiiII',40,1,2,1,32,0,4,0,0,0,0)+b'\0\0\0\xff'+bytes(4)
        self.cur.write_bytes(struct.pack('<HHHBBBBHHII',0,2,1,1,1,0,0,0,0,len(dib),22)+dib)
        self.wall=Wallpaper(set(),self.config/'wallpaper.json');label=self.wall.register(self.wallfile);self.wall.apply(label,'tile','Custom',(128,64,32,16,8,4,2,1))
        self.mouse=[MousePreferences(True,650,8,'Windows Standard',{'arrow':str(self.cur)})];self.mouse[0].save(self.config/'mouse.json')
        self.backend=SoundBackend(self.assets);events={key:''for key in KEYS};events['MenuPopup']=str(self.wave)
        self.sound=SoundPreferences('',events,{'User custom':{key:''for key in KEYS}})
        self.backend.restore(self.sound);save_preferences(self.sound,self.config/'sounds.json')
        self.sound_controller=PreferenceController(self.config/'sounds.json',self.backend,SoundPreferences)
        self.refreshes=[]
        self.providers={'wallpaper':WallpaperProvider(self.wall,lambda:self.refreshes.append(self.wall.name),self.assets),
            'pointers':PointerThemeProvider(self.config/'mouse.json',lambda:self.mouse[0],lambda value:self.mouse.__setitem__(0,value),('(None)','Windows Standard')),
            'sounds':CurrentPreferenceProvider(self.sound_controller,lambda value,previous:replace(previous,scheme=value['scheme'],events=dict(value['events'])).validate())}
        self.factory={'Factory':definition()}
        self.store=ThemeStore(self.root/'themes',self.factory)
        self.controller=ThemeController(deepcopy(self.factory),self.providers,self.config/'theme.json').attach_store(self.store)

    def test_save_captures_actual_custom_settings_without_applying_pending_preset(self):
        self.controller.select('Factory');before={p.name:p.read_bytes()for p in self.config.iterdir()}
        self.controller.save_current('Actual')
        saved=self.store.catalog()['Actual']
        self.assertEqual(saved['wallpaper']['file'],str(self.wallfile));self.assertEqual(saved['wallpaper']['pattern_rows'],[128,64,32,16,8,4,2,1])
        self.assertEqual(saved['pointers']['overrides'],{'arrow':str(self.cur)});self.assertEqual(saved['sounds']['events']['MenuPopup'],str(self.wave))
        self.assertEqual({p.name:p.read_bytes()for p in self.config.iterdir()},before);self.assertEqual(self.refreshes,[])

    def test_save_selects_pending_definition_and_enables_apply_without_metadata(self):
        self.controller.save_current('Pending');self.assertEqual(self.controller.pending.name,'Pending');self.assertIsNone(self.controller.applied)
        self.assertTrue(self.controller.edited);self.assertFalse(self.controller.path.exists())

    def test_cancel_after_save_keeps_definition_and_original_desktop(self):
        before=self.mouse[0];self.controller.save_current('Keep file');self.controller.cancel()
        self.assertTrue(self.store.exists('Keep file'));self.assertIsNone(self.controller.pending);self.assertEqual(self.mouse[0],before)

    def test_custom_apply_restores_patterns_cursor_overrides_and_event_mapping(self):
        self.controller.save_current('Custom');original=self.controller.capture_current()
        self.wall.apply('(None)','center');self.mouse[0]=replace(self.mouse[0],scheme='(None)',overrides={});self.sound_controller.applied=SoundPreferences(scheme='No Sounds',events={key:''for key in KEYS})
        self.controller.select('Custom');self.controller.apply()
        self.assertEqual(self.controller.capture_current(),original);self.assertEqual(self.controller.applied.name,'Custom')

    def test_pointer_application_preserves_current_button_speed_doubleclick(self):
        self.controller.save_current('Pointers');self.mouse[0]=replace(self.mouse[0],left_handed=False,speed=2,double_click_ms=300)
        self.controller.select('Pointers',('pointers',));self.controller.apply()
        self.assertEqual((self.mouse[0].left_handed,self.mouse[0].speed,self.mouse[0].double_click_ms),(False,2,300));self.assertEqual(self.mouse[0].overrides,{'arrow':str(self.cur)})

    def test_sound_apply_keeps_new_unrelated_saved_scheme(self):
        self.controller.save_current('Sounds');updated=replace(self.sound,schemes={**self.sound.schemes,'Added later':dict(self.sound.events)});save_preferences(updated,self.config/'sounds.json')
        self.controller.select('Sounds',('sounds',));self.controller.apply()
        self.assertIn('Added later',self.sound_controller.applied.schemes)

    def test_deleted_media_causes_failed_apply_and_exact_preference_rollback(self):
        self.controller.save_current('Broken later');self.cur.unlink();before={p.name:p.read_bytes()for p in self.config.iterdir()}
        self.controller.select('Broken later')
        with self.assertRaises(OSError):self.controller.apply()
        self.assertEqual({p.name:p.read_bytes()for p in self.config.iterdir()},before)

    def test_invalid_cursor_bytes_fail_before_mouse_session_mutation(self):
        self.controller.save_current('Bad cursor');self.cur.write_bytes(b'not a cursor');before=self.mouse[0]
        self.controller.select('Bad cursor',('pointers',))
        with self.assertRaises(ValueError):self.controller.apply()
        self.assertEqual(self.mouse[0],before)

    def test_none_wallpaper_pattern_only_is_functional(self):
        self.wall.apply('(None)','center','Custom',(255,0)*4);self.controller.save_current('Pattern')
        self.wall.apply('(None)','tile','(None)',(0,)*8);self.controller.select('Pattern',('wallpaper',));self.controller.apply()
        self.assertEqual(self.wall.name,'(None)');self.assertEqual(self.wall.pattern_rows,(255,0)*4)

    def test_subsets_do_not_reset_unselected_pointer_or_sound_preferences(self):
        self.controller.save_current('Only wall');self.mouse[0]=replace(self.mouse[0],speed=1,overrides={})
        before=self.mouse[0];sounds=(self.config/'sounds.json').read_bytes()
        self.controller.select('Only wall',('wallpaper',));self.controller.apply()
        self.assertEqual(self.mouse[0],before);self.assertEqual((self.config/'sounds.json').read_bytes(),sounds)

    def test_delete_applied_definition_does_not_change_active_settings(self):
        self.controller.save_current('Delete active');self.controller.apply();before=self.controller.capture_current();media=self.wallfile.read_bytes();history=self.controller.path.read_bytes()
        self.controller.delete_theme('Delete active',expected=self.store.token('Delete active'))
        self.assertEqual(self.controller.capture_current(),before);self.assertIsNone(self.controller.pending);self.assertEqual(self.controller.path.read_bytes(),history);self.assertEqual(self.wallfile.read_bytes(),media)

    def test_reopen_can_restore_custom_selected_metadata(self):
        self.controller.save_current('Reopen');self.controller.apply()
        reopened=ThemeController(deepcopy(self.factory),self.providers,self.controller.path).attach_store(ThemeStore(self.store.directory,self.factory))
        self.assertEqual(reopened.applied.name,'Reopen');self.assertEqual(reopened.pending.name,'Reopen')

    def test_source_references_missing_after_save_do_not_delete_definition(self):
        self.controller.save_current('Missing wall');self.wallfile.unlink();self.controller.select('Missing wall',('wallpaper',))
        with self.assertRaises(ValueError):self.controller.apply()
        self.assertTrue(self.store.exists('Missing wall'))


    def test_save_external_then_cancel_reopens_default_folder(self):
        external=self.root/'Desktop';external.mkdir()
        self.controller.save_current(path=external/'External.Theme');self.assertEqual(tuple(self.controller.themes),('External',))
        self.controller.cancel();self.assertFalse(self.controller.path.exists());self.assertTrue((external/'External.theme').exists())
        reopened=ThemeController(deepcopy(self.factory),self.providers,self.controller.path).attach_store(ThemeStore(self.store.default_directory,self.factory))
        self.assertIn('Factory',reopened.themes);self.assertNotIn('External',reopened.themes)

    def test_external_applied_selection_reopens_from_explicit_directory(self):
        external=self.root/'Desktop';external.mkdir();self.controller.save_current(path=external/'External.theme');self.controller.apply()
        saved=json.loads(self.controller.path.read_text());self.assertEqual(saved['directory'],str(external))
        reopened=ThemeController(deepcopy(self.factory),self.providers,self.controller.path).attach_store(ThemeStore(self.store.default_directory,self.factory))
        self.assertEqual(reopened.pending.name,'External');self.assertEqual(tuple(reopened.themes),('External',))

    def test_failed_open_theme_keeps_current_scope_selection_and_desktop(self):
        self.controller.select('Factory');old=self.controller.pending;before=self.controller.capture_current()
        other=self.root/'Other';other.mkdir();bad=other/'Broken.theme';bad.write_text('bad')
        with self.assertRaises(ValueError):self.controller.open_theme(bad)
        self.assertEqual(self.controller.pending,old);self.assertTrue(self.store.is_default_directory);self.assertEqual(self.controller.capture_current(),before)


    def test_actual_appearance_providers_save_and_restore_custom_values(self):
        from win95lx.control_panel.theme_appearance import Appearance,AppearanceProvider
        runtime=Appearance();runtime.font_resolver=lambda record,fallback:record
        for component in ('colors','fonts','metrics'):self.providers[component]=AppearanceProvider(component,self.config/(component+'.json'),runtime)
        color=deepcopy(runtime.values['colors']);color['ActiveTitle']=[128,0,0];runtime.update('colors',color)
        fonts=deepcopy(runtime.values['fonts']);fonts['menu']['weight']=700;runtime.update('fonts',fonts)
        metrics=deepcopy(runtime.values['metrics']);metrics['icon_spacing_x']=90;runtime.update('metrics',metrics)
        self.controller.save_current('Complete');saved=self.controller.capture_current()
        color['ActiveTitle']=[0,0,128];runtime.update('colors',color);metrics['icon_spacing_x']=75;runtime.update('metrics',metrics)
        self.controller.select('Complete');self.controller.apply()
        self.assertEqual(self.controller.capture_current(),saved);self.assertEqual(runtime.values['fonts']['menu']['weight'],700)

    def test_late_appearance_failure_rolls_back_all_prior_components_and_files(self):
        from win95lx.control_panel.theme_appearance import Appearance,AppearanceProvider
        runtime=Appearance();runtime.font_resolver=lambda record,fallback:record
        for component in ('colors','fonts','metrics'):self.providers[component]=AppearanceProvider(component,self.config/(component+'.json'),runtime)
        self.controller.save_current('Rollback all');before=self.controller.capture_current();files={p.name:p.read_bytes()for p in self.config.iterdir()}
        provider=self.providers['metrics'];original=provider.apply
        def fail(value):original(value);raise RuntimeError('Late appearance failure')
        provider.apply=fail;self.controller.select('Rollback all')
        with self.assertRaisesRegex(RuntimeError,'Late appearance'):self.controller.apply()
        self.assertEqual(self.controller.capture_current(),before);self.assertEqual({p.name:p.read_bytes()for p in self.config.iterdir()},files)


    def test_external_applied_name_equal_to_builtin_uses_correct_directory(self):
        external=self.root/'Desktop';external.mkdir();self.controller.save_current(path=external/'Factory.theme');self.controller.apply()
        reopened=ThemeController(deepcopy(self.factory),self.providers,self.controller.path).attach_store(ThemeStore(self.store.default_directory,self.factory))
        self.assertFalse(reopened.store.is_default_directory);self.assertEqual(reopened.themes['Factory']['wallpaper']['file'],str(self.wallfile))

    def test_missing_persisted_external_definition_falls_back_to_default_catalog(self):
        external=self.root/'Desktop';external.mkdir();self.controller.save_current(path=external/'Gone.theme');self.controller.apply();(external/'Gone.theme').unlink()
        reopened=ThemeController(deepcopy(self.factory),self.providers,self.controller.path).attach_store(ThemeStore(self.store.default_directory,self.factory))
        self.assertTrue(reopened.store.is_default_directory);self.assertIn('Factory',reopened.themes);self.assertIsNone(reopened.pending)


    def test_failed_current_capture_creates_no_definition_or_preference_change(self):
        self.controller.select('Factory');pending=self.controller.pending;before={p.name:p.read_bytes()for p in self.config.iterdir()}
        self.providers['sounds'].export_current=lambda:(_ for _ in ()).throw(ValueError('Sound settings unreadable'))
        with self.assertRaisesRegex(ValueError,'unreadable'):self.controller.save_current('Not saved')
        self.assertEqual(self.controller.pending,pending);self.assertFalse(self.store.directory.exists());self.assertEqual({p.name:p.read_bytes()for p in self.config.iterdir()},before)

    def test_delete_confirmation_stale_token_preserves_selection_and_desktop(self):
        self.controller.save_current('Changed');self.controller.apply();token=self.store.token('Changed');pending=self.controller.pending;before=self.controller.capture_current()
        self.store.save('Changed',definition(),overwrite=True)
        with self.assertRaises(ThemeChangedError):self.controller.delete_theme('Changed',expected=token)
        self.assertEqual(self.controller.pending,pending);self.assertEqual(self.controller.capture_current(),before)


if __name__=='__main__':unittest.main()
