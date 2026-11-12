import struct,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from resources import extract,dimensions
class Resources(unittest.TestCase):
    def test_ne_numeric_resource(self):
        b=bytearray(256); b[:2]=b'MZ'; struct.pack_into('<I',b,60,64); b[64:66]=b'NE'; struct.pack_into('<HH',b,100,64,96)
        struct.pack_into('<H',b,128,0); struct.pack_into('<HHI',b,130,0x8002,1,0); struct.pack_into('<HHHHHH',b,138,200,40,0,0x8007,0,0)
        struct.pack_into('<Iii',b,200,40,16,20)
        rows=list(extract(b)); self.assertEqual(rows[0][:3],(2,7,None)); self.assertEqual(dimensions(2,rows[0][3]),[16,20])
    def test_unsupported_is_explicit(self):
        with self.assertRaises(ValueError): list(extract(b'not an executable'))
    def test_ne_truncated_resource(self):
        b=bytearray(256); b[:2]=b'MZ'; struct.pack_into('<I',b,60,64); b[64:66]=b'NE'; struct.pack_into('<HH',b,100,64,96); struct.pack_into('<HHI',b,130,0x8002,1,0); struct.pack_into('<HHHHHH',b,138,250,40,0,0x8007,0,0)
        with self.assertRaises(ValueError): list(extract(b))
