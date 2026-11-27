import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.command_button import metrics,parse_label,resolve_default,draw_command_button

class Font:
    height=13
    def width(self,text):return sum(7 if char.isupper() else 6 for char in text)
    def glyph(self,char):return (7 if char.isupper() else 6,[(1,2),(2,2),(1,3),(2,4)])

class CommandButtonTests(unittest.TestCase):
    def test_win32_mnemonic_markers_do_not_consume_label_width(self):
        self.assertEqual(parse_label('&Apply'),('Apply',0));self.assertEqual(parse_label('A&dd...'),('Add...',1));self.assertEqual(parse_label('P&roperties'),('Properties',1));self.assertEqual(parse_label('Save && Exit'),('Save & Exit',None))
    def test_native_label_origin_and_pressed_offset(self):
        normal=metrics(Font(),'OK',(10,20,75,23));pressed=metrics(Font(),'OK',(10,20,75,23),pressed=True)
        self.assertEqual(normal.text_origin,(40,24));self.assertEqual(pressed.text_origin,(41,25));self.assertEqual(normal.rect,(10,20,75,23))
    def test_solid_focus_rectangle_changes_inset_with_default_border(self):
        self.assertEqual(metrics(Font(),'OK',(10,20,75,23),focused=True).focus_rect,(13,23,69,17))
        self.assertEqual(metrics(Font(),'OK',(10,20,75,23),focused=True,default=True).focus_rect,(14,24,67,15))
    def test_disabled_controls_cannot_acquire_focus_or_pressed_state(self):
        state=metrics(Font(),'&Apply',(0,0,75,23),enabled=False,pressed=True,focused=True,default=True)
        self.assertFalse(state.pressed);self.assertFalse(state.focused);self.assertIsNone(state.focus_rect);self.assertTrue(state.default)
    def test_default_moves_to_one_enabled_focused_command(self):
        enabled={'ok':True,'cancel':True,'add':True,'apply':False}
        for focus,expected in (('add','add'),('cancel','cancel'),('edit','ok'),('apply','ok'),(None,'ok')):
            selected=resolve_default('ok',focus,enabled);self.assertEqual(selected,expected);self.assertEqual(sum(key==selected for key in enabled),1)
        self.assertIsNone(resolve_default('missing','edit',enabled));self.assertIsNone(resolve_default('ok','ok',{'ok':False}))
    def test_hwnd_hit_bounds_include_the_frame_and_exclude_the_outside(self):
        state=metrics(Font(),'OK',(10,20,75,23),default=True)
        for point in ((10,20),(84,42),(11,21)):self.assertTrue(state.contains(*point))
        for point in ((9,20),(85,20),(10,19),(10,43)):self.assertFalse(state.contains(*point))
    def test_invalid_geometry_and_state_types_are_rejected(self):
        for rect in ((0,0,3,23),(0,0,75,3),(0.5,0,75,23),(True,0,75,23)):
            with self.assertRaises(ValueError):metrics(Font(),'OK',rect)
        with self.assertRaises(TypeError):metrics(Font(),'OK',(0,0,75,23),default=1)
    def test_explicit_mnemonic_index_and_character(self):
        self.assertEqual(metrics(Font(),'Properties',(0,0,108,23),mnemonic='r').mnemonic,1)
        self.assertEqual(metrics(Font(),'Properties',(0,0,108,23),mnemonic=3).mnemonic,3)
        self.assertIsNone(metrics(Font(),'OK',(0,0,75,23),mnemonic=5).mnemonic)
    def test_every_state_keeps_paint_inside_hwnd_even_for_long_labels(self):
        import cairo
        from win95lx.shell.widgets import Painter
        for width,height in ((75,23),(108,23),(10,8),(4,4)):
            for default,focus,pressed,enabled in ((False,False,False,True),(True,True,False,True),(True,True,True,True),(False,False,True,True),(True,True,True,False)):
                surface=cairo.ImageSurface(cairo.FORMAT_RGB24,width+10,height+10);context=cairo.Context(surface);p=Painter(context,Font());p.fill(0,0,width+10,height+10,(255,0,255));before=bytes(surface.get_data())
                draw_command_button(p,'A very long &label',(5,5,width,height),default=default,focused=focus,pressed=pressed,enabled=enabled);surface.flush();after=bytes(surface.get_data());stride=surface.get_stride()
                for y in range(height+10):
                    for x in range(width+10):
                        if not (5<=x<5+width and 5<=y<5+height):self.assertEqual(after[y*stride+x*4:y*stride+x*4+4],before[y*stride+x*4:y*stride+x*4+4])
    def test_legacy_default_painter_reproduces_outside_hwnd_defect(self):
        import cairo
        from win95lx.shell.widgets import Painter
        surface=cairo.ImageSurface(cairo.FORMAT_RGB24,85,33);p=Painter(cairo.Context(surface),Font());p.fill(0,0,85,33,(255,0,255));before=bytes(surface.get_data());p.button('OK',5,5,75,23,default=True);surface.flush();after=bytes(surface.get_data());stride=surface.get_stride();changed=0
        for y in range(33):
            for x in range(85):
                if not (5<=x<80 and 5<=y<28):changed+=after[y*stride+x*4:y*stride+x*4+4]!=before[y*stride+x*4:y*stride+x*4+4]
        self.assertEqual(changed,200)
if __name__=='__main__':unittest.main()
