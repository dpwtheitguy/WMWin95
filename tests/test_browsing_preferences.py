import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.browsing import BrowsingPreferences

class BrowsingPolicy(unittest.TestCase):
 def test_reference_single_window_default_and_explicit_separate_persistence(self):
  with TemporaryDirectory() as folder:
   path=Path(folder)/'folders.json'
   self.assertTrue(BrowsingPreferences.load(path).single_window)
   BrowsingPreferences(False).save(path)
   self.assertFalse(BrowsingPreferences.load(path).single_window)
   BrowsingPreferences(True).save(path)
   self.assertTrue(BrowsingPreferences.load(path).single_window)
 def test_invalid_setting_never_becomes_truthy_string(self):
  with TemporaryDirectory() as folder:
   path=Path(folder)/'folders.json';path.write_text('{"single_window":"false"}')
   self.assertTrue(BrowsingPreferences.load(path).single_window)
