import sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from pixels import read,write
from compare import compare, compare_images, crop
class Pixels(unittest.TestCase):
    def test_exact_difference_and_mask(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.png'; b=Path(d)/'b.png'
            write(a,2,2,[(0,0,0,255)]*4); write(b,2,2,[(0,0,0,255)]*3+[(1,0,0,255)])
            result,_=compare(a,b,[])
            self.assertEqual(result['differing_pixels'],1); self.assertEqual(result['differing_percent'],25); self.assertEqual(result['bbox_xyxy_exclusive'],[1,1,2,2])
            result,_=compare(a,b,[{'rect':[1,1,1,1],'reason':'test clock'}]); self.assertTrue(result['passed'])
            with self.assertRaises(ValueError): compare(a,b,[{'rect':[0,0,2,2],'reason':'everything'}])
    def test_cropped_regions_keep_local_coordinates_and_exact_colors(self):
        gray, white = (192,192,192,255), (255,255,255,255)
        expected = crop((3, 3, [gray]*9), (1,1,2,2))
        observed = crop((2, 3, [white, white, gray, white, gray, white]), (0,1,2,2))
        result, _ = compare_images(expected, observed, [])
        self.assertEqual(result['bbox_xyxy_exclusive'], [1,0,2,2])
        self.assertEqual(result['rows_with_differences'], {0:1, 1:1})
        self.assertEqual(result['columns_with_differences'], {1:2})
        self.assertEqual(result['top_color_changes'], [
            {'reference_rgba': gray, 'actual_rgba': white, 'pixels': 2},
        ])
        with self.assertRaises(ValueError):
            crop((2, 3, [gray]*6), (1,1,2,2))

    def test_alpha_is_compared(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.png'; b=Path(d)/'b.png'; write(a,1,1,[(0,0,0,0)]); write(b,1,1,[(0,0,0,255)])
            self.assertFalse(compare(a,b,[])[0]['passed'])
    def test_size_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/'a.png'; b=Path(d)/'b.png'; write(a,1,1,[(0,0,0,255)]); write(b,2,1,[(0,0,0,255)]*2)
            with self.assertRaises(ValueError): compare(a,b,[])
if __name__=='__main__': unittest.main()
