import sys,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences,ScreenSaverIdle


class SaverIdleTests(unittest.TestCase):
    def setUp(self):
        self.runtime=Mock();self.process=Mock();self.process.poll.return_value=None
        self.runtime.launch.return_value=self.process
        self.errors=[]
        self.idle=ScreenSaverIdle(self.runtime,ScreenSaverPreferences('nature',1),self.errors.append)

    def test_threshold_launches_exactly_once(self):
        self.idle.tick(59.9);self.runtime.launch.assert_not_called()
        self.idle.tick(60);self.idle.tick(61)
        self.runtime.launch.assert_called_once_with('nature',mode='fullscreen')

    def test_activity_stops_and_allows_next_idle_period(self):
        self.idle.tick(60);self.idle.tick(0);self.runtime.stop.assert_called_once()
        self.idle.tick(60);self.assertEqual(self.runtime.launch.call_count,2)

    def test_natural_exit_does_not_immediately_restart(self):
        self.idle.tick(60);self.process.poll.return_value=0
        self.idle.tick(61);self.idle.tick(65)
        self.assertEqual(self.runtime.launch.call_count,1)
        self.runtime.stop.assert_called_once()

    def test_failed_launch_reported_once_until_activity(self):
        self.runtime.launch.side_effect=RuntimeError('missing package')
        self.idle.tick(60);self.idle.tick(80)
        self.assertEqual(len(self.errors),1);self.assertEqual(self.runtime.launch.call_count,1)
        self.idle.tick(0);self.idle.tick(60);self.assertEqual(len(self.errors),2)

    def test_inhibit_blocks_launch_and_stops_running_saver(self):
        self.idle.tick(60,inhibited=True);self.runtime.launch.assert_not_called()
        self.idle.tick(61);self.idle.tick(62,inhibited=True)
        self.runtime.stop.assert_called_once()

    def test_none_selection_never_launches(self):
        self.idle.configure(ScreenSaverPreferences());self.idle.tick(100000)
        self.runtime.launch.assert_not_called()

    def test_changing_settings_stops_old_process(self):
        self.idle.tick(60);self.idle.configure(ScreenSaverPreferences('stars',2))
        self.runtime.stop.assert_called_once();self.idle.tick(119)
        self.assertEqual(self.runtime.launch.call_count,1)
        self.idle.tick(120);self.assertEqual(self.runtime.launch.call_args.args,('stars',))

    def test_close_is_idempotent_and_disables_future_ticks(self):
        self.idle.tick(60);self.idle.close();self.idle.close();self.idle.tick(100)
        self.runtime.stop.assert_called_once();self.assertEqual(self.runtime.launch.call_count,1)

    def test_invalid_idle_samples_rejected(self):
        for value in(-1,True,None,float('nan'),float('inf')):
            with self.subTest(value=value),self.assertRaises(ValueError):self.idle.tick(value)

    def test_invalid_preferences_rejected(self):
        for value in(ScreenSaverPreferences(wait_minutes=True),ScreenSaverPreferences(wait_minutes=0),ScreenSaverPreferences(wait_minutes=61),ScreenSaverPreferences('bad\0name')):
            with self.subTest(value=value),self.assertRaises(ValueError):value.validate()

if __name__=='__main__':unittest.main()
