import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.assets.dialog_template import parse_dialog,pixel_rect

def text(value):return value.encode('utf-16le')+b'\0\0'
class DialogTemplateTests(unittest.TestCase):
    def fixture(self):
        data=struct.pack('<IIHhhhh',0x40,0,1,0,0,252,218)+b'\0\0'*2+text('Speed')+struct.pack('<H',8)+text('MS Sans Serif')
        data+=b'\0'*((-len(data))%4)
        return data+struct.pack('<IIhhhhH',0x50000000,0,7,7,100,14,101)+b'\xff\xff\x80\0'+text('Apply')+b'\0\0'
    def test_font_caption_ordinals_and_control_bounds(self):
        result=parse_dialog(self.fixture());self.assertEqual(result['caption'],'Speed');self.assertEqual(result['font']['face'],'MS Sans Serif')
        self.assertEqual(result['controls'][0]['class'],128);self.assertEqual(result['controls'][0]['text'],'Apply')
    def test_truncated_header_string_control_and_creation_data_fail(self):
        data=self.fixture()
        for size in (0,17,22,len(data)-1,len(data)-7):
            with self.assertRaises(ValueError):parse_dialog(data[:size])
    def test_extended_templates_are_explicitly_unsupported(self):
        with self.assertRaises(ValueError):parse_dialog(b'\x01\0\xff\xff'+b'\0'*30)
    def test_no_implicit_property_page_origin(self):
        with self.assertRaises(TypeError):pixel_rect([4,8,20,16])
    def test_dialog_units_require_explicit_measured_base_for_pixel_claims(self):
        self.assertEqual(pixel_rect([4,8,20,16],origin=(10,20),base=(6,12)),(16,32,30,24))

if __name__=='__main__':unittest.main()
