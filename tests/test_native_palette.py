"""Compare compiled conversion with the independently retained Python rules."""
import ctypes,random,shutil,subprocess,sys,tempfile,unittest
from array import array
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from win95lx.control_panel.display_preferences import color_256,nearest_vga,packed_color,VGA

class NativePaletteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler=shutil.which('cc')
        if not compiler:raise unittest.SkipTest('C compiler unavailable; runtime uses Python fallback')
        cls.temporary=tempfile.TemporaryDirectory();path=Path(cls.temporary.name)/'palette.so'
        subprocess.run([compiler,'-O3','-std=c99','-Wall','-Wextra','-Werror','-fPIC','-shared',str(ROOT/'src/win95lx/assets/palette.c'),'-o',str(path)],check=True,capture_output=True)
        cls.lib=ctypes.CDLL(str(path));cls.lib.win95lx_palette_convert.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
        cls.lib.win95lx_palette_over_256.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()
    def convert(self,values,palette):
        source=array('I',values);output=array('I',[0])*len(values)
        self.assertEqual(self.lib.win95lx_palette_convert(source.buffer_info()[0],output.buffer_info()[0],len(values),palette),0)
        return list(output)
    def test_random_colors_and_cache_collisions_match_both_python_palettes(self):
        randomizer=random.Random(95);values=[randomizer.getrandbits(32) for _ in range(12000)]
        for palette in (0,1):
            expected=[packed_color(color_256(v)) if palette else packed_color(nearest_vga(v>>20&15,v>>12&15,v>>4&15)) for v in values]
            self.assertEqual(self.convert(values,palette),expected)
    def test_boundaries_and_vga_tie_precedence(self):
        edges=(0,1,25,26,50,51,76,77,102,127,128,153,178,179,204,229,230,254,255)
        values=[r<<16|g<<8|b for r in edges for g in edges for b in edges]
        self.assertEqual(self.convert(values,1),[packed_color(color_256(v)) for v in values])
        self.assertEqual(self.convert([packed_color(color) for color in VGA],1),[packed_color(color) for color in VGA])
    def test_unique_threshold_repeated_pixels_and_alpha_bits(self):
        for values,expected in (([0]*10000,0),(list(range(256)),0),(list(range(257)),1),([0,0xff000000]*3000,0)):
            source=array('I',values);self.assertEqual(self.lib.win95lx_palette_over_256(source.buffer_info()[0],len(values)),expected)
    def test_repeated_runs_keep_the_same_result_and_invalid_palette_is_rejected(self):
        values=[0x123456]*3000+[0xabcdef]*3000
        self.assertEqual(self.convert(values,1),[packed_color(color_256(v)) for v in values])
        source=array('I',[0]);output=array('I',[0]);self.assertEqual(self.lib.win95lx_palette_convert(source.buffer_info()[0],output.buffer_info()[0],1,7),-1)

if __name__=='__main__':unittest.main()
