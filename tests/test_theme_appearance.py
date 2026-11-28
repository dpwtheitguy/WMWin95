import json
import struct
import tempfile
import unittest
import sys
from copy import deepcopy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.theme_appearance import *

class ThemeAppearanceTests(unittest.TestCase):
    def test_startup_bad_component_does_not_block_other_saved_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'theme-colors.json').write_text('invalid')
            (root/'theme-metrics.json').write_text(json.dumps(dict(DEFAULT_METRICS,caption_height=24)))
            runtime=Appearance()
            errors=load_session(root,root/'missing-font-library',runtime)
            self.assertEqual({key for key,_ in errors},{'font-library','colors'})
            self.assertEqual(runtime.color('ButtonFace'),(192,192,192))
            self.assertEqual(runtime.metric('caption_height'),24)
            self.assertEqual((root/'theme-colors.json').read_text(),'invalid')

    def test_startup_without_preferences_uses_original_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);runtime=Appearance()
            runtime.values['metrics']['caption_height']=30
            load_session(root,root/'missing-font-library',runtime)
            self.assertEqual(runtime.values,DEFAULTS)
            self.assertEqual(list(root.iterdir()),[])

    def test_color_exact_roles(self):
        self.assertEqual(validate_colors(DEFAULT_COLORS),DEFAULT_COLORS)
        v=deepcopy(DEFAULT_COLORS);v['extra']=[0,0,0]
        with self.assertRaises(ValueError):validate_colors(v)
    def test_color_boolean_not_integer(self):
        v=deepcopy(DEFAULT_COLORS);v['Window']=[True,0,0]
        with self.assertRaises(ValueError):validate_colors(v)
    def test_fonts_defaults_completed(self):
        value={role:dict(family='Arial',height=-12) for role in FONT_ROLES}
        self.assertEqual(validate_fonts(value)['menu']['weight'],400)
    def test_font_injection_rejected(self):
        value=deepcopy(DEFAULT_FONTS);value['menu']['family']='Arial\nOther'
        with self.assertRaises(ValueError):validate_fonts(value)
    def test_zero_height_rejected(self):
        value=deepcopy(DEFAULT_FONTS);value['menu']['height']=0
        with self.assertRaises(ValueError):validate_fonts(value)
    def test_metric_boolean_rejected(self):
        value=dict(DEFAULT_METRICS,caption_height=True)
        with self.assertRaises(ValueError):validate_metrics(value)
    def test_icon_spacing_limits(self):
        for v in (15,513):
            with self.assertRaises(ValueError):validate_metrics(dict(DEFAULT_METRICS,icon_spacing_x=v))
    def records(self):
        non=bytearray(340);icon=bytearray(76);struct.pack_into('<I',non,0,340);struct.pack_into('<I',icon,0,76)
        offsets=(4,8,12,16,20,84,88,152,156)
        for off,val in zip(offsets,(1,13,13,18,18,15,15,18,18)):struct.pack_into('<i',non,off,val)
        def font(data,off):
            struct.pack_into('<5i',data,off,-11,0,0,0,400);data[off+28:off+60]=b'Arial\0'+bytes([255])*26
        for off in (24,92,160,220,280):font(non,off)
        struct.pack_into('<3i',icon,4,75,75,1);font(icon,16)
        return non,icon
    def test_original_structure_tail_ignored(self):
        fonts,metrics=parse_metrics(*self.records());self.assertEqual(fonts['caption']['family'],'Arial');self.assertEqual(metrics,DEFAULT_METRICS)
    def test_truncated_original_structure_rejected(self):
        n,i=self.records()
        with self.assertRaises(ValueError):parse_metrics(n[:-1],i)
    def test_wrong_original_cbsize_rejected(self):
        n,i=self.records();struct.pack_into('<I',n,0,344)
        with self.assertRaises(ValueError):parse_metrics(n,i)
    def test_live_roles_separate_equal_baseline_rgb(self):
        r=Appearance();v=deepcopy(DEFAULT_COLORS);v['MenuText']=[0,128,0];r.update('colors',v)
        self.assertEqual(r.color('MenuText'),(0,128,0));self.assertEqual(r.color('ButtonText'),(0,0,0))
    def test_callback_failure_rolls_back_live_state(self):
        r=Appearance();r.listeners.append(lambda:(_ for _ in ()).throw(RuntimeError('redraw')))
        v=deepcopy(DEFAULT_COLORS);v['ButtonFace']=[128,200,128]
        with self.assertRaises(RuntimeError):r.update('colors',v)
        self.assertEqual(r.values,DEFAULTS)
    def test_provider_reopen_and_restore(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'colors.json';r=Appearance();p=AppearanceProvider('colors',path,r);old=p.snapshot()
            v=deepcopy(DEFAULT_COLORS);v['ActiveTitle']=[128,0,0];p.apply(v)
            new=Appearance();AppearanceProvider('colors',path,new).load();self.assertEqual(new.color('ActiveTitle'),(128,0,0))
            p.restore(old);self.assertFalse(path.exists());self.assertEqual(r.values,DEFAULTS)
    def test_failed_persistence_restores_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            obstruction=Path(temp)/'file';obstruction.write_text('x');r=Appearance();p=AppearanceProvider('metrics',obstruction/'state',r)
            with self.assertRaises(OSError):p.apply(dict(DEFAULT_METRICS,caption_height=24))
            self.assertEqual(r.values,DEFAULTS)
    def test_font_resolution_preflight_before_change(self):
        r=Appearance();v=deepcopy(DEFAULT_FONTS);v['menu']['family']='Absent'
        with self.assertRaises(ValueError):r.update('fonts',v)
        self.assertEqual(r.values,DEFAULTS)

if __name__=='__main__':unittest.main()
