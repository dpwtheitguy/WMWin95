"""Independent USER popup menu capture, not generated expected geometry."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
try:import cairo
except ImportError:cairo=None
@unittest.skipIf(cairo is None,'Cairo required')
class NamespaceDropRendering(unittest.TestCase):
 def fixture(self):
  font=ROOT/'private/shell-assets/ms-sans-serif-8.fnt';art=ROOT/'private/shell-assets/namespace-drop-menu-ie4.png';meta=ROOT/'private/reference-tools/namespace-transfer-native-20261127/ie4-right-menu.json'
  if not all(path.is_file() for path in (font,art,meta)):self.skipTest('Private native drop-menu references required')
  from win95lx.assets.bitmap import BitmapFont
  from win95lx.shell.namespace_drop import NamespaceDropContext
  return NamespaceDropContext(0,0,[('Create Shortcut(s) Here',('create',)),None,('Cancel',('cancel',))],183,183,49),BitmapFont(font.read_bytes()),art,json.loads(meta.read_text())
 def test_full_resting_menu_matches_actual_native_user_popup(self):
  from win95lx.shell.widgets import Painter
  menu,font,path,meta=self.fixture();w,h=meta['rect'][2:];actual=cairo.ImageSurface(cairo.FORMAT_RGB24,w,h);menu.draw(Painter(cairo.Context(actual),font));expected=cairo.ImageSurface(cairo.FORMAT_RGB24,w,h);cr=cairo.Context(expected);cr.set_source_surface(cairo.ImageSurface.create_from_png(str(path)));cr.paint();a,b=bytes(actual.get_data()),bytes(expected.get_data());channels=(0,1,2) if sys.byteorder=='little' else(1,2,3)
  self.assertEqual(sum(any(a[y*actual.get_stride()+x*4+c]!=b[y*expected.get_stride()+x*4+c]for c in channels)for y in range(h)for x in range(w)),0)
 def test_hit_rows_follow_native_rectangles_and_separator_is_not_actionable(self):
  menu,font,path,meta=self.fixture();entries=list(menu.entries());self.assertEqual(menu.height,meta['rect'][3]);self.assertEqual([y for y,row in entries],[item['rect'][1] for item in meta['items']]);self.assertIsNone(menu.at(10,23));self.assertIsNone(menu.at(2,10));self.assertEqual(menu.at(3,3)[1][1],('create',));self.assertEqual(menu.at(179,45)[1][1],('cancel',));self.assertIsNone(menu.at(180,45))

 def test_right_alignment_matches_native_drop_anchor(self):
  from win95lx.shell.namespace_drop import NamespaceDropContext
  menu,font,path,meta=self.fixture();actual=NamespaceDropContext.at_drop(700,400,menu.rows,183,800,600);self.assertEqual([actual.x,actual.y,actual.width,actual.height],meta['rect'])
 def test_native_source_grab_offset_is_preserved(self):
  from win95lx.shell.namespace_drop import drag_image_origin
  self.assertEqual(drag_image_origin((260,258),(77,0),(369,279),(700,400),(0,0),image_x=15),(683,379))
