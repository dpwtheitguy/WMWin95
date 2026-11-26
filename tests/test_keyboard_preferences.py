import json,sys,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.keyboard_preferences import KeyboardPreferences,X11Keyboard
from win95lx.control_panel.preferences import PreferenceController

class Backend:
    def __init__(self):self.value=KeyboardPreferences();self.fail=False
    def preferences(self):return self.value
    def snapshot(self):return self.value
    def restore(self,value):self.value=value
    def apply(self,value):
        self.value=value
        if self.fail:raise RuntimeError('Device rejected settings')

class KeyboardTests(unittest.TestCase):
    def test_slider_ranges_and_clamped_keyboard_steps(self):
        p=KeyboardPreferences()
        for field,low,high in (('delay_ms',1000,250),('rate',1,32),('blink_ms',1200,200)):
            maximum=p.position(field)[1]
            self.assertEqual(getattr(p.slider(field,-5),field),low)
            self.assertEqual(getattr(p.slider(field,maximum+8),field),high)
        self.assertEqual(p.position('rate'),(15,31))
    def test_layouts_validate_duplicates_options_and_corrupt_values(self):
        for value in (replace(KeyboardPreferences(),layouts=()),replace(KeyboardPreferences(),layouts=('us','us'),variants=('','')),
                      replace(KeyboardPreferences(),rate=0),replace(KeyboardPreferences(),options='bad;command'),
                      replace(KeyboardPreferences(),layouts=('us',),variants=('',''))):
            with self.assertRaises(ValueError):value.validate()
    def test_apply_cancel_reopen_and_atomic_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'keyboard.json';backend=Backend();calls=[]
            c=PreferenceController(path,backend,KeyboardPreferences,calls.append)
            c.pending=replace(c.pending,rate=25,layouts=('us','gb'),variants=('',''),switch='alt_shift');c.apply()
            self.assertEqual(backend.value,c.applied);self.assertEqual(json.loads(path.read_text())['rate'],25)
            c.pending=replace(c.pending,rate=1);c.cancel();self.assertEqual(c.pending.rate,25)
            self.assertEqual(PreferenceController(path,backend,KeyboardPreferences).pending,c.applied)
    def test_backend_failure_rolls_back_without_saving(self):
        with tempfile.TemporaryDirectory() as d:
            backend=Backend();original=backend.value;backend.fail=True;path=Path(d)/'keyboard.json';c=PreferenceController(path,backend,KeyboardPreferences)
            c.pending=replace(original,rate=30)
            with self.assertRaises(RuntimeError):c.apply()
            self.assertEqual(backend.value,original);self.assertFalse(path.exists());self.assertEqual(c.applied,original)
    def test_save_failure_restores_backend_and_session(self):
        with tempfile.TemporaryDirectory() as d:
            backend=Backend();calls=[];c=PreferenceController(Path(d)/'prefs',backend,KeyboardPreferences,calls.append);old=c.applied;c.pending=replace(old,rate=24)
            with patch('win95lx.control_panel.preferences.save_preferences',side_effect=OSError('Full disk')):
                with self.assertRaises(OSError):c.apply()
            self.assertEqual(backend.value,old);self.assertEqual(calls[-1],old)
    def test_corrupt_saved_config_keeps_real_server_preferences(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'prefs';path.write_text('{broken');backend=Backend();backend.value=replace(backend.value,delay_ms=660,rate=70)
            self.assertEqual(PreferenceController(path,backend,KeyboardPreferences).applied,backend.value)
    def test_x11_read_preserves_existing_layout_options_model_and_repeat(self):
        def run(*args):
            return 'auto repeat: off\nauto repeat delay: 660 repeat rate: 70\n' if args[0]=='xset' else 'rules: evdev\nmodel: pc104\nlayout: us,de\nvariant: dvorak,\noptions: compose:ralt,grp:alt_shift_toggle\n'
        backend=X11Keyboard(run);p=backend.preferences()
        self.assertEqual((p.delay_ms,p.rate,p.layouts,p.variants,p.model),(660,70,('us','de'),('dvorak',''),'pc104'))
        self.assertEqual(backend.snapshot()[2]['_repeat_enabled'],'off')
    def test_x11_unrelated_edit_does_not_reconfigure_repeat_or_layout(self):
        calls=[]
        def run(*args):
            calls.append(args)
            return 'auto repeat: on\nauto repeat delay: 250 repeat rate: 16\n' if args[0]=='xset' else 'rules: evdev\nmodel: pc105\nlayout: us\n'
        backend=X11Keyboard(run);backend.apply(replace(backend.preferences(),blink_ms=700))
        self.assertTrue(all(args in (('xset','q'),('setxkbmap','-query')) for args in calls))

if __name__=='__main__':unittest.main()
