import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
try:
    import cairo
    from win95lx.shell.widgets import Painter,selected_icon_mask
except ImportError:
    cairo=None
@unittest.skipIf(cairo is None,'Cairo rendering dependency is unavailable')
class SelectedMaskTests(unittest.TestCase):
    def setUp(self):selected_icon_mask.cache_clear()
    def tearDown(self):selected_icon_mask.cache_clear()
    def image(self):
        image=cairo.ImageSurface(cairo.FORMAT_ARGB32,2,2);cr=cairo.Context(image);cr.set_source_rgba(1,1,0,1);cr.paint();return image
    def test_cache_keys_use_source_object_and_checker_phase(self):
        image=self.image();first=selected_icon_mask(image,0);self.assertIs(first,selected_icon_mask(image,0));self.assertIsNot(first,selected_icon_mask(image,1));self.assertIsNot(first,selected_icon_mask(self.image(),0));self.assertEqual(selected_icon_mask.cache_info().currsize,3)
    def test_alpha_holes_remain_transparent_in_selection_mask(self):
        image=self.image();cr=cairo.Context(image);cr.set_operator(cairo.OPERATOR_CLEAR);cr.rectangle(0,0,1,1);cr.fill();mask=selected_icon_mask(image,0);mask.flush();data=mask.get_data();self.assertEqual(data[0],0);self.assertEqual(data[mask.get_stride()+1],255)
    def test_offset_phase_does_not_paint_outside_icon_bounds(self):
        image=self.image();target=cairo.ImageSurface(cairo.FORMAT_RGB24,6,5);p=Painter(cairo.Context(target),None);p.fill(0,0,6,5,(0,128,128));p.selected_image(image,2,1,phase=1);target.flush();data=target.get_data();stride=target.get_stride();navy=0
        for y in range(5):
            for x in range(6):
                b,g,r=data[y*stride+x*4:y*stride+x*4+3]
                if 2<=x<4 and 1<=y<3:navy+=(r,g,b)==(0,0,128)
                else:self.assertEqual((r,g,b),(0,128,128))
        self.assertEqual(navy,2)
    def test_cache_is_bounded_for_many_source_surfaces(self):
        for _ in range(150):selected_icon_mask(self.image(),0)
        self.assertEqual(selected_icon_mask.cache_info().currsize,128)
if __name__=='__main__':unittest.main()
