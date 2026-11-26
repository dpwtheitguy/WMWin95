import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.namespace import create_shortcut,shortcut_target
from win95lx.shell.explorer_menu import computer_file_rows

class NamespaceTests(unittest.TestCase):
    def test_empty_and_namespace_selections_have_different_capabilities(self):
        empty=computer_file_rows(selection=None)
        disk=computer_file_rows(selection='(C:)')
        panel=computer_file_rows(selection='Control Panel')
        self.assertTrue(all(not row.enabled for row in empty[:4]))
        self.assertTrue(disk[0].enabled);self.assertTrue(disk[3].enabled)
        self.assertTrue(panel[0].enabled);self.assertFalse(panel[3].enabled)
        self.assertFalse(panel[1].enabled)
    def test_shortcuts_round_trip_and_do_not_overwrite(self):
        with TemporaryDirectory() as root:
            first=create_shortcut(root,'Control Panel');second=create_shortcut(root,'Control Panel')
            self.assertNotEqual(first,second)
            self.assertEqual(shortcut_target(first),'control')
            self.assertEqual(shortcut_target(second),'control')
    def test_unknown_links_never_execute_commands(self):
        with TemporaryDirectory() as root:
            link=Path(root)/'bad.desktop'
            link.write_text('[Desktop Entry]\nType=Application\nExec=anything\n')
            self.assertIsNone(shortcut_target(link))
            link.write_text('[Desktop Entry]\nType=Link\nURL=win95lx:unrecognized\n')
            self.assertIsNone(shortcut_target(link))
