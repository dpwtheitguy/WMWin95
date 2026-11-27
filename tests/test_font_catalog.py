import json,os,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.font_catalog import FontCatalog,FontFace,Fontconfig,font_metadata,MAX_FONT_BYTES

class Scanner:
    def inventory(self):return ()
    def query(self,path):
        if not Path(path).read_bytes().startswith(b'valid-font'):raise ValueError('Invalid font')
        return (FontFace(Path(path),0,'Example','Regular','TrueType',65536),)
    def refresh(self):pass
    def visible(self,path):return True
class FontTests(unittest.TestCase):
    def setup_catalog(self,d,cache=None):return FontCatalog(root=Path(d)/'fonts',manifest=Path(d)/'config/fonts.json',home=d,scanner=Scanner(),cache=cache or (lambda:None))
    def source(self,d,name='example.ttf'):
        path=Path(d)/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'valid-font-data');return path
    def test_install_inventory_and_owned_removal(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d);faces=c.install(source);self.assertEqual(faces[0].label,'Example');self.assertEqual(len(c.inventory()),1)
            self.assertIsNone(c.removal_reason(faces[0].path));c.remove(faces[0].path);self.assertFalse(faces[0].path.exists());self.assertEqual(c.ledger(),{});self.assertTrue(source.exists())
    def test_invalid_font_never_installs_or_writes_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=Path(d)/'bad.ttf';source.write_bytes(b'not-font')
            with self.assertRaises(ValueError):c.install(source)
            self.assertFalse(c.manifest.exists());self.assertFalse((c.root/source.name).exists())
    def test_collision_preserves_original_and_install_record(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d);c.install(source);old=c.manifest.read_bytes();target=c.root/source.name;before=target.read_bytes()
            with self.assertRaises(FileExistsError):c.install(source)
            self.assertEqual(target.read_bytes(),before);self.assertEqual(c.manifest.read_bytes(),old)
    def test_cache_failure_rolls_back_install(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def fail():calls.append(1);raise RuntimeError('Cache failed')
            c=self.setup_catalog(d,fail);source=self.source(d)
            with self.assertRaises(RuntimeError):c.install(source)
            self.assertFalse((c.root/source.name).exists());self.assertFalse(c.manifest.exists());self.assertFalse(list(c.root.glob('.install-*')));self.assertEqual(len(calls),2)
    def test_ledger_failure_rolls_back_install(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d)
            with patch.object(c,'save_ledger',side_effect=OSError('Full disk')):
                with self.assertRaises(OSError):c.install(source)
            self.assertFalse((c.root/source.name).exists());self.assertTrue(source.exists())
    def test_remove_cache_failure_restores_font_and_record(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);installed=c.install(self.source(d))[0].path;before=c.manifest.read_bytes();content=installed.read_bytes()
            c.cache=lambda:(_ for _ in ()).throw(RuntimeError('Cache failed'))
            with self.assertRaises(RuntimeError):c.remove(installed)
            self.assertEqual(installed.read_bytes(),content);self.assertEqual(c.manifest.read_bytes(),before);self.assertFalse(list(c.root.glob('.remove-*')))
    def test_external_changed_unmanaged_and_system_files_are_read_only(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d);installed=c.install(source)[0].path;installed.write_bytes(b'valid-font-external-change')
            for target in (source,installed):
                with self.assertRaises(PermissionError):c.remove(target)
            self.assertTrue(source.exists());self.assertTrue(installed.exists())
    def test_symlink_source_root_target_and_outside_parent_rejected(self):
        with tempfile.TemporaryDirectory() as d,tempfile.TemporaryDirectory() as outside:
            c=self.setup_catalog(d);source=self.source(d);link=Path(d)/'link.ttf';link.symlink_to(source)
            with self.assertRaises(ValueError):c.install(link)
            c.root.mkdir();target=c.root/'foreign.ttf';target.symlink_to(source)
            with self.assertRaises(PermissionError):c.remove(target)
            target.unlink();c.root.rmdir();c.root.symlink_to(outside,target_is_directory=True)
            with self.assertRaises(ValueError):c.install(source)
    def test_nested_candidates_and_unmanaged_nested_inventory(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d,'source/nested/example.ttf');other=Path(d)/'source/no.txt';other.write_text('x')
            self.assertEqual(c.candidates(Path(d)/'source'),(source,));nested=self.source(d,'fonts/subfolder/manual.ttf');self.assertEqual(len(c.inventory()),1)
            with self.assertRaises(PermissionError):c.remove(nested)
    def test_copy_failure_leaves_no_partial_install(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d)
            with patch('win95lx.control_panel.font_catalog.shutil.copyfileobj',side_effect=OSError('Read error')):
                with self.assertRaises(OSError):c.install(source)
            self.assertFalse((c.root/source.name).exists());self.assertFalse(list(c.root.glob('.install-*')))
    def test_damaged_ledger_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);c.manifest.parent.mkdir();c.manifest.write_text('{bad');source=self.source(d)
            with self.assertRaises(ValueError):c.install(source)
            self.assertEqual(c.manifest.read_text(),'{bad')
    def test_large_file_is_rejected_before_scanning(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=Path(d)/'large.ttf'
            with source.open('wb') as f:f.truncate(MAX_FONT_BYTES+1)
            with self.assertRaisesRegex(ValueError,'too large'):c.install(source)
    def test_bounded_sfnt_metadata_and_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            value='Version 1.23'.encode('utf-16-be');names=struct.pack('>HHH',0,1,18)+struct.pack('>HHHHHH',3,1,0x409,5,len(value),0)+value
            data=b'\0\x01\0\0'+struct.pack('>HHHH',1,0,0,0)+b'name'+struct.pack('>III',0,28,len(names))+names;p=Path(d)/'meta.ttf';p.write_bytes(data)
            self.assertEqual(font_metadata(p)['version'],'Version 1.23');p.write_bytes(data[:-1]);self.assertEqual(font_metadata(p),{})
    def test_failed_install_keeps_a_concurrently_replaced_destination(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d)
            def cache():
                target=c.root/source.name;replacement=c.root/'replacement.tmp';replacement.write_bytes(b'user-new-data');os.replace(replacement,target);raise RuntimeError('Cache failed')
            c.cache=cache
            with self.assertRaises(RuntimeError):c.install(source)
            self.assertEqual((c.root/source.name).read_bytes(),b'user-new-data');self.assertFalse(c.manifest.exists())
    def test_remove_rollback_never_overwrites_new_file_at_original_name(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);target=c.install(self.source(d))[0].path
            def cache():target.write_bytes(b'new-user-file');raise RuntimeError('Cache failed')
            c.cache=cache
            with self.assertRaisesRegex(RuntimeError,'retained'):c.remove(target)
            self.assertEqual(target.read_bytes(),b'new-user-file');backups=list(c.root.glob('.remove-*'));self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_bytes(),b'valid-font-data')
    def test_recognized_but_unavailable_font_is_rolled_back(self):
        with tempfile.TemporaryDirectory() as d:
            c=self.setup_catalog(d);source=self.source(d)
            with patch.object(c.scanner,'visible',return_value=False):
                with self.assertRaisesRegex(ValueError,'not enabled'):c.install(source)
            self.assertFalse((c.root/source.name).exists());self.assertFalse(c.manifest.exists())
    def test_private_preview_config_does_not_replace_global_config(self):
        scanner=Fontconfig();font=scanner.inventory()[0].path;before=scanner.lib.FcConfigGetCurrent();config=scanner.preview_config([font])
        try:self.assertEqual(scanner.lib.FcConfigGetCurrent(),before);self.assertNotEqual(config,before)
        finally:scanner.destroy_config(config)
    def test_actual_fontconfig_inventory_and_invalid_query(self):
        scanner=Fontconfig();rows=scanner.inventory();self.assertTrue(rows);self.assertTrue(any(face.path.is_file() for face in rows));self.assertTrue(scanner.query(rows[0].path))
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.ttf';p.write_bytes(b'bad')
            with self.assertRaises(ValueError):scanner.query(p)

class LegacyFontPolicyTests(unittest.TestCase):
    def catalog(self,d,cache=None):return FontCatalog(root=Path(d)/'fonts',manifest=Path(d)/'config/fonts.json',home=d,scanner=Scanner(),cache=cache or (lambda:None))
    def test_bitmap_acceptance_is_per_owned_file_and_removed_after_delete(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'legacy.fon';source.write_bytes(b'valid-font-data');c=self.catalog(d);target=c.install(source)[0].path
            policy=c.bitmap_policy.path.read_text();self.assertIn(str(target),policy);self.assertNotIn('<glob>',policy)
            c.remove(target);self.assertNotIn(str(target),c.bitmap_policy.path.read_text())
    def test_bitmap_cache_failure_restores_policy_and_font_state(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'legacy.fon';source.write_bytes(b'valid-font-data');c=self.catalog(d,lambda:(_ for _ in ()).throw(RuntimeError('Cache failed')))
            with self.assertRaises(RuntimeError):c.install(source)
            self.assertFalse(c.bitmap_policy.path.exists());self.assertFalse((c.root/source.name).exists())
    def test_external_bitmap_policy_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'legacy.fon';source.write_bytes(b'valid-font-data');c=self.catalog(d);p=c.bitmap_policy.path;p.parent.mkdir(parents=True);p.write_bytes(b'user configuration')
            with self.assertRaises(PermissionError):c.install(source)
            self.assertEqual(p.read_bytes(),b'user configuration');self.assertFalse((c.root/source.name).exists())
    def test_filename_collision_matches_windows_case_rules(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'Example.ttf';source.write_bytes(b'valid-font-old');c=self.catalog(d);target=c.install(source)[0].path
            other=root/'example.TTF';other.write_bytes(b'valid-font-new')
            with self.assertRaises(FileExistsError):c.install(other)
            self.assertEqual(target.read_bytes(),b'valid-font-old')

class RealBitmapIsolationTests(unittest.TestCase):
    def test_same_family_external_bitmap_is_not_enabled_and_failures_restore_owned_policy(self):
        """Use a fresh Fontconfig process; never modify the desktop's config."""
        import subprocess
        project=Path(__file__).resolve().parents[1]
        source=project/'private/cabsets/windows95/sserife.fon'
        if not source.exists():self.skipTest('Private licensed bitmap reference is unavailable')
        code=r'''
import hashlib,json,os,shutil,subprocess
from pathlib import Path
from win95lx.control_panel.font_catalog import FontCatalog,Fontconfig
home=Path.home();fonts=home/'.local/share/fonts';unmanaged=fonts/'Unmanaged';unmanaged.mkdir(parents=True)
external=unmanaged/'external-same-family.fon';shutil.copyfile(SOURCE,external)
scanner=Fontconfig();assert scanner.query(external)[0].family=='MS Sans Serif'
assert not scanner.visible(external),'Reject rule did not establish the negative baseline'
c=FontCatalog(scanner=scanner);installed=c.install(Path(SOURCE))[0].path
assert scanner.visible(installed),'Owned bitmap is not enabled'
assert not scanner.visible(external),'Owned acceptance leaked to an external same-family bitmap'
listed=subprocess.check_output(['fc-list','--format','%{file}\n'],text=True)
assert str(installed) in listed and str(external) not in listed
before_policy=c.bitmap_policy.path.read_bytes();before_ledger=c.manifest.read_bytes();before_font=installed.read_bytes()
second=home/'other-name.fon';shutil.copyfile(SOURCE,second)
def fail():raise RuntimeError('Injected cache failure')
c.cache=fail
try:c.install(second)
except RuntimeError:pass
else:raise AssertionError('Injected install failure was ignored')
assert not (c.root/second.name).exists();assert c.bitmap_policy.path.read_bytes()==before_policy;assert c.manifest.read_bytes()==before_ledger
try:c.remove(installed)
except RuntimeError:pass
else:raise AssertionError('Injected removal failure was ignored')
assert installed.read_bytes()==before_font;assert c.bitmap_policy.path.read_bytes()==before_policy;assert c.manifest.read_bytes()==before_ledger
listed=subprocess.check_output(['fc-list','--format','%{file}\n'],text=True)
assert str(installed) in listed and str(external) not in listed
c.cache=c.update_cache;c.remove(installed);scanner.refresh()
assert not installed.exists() and not scanner.visible(external)
assert external.exists() and external.read_bytes()==Path(SOURCE).read_bytes()
print(json.dumps({'same_family_external_rejected':True,'owned_cross_process_visible':True,'install_and_remove_failure_policy_restored':True,'external_unchanged':True}))
'''.replace('SOURCE',repr(str(source)))
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory);config=home/'fontconfig.xml';conf=home/'.config/fontconfig/conf.d';conf.mkdir(parents=True)
            config.write_text('<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd"><fontconfig>'
                f'<dir>{home}/.local/share/fonts</dir><cachedir>{home}/.cache/fontconfig</cachedir>'
                '<selectfont><rejectfont><pattern><patelt name="scalable"><bool>false</bool></patelt></pattern></rejectfont></selectfont>'
                f'<include ignore_missing="yes">{conf}</include></fontconfig>')
            env={**os.environ,'HOME':str(home),'XDG_CONFIG_HOME':str(home/'.config'),'XDG_CACHE_HOME':str(home/'.cache'),'XDG_DATA_HOME':str(home/'.local/share'),'FONTCONFIG_FILE':str(config),'PYTHONPATH':str(project/'src')}
            result=subprocess.run([sys.executable,'-c',code],env=env,capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertTrue(json.loads(result.stdout)['same_family_external_rejected'])

if __name__=='__main__':unittest.main()
