"""No Wine/media execution: lifecycle boundaries exercised with fake children."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.screensaver_runtime import ScreenSaverCatalog, WineScreenSaverRuntime


class Child:
    def __init__(self):self.code=None;self.terminated=False;self.killed=False;self.timeout=False
    def poll(self):return self.code
    def terminate(self):self.terminated=True;self.code=0
    def kill(self):self.killed=True;self.code=-9
    def wait(self,timeout=None):
        if self.timeout and not self.killed:raise subprocess.TimeoutExpired('fake',timeout)
        return self.code


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.media=self.root/'media';(self.media/'nature').mkdir(parents=True)
        raw=b'MZfake-disposable-test';(self.media/'nature/Nature.scr').write_bytes(raw)
        self.document={'schema':1,'presentations':{'nature':{'label':'Nature','architecture':'win32','directory':'nature','executable':'Nature.scr','files':{'Nature.scr':hashlib.sha256(raw).hexdigest()},'modes':['fullscreen','configure','preview']}}}
        self.catalog=ScreenSaverCatalog(self.media,self.document);self.commands=[];self.children=[]
        self.runtime=WineScreenSaverRuntime(self.catalog,self.root/'state',run=self.run_fake,popen=self.spawn_fake,runner_version='fake1')
        self.addCleanup(self.runtime.close)
    def run_fake(self,command,**kwargs):self.commands.append((command,kwargs));return subprocess.CompletedProcess(command,0)
    def spawn_fake(self,command,**kwargs):
        self.commands.append((command,kwargs));child=Child();self.children.append(child);return child
    def prepare(self):self.runtime.prepare('nature')
    def test_prepare_is_explicit(self):
        with self.assertRaisesRegex(RuntimeError,'Prepare'):self.runtime.launch('nature')
        self.assertEqual(self.commands,[])
    def test_prepare_initializes_dedicated_architecture(self):
        self.prepare();command,kw=self.commands[0];self.assertEqual(command,['wineboot','-u']);self.assertEqual(kw['env']['WINEARCH'],'win32');self.assertEqual(kw['env']['WINEPREFIX'],str(self.runtime.prefix('nature')))
    def test_prepare_suppresses_optional_installers(self):
        self.prepare();self.assertEqual(self.commands[0][1]['env']['WINEDLLOVERRIDES'],'winemenubuilder.exe=d;mscoree,mshtml=')
    def test_ready_preserves_settings_without_reinitializing(self):
        self.prepare();registry=self.runtime.prefix('nature')/'user.reg';registry.write_text('custom');self.prepare();self.assertEqual(sum(c[0][0]=='wineboot'for c in self.commands),1);self.assertEqual(registry.read_text(),'custom')
    def test_fullscreen_argv_and_working_directory(self):
        self.prepare();self.runtime.launch('nature');command,kw=self.commands[-1];self.assertEqual(command[-1],'/s');self.assertEqual(Path(command[1]).name,'Nature.scr');self.assertTrue(kw['start_new_session']);self.assertNotIn('shell',kw)
    def test_configuration_argv(self):
        self.prepare();self.runtime.launch('nature','configure');self.assertEqual(self.commands[-1][0][-1],'/c')
    def test_preview_argv(self):
        self.prepare();self.runtime.launch('nature','preview',parent_hwnd=123456);self.assertEqual(self.commands[-1][0][-2:],['/p','123456'])
    def test_preview_rejects_nonhandle_inputs(self):
        self.prepare()
        for handle in (None,True,0,-1,'123',2**65):
            with self.subTest(handle=handle),self.assertRaises(ValueError):self.runtime.launch('nature','preview',parent_hwnd=handle)
    def test_nonpreview_parent_rejected(self):
        self.prepare()
        with self.assertRaises(ValueError):self.runtime.launch('nature',parent_hwnd=1)
    def test_unknown_mode_never_spawns(self):
        self.prepare()
        with self.assertRaises(ValueError):self.runtime.launch('nature','/s;echo surprise')
        self.assertEqual(self.children,[])
    def test_no_parallel_child(self):
        self.prepare();self.runtime.launch('nature')
        with self.assertRaises(RuntimeError):self.runtime.launch('nature')
    def test_stop_terminates_only_owned_prefix(self):
        self.prepare();child=self.runtime.launch('nature');self.runtime.stop();self.assertTrue(child.terminated);command,kw=self.commands[-1];self.assertEqual(command,['wineserver','-w']);self.assertEqual(kw['env']['WINEPREFIX'],str(self.runtime.prefix('nature')))
    def test_stop_idle_does_nothing(self):self.runtime.stop();self.assertEqual(self.commands,[])
    def test_normal_exit_still_cleans_owned_server(self):
        self.prepare();child=self.runtime.launch('nature');child.code=18;self.runtime.stop();self.assertFalse(child.terminated);self.assertEqual(self.commands[-1][0],['wineserver','-w'])
    def test_timeout_escalates(self):
        self.prepare();child=self.runtime.launch('nature');child.timeout=True;self.runtime.stop();self.assertTrue(child.killed)
    def test_close_blocks_future_launch_and_prepare(self):
        self.runtime.close()
        with self.assertRaises(RuntimeError):self.prepare()
        with self.assertRaises(RuntimeError):self.runtime.launch('nature')
    def test_runner_version_invalidates_marker(self):
        self.prepare();self.runtime.runner_version='fake2';self.assertFalse(self.runtime.ready('nature'))
    def test_failed_initialization_not_ready(self):
        self.runtime._run=lambda *a,**k:subprocess.CompletedProcess(a,1)
        with self.assertRaises(RuntimeError):self.prepare()
        self.assertFalse(self.runtime.ready('nature'))
    def test_initialization_timeout_not_ready(self):
        self.runtime._run=lambda *a,**k:(_ for _ in ()).throw(subprocess.TimeoutExpired('fake',90))
        with self.assertRaises(subprocess.TimeoutExpired):self.prepare()
        self.assertFalse(self.runtime.ready('nature'))
    def test_spawn_failure_releases_lease(self):
        self.prepare();self.runtime._popen=lambda *a,**k:(_ for _ in ()).throw(OSError('fake spawn failure'))
        with self.assertRaises(OSError):self.runtime.launch('nature')
        self.runtime._popen=self.spawn_fake;self.runtime.launch('nature')
    def test_cross_instance_same_prefix_exclusive(self):
        self.prepare();self.runtime.launch('nature');other=WineScreenSaverRuntime(self.catalog,self.root/'state',run=self.run_fake,popen=self.spawn_fake,runner_version='fake1')
        with self.assertRaisesRegex(RuntimeError,'already in use'):other.launch('nature')
        self.runtime.stop();other.launch('nature');other.close()
    def test_different_namespaces_stop_independently(self):
        self.prepare();first=self.runtime.launch('nature');other=WineScreenSaverRuntime(self.catalog,self.root/'other-state',run=self.run_fake,popen=self.spawn_fake)
        other.prepare('nature');second=other.launch('nature');other.stop();self.assertIsNone(first.poll());self.assertIsNotNone(second.poll());other.close()
    def test_source_tampering_rejected(self):
        self.prepare();(self.media/'nature/Nature.scr').write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.runtime.launch('nature')
    def test_prepared_tampering_rejected(self):
        self.prepare();(self.runtime.prefix('nature')/'drive_c/Win95LX/Saver/Nature.scr').write_bytes(b'tampered')
        with self.assertRaises(ValueError):self.runtime.launch('nature')
    def test_missing_source_rejected(self):
        (self.media/'nature/Nature.scr').unlink()
        with self.assertRaises(ValueError):self.prepare()
    def test_symlink_source_rejected(self):
        path=self.media/'nature/Nature.scr';raw=path.read_bytes();path.unlink();(self.root/'outside').write_bytes(raw);path.symlink_to(self.root/'outside')
        with self.assertRaises(ValueError):self.prepare()
    def test_symlink_state_rejected(self):
        actual=self.root/'actual';actual.mkdir();(self.root/'state').symlink_to(actual,target_is_directory=True)
        with self.assertRaises(ValueError):self.prepare()
    def test_catalog_identity_traversal(self):
        for identity in ('../escape','.','..'):
            doc=copy.deepcopy(self.document);doc['presentations'][identity]=doc['presentations'].pop('nature')
            with self.subTest(identity=identity),self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)
    def test_catalog_path_traversal(self):
        for value in ('../bad','/bad','a/../bad','a\\bad','a//bad'):
            doc=copy.deepcopy(self.document);doc['presentations']['nature']['directory']=value
            with self.subTest(value=value),self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)
    def test_case_collision_rejected(self):
        doc=copy.deepcopy(self.document);doc['presentations']['nature']['files']['nature.SCR']='0'*64
        with self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)
    def test_unknown_architecture_rejected(self):
        doc=copy.deepcopy(self.document);doc['presentations']['nature']['architecture']='win64'
        with self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)
    def test_catalog_data_is_copy(self):
        row=self.catalog.resolve('nature');row['files'].clear();self.catalog.validate('nature')
    def test_catalog_file_roundtrip(self):
        path=self.media/'catalog.json';path.write_text(json.dumps(self.document));self.assertEqual(ScreenSaverCatalog.load(path).resolve('nature'),self.catalog.resolve('nature'))
    def test_missing_wine_unavailable(self):
        with patch('shutil.which',return_value=None):self.assertFalse(self.runtime.availability('nature')[0])
    def test_supported_wine_available(self):
        with patch('shutil.which',return_value='/fake/wine'):self.assertEqual(self.runtime.availability('nature'),(True,''))
    def test_unknown_saver_unavailable(self):self.assertFalse(self.runtime.availability('missing')[0])
    def test_disabled_mode_unavailable(self):
        self.catalog.presentations['nature']['modes']=['configure'];self.assertFalse(self.runtime.availability('nature','fullscreen')[0])


class StagerTests(unittest.TestCase):
    def setUp(self):
        import importlib.util
        tool=Path(__file__).resolve().parents[1]/'tools/stage_screensaver_assets.py'
        spec=importlib.util.spec_from_file_location('screensaver_stager_test',tool);self.stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.stage)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.classic=self.root/'classic';self.plus=self.root/'plus';self.classic.mkdir();self.plus.mkdir()
        import struct
        raw=bytearray(128);raw[:2]=b'MZ';struct.pack_into('<I',raw,60,64);raw[64:68]=b'PE\0\0';struct.pack_into('<H',raw,68,0x14c);struct.pack_into('<H',raw,88,0x10b)
        for stem in self.stage.CLASSIC:(self.classic/(stem+'.scr')).write_bytes(raw)
        for name in ['WL32SCR.EXE','WL32DLL.DLL','WILDLB32.DLL','BLOCKS.SCR','LENS.SCR']+[pair[1]for pair in self.stage.PLUS.values()]:(self.plus/name).write_bytes(raw)
        font=bytearray(raw);font[64:68]=b'NE\0\0'
        for name in ('sserife.fon','vgasys.fon'):(self.classic/name).write_bytes(font)
        self.output=self.root/'output'
    def build(self):return self.stage.stage_bundle(self.output,self.classic,self.plus)
    def test_exact_22_presentations(self):self.assertEqual(len(self.build()['presentations']),22)
    def test_nature_dependency_aliases(self):
        row=self.build()['presentations']['plus95-nature'];self.assertEqual(set(row['files']),{'Nature.scr','Nature.dll','WL32DLL.DLL','WILDLB32.DLL'})
    def test_lens_two_aliases_same_bytes(self):
        doc=self.build()['presentations'];self.assertEqual(doc['plus95-science']['files']['Science.scr'],doc['plus95-sixties']['files']["The 60's USA.scr"])
    def test_staged_catalog_validates_every_file(self):
        self.build();catalog=ScreenSaverCatalog.load(self.output/'catalog.json')
        for identity in catalog.presentations:catalog.validate(identity)
    def test_repeat_rebuild_allowed(self):self.build();self.build();self.assertTrue((self.output/'catalog.json').is_file())
    def test_unknown_output_preserved(self):
        self.output.mkdir();(self.output/'personal').write_text('keep')
        with self.assertRaises(ValueError):self.build()
        self.assertEqual((self.output/'personal').read_text(),'keep')
    def test_failed_rebuild_preserves_previous(self):
        self.build();original=(self.output/'catalog.json').read_bytes();(self.plus/'WL32DLL.DLL').unlink()
        with self.assertRaises(FileNotFoundError):self.build()
        self.assertEqual((self.output/'catalog.json').read_bytes(),original)
    def test_nonpe_dependency_rejected(self):
        (self.plus/'WL32DLL.DLL').write_bytes(b'MZnot-real')
        with self.assertRaises(ValueError):self.build()
        self.assertFalse(self.output.exists())
    def test_wrong_architecture_rejected(self):
        import struct
        path=self.plus/'WL32DLL.DLL';raw=bytearray(path.read_bytes());struct.pack_into('<H',raw,68,0x8664);path.write_bytes(raw)
        with self.assertRaises(ValueError):self.build()
    def test_staging_does_not_execute(self):
        with patch('subprocess.run',side_effect=AssertionError('Must not execute')),patch('subprocess.Popen',side_effect=AssertionError('Must not execute')):self.build()
    def test_case_aliases_remain_original(self):
        self.build();self.assertTrue((self.output/'plus95-dangerous/Dangerous Creatures.dll').exists());self.assertTrue((self.output/'plus95-sixties'/"The 60's USA.scr").exists())
    def test_mode_status_does_not_claim_full_acceptance(self):
        row=self.build()['presentations']['win95-ssmaze'];self.assertEqual(row['mode_status']['preview'],'unverified')

    def test_font_profile_is_hashed_separate_ne_assets(self):
        doc=self.build();profile=doc['font_profiles']['classic95'];self.assertEqual(set(profile['files']),{'sserife.fon','vgasys.fon'});self.assertEqual(doc['runtime_groups']['trusted95']['trust'],'builtin95')
        for row in doc['presentations'].values():self.assertEqual(row['runtime_group'],'trusted95');self.assertNotIn('sserife.fon',row['files'])
    def test_failed_font_rebuild_preserves_previous_and_cleans_temporary(self):
        self.build();before=(self.output/'catalog.json').read_bytes();(self.classic/'sserife.fon').write_bytes(b'bad')
        with self.assertRaises(ValueError):self.build()
        self.assertEqual((self.output/'catalog.json').read_bytes(),before);self.assertFalse(list(self.root.glob('.screensavers-*')))
    def test_linked_font_source_rejected(self):
        path=self.classic/'sserife.fon';path.unlink();path.symlink_to(self.classic/'vgasys.fon')
        with self.assertRaises(ValueError):self.build()
        self.assertFalse(self.output.exists())


class SharedGroupTests(unittest.TestCase):
    run_fake=RuntimeTests.run_fake
    spawn_fake=RuntimeTests.spawn_fake
    def setUp(self):
        RuntimeTests.setUp(self)
        from win95lx.control_panel.theme_appearance import DEFAULT_COLORS
        import struct
        fonts=self.media/'font-profiles/classic95';fonts.mkdir(parents=True)
        raw=bytearray(128);raw[:2]=b'MZ';struct.pack_into('<I',raw,60,64);raw[64:66]=b'NE'
        for name in('sserife.fon','vgasys.fon'):(fonts/name).write_bytes(raw)
        self.document['runtime_groups']={'trusted95':{'trust':'builtin95','profile':'classic95'}}
        self.document['font_profiles']={'classic95':{'directory':'font-profiles/classic95','files':{name:hashlib.sha256(raw).hexdigest()for name in('sserife.fon','vgasys.fon')},'recipe':1,'colors':copy.deepcopy(DEFAULT_COLORS)}}
        row=self.document['presentations']['nature'];row.update(product='Plus95',runtime_group='trusted95')
        travel=copy.deepcopy(row);travel.update(label='Travel',directory='travel',executable='Travel.scr',files={'Travel.scr':next(iter(row['files'].values()))})
        (self.media/'travel').mkdir();(self.media/'travel/Travel.scr').write_bytes((self.media/'nature/Nature.scr').read_bytes());self.document['presentations']['travel']=travel
        self.catalog=ScreenSaverCatalog(self.media,self.document);self.registry=[]
        self.runtime=WineScreenSaverRuntime(self.catalog,self.root/'state',run=self.group_run,popen=self.spawn_fake,runner_version='group1');self.addCleanup(self.runtime.close)
    def group_run(self,command,**kwargs):
        if len(command)>2 and command[1:3]==['regedit','/S']:self.registry.append(Path(command[3]).read_text(encoding='utf-16'))
        return self.run_fake(command,**kwargs)
    def other(self):return WineScreenSaverRuntime(self.catalog,self.root/'state',run=self.group_run,popen=self.spawn_fake,runner_version='group1')
    def prepare_both(self):self.runtime.prepare('nature');self.runtime.prepare('travel')
    def test_two_presentations_share_one_prefix(self):self.assertEqual(self.runtime.prefix('nature'),self.runtime.prefix('travel'))
    def test_baseline_initializes_only_once(self):
        self.prepare_both();self.assertEqual(sum(c[0][0]=='wineboot'for c in self.commands),1);self.assertEqual(len(self.registry),1)
    def test_fonts_are_separate_from_presentation_pe_files(self):
        self.prepare_both();self.assertNotIn('sserife.fon',self.catalog.resolve('nature')['files']);self.assertTrue((self.runtime.prefix('nature')/'drive_c/windows/Fonts/sserife.fon').is_file())
    def test_registry_recipe_uses_original_bitmap_logical_mapping(self):
        self.runtime.prepare('nature');text=self.registry[0];self.assertIn('"MS Shell Dlg"="MS Sans Serif"',text);self.assertIn('"ButtonFace"="192 192 192"',text);self.assertNotIn('Screen Savers',text)
    def test_package_folders_keep_original_basenames(self):
        self.prepare_both();prefix=self.runtime.prefix('nature');self.assertTrue((prefix/'drive_c/Win95LX/Savers/nature/Nature.scr').exists());self.assertTrue((prefix/'drive_c/Win95LX/Savers/travel/Travel.scr').exists())
    def test_warm_prepare_preserves_shared_user_registry(self):
        self.runtime.prepare('nature');reg=self.runtime.prefix('nature')/'user.reg';reg.write_text('shared native settings');self.runtime.prepare('travel');self.assertEqual(reg.read_text(),'shared native settings');self.assertEqual(sum(c[0][0]=='wineboot'for c in self.commands),1)
    def test_legacy_identity_prefix_untouched_by_migration(self):
        legacy=self.root/'state/nature/prefix';legacy.mkdir(parents=True);(legacy/'user.reg').write_text('legacy keep');self.prepare_both();self.assertEqual((legacy/'user.reg').read_text(),'legacy keep');self.assertNotEqual(legacy,self.runtime.prefix('nature'))
    def test_other_presentation_cannot_launch_into_owned_group(self):
        self.prepare_both();child=self.runtime.launch('nature');other=self.other()
        try:
            with self.assertRaisesRegex(RuntimeError,'already in use'):other.launch('travel')
            other.stop();self.assertIsNone(child.poll())
        finally:other.close()
    def test_warm_ready_prepare_is_noop_during_other_owner(self):
        self.prepare_both();child=self.runtime.launch('nature');other=self.other();count=len(self.commands)
        try:other.prepare('travel');self.assertEqual(len(self.commands),count);self.assertIsNone(child.poll())
        finally:other.close()
    def test_cold_package_prepare_never_kills_other_owner(self):
        self.runtime.prepare('nature');child=self.runtime.launch('nature');other=self.other();count=len(self.commands)
        try:
            with self.assertRaisesRegex(RuntimeError,'already in use'):other.prepare('travel')
            self.assertEqual(len(self.commands),count);self.assertIsNone(child.poll())
        finally:other.close()
    def test_second_owner_after_release_uses_shared_prefix(self):
        self.prepare_both();self.runtime.launch('nature');self.runtime.stop();other=self.other()
        try:other.launch('travel');self.assertEqual(self.commands[-1][1]['env']['WINEPREFIX'],str(self.runtime.prefix('nature')))
        finally:other.close()
    def test_cleanup_failure_retains_group_lease_until_retry(self):
        self.prepare_both();self.runtime.launch('nature');old=self.runtime._run;self.runtime._run=lambda *a,**k:subprocess.CompletedProcess(a,1)
        try:
            with self.assertRaises(RuntimeError):self.runtime.stop()
            other=self.other()
            try:
                with self.assertRaisesRegex(RuntimeError,'already in use'):other.launch('travel')
            finally:other.close()
        finally:self.runtime._run=old;self.runtime.stop()
    def test_profile_change_invalidates_all_package_markers(self):
        self.prepare_both();self.catalog.profiles['classic95']['colors']['ButtonFace'][0]=180;self.assertFalse(self.runtime.ready('nature'));self.assertFalse(self.runtime.ready('travel'))
    def test_missing_installed_font_invalidates_baseline(self):
        self.prepare_both();font=self.runtime.prefix('nature')/'drive_c/windows/Fonts/sserife.fon';font.unlink();self.assertFalse(self.runtime.ready('nature'));self.runtime.prepare('nature');self.assertTrue(self.runtime.ready('nature'))
    def test_changed_source_font_rejected_before_wine(self):
        (self.media/'font-profiles/classic95/sserife.fon').write_bytes(b'bad')
        with self.assertRaises(ValueError):self.runtime.prepare('nature')
        self.assertEqual(self.commands,[])
    def test_linked_prefix_font_rejected(self):
        self.prepare_both();font=self.runtime.prefix('nature')/'drive_c/windows/Fonts/sserife.fon';font.unlink();font.symlink_to(self.media/'font-profiles/classic95/sserife.fon');self.assertFalse(self.runtime.ready('nature'))
        with self.assertRaises(ValueError):self.runtime.prepare('nature')
    def test_third_party_cannot_claim_original_runtime_group(self):
        doc=copy.deepcopy(self.document);doc['presentations']['nature']['product']='ThirdParty'
        with self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)
    def test_missing_profile_rejected(self):
        doc=copy.deepcopy(self.document);doc['font_profiles'].clear()
        with self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)
    def test_wrong_font_container_rejected(self):
        file=self.media/'font-profiles/classic95/sserife.fon';raw=bytearray(file.read_bytes());raw[64:66]=b'PE';file.write_bytes(raw);self.catalog.profiles['classic95']['files']['sserife.fon']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(ValueError):self.runtime.prepare('nature')
    def test_color_profile_injection_rejected(self):
        doc=copy.deepcopy(self.document);doc['font_profiles']['classic95']['colors']['ButtonFace']=[999,0,0]
        with self.assertRaises(ValueError):ScreenSaverCatalog(self.media,doc)


    def test_preparation_never_inherits_interactive_display(self):
        with patch.dict('os.environ',{'DISPLAY':':88','WAYLAND_DISPLAY':'wayland-test'}):
            self.runtime.prepare('nature')
            for command,kwargs in self.commands:
                if command[0]=='wineboot'or command[1:3]==['regedit','/S']:
                    self.assertNotIn('DISPLAY',kwargs['env']);self.assertNotIn('WAYLAND_DISPLAY',kwargs['env'])
            self.assertEqual(self.runtime.environment('nature')['DISPLAY'],':88')
    def test_quiet_guard_is_part_of_readiness(self):
        self.runtime.prepare('nature');stamp=self.runtime.prefix('nature')/'.update-timestamp';self.assertEqual(stamp.read_text(),'disable\n');stamp.unlink();self.assertFalse(self.runtime.ready('nature'));self.runtime.prepare('nature');self.assertTrue(self.runtime.ready('nature'))
    def test_bad_quiet_guard_is_repaired_not_unicode_crash(self):
        self.runtime.prepare('nature');stamp=self.runtime.prefix('nature')/'.update-timestamp';stamp.write_bytes(b'\xff');self.assertFalse(self.runtime.ready('nature'));self.runtime.prepare('nature');self.assertEqual(stamp.read_text(),'disable\n')
    def test_linked_update_guard_rejected_before_wineboot(self):
        prefix=self.runtime.prefix('nature');prefix.mkdir(parents=True);outside=self.root/'outside';outside.write_text('keep');(prefix/'.update-timestamp').symlink_to(outside)
        with self.assertRaises(ValueError):self.runtime.prepare('nature')
        self.assertEqual(self.commands,[]);self.assertEqual(outside.read_text(),'keep')
    def test_hardlinked_update_guard_rejected_before_wineboot(self):
        import os
        prefix=self.runtime.prefix('nature');prefix.mkdir(parents=True);outside=self.root/'outside';outside.write_text('keep');os.link(outside,prefix/'.update-timestamp')
        with self.assertRaises(ValueError):self.runtime.prepare('nature')
        self.assertEqual(self.commands,[]);self.assertEqual(outside.read_text(),'keep')
    def test_wine_inf_update_invalidates_prepared_group(self):
        binary=self.root/'bin/wine';binary.parent.mkdir();binary.write_text('fake');inf=self.root/'share/wine/wine.inf';inf.parent.mkdir(parents=True);inf.write_text('old')
        with patch('shutil.which',return_value=str(binary)):
            self.runtime.prepare('nature');self.assertTrue(self.runtime.ready('nature'));inf.write_text('new-system-update');self.assertFalse(self.runtime.ready('nature'))


if __name__=='__main__':unittest.main()
