"""Typed Mouse command specifications, input tolerances and native states."""
import sys,json,unittest,hashlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
try:
 import cairo,gi
 gi.require_version('Gtk','3.0')
 from win95lx.apps.mouse import MouseWindow
 from gi.repository import Gdk
except (ImportError,ValueError):cairo=None
class Font:
 height=13
 def width(self,text,bold=False):return len(text)*(6+int(bold))
 def glyph(self,char):return 6,[(x,3) for x in range(1,5)]
@unittest.skipIf(cairo is None,'Cairo/GTK imports required')
class MouseCommandSpecifications(unittest.TestCase):
 def fixture(self):
  from win95lx.shell.widgets import Painter,FACE
  image=cairo.ImageSurface(cairo.FORMAT_RGB24,240,100);p=Painter(cairo.Context(image),Font());p.fill(0,0,240,100,FACE)
  calls=[];obj=SimpleNamespace(button_specs=[],command_actions=set(),command_mnemonics={},hits=[],focus_action=('body',),caption_active=True,pressed=None,press_inside=True,default_command=None,combo=SimpleNamespace(expanded=False),tab=0,scheme_drag=None,caption_drag=None,dragging=None,area=SimpleNamespace(queue_draw=lambda:None),action=lambda a:calls.append(a))
  obj.hit=lambda r,a:obj.hits.append((r,a));return obj,p,image,calls
 def test_deferred_painting_and_disabled_dispatch(self):
  obj,p,image,calls=self.fixture();before=bytes(image.get_data())
  MouseWindow.button(obj,p,'OK',(10,10,75,23),('ok',));MouseWindow.button(obj,p,'&Apply',(100,10,75,23),('apply',),False)
  self.assertEqual(before,bytes(image.get_data()));self.assertEqual(obj.command_actions,{('ok',)});self.assertEqual(obj.hits,[((10,10,75,23),('ok',))])
  MouseWindow.draw_commands(obj,p);self.assertEqual(obj.default_command,('ok',));self.assertNotIn('a',obj.command_mnemonics)
 def test_one_enabled_default_transfers_and_returns_from_body(self):
  obj,p,image,calls=self.fixture()
  for label,x,action,enabled in [('OK',10,('ok',),True),('Cancel',100,('cancel',),True),('&Apply',10,('apply',),False)]:MouseWindow.button(obj,p,label,(x,10,75,23),action,enabled)
  obj.focus_action=('cancel',);MouseWindow.draw_commands(obj,p);self.assertEqual(obj.default_command,('cancel',))
  obj.focus_action=('body',);MouseWindow.draw_commands(obj,p);self.assertEqual(obj.default_command,('ok',))
  obj.focus_action=('apply',);MouseWindow.draw_commands(obj,p);self.assertEqual(obj.default_command,('ok',))
 def test_mnemonic_and_focused_enter_route_exact_command(self):
  obj,p,image,calls=self.fixture()
  MouseWindow.button(obj,p,'&Browse...',(10,10,75,23),('browse',));MouseWindow.button(obj,p,'Cancel',(100,10,75,23),('cancel',));MouseWindow.draw_commands(obj,p)
  MouseWindow.key(obj,None,SimpleNamespace(keyval=Gdk.KEY_b,state=Gdk.ModifierType.MOD1_MASK));self.assertEqual(calls,[('browse',)])
  obj.focus_action=('cancel',);MouseWindow.key(obj,None,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));self.assertEqual(calls[-1],('cancel',))
 def test_press_out_reenter_and_release_out_tolerance(self):
  obj,p,image,calls=self.fixture();MouseWindow.button(obj,p,'Cancel',(10,10,75,23),('cancel',))
  def e(x,y):return SimpleNamespace(x=x,y=y,button=1,type=Gdk.EventType.BUTTON_PRESS)
  MouseWindow.press(obj,None,e(20,20));self.assertTrue(obj.press_inside)
  MouseWindow.motion(obj,None,e(86,20));self.assertFalse(obj.press_inside)
  MouseWindow.motion(obj,None,e(84,20));self.assertTrue(obj.press_inside)
  MouseWindow.release(obj,None,e(85,20));self.assertEqual(calls,[])
  MouseWindow.press(obj,None,e(10,10));MouseWindow.release(obj,None,e(84,32));self.assertEqual(calls,[('cancel',)])
 def test_all_sixty_four_actual_mouse_label_native_button_states(self):
  manifest=ROOT/'private/shell-assets/mouse-command-references.json'
  if not manifest.exists():self.skipTest('Private original Mouse command matrix unavailable')
  from win95lx.assets.bitmap import BitmapFont
  from win95lx.shell.widgets import Painter,FACE
  from win95lx.shell.command_button import draw_command_button
  font=BitmapFont((manifest.parent/'ms-sans-serif-8.fnt').read_bytes());cases=json.loads(manifest.read_text())['cases'];self.assertEqual(len(cases),64)
  for case in cases:
   with self.subTest(label=case['raw_label'],state=case['state_index']):
    path=manifest.parent/case['file'];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),case['png_sha256'])
    expected=cairo.ImageSurface.create_from_png(str(path));image=cairo.ImageSurface(cairo.FORMAT_RGB24,79,27);p=Painter(cairo.Context(image),font);p.fill(0,0,79,27,FACE);state=case['state_index']
    draw_command_button(p,case['raw_label'],(2,2,75,23),default=state in (1,3,5,7),focused=state in (2,3,5),pressed=state in (4,5),enabled=state not in (6,7));image.flush();aa=bytes(image.get_data());bb=bytes(expected.get_data());indices=(2,1,0) if sys.byteorder=='little' else (1,2,3)
    for y in range(27):
     for x in range(79):
      a=y*image.get_stride()+x*4;b=y*expected.get_stride()+x*4;self.assertEqual(tuple(aa[a+i] for i in indices),tuple(bb[b+i] for i in indices),(x,y))
