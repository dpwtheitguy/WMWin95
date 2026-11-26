import io,json,sys,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.datetime_settings import DateTimePreferences,DateTimeController,TimedateBackend,fixed_tzif,fixed_zone_name,wall_timestamp

class Backend:
    def __init__(self):self.zone=DateTimePreferences();self.edited=None;self.fail=False
    def preferences(self):return self.zone
    def snapshot(self):return self.zone,self.edited
    def restore(self,state):self.zone,self.edited=state
    def apply(self,prefs,edited=None):
        self.zone,self.edited=prefs,edited
        if self.fail:raise RuntimeError('Permission denied')

class DateTimeTests(unittest.TestCase):
    def test_fixed_zone_binary_handles_quarter_and_half_hour_offsets(self):
        for offset in range(-720,841,15):
            tz=ZoneInfo.from_file(io.BytesIO(fixed_tzif(offset)),key=fixed_zone_name(offset))
            for month in (1,7):self.assertEqual(datetime(2026,month,1,tzinfo=tz).utcoffset(),timedelta(minutes=offset))
    def test_dst_and_standard_time_are_distinct_functional_policies(self):
        prefs=DateTimePreferences('America/Los_Angeles',True)
        self.assertEqual(datetime(2026,7,1,tzinfo=prefs.tzinfo).utcoffset(),timedelta(hours=-7))
        fixed=replace(prefs,daylight=False)
        self.assertEqual(datetime(2026,7,1,tzinfo=fixed.tzinfo).utcoffset(),timedelta(hours=-8))
    def test_nonexistent_local_time_is_rejected_and_leap_day_round_trips(self):
        prefs=DateTimePreferences()
        with self.assertRaises(ValueError):wall_timestamp(datetime(2026,3,8,2,30),prefs)
        instant=wall_timestamp(datetime(2024,2,29,12),prefs)
        self.assertEqual(datetime.fromtimestamp(instant,prefs.tzinfo).day,29)
    def test_apply_cancel_reopen_never_replays_a_saved_clock_edit(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'datetime.json';backend=Backend();c=DateTimeController(path,backend)
            c.pending=DateTimePreferences('Asia/Kolkata');c.edited=datetime(2026,11,26,12);c.apply()
            self.assertIsNone(c.edited);self.assertNotIn('edited',json.loads(path.read_text()))
            reopened=DateTimeController(path,backend);self.assertEqual(reopened.pending,c.applied);self.assertIsNone(reopened.edited)
            reopened.pending=DateTimePreferences();reopened.edited=datetime(1997,1,1);reopened.cancel();self.assertEqual(reopened.pending,c.applied);self.assertIsNone(reopened.edited)
    def test_denied_backend_and_failed_save_restore_previous_settings(self):
        with tempfile.TemporaryDirectory() as d:
            backend=Backend();c=DateTimeController(Path(d)/'prefs',backend);original=backend.snapshot();c.pending=DateTimePreferences('Asia/Tokyo');backend.fail=True
            with self.assertRaises(RuntimeError):c.apply()
            self.assertEqual(backend.snapshot(),original);self.assertFalse(c.path.exists())
            backend.fail=False
            with patch('win95lx.control_panel.preferences.save_preferences',side_effect=OSError('Full disk')):
                with self.assertRaises(OSError):c.apply()
            self.assertEqual(backend.snapshot(),original)
    def test_timedate_backend_disables_ntp_only_for_explicit_clock_edits(self):
        calls=[];zone=['America/Los_Angeles']
        def run(*args):
            calls.append(args)
            if args[1]=='show':return 'Timezone='+zone[0]+'\nNTP=yes\n'
            if 'set-timezone' in args:zone[0]=args[-1]
            return ''
        backend=TimedateBackend(run);backend.apply(DateTimePreferences('Asia/Tokyo'))
        self.assertFalse(any('set-time' in args or 'set-ntp' in args for args in calls))
        backend.apply(DateTimePreferences('Asia/Tokyo'),datetime(2026,11,26,10))
        self.assertTrue(any('set-ntp' in args and args[-1]=='false' for args in calls));self.assertTrue(any('set-time' in args for args in calls))

if __name__=='__main__':unittest.main()
