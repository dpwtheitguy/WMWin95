import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.assets.rle8 import decode
class RLETests(unittest.TestCase):
 def test_runs_bottom_up_and_absolute_padding(self):
  self.assertEqual(decode(bytes([3,1,0,0,0,3,2,3,4,0,0,1]),3,2),[2,3,4,1,1,1])
 def test_delta_preserves_previous_frame(self):
  self.assertEqual(decode(bytes([0,2,1,1,1,9,0,1]),3,2,[1]*6),[1,9,1,1,1,1])
 def test_unchanged_frame(self):self.assertEqual(decode(b'\0\1',2,1,[3,4]),[3,4])
 def test_truncation_and_bounds_rejected(self):
  for data in (b'\x04\x01\0\1',b'\0\2\x01',b'\0\3\x01',b'\0\2\x03\x01',b'\x01\x01'):
   with self.assertRaises(ValueError):decode(data,2,1)
