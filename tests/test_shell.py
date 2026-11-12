import struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.model import DesktopState,DriveView
from win95lx.assets.bitmap import BitmapFont,icon_dib
class ShellState(unittest.TestCase):
    def test_existing_window_restores_and_focuses(self):
        s=DesktopState();s.open('computer');old=s.active;s.active.minimized=True;s.open('control');s.open('computer');self.assertIs(s.active,old);self.assertFalse(old.minimized);self.assertEqual(len(s.windows),2)
    def test_task_switch_restores_minimized_window(self):
        s=DesktopState();s.open('computer');s.open('control');target=s.active;target.minimized=True;s.cycle();self.assertIs(s.active,target);self.assertFalse(target.minimized)
    def test_modal_close_does_not_close_underlying_window(self):
        s=DesktopState();s.open('computer');s.dialog='shutdown';s.close();self.assertIsNone(s.dialog);self.assertEqual(len(s.windows),1)
    def test_drive_rejects_escape_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'drive';root.mkdir();outside=Path(tmp)/'private';outside.write_text('secret');(root/'escape').symlink_to(outside);(root/'document.txt').write_text('hello');d=DriveView(root)
            self.assertEqual(d.entries(),[('document.txt',False)])
            with self.assertRaises(PermissionError):d.entries('..')
    def test_icon_mask_and_palette(self):
        b=bytearray(40+8+4+4);struct.pack_into('<IiiHHI',b,0,40,1,2,1,1,0);b[44:48]=bytes([0,0,255,0]);b[48]=128
        self.assertEqual(icon_dib(b),(1,1,[(255,0,0,255)]));b[52]=128;self.assertEqual(icon_dib(b)[2][0][3],0)
    def test_original_style_font_uses_column_major_glyph_bits(self):
        b=bytearray(140);struct.pack_into('<HI',b,0,0x200,len(b));struct.pack_into('<H',b,88,2);b[95]=b[96]=65;struct.pack_into('<I',b,105,130);b[130:135]=b'Test\0';struct.pack_into('<HH',b,118,9,122);b[122:126]=bytes([128,0,128,128]);font=BitmapFont(b)
        self.assertEqual(font.glyph('A'),(9,[(0,0),(8,0),(8,1)]));self.assertEqual(font.width('AA'),18)
if __name__=='__main__':unittest.main()
