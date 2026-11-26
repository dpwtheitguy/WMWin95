import sys,unittest,struct,json
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.assets.cursors import decode,PointerLibrary

def cur(white=False,invert=False):
 dib=struct.pack('<IiiHHIIiiII',40,1,2,1,1,0,8,0,0,2,0)+bytes([0,0,0,0,255,255,255,0])+bytes([128 if white else 0,0,0,0,128 if invert else 0,0,0,0])
 return struct.pack('<HHH',0,2,1)+struct.pack('<BBBBHHII',1,1,2,0,0,0,len(dib),22)+dib

def chunk(tag,data):return tag+struct.pack('<I',len(data))+data+(b'\0' if len(data)%2 else b'')
def ani():
 header=struct.pack('<9I',36,2,3,0,0,0,0,6,3)
 payload=b'ACON'+chunk(b'anih',header)+chunk(b'seq ',struct.pack('<3I',1,0,1))+chunk(b'rate',struct.pack('<3I',6,12,3))+chunk(b'LIST',b'fram'+chunk(b'icon',cur())+chunk(b'icon',cur(True)))
 return chunk(b'RIFF',payload)
class CursorTests(unittest.TestCase):
 def test_cur_hotspot_opaque_and_inversion(self):
  f,s,t=decode(cur());self.assertEqual(f[0].pixels,[(0,0,0,255)]);self.assertEqual(f[0].hotspot,(0,0))
  f,_,_=decode(cur(True,True));self.assertEqual(f[0].invert,((0,0),));self.assertEqual(f[0].pixels,[(0,0,0,255)])
 def test_ani_sequence_rates_and_frame_colors(self):
  frames,sequence,times=decode(ani());self.assertEqual(sequence,[1,0,1]);self.assertEqual(times,[100,200,50]);self.assertEqual(frames[1].pixels,[(255,255,255,255)])
 def test_original_plus_legacy_riff_size(self):
  data=bytearray(ani());struct.pack_into('<I',data,4,len(data));self.assertEqual(decode(data)[1],[1,0,1])
 def test_truncation_and_bad_hotspots_rejected(self):
  for data in (cur()[:30],ani()[:-20],b'RIFF\0\0\0\0WAVE'):
   with self.assertRaises(ValueError):decode(data)
  data=bytearray(cur());struct.pack_into('<H',data,10,3)
  with self.assertRaises(ValueError):decode(data)
 def test_timeline_boundaries_and_wrap(self):
  with TemporaryDirectory() as root:
   root=Path(root);definition={'frames':[{'file':'A'},{'file':'B'}],'sequence':[1,0,1],'durations_ms':[100,200,50]}
   (root/'pointer-schemes.json').write_text(json.dumps({'schemes':{'(None)':{'arrow':'a'}},'assets':{'a':definition}}))
   lib=PointerLibrary(root)
   for time,expected in ((0,'B'),(99,'B'),(100,'A'),(299,'A'),(300,'B'),(349,'B'),(350,'B')):self.assertEqual(lib.frame('(None)','arrow',time)['file'],expected)
   self.assertTrue(lib.animated('(None)'))
