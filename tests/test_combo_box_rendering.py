"""Meaningful Cairo containment/state regressions; no private font required."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
try:import cairo
except ImportError:cairo=None
from win95lx.shell.combo_box import ComboBox
class Font:
    height=13
    def glyph(self,char):return 6,[(x,y) for y in range(2,11) for x in range(1,5)]
    def width(self,text,bold=False):return len(text)*(6+int(bold))
@unittest.skipIf(cairo is None,'Cairo renderer is required')
class ComboBoxRendering(unittest.TestCase):
    def render(self,choices,width=75,value=0,x=20,y=10):
        from win95lx.shell.widgets import Painter
        image=cairo.ImageSurface(cairo.FORMAT_RGB24,420,140);p=Painter(cairo.Context(image),Font());p.fill(0,0,420,140,(0,128,128))
        before=bytes(image.get_data());combo=ComboBox(tuple(choices),value);combo.draw_list(p,x,y,width);image.flush()
        return image,p,before,(x,y+21,width,len(choices)*13+2)
    def rgb(self,image,x,y):
        # Cairo native-endian RGB24: use a copied pixel through data bytes.
        data=bytes(image.get_data());offset=y*image.get_stride()+x*4
        return tuple(data[offset+i] for i in ((2,1,0) if sys.byteorder=='little' else (1,2,3)))
    def assert_contained(self,image,before,rect):
        x,y,w,h=rect;after=bytes(image.get_data());stride=image.get_stride()
        for yy in range(image.get_height()):
            for xx in range(image.get_width()):
                if not (x<=xx<x+max(0,w) and y<=yy<y+h):
                    off=yy*stride+xx*4;self.assertEqual(after[off:off+4],before[off:off+4],(xx,yy,rect))
    def test_long_selected_and_unselected_labels_do_not_escape_or_erase_border(self):
        for value in (0,1):
            image,p,before,rect=self.render(('A'*80,'B'*80),value=value);self.assert_contained(image,before,rect)
            x,y,w,h=rect
            for yy in range(y,y+h):
                self.assertEqual(self.rgb(image,x,yy),(0,0,0));self.assertEqual(self.rgb(image,x+w-1,yy),(0,0,0))
    def test_native_focus_perimeter_and_selection_colors_preserved(self):
        image,p,before,(x,y,w,h)=self.render(('A','B'))
        self.assertEqual(self.rgb(image,x+1,y+1),(255,255,0))
        self.assertEqual(self.rgb(image,x+40,y+6),(0,0,128))
        self.assertEqual(self.rgb(image,x+40,y+18),(255,255,255))
    def test_tiny_zero_negative_widths_and_empty_choices_remain_bounded(self):
        for width in (-2,0,1,2,3,4):
            image,p,before,rect=self.render(('A'*80,),width);self.assert_contained(image,before,rect)
        image,p,before,rect=self.render((),75);self.assert_contained(image,before,rect)
        combo=ComboBox(());combo.step(1);combo.step(-1);self.assertEqual(combo.value,0);self.assertIsNone(combo.row_at(0,22,75))
    def test_drawing_restores_caller_clip_and_moved_hits_stay_aligned(self):
        image,p,before,rect=self.render(('A'*80,),x=180,y=30);self.assert_contained(image,before,rect)
        p.fill(0,0,5,5,(255,0,0));self.assertEqual(self.rgb(image,2,2),(255,0,0))
        combo=ComboBox(('first','second'));self.assertEqual(combo.row_at(74,22,75),0);self.assertEqual(combo.row_at(0,35,75),1)
        self.assertIsNone(combo.row_at(75,22,75));self.assertIsNone(combo.row_at(-1,22,75))

    def test_open_placement_popup_matches_independent_native_when_assets_available(self):
        root=Path(__file__).resolve().parents[1]
        source=root/'private/screenshots/start-development-20261110/native-wallpaper-combo-center-open.png'
        fontfile=root/'private/shell-assets/ms-sans-serif-8.fnt'
        if not source.exists() or not fontfile.exists():self.skipTest('Independent private native capture/font unavailable')
        import hashlib
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),'6b14b6cefcc38116e727d0b69fae10c8096262e52d370b949852e7d3564d3bf6')
        from win95lx.assets.bitmap import BitmapFont
        from win95lx.shell.widgets import Painter
        native=cairo.ImageSurface.create_from_png(str(source));expected=bytes(native.get_data());ns=native.get_stride()
        for width,height in ((800,600),(1280,720)):
            image=cairo.ImageSurface(cairo.FORMAT_RGB24,width,height);p=Painter(cairo.Context(image),BitmapFont(fontfile.read_bytes()));p.fill(0,0,width,height,(192,192,192))
            x,y=width-90,height-80
            ComboBox(('Center','Tile')).draw_list(p,x,y-21,75);image.flush();actual=bytes(image.get_data());stride=image.get_stride()
            for yy in range(28):
                for xx in range(75):
                    aa=(y+yy)*stride+(x+xx)*4;bb=(448+yy)*ns+(360+xx)*4
                    self.assertEqual(actual[aa:aa+3],expected[bb:bb+3],(width,height,xx,yy))
