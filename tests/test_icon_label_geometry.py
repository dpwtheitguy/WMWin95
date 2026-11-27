import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.icon_labels import icon_label_metrics,draw_icon_label,focus_color_for
class Font:
    def width(self,text):return len(text)*5
class Painter:
    font=Font()
    def __init__(self):self.fills=[];self.texts=[]
    def fill(self,*values):self.fills.append(values)
    def text(self,*values):self.texts.append(values)
class LabelTests(unittest.TestCase):
    def test_multiline_union_uses_tall_native_rect_not_one_row(self):
        m=icon_label_metrics('This needs two lines',Font(),37,38,width=45)
        self.assertEqual(m['origins'][1][1],51);self.assertEqual(m['rect'][3],28);self.assertLessEqual(len(m['lines']),2)
    def test_unlimited_classic_labels_do_not_invent_two_line_ellipsis(self):
        m=icon_label_metrics('Many words '*20,Font(),37,38,max_lines=None)
        self.assertGreater(len(m['lines']),3);self.assertNotIn('...', ''.join(m['lines']));self.assertEqual(m['rect'][3],13*len(m['lines'])+2)
    def test_desktop_inactive_hides_selection_but_preserves_white_text(self):
        p=Painter();draw_icon_label(p,'Text',37,38,desktop=True,selected=True,focused=True,active=False)
        self.assertEqual(len(p.fills),1);self.assertEqual(p.fills[0][-1],(0,128,128));self.assertEqual(p.texts[0][-1],(255,255,255))
    def test_selected_focus_encloses_entire_multiline_highlight(self):
        p=Painter();m=draw_icon_label(p,'This needs two lines',37,38,width=45,desktop=True,selected=True,focused=True)
        self.assertEqual(p.fills[0],(*m['rect'],(0,0,128)));self.assertTrue(all(row[-1]==(255,255,0)for row in p.fills[1:]))
    def test_native_vga_palette_focus_colors_are_not_rgb_inversion(self):
        for background,expected in [((0,0,0),(255,255,255)),((0,128,128),(255,0,0)),((0,0,128),(255,255,0)),((192,192,192),(128,128,128)),((255,0,0),(0,128,128))]:self.assertEqual(focus_color_for(background),expected)
        with self.assertRaises(ValueError):focus_color_for((20,30,40))
    def test_silver_desktop_text_and_explicit_override(self):
        p=Painter();draw_icon_label(p,'Text',37,38,desktop=True,desktop_color=(192,192,192));self.assertEqual(p.texts[0][-1],(0,0,0))
        p=Painter();draw_icon_label(p,'Text',37,38,desktop=True,text_color=(1,2,3));self.assertEqual(p.texts[0][-1],(1,2,3))
    def test_desktop_opaque_patch_uses_whole_wrapped_union(self):
        p=Painter();m=draw_icon_label(p,'Words that wrap across lines',37,38,desktop=True,width=45)
        self.assertEqual(p.fills,[(*m['rect'],(0,128,128))]);self.assertEqual(m['rect'][3],28)
    def test_selected_ie4_expands_and_inactive_shrinks_before_metrics(self):
        text='Many words '*12;p=Painter();active=draw_icon_label(p,text,37,38,desktop=True,selected=True)
        inactive=draw_icon_label(Painter(),text,37,38,desktop=True,selected=True,active=False)
        self.assertGreater(len(active['lines']),2);self.assertEqual(len(inactive['lines']),2)
    def test_explorer_unselected_text_remains_black(self):
        p=Painter();draw_icon_label(p,'Text',37,38);self.assertEqual(p.texts[0][-1],(0,0,0));self.assertFalse(p.fills)
if __name__=='__main__':unittest.main()
