import importlib.util,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('windows98_asset_library',ROOT/'tools/windows98_asset_library.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

def dib(width=16):
    return struct.pack('<IiiHHIIIIII',40,width,width*2,1,32,0,0,0,0,0,0)+bytes([0,0,255,255])*(width*width)+bytes(((width+31)//32)*4*width)
class Windows98AssetTests(unittest.TestCase):
    def test_group_export_preserves_native_icon_bytes_and_offsets(self):
        icon=dib();group=struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHIH',16,16,0,0,1,32,len(icon),7)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();(source/'sample.dll').write_bytes(b'fake executable')
            with patch.object(module,'extract',return_value=iter([(3,7,1033,icon,'PE'),(14,2,1033,group,'PE')])):
                report=module.export(source,root/'output')
            self.assertEqual(report['ico_files'],1);self.assertEqual(report['png_previews'],1)
            path=root/'output'/report['icons'][0]['ico'];data=path.read_bytes()
            self.assertEqual(struct.unpack_from('<HHH',data),(0,1,1));self.assertEqual(struct.unpack_from('<I',data,18)[0],22)
            self.assertEqual(data[22:],icon)
    def test_invalid_image_keeps_original_ico_and_reports_preview_failure(self):
        icon=b'invalid image';group=struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHIH',16,16,0,0,1,32,len(icon),7)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();(source/'sample.dll').write_bytes(b'fake')
            with patch.object(module,'extract',return_value=iter([(3,7,1033,icon,'PE'),(14,2,1033,group,'PE')])):
                report=module.export(source,root/'output')
            self.assertEqual(report['ico_files'],1);self.assertEqual(report['png_previews'],0)
            self.assertTrue(report['errors'][0]['original_ico_preserved'])
    def test_bitmap_wrapper_preserves_dib_and_new_output_required(self):
        bits=struct.pack('<IiiHHIIIIII',40,1,1,1,24,0,4,0,0,0,0)+bytes([1,2,3,0])
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source=root/'source';source.mkdir();(source/'sample.dll').write_bytes(b'fake')
            with patch.object(module,'extract',return_value=iter([(2,1,1033,bits,'PE')])):
                report=module.export(source,root/'output')
            self.assertEqual(report['bitmap_files'],1);path=next((root/'output').rglob('*.bmp'));data=path.read_bytes()
            self.assertEqual(data[:2],b'BM');self.assertEqual(struct.unpack_from('<I',data,10)[0],54);self.assertEqual(data[14:],bits)
            with self.assertRaises(FileExistsError):module.export(source,root/'output')
if __name__=='__main__':unittest.main()
