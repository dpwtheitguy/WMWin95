"""Independent native radio-state comparisons; private evidence stays optional."""
import json,sys,unittest,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
try:
 import cairo,gi
 gi.require_version('Gtk','3.0')
 from win95lx.apps.network import draw_network_radio
except (ImportError,ValueError):cairo=None
@unittest.skipIf(cairo is None,'Cairo/GTK import required for Network renderer')
class NetworkRadioRendering(unittest.TestCase):
 def setUp(self):
  self.assets=ROOT/'private/shell-assets';manifest=self.assets/'network-radio-states.json'
  if not manifest.exists():self.skipTest('Independent private native radio matrix unavailable')
  from win95lx.assets.bitmap import BitmapFont
  self.font=BitmapFont((self.assets/'ms-sans-serif-8.fnt').read_bytes());self.cases=json.loads(manifest.read_text())['cases']
  self.images={state:cairo.ImageSurface.create_from_png(str(self.assets/f'network-radio-{state}.png')) for state in ('normal-unchecked','normal-checked','pressed-unchecked','pressed-checked','disabled-unchecked','disabled-checked')}
 def render(self,case):
  from win95lx.shell.widgets import Painter,FACE
  width=case['width'];state=case['state_index'];im=cairo.ImageSurface(cairo.FORMAT_RGB24,width+4,20);p=Painter(cairo.Context(im),self.font);p.fill(0,0,width+4,20,FACE)
  geometry=draw_network_radio(p,case['raw_label'],(2,2,width,16),self.images,checked=state in (1,3,5,7),focused=state in (2,3,5),pressed=state in (4,5),enabled=state not in (6,7));im.flush();return im,geometry
 def test_all_sixteen_independent_native_states_match_exactly(self):
  self.assertEqual(len(self.cases),16)
  for case in self.cases:
   with self.subTest(label=case['raw_label'],state=case['state_index']):
    path=self.assets/case['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),case['png_sha256'])
    expected=cairo.ImageSurface.create_from_png(str(path));actual,geometry=self.render(case);aa=bytes(actual.get_data());bb=bytes(expected.get_data())
    for y in range(20):
     for x in range(case['width']+4):
      a=y*actual.get_stride()+x*4;b=y*expected.get_stride()+x*4
      indices=(2,1,0) if sys.byteorder=='little' else (1,2,3)
      self.assertEqual(tuple(aa[a+i] for i in indices),tuple(bb[b+i] for i in indices),(x,y))
 def test_disabled_never_acquires_focus_and_mnemonic_origin_is_measured(self):
  case=next(c for c in self.cases if c['label_index']==1 and c['state_index']==7);image,g=self.render(case)
  self.assertEqual(g['label'],'Specify an IP address:');self.assertEqual(g['mnemonic'],0);self.assertEqual(g['text_origin'],(20,3));self.assertIsNone(g['focus_rect'])
  from win95lx.shell.widgets import Painter
  forced=draw_network_radio(Painter(cairo.Context(image),self.font),case['raw_label'],(2,2,case['width'],16),self.images,checked=True,enabled=False,focused=True)
  self.assertIsNone(forced['focus_rect'])
 def test_long_label_and_focus_never_escape_given_control(self):
  from win95lx.shell.widgets import Painter
  im=cairo.ImageSurface(cairo.FORMAT_RGB24,240,40);p=Painter(cairo.Context(im),self.font);p.fill(0,0,240,40,(0,128,128));before=bytes(im.get_data())
  draw_network_radio(p,'&'+'A'*100,(20,10,70,16),self.images,checked=True,focused=True);im.flush();after=bytes(im.get_data());stride=im.get_stride()
  for y in range(40):
   for x in range(240):
    if not (20<=x<90 and 10<=y<26):
     off=y*stride+x*4;self.assertEqual(before[off:off+4],after[off:off+4])
 def test_other_font_height_requires_separate_native_profile(self):
  from win95lx.shell.widgets import Painter
  im=cairo.ImageSurface(cairo.FORMAT_RGB24,240,40);p=Painter(cairo.Context(im),self.font)
  with self.assertRaises(ValueError):draw_network_radio(p,'X',(0,0,70,23),self.images)
