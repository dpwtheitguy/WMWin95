"""Track ownership, clipping, states and native white-track exceptions."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
try:import cairo
except ImportError:cairo=None
from win95lx.shell.scrollbar import VerticalScrollbar

class Font:
    def width(self,text):return len(text)*5
    def glyph(self,char):return 5,()

@unittest.skipIf(cairo is None,'Cairo rendering dependency unavailable')
class ScrollbarRendering(unittest.TestCase):
    def render(self,height,maximum,value,style='classic',origin=(7,9)):
        from win95lx.shell.widgets import Painter
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,40,height+20)
        painter=Painter(cairo.Context(surface),Font());painter.fill(0,0,40,height+20,(0,128,128))
        bar=VerticalScrollbar(height,maximum);bar.draw(painter,*origin,value,track=style);surface.flush()
        def rgb(x,y):
            data=surface.get_data();i=y*surface.get_stride()+4*x
            return tuple(data[i+j] for j in (2,1,0))
        return bar,rgb
    def test_native_getscrollinfo_page_sizes_and_positions(self):
        for total,value,height,top in ((21,0,176,16),(31,0,119,16),(31,7,119,68),(31,15,119,128)):
            bar=VerticalScrollbar.for_page(263,total-16,16)
            self.assertEqual((bar.thumb,bar.thumb_top(value)),(height,top))
        with self.assertRaises(ValueError):VerticalScrollbar.for_page(263,15,0)

    def test_default_track_is_control_owned_gray_stipple_in_all_positions(self):
        for height in (78,120,264):
            for maximum in (0,100):
                for value in (0,50,100):
                    with self.subTest(height=height,maximum=maximum,value=value):
                        bar,rgb=self.render(height,maximum,value);top=bar.thumb_top(value)
                        pixels=[rgb(7+x,9+y) for y in range(16,height-16) if not top<=y<top+21 for x in range(16)]
                        self.assertEqual(set(pixels),{(192,192,192),(255,255,255)})
                        self.assertEqual(pixels.count((192,192,192)),pixels.count((255,255,255)))
                        for point in ((6,10),(23,10),(7,8),(7,height+9)):
                            self.assertEqual(rgb(*point),(0,128,128))
    def test_native_window_track_requires_explicit_opt_in(self):
        bar,rgb=self.render(120,100,0,'window')
        self.assertEqual({rgb(x,y) for y in range(60,90) for x in range(7,23)},{(255,255,255)})
    def test_track_phase_moves_with_control_not_parent_window(self):
        _,a=self.render(120,100,100,origin=(7,9));_,b=self.render(120,100,100,origin=(8,10))
        for y in range(16,40):
            for x in range(16):self.assertEqual(a(7+x,9+y),b(8+x,10+y))
    def test_unknown_style_cannot_silently_inherit_parent_color(self):
        with self.assertRaises(ValueError):self.render(120,100,0,'theme')
    def test_absent_or_invalid_mnemonics_do_not_add_an_underline(self):
        from win95lx.shell.widgets import Painter,FACE
        for mnemonic in (None,'',-1,99,'z'):
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,30,20);p=Painter(cairo.Context(surface),Font());p.fill(0,0,30,20,FACE)
            p.menu_text('Use',2,2,mnemonic=mnemonic);surface.flush();data=surface.get_data();stride=surface.get_stride()
            self.assertTrue(all(bytes(data[14*stride+x*4:14*stride+x*4+3])==bytes([192,192,192]) for x in range(30)),mnemonic)

    def test_first_character_mnemonic_is_underlined(self):
        from win95lx.shell.widgets import Painter,FACE
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,30,20);p=Painter(cairo.Context(surface),Font());p.fill(0,0,30,20,FACE)
        p.menu_text('Use',2,2,mnemonic=0);surface.flush();data=surface.get_data();stride=surface.get_stride()
        self.assertTrue(all(bytes(data[14*stride+x*4:14*stride+x*4+3])==b'\0\0\0' for x in range(2,7)))

if __name__=='__main__':unittest.main()
