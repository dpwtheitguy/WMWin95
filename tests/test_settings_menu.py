import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.start_menu import SUBMENUS
class SettingsTests(unittest.TestCase):
 def test_implemented_settings_are_in_native_order(self):
  labels=[row[0] for row in SUBMENUS[3]]
  native=['Control Panel','Printers','Taskbar & Start Menu','Folder Options','Active Desktop']
  self.assertEqual(labels,[name for name in native if name in labels])
  self.assertNotIn('Display Properties',labels)
 def test_control_panel_route_is_present_and_no_unimplemented_targets(self):
  self.assertEqual(SUBMENUS[3],(('Control Panel',36,('open','control')),))
