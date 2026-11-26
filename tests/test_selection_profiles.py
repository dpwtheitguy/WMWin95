import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.commands import Context,Item,file_commands
from win95lx.explorer.namespace import create_file_shortcut,resolve_shortcut,read_shortcut,write_shortcut,Shortcut,display_name
from win95lx.explorer.webview_details import describe,wrapped

class ProfileTests(unittest.TestCase):
    def test_selected_drive_adds_verbs_and_default_open(self):
        rows=file_commands(Context('computer',(Item('drive','(C:)',False),)))
        active={r.command for r in rows if r and r.enabled}
        self.assertTrue({'open','explore','find','format','shortcut','properties'}<=active)
        self.assertFalse(next(r for r in rows if r and r.command=='delete').enabled)
    def test_file_folder_mixed_and_readonly_contexts(self):
        for kind in ('file','folder','shortcut'):
            rows={r.command:r for r in file_commands(Context('filesystem',(Item(kind,'item'),))) if r}
            self.assertTrue(rows['open'].default);self.assertTrue(rows['shortcut'].enabled)
            self.assertTrue(rows['rename'].enabled)
            self.assertEqual('explore' in rows,kind=='folder')
        rows={r.command:r for r in file_commands(Context('filesystem',(Item('file','a'),Item('folder','b')))) if r}
        self.assertFalse(rows['rename'].enabled);self.assertFalse(rows['properties'].enabled)
        self.assertNotIn('explore',rows)
        rows={r.command:r for r in file_commands(Context('filesystem',(Item('file','a',False),))) if r}
        self.assertFalse(rows['trash'].enabled);self.assertFalse(rows['rename'].enabled)
    def test_file_and_folder_shortcuts_survive_move_and_rename(self):
        with TemporaryDirectory() as root:
            root=Path(root);target=root/'a % ü.txt';target.write_text('preserve')
            link=create_file_shortcut(root,target);moved=root/'renamed.desktop';link.rename(moved)
            self.assertEqual(Path(resolve_shortcut(moved).target),target)
            folder=root/'folder';folder.mkdir();nested=create_file_shortcut(root,folder)
            self.assertEqual(Path(resolve_shortcut(nested).target),folder)
            duplicate=create_file_shortcut(root,target)
            self.assertTrue(duplicate.exists());self.assertEqual(target.read_text(),'preserve')
            self.assertNotIn('.desktop',display_name(moved.name))
    def test_broken_cycles_and_nonexecuting_links(self):
        with TemporaryDirectory() as root:
            root=Path(root);target=root/'target.txt';target.write_text('x')
            link=create_file_shortcut(root,target);target.unlink()
            with self.assertRaises(FileNotFoundError):resolve_shortcut(link)
            a=root/'a.desktop';b=root/'b.desktop'
            for path,destination in ((a,b),(b,a)):
                path.write_text(f'[Desktop Entry]\nType=Link\nURL={destination.as_uri()}\n')
            with self.assertRaises(ValueError):resolve_shortcut(a)
    def test_multiselection_template_limits(self):
        strings={'templates':{'mycomp':{'strings':{'L_Intro_Text':'intro'}}},'infotips':{'CONTROLPANEL_IT':'native description'}}
        self.assertEqual(describe(None,strings).description,'intro')
        self.assertEqual(describe(['Control Panel'],strings).description,'native description')
        self.assertEqual(len(describe(list(map(str,range(16))),strings).names),16)
        self.assertEqual(describe(list(map(str,range(17))),strings).names,())
