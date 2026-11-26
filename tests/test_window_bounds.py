import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.window_bounds import fit_bounds
from win95lx.display_modes import DISPLAY_MODES
from win95lx.control_panel.display_settings import slider_center,slider_index

class WindowBoundsTests(unittest.TestCase):
    def test_every_catalog_resolution_fits_native_property_sheets(self):
        for screen in DISPLAY_MODES:
            for w,h in ((404,448),(408,448),(404,341)):
                x,y,width,height=fit_bounds((500,400,w,h),screen)
                self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0)
                self.assertLessEqual(x+width,screen[0]);self.assertLessEqual(y+height,screen[1]-28)
    def test_low_resolution_shrinks_explorer_and_preserves_fixed_dialog_dimensions(self):
        self.assertEqual(fit_bounds((100,65,512,461),(640,480),resizable=True),(100,0,512,452))
        self.assertEqual(fit_bounds((100,65,404,448),(640,480)),(100,4,404,448))
    def test_native_800_detent_is_stable_with_extra_advertised_small_modes(self):
        modes=sorted(set(DISPLAY_MODES)|{(720,480),(800,480)},key=lambda m:(m[0]*m[1],*m));index=modes.index((800,600))
        self.assertEqual(slider_center(index,len(modes),index),280)
        self.assertEqual(slider_index(280,len(modes),index),index)
        self.assertEqual(slider_index(0,len(modes),index),0);self.assertEqual(slider_index(1000,len(modes),index),len(modes)-1)

if __name__=='__main__':unittest.main()
