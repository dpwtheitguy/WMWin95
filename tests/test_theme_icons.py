import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import cairo
from win95lx.control_panel.theme_icons import IconThemeProvider,apply_icons,load_icons,validate_icons

class IconTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.large=cairo.ImageSurface(cairo.FORMAT_ARGB32,32,32);self.small=cairo.ImageSurface(cairo.FORMAT_ARGB32,16,16)
        self.shell=SimpleNamespace(images={'computer':self.large,32:self.large,33:self.large,'network':self.large},small_images={'computer':self.small,32:self.small,33:self.small,'network':self.small})
        self.paths={}
        for size,kind in((32,'large'),(16,'small')):
            image=cairo.ImageSurface(cairo.FORMAT_ARGB32,size,size);cr=cairo.Context(image);cr.set_source_rgb(1,0,0);cr.paint();p=self.root/(kind+'.png');image.write_to_png(str(p));self.paths[kind]=str(p)
        self.value={'computer':dict(self.paths),'recycle-empty':dict(self.paths),'recycle-full':dict(self.paths),'network':dict(self.paths)}
        self.path=self.root/'theme-icons.json';self.provider=IconThemeProvider(self.shell,self.path)
    def test_apply_capture_and_load_original_art(self):
        self.provider.apply(self.value);self.assertEqual(self.provider.export_current(),self.value)
        self.assertIsNot(self.shell.images['computer'],self.large)
        loaded=json.loads(self.path.read_text());self.assertEqual(loaded['icons'],self.value)
        state=self.provider.export_current();state['computer']['large']='changed';self.assertEqual(self.provider.export_current(),self.value)
        load_icons(self.shell,self.path);self.assertEqual(self.provider.export_current(),self.value)
    def test_default_selection_restores_all_original_sizes(self):
        self.provider.apply(self.value);self.provider.apply({})
        self.assertIs(self.shell.images['computer'],self.large);self.assertIs(self.shell.small_images[32],self.small)
        self.assertNotIn('network-neighborhood',self.shell.images)
    def test_network_neighborhood_never_changes_network_cpl_icon(self):
        self.provider.apply(self.value)
        self.assertIs(self.shell.images['network'],self.large);self.assertIsNot(self.shell.images['network-neighborhood'],self.large)
    def test_recycle_full_empty_and_unselected_roles_are_independent(self):
        self.provider.apply({'recycle-full':self.paths})
        self.assertIs(self.shell.images[32],self.large);self.assertIsNot(self.shell.images[33],self.large)
        self.assertIs(self.shell.images['computer'],self.large)
    def test_restore_preserves_exact_prior_bytes(self):
        self.path.write_bytes(b'{"version":1,"icons":{}}\n\n');before=self.provider.snapshot()
        self.provider.apply(self.value);self.provider.restore(before)
        self.assertEqual(self.path.read_bytes(),b'{"version":1,"icons":{}}\n\n');self.assertIs(self.shell.images['computer'],self.large)
    def test_restore_absent_preferences_removes_new_file(self):
        before=self.provider.snapshot();self.provider.apply(self.value);self.provider.restore(before);self.assertFalse(self.path.exists())
    def test_invalid_role_or_pair_rejects_without_mutation(self):
        for value in({'unknown':self.paths},{'computer':{'large':self.paths['large']}},[],None):
            with self.assertRaises(ValueError):self.provider.apply(value)
            self.assertIs(self.shell.images['computer'],self.large);self.assertFalse(self.path.exists())
    def test_bad_size_and_missing_resource_reject_before_replacing_valid_icon(self):
        for large in(self.paths['small'],str(self.root/'missing.png')):
            with self.assertRaises(ValueError):self.provider.apply({'computer':{'large':large,'small':self.paths['small']}})
            self.assertIs(self.shell.images['computer'],self.large)
    def test_truncated_png_cannot_prevent_desktop_start(self):
        broken=self.root/'broken.png';broken.write_bytes(Path(self.paths['large']).read_bytes()[:24])
        self.path.write_text(json.dumps({'version':1,'icons':{'computer':{'large':str(broken),'small':self.paths['small']}}}))
        with patch('builtins.print'):load_icons(self.shell,self.path)
        self.assertIs(self.shell.images['computer'],self.large);self.assertTrue(self.path.exists())
    def test_malformed_saved_settings_keep_original_icons(self):
        for text in ('[]','null','{"version":2,"icons":{}}','{"version":1,"icons":{"computer":{}}}'):
            self.path.write_text(text)
            with patch('builtins.print'):load_icons(self.shell,self.path)
            self.assertIs(self.shell.images['computer'],self.large)
    def test_atomic_decode_failure_preserves_every_role(self):
        before=dict(self.shell.images)
        broken=self.root/'bad-crc.png';broken.write_bytes(Path(self.paths['large']).read_bytes()[:24])
        value={'computer':self.paths,'recycle-empty':{'large':str(broken),'small':self.paths['small']}}
        with self.assertRaises(cairo.Error):apply_icons(self.shell,value)
        self.assertEqual(self.shell.images,before)
    def test_readonly_capture_has_no_files_or_image_changes(self):
        self.assertEqual(self.provider.export_current(),{});self.assertFalse(self.path.exists());self.assertIs(self.shell.images['computer'],self.large)

if __name__=='__main__':unittest.main()
