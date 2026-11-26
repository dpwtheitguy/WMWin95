import struct,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.model import DesktopState,DriveView
from win95lx.shell.desktop_icons import ShortcutIcons
from win95lx.shell.shortcut_folders import ShortcutFolders
from win95lx.explorer.drive_browser import DriveBrowser
from win95lx.assets.bitmap import BitmapFont,icon_dib
class ShellState(unittest.TestCase):
    def test_drive_navigation_paginates_and_preserves_state_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'home').mkdir()
            (root/'home'/'notes.txt').write_text('notes')
            for index in range(20):
                (root/f'file-{index:02d}').touch()
            drive = DriveBrowser(root)
            drive.navigate('.')
            first = drive.page(438, 232)
            self.assertEqual(first[0], ('home', True))
            drive.scroll = 50
            self.assertIn(('file-19', False), drive.page(438, 232))
            drive.navigate('home')
            self.assertEqual(drive.title, 'C:\\home')
            self.assertEqual(drive.entries, [('notes.txt', False)])
            self.assertEqual(drive.scroll, 0)
            with self.assertRaises(PermissionError):
                drive.navigate('../..')
            self.assertEqual(drive.title, 'C:\\home')
    def test_shortcut_moves_between_folders_and_reloads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'folders.json'
            tree = ShortcutFolders(path)
            self.assertTrue(tree.move('calc', 'games'))
            tree = ShortcutFolders(path)
            self.assertIn('Calculator', [row[0] for row in tree.entries('games')])
            self.assertNotIn('Calculator', [row[0] for row in tree.entries('accessories')])
            self.assertTrue(tree.move('calc', 0))
            self.assertIn('Calculator', [row[0] for row in ShortcutFolders(path).entries(0)])
            self.assertFalse(tree.move('calc', None))
            self.assertFalse(tree.move('unknown', 0))

    def test_start_folders_can_be_open_side_by_side(self):
        state = DesktopState()
        state.open('start-folder', 0)
        programs = state.active
        state.open('start-folder', 'accessories')
        self.assertEqual(len(state.windows), 2)
        state.open('start-folder', 0)
        self.assertIs(state.active, programs)
    def test_shortcut_positions_survive_reload_and_stay_in_their_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'icons.json'
            layout = ShortcutIcons(path)
            layout.move('accessories', 'Calculator', (20, 100))
            layout.move('games', 'Minesweeper', (44, 73))
            reloaded = ShortcutIcons(path)
            self.assertEqual(reloaded.position('accessories', 'Calculator', (0, 0)), (20, 100))
            self.assertEqual(reloaded.position('games', 'Minesweeper', (0, 0)), (44, 73))
            self.assertEqual(reloaded.position('games', 'Calculator', (10, 10)), (10, 10))
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
