import copy,json,sys,tempfile,unittest
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.audio_preferences import AudioPreferences,PulseAudio,endpoints,merge_untouched_audio
from win95lx.control_panel.preferences import PreferenceController

class FakePulse:
    def __init__(self):
        self.rows={'sinks':[self.row('speaker',(65536,32768)),self.row('headphones',(16384,16384))],
                   'sources':[self.row('mic',(32768,32768)),self.row('speaker.monitor',(65536,65536),True)]}
        self.default={'sink':'speaker','source':'mic'};self.calls=[];self.fail=None
    @staticmethod
    def row(name,volumes,monitor=False):return {'name':name,'description':name.title(),'volume':{str(i):{'value':v} for i,v in enumerate(volumes)},'mute':True,'properties':{'device.class':'monitor'} if monitor else {}}
    def run(self,*args):
        self.calls.append(args)
        if self.fail and args[0]==self.fail:self.fail=None;raise RuntimeError('Device changed')
        if args[:2]==('--format=json','list'):return json.dumps(self.rows[args[2]])
        if args[0].startswith('get-default-'):return self.default[args[0].removeprefix('get-default-')]
        if args[0].startswith('set-default-'):self.default[args[0].removeprefix('set-default-')]=args[1];return ''
        kind='sinks' if args[0].startswith('set-sink') else 'sources';row=next(r for r in self.rows[kind] if r['name']==args[1])
        if args[0].endswith('-volume'):row['volume']={str(i):{'value':int(v)} for i,v in enumerate(args[2:])}
        else:row['mute']=args[2]=='1'
        return ''
class AudioTests(unittest.TestCase):
    def test_unrelated_edit_merges_live_external_changes(self):
        original=AudioPreferences(playback='speaker',recording='mic',playback_volume=100,recording_volume=50)
        live=replace(original,playback='headphones',playback_volume=25,recording_volume=63)
        merged=merge_untouched_audio(replace(original,tray=True),original,live)
        self.assertEqual((merged.playback,merged.playback_volume,merged.recording_volume,merged.tray),('headphones',25,63,True))
        edited=merge_untouched_audio(replace(original,playback_volume=40),original,live)
        self.assertEqual((edited.playback,edited.playback_volume,edited.recording_volume),('speaker',40,63))
    def test_actual_defaults_levels_and_monitor_exclusion(self):
        fake=FakePulse();backend=PulseAudio(fake.run);prefs=backend.preferences()
        self.assertEqual((prefs.playback,prefs.recording,prefs.playback_volume,prefs.recording_volume),('speaker','mic',100,50))
        fake.default['source']='speaker.monitor';self.assertEqual(backend.preferences().recording,'mic')
    def test_master_volume_preserves_balance_and_mute(self):
        fake=FakePulse();backend=PulseAudio(fake.run);backend.apply(replace(backend.preferences(),playback_volume=50))
        speaker=backend.inventory()['sinks'][0];self.assertEqual(speaker.channels,(32768,16384));self.assertTrue(speaker.muted)
        self.assertFalse(any('mute' in c[0] for c in fake.calls))
    def test_default_device_selection_and_recording_level(self):
        fake=FakePulse();backend=PulseAudio(fake.run);backend.apply(replace(backend.preferences(),playback='headphones',playback_volume=25,recording_volume=70))
        self.assertEqual(fake.default['sink'],'headphones');self.assertEqual(backend.preferences().recording_volume,70)
    def test_unrelated_preference_does_not_modify_server(self):
        fake=FakePulse();backend=PulseAudio(fake.run);backend.apply(replace(backend.preferences(),tray=True))
        self.assertFalse(any(c[0].startswith('set-') for c in fake.calls))
    def test_apply_failure_restores_levels_defaults_and_saved_preferences(self):
        with tempfile.TemporaryDirectory() as d:
            fake=FakePulse();backend=PulseAudio(fake.run);path=Path(d)/'prefs';controller=PreferenceController(path,backend,AudioPreferences);before=copy.deepcopy(fake.rows)
            controller.pending=replace(controller.pending,playback='headphones',playback_volume=10,recording_volume=80)
            fake.fail='set-source-volume'
            with self.assertRaises(RuntimeError):controller.apply()
            self.assertEqual(fake.rows,before);self.assertEqual(fake.default,{'sink':'speaker','source':'mic'});self.assertFalse(path.exists())
    def test_disappearing_device_does_not_change_unrelated_endpoints(self):
        fake=FakePulse();backend=PulseAudio(fake.run)
        with self.assertRaisesRegex(ValueError,'no longer available'):backend.apply(replace(backend.preferences(),playback='gone'))
        self.assertFalse(any(c[0].startswith('set-') for c in fake.calls))
    def test_volume_popup_changes_only_actual_playback(self):
        fake=FakePulse();backend=PulseAudio(fake.run);backend.set_playback_volume(40);backend.set_playback_mute(False)
        self.assertEqual(backend.preferences().playback_volume,40);self.assertEqual(backend.preferences().recording_volume,50)
        self.assertFalse(backend.inventory()['sinks'][0].muted)
    def test_master_zero_then_restore_preserves_prior_stereo_balance(self):
        fake=FakePulse();backend=PulseAudio(fake.run);backend.set_playback_volume(0);self.assertEqual(backend.inventory()['sinks'][0].channels,(0,0))
        backend.set_playback_volume(100);self.assertEqual(backend.inventory()['sinks'][0].channels,(65536,32768))
        backend.apply(replace(backend.preferences(),playback_volume=0));backend.apply(replace(backend.preferences(),playback_volume=50))
        self.assertEqual(backend.inventory()['sinks'][0].channels,(32768,16384))
    def test_invalid_types_and_device_strings_rejected(self):
        for prefs in (AudioPreferences(playback='-bad'),AudioPreferences(playback='name\ncmd'),AudioPreferences(playback_volume=True),AudioPreferences(recording_volume=-1),AudioPreferences(tray=1)):
            with self.assertRaises(ValueError):prefs.validate()
        backend=PulseAudio(FakePulse().run)
        for value in (101,-1,True):
            with self.assertRaises(ValueError):backend.set_playback_volume(value)
    def test_zero_volume_stereo_device_can_be_raised(self):
        self.assertEqual(PulseAudio.scaled_channels(endpoints([FakePulse.row('silent',(0,0))])[0],25),(16384,16384))
    def test_cancel_discards_pending_changes_and_reopen_keeps_applied(self):
        with tempfile.TemporaryDirectory() as d:
            backend=PulseAudio(FakePulse().run);path=Path(d)/'prefs';c=PreferenceController(path,backend,AudioPreferences);c.pending=replace(c.pending,tray=True);c.apply();c.pending=replace(c.pending,playback_volume=1);c.cancel()
            self.assertEqual(c.pending.playback_volume,100);self.assertTrue(PreferenceController(path,backend,AudioPreferences).applied.tray)
if __name__=='__main__':unittest.main()
