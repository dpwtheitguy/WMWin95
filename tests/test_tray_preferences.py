import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.display_preferences import DisplayPreferences

class TrayPreferences(unittest.TestCase):
 def test_native_default_is_off_and_missing_preference_stays_off(self):
  with TemporaryDirectory() as folder:
   self.assertFalse(DisplayPreferences().tray)
   self.assertFalse(DisplayPreferences.load(Path(folder)/'display.json').tray)
 def test_both_saved_states_survive_restart_without_default_override(self):
  with TemporaryDirectory() as folder:
   path=Path(folder)/'display.json'
   for enabled in (True,False,True):
    DisplayPreferences(tray=enabled).save(path)
    self.assertIs(DisplayPreferences.load(path).tray,enabled)
 def test_cancelled_pending_change_does_not_replace_saved_state(self):
  with TemporaryDirectory() as folder:
   path=Path(folder)/'display.json';DisplayPreferences(tray=True).save(path)
   pending=DisplayPreferences(tray=False)
   self.assertFalse(pending.tray);self.assertTrue(DisplayPreferences.load(path).tray)
