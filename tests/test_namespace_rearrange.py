import tempfile,unittest
from pathlib import Path
from win95lx.explorer.namespace_layout import drag_position,arrange
from win95lx.shell.desktop_icons import ShortcutIcons
class NamespaceRearrangeTests(unittest.TestCase):
 def test_grab_offset_and_release_endpoint(self):
  self.assertEqual(drag_position((75,0),(180,100),(213,139),(0,0),(0,0),(300,200),(75,75)),(108,39))
 def test_scroll_delta_is_content_relative(self):
  self.assertEqual(drag_position((100,100),(180,100),(190,110),(20,30),(40,60),(300,200),(75,75)),(130,140))
 def test_bounds_do_not_place_cell_beyond_visible_extent(self):
  self.assertEqual(drag_position((2,2),(0,0),(-99,-99),(0,0),(0,0),(200,150),(75,75)),(0,0))
  self.assertEqual(drag_position((2,2),(0,0),(999,999),(0,0),(0,0),(200,150),(75,75)),(125,75))
 def test_small_view_and_tiny_pane(self):
  self.assertEqual(drag_position((0,0),(0,0),(99,99),(0,0),(0,0),(10,10),(140,17)),(0,0))
 def test_namespace_label_keys_survive_reordering_and_reopen(self):
  with tempfile.TemporaryDirectory() as home:
   path=Path(home)/'positions.json';store=ShortcutIcons(path);store.move('namespace:computer:large','(C:)',(33,49));store.move('namespace:control:large','Mouse',(60,80));store=ShortcutIcons(path)
   self.assertEqual(store.position('namespace:computer:large','(C:)',(0,0)),(33,49));self.assertEqual(store.position('namespace:control:large','Mouse',(0,0)),(60,80));self.assertEqual(store.position('namespace:computer:small','(C:)',(0,0)),(0,0))
 def test_auto_arrange_discards_manual_positions_only_when_enabled(self):
  positions=((31,47),(149,83));self.assertEqual(arrange(2,400,200,auto=False,positions=positions).positions,positions);self.assertNotEqual(arrange(2,400,200,auto=True,positions=positions).positions,positions)
