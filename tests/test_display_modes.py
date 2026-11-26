import sys,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.display_modes import available_modes,set_resolution,MODERN_MODES

LISTING='Screen 0: minimum 320 x 200, current 800 x 600, maximum 4096 x 2160\nVirtual-1 connected primary 800x600+0+0\n   800x600 60.00*+\n   1234x777 60.00\nOther disconnected\n'
class DisplayModesTests(unittest.TestCase):
    def test_native_unusual_resolution_and_server_limits(self):
        modes=available_modes(LISTING)
        self.assertIn((1234,777),modes);self.assertIn((640,480),modes)
        self.assertTrue(all(w<=4096 and h<=2160 for w,h in modes))
        self.assertEqual(len(modes),len(set(modes)))
    def test_top_twenty_are_retained_when_server_supports_them(self):
        modes=available_modes(LISTING.replace('4096 x 2160','16384 x 16384'))
        self.assertTrue(set(MODERN_MODES)<=set(modes))
    def test_advertised_unusual_mode_uses_native_name(self):
        with patch('win95lx.display_modes._run',side_effect=[LISTING,'']) as run:
            set_resolution(1234,777)
            self.assertEqual(run.call_args.args,('xrandr','--output','Virtual-1','--mode','1234x777'))
    def test_refresh_suffix_uses_advertised_timing_instead_of_creating_a_mode(self):
        listing=LISTING.replace('1234x777 60.00','1234x777_59.95 59.95')
        with patch('win95lx.display_modes._run',side_effect=[listing,'']) as run:
            set_resolution(1234,777)
            self.assertEqual(run.call_args.args,('xrandr','--output','Virtual-1','--mode','1234x777_59.95'))
    def test_invalid_and_oversized_requests_do_not_mutate_outputs(self):
        for size in ((-1,600),(800,0),('800',600),(7680,4320)):
            with patch('win95lx.display_modes._run',return_value=LISTING) as run:
                with self.assertRaises(ValueError):set_resolution(*size)
                self.assertTrue(all(call.args==('xrandr','--query') for call in run.call_args_list))
    def test_1366_cvt_rounding_preserves_exact_active_width(self):
        listing=LISTING.replace('4096 x 2160','8192 x 8192')
        cvt='Modeline "1360x768R" 72.00 1360 1408 1440 1520 768 771 781 790 +hsync -vsync\n'
        with patch('win95lx.display_modes._run',side_effect=[listing,cvt,'','','']) as run:
            set_resolution(1366,768)
            call=run.call_args_list[2].args
            self.assertEqual(call[4:8],('1366','1414','1446','1526'))

if __name__=='__main__':unittest.main()
