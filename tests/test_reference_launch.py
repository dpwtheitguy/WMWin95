import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dev'))
from start_reference_variant import visible_command
class ReferenceLaunchTests(unittest.TestCase):
 def test_normal_launch_visible_without_rewinding_the_disk(self):
  saved=['qemu','-display','none','-loadvm','old-checkpoint','-daemonize','-drive','private.qcow2']
  result=visible_command(saved)
  self.assertEqual(result[result.index('-display')+1],'gtk,show-tabs=off,zoom-to-fit=off')
  self.assertNotIn('-daemonize',result);self.assertNotIn('-loadvm',result)
  self.assertIn('old-checkpoint',saved);self.assertEqual(saved[2],'none')
 def test_recovery_snapshot_is_explicit_and_replaces_old_argument(self):
  result=visible_command({'command':['qemu','-display','gtk','-loadvm','old']},'working')
  self.assertEqual(result.count('-loadvm'),1);self.assertEqual(result[-2:],['-loadvm','working'])
  self.assertNotIn('old',result)

 def test_visible_references_use_realtime_clock_for_animation_comparisons(self):
  result=visible_command(['qemu','-display','none','-icount','shift=5,sleep=off'])
  self.assertEqual(result[result.index('-icount')+1],'shift=5,sleep=on')
