import io,json,struct,sys,tempfile,unittest,wave
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.sound_preferences import SoundPreferences,SoundBackend,DEFAULT,KEYS,wave_details
from win95lx.control_panel.preferences import PreferenceController
from win95lx.sound import SoundPlayer,play_event,notify,play_startup

def wav(path):
    with wave.open(str(path),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(bytes(1600))
class SoundTests(unittest.TestCase):
    def test_original_default_event_mapping_and_silent_menu_clicks(self):
        p=SoundPreferences().validate();self.assertEqual(set(p.events),KEYS)
        self.assertEqual(p.events['SystemStart'],'sound-mssound.wav')
        self.assertEqual(p.events['SystemExit'],'sound-tada.wav')
        self.assertEqual(p.events['MenuPopup'],'');self.assertEqual(p.events['MenuCommand'],'')
    def test_no_sounds_clears_every_event(self):self.assertTrue(all(not v for v in SoundPreferences().select('No Sounds').events.values()))
    def test_custom_save_switch_delete_preserves_other_schemes(self):
        p=SoundPreferences().assign('MenuPopup','sound-ding.wav').save_scheme('Clicks')
        p=p.select('No Sounds').save_scheme('Quiet').select('Clicks')
        self.assertEqual(p.events['MenuPopup'],'sound-ding.wav')
        p=p.delete_scheme('Clicks');self.assertNotIn('Clicks',p.schemes);self.assertIn('Quiet',p.schemes)
        with self.assertRaises(ValueError):p.delete_scheme('Windows Default')
    def test_invalid_events_names_paths_and_corrupt_config(self):
        for p in (replace(SoundPreferences(),schemes=[]),replace(SoundPreferences(),events={}),replace(SoundPreferences(),schemes={'No Sounds':dict(DEFAULT)})):
            with self.assertRaises(ValueError):p.validate()
        for value in ('../ding.wav','sound-../../etc/x.wav','bad\0.wav'):
            with self.assertRaises(ValueError):SoundPreferences().assign('SystemStart',value)
        with self.assertRaises(ValueError):SoundPreferences().assign('NoSuchEvent','sound-ding.wav')
        with self.assertRaises(ValueError):SoundPreferences().save_scheme('  ')
    def test_wave_metadata_and_truncation(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';wav(p);info=wave_details(p);self.assertEqual(info['sample_rate'],8000);self.assertAlmostEqual(info['duration'],.1)
            bits=p.read_bytes()
            for end in (0,11,20,len(bits)-1):
                p.write_bytes(bits[:end])
                with self.assertRaises(ValueError):wave_details(p)
    def test_wave_odd_unknown_chunk_and_malformed_format(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.wav';wav(p);bits=p.read_bytes();new=bits[:12]+b'JUNK'+struct.pack('<I',1)+b'X\0'+bits[12:];new=new[:4]+struct.pack('<I',len(new)-8)+new[8:];p.write_bytes(new)
            self.assertEqual(wave_details(p)['bits'],16)
            damaged=bytearray(new);damaged[30:34]=b'\xff'*4;p.write_bytes(damaged)
            with self.assertRaises(ValueError):wave_details(p)
    def test_apply_cancel_reopen_and_failed_validation_preserve_applied(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);path=root/'sounds.json';backend=SoundBackend(root);c=PreferenceController(path,backend,SoundPreferences)
            c.pending=c.pending.select('No Sounds');c.apply();c.pending=c.pending.assign('SystemStart','sound-missing.wav')
            with self.assertRaises(FileNotFoundError):c.apply()
            self.assertEqual(json.loads(path.read_text())['scheme'],'No Sounds');self.assertEqual(c.applied.scheme,'No Sounds')
            c.cancel();self.assertEqual(c.pending,c.applied);self.assertEqual(PreferenceController(path,backend,SoundPreferences).pending,c.applied)
    def test_player_argument_list_stop_and_replace(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'sound $(never).wav';wav(path);process=Mock();process.poll.return_value=None
            with patch('win95lx.sound.shutil.which',return_value='/usr/bin/pw-play'),patch('win95lx.sound.subprocess.Popen',return_value=process) as popen:
                p=SoundPlayer();p.play(path);self.assertTrue(p.playing);p.play(path);process.terminate.assert_called_once();p.stop();self.assertFalse(p.playing)
                self.assertEqual(popen.call_args.args[0],['/usr/bin/pw-play',str(path)])
    def test_unavailable_player_is_actionable(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'a.wav';wav(path)
            with patch('win95lx.sound.shutil.which',return_value=None):
                with self.assertRaisesRegex(RuntimeError,'No audio'):SoundPlayer().play(path)
    def test_event_executes_once_and_silence_executes_never(self):
        p=SoundPreferences()
        with patch('win95lx.sound.preferences',return_value=p),patch('win95lx.sound._player.play') as play:
            self.assertTrue(play_event(Path('/assets'),'SystemHand'));play.assert_called_once_with(Path('/assets/sound-chord.wav'))
            play.reset_mock();self.assertFalse(play_event(Path('/assets'),'MenuPopup'));self.assertFalse(play_event(Path('/assets'),'unknown'));play.assert_not_called()
        with patch('win95lx.sound.preferences',return_value=p.select('No Sounds')),patch('win95lx.sound._player.play') as play:
            for event in KEYS:self.assertFalse(play_event(Path('/assets'),event))
            play.assert_not_called()
    def test_startup_success_is_recorded_once_per_boot(self):
        with tempfile.TemporaryDirectory() as d,patch('pathlib.Path.home',return_value=Path(d)),patch('win95lx.sound.play_event',return_value=True) as play,patch('win95lx.sound._player') as player:
            player.process.wait.return_value=0
            self.assertTrue(play_startup(Path('/assets')))
            self.assertFalse(play_startup(Path('/assets')))
            play.assert_called_once_with(Path('/assets'),'SystemStart')
    def test_muted_or_failed_startup_does_not_claim_success(self):
        with tempfile.TemporaryDirectory() as d,patch('pathlib.Path.home',return_value=Path(d)),patch('win95lx.sound.play_event',return_value=False):
            self.assertFalse(play_startup(Path('/assets')));self.assertFalse((Path(d)/'.cache/win95lx/startup-boot-id').exists())
        with tempfile.TemporaryDirectory() as d,patch('pathlib.Path.home',return_value=Path(d)),patch('win95lx.sound.play_event',return_value=True),patch('win95lx.sound._player') as player:
            player.process.wait.return_value=1
            self.assertFalse(play_startup(Path('/assets')));self.assertFalse((Path(d)/'.cache/win95lx/startup-boot-id').exists())
    def test_transient_owner_resolution_and_cycle_protection(self):
        class Owner:
            def __init__(self,parent=None,assets=None):self.parent=parent;self.assets=assets
            def get_transient_for(self):return self.parent
        owner=Owner(Owner(assets=Path('/assets')))
        with patch('win95lx.sound.play_event',return_value=True) as play:self.assertTrue(notify(owner,'SystemQuestion'));play.assert_called_once_with(Path('/assets'),'SystemQuestion')
        owner.parent=owner;self.assertFalse(notify(owner,'SystemHand'))
if __name__=='__main__':unittest.main()
