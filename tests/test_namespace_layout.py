import unittest
from win95lx.explorer.namespace_layout import arrange,clipped_hit,reveal
from win95lx.explorer.webview_details import wrapped
from win95lx.shell.icon_labels import wrap_label
class Font:
    def width(self,text):return len(text)*6
class NamespaceLayoutTests(unittest.TestCase):
    def test_large_wraps_at_width_and_narrow_has_vertical_access(self):
        for width in (70,90,160,300,550,1000):
            a=arrange(20,width,190)
            self.assertEqual(len(a.positions),20)
            if width<550:
                self.assertTrue(a.vertical)
                self.assertGreater(a.extent[1],a.viewport[1])
            for x,y in a.positions:
                self.assertLessEqual(x+70,max(72,a.viewport[0]))
    def test_wide_short_count_has_no_scrollbars(self):
        a=arrange(9,700,200);self.assertFalse(a.horizontal);self.assertFalse(a.vertical)
    def test_small_wraps_and_list_flows_down_then_right(self):
        a=arrange(20,350,100,'small');self.assertEqual(a.positions[0][1],a.positions[1][1]);self.assertTrue(a.vertical)
        b=arrange(20,350,100,'list');self.assertEqual(b.positions[0][0],b.positions[1][0]);self.assertTrue(b.horizontal)
    def test_details_has_header_and_both_scrollbars(self):
        a=arrange(20,220,120,'details');self.assertEqual(a.header,17);self.assertTrue(a.vertical);self.assertTrue(a.horizontal)
    def test_manual_positions_preserved_on_resize_and_auto_reflows(self):
        a=arrange(9,700,200);b=arrange(9,170,200,auto=False,positions=a.positions)
        self.assertEqual(b.positions,a.positions);self.assertTrue(b.horizontal)
        c=arrange(9,170,200,auto=True,positions=a.positions);self.assertNotEqual(c.positions,a.positions)
    def test_scroll_clamps_after_resize_and_mode_transition(self):
        for mode in ('large','small','list','details'):
            a=arrange(20,170,100,mode,(99999,99999))
            self.assertLessEqual(a.scroll[0],max(0,a.extent[0]-a.viewport[0]));self.assertLessEqual(a.scroll[1],max(0,a.extent[1]-a.viewport[1]))
        self.assertEqual(arrange(1,800,600,scroll=(999,999)).scroll,(0,0))
    def test_hits_shrink_move_and_offscreen_are_intersected(self):
        self.assertEqual(clipped_hit((100,100,70,60),(120,110,20,20)),(120,110,20,20))
        self.assertIsNone(clipped_hit((100,100,70,60),(300,200,20,20)))
    def test_keyboard_reveal_last_item_reaches_all_views(self):
        for mode in ('large','small','list','details'):
            a=arrange(20,170,100,mode);sx,sy=reveal(a,19);x,y=a.positions[19]
            self.assertLess(x-sx,a.viewport[0]);self.assertLess(y-sy,a.viewport[1]);self.assertGreaterEqual(y-sy,a.header)
    def test_long_descriptions_and_control_labels_fit_measured_width(self):
        for text in ('Changes settings for your display.','A'*120,'Regional Settings','Accessibility Options'):
            self.assertTrue(all(Font().width(line)<=72 for line in wrapped(text,Font(),72)))
            self.assertTrue(all(Font().width(line)<=70 for line in wrap_label(text,Font())))
    def test_no_entries_zero_space_and_invalid_mode(self):
        self.assertEqual(arrange(0,0,0).positions,())
        with self.assertRaises(ValueError):arrange(1,100,100,'wrong')
