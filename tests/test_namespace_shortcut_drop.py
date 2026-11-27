import tempfile,unittest
from pathlib import Path
from win95lx.explorer.namespace import create_shortcut,read_shortcut
class NamespaceShortcutDropTests(unittest.TestCase):
 def test_drive_and_control_panel_are_links_not_filesystem_moves(self):
  with tempfile.TemporaryDirectory() as home:
   directory=Path(home)
   for label,target in (('(C:)','drive'),('Control Panel','control')):
    path=create_shortcut(directory,label);self.assertEqual(read_shortcut(path).target,target);self.assertEqual(read_shortcut(path).kind,'namespace');self.assertFalse(path.is_symlink());self.assertIn('Type = Link',path.read_text())
 def test_stale_target_does_not_invent_directory(self):
  with tempfile.TemporaryDirectory() as home:
   directory=Path(home)/'gone'
   with self.assertRaises(NotADirectoryError):create_shortcut(directory,'Control Panel')
   self.assertFalse(directory.exists())
 def test_file_target_and_existing_content_are_untouched(self):
  with tempfile.TemporaryDirectory() as home:
   file=Path(home)/'existing';file.write_text('keep')
   with self.assertRaises(NotADirectoryError):create_shortcut(file,'(C:)')
   self.assertEqual(file.read_text(),'keep')
 def test_duplicate_drop_preserves_previous_shortcut(self):
  with tempfile.TemporaryDirectory() as home:
   first=create_shortcut(home,'(C:)');before=first.read_bytes();second=create_shortcut(home,'(C:)');self.assertEqual(first.name,'Shortcut to  (C).desktop');self.assertEqual(second.name,'Shortcut (2) to  (C).desktop');self.assertNotEqual(first,second);self.assertEqual(first.read_bytes(),before);self.assertEqual(read_shortcut(first),read_shortcut(second))

 def test_partial_write_failure_removes_only_new_file(self):
  from unittest.mock import patch
  with tempfile.TemporaryDirectory() as home:
   original=Path(home)/'keep.txt';original.write_text('keep')
   with patch('configparser.ConfigParser.write',side_effect=OSError('disk full')):
    with self.assertRaises(OSError):create_shortcut(home,'(C:)')
   self.assertEqual(list(Path(home).iterdir()),[original]);self.assertEqual(original.read_text(),'keep')

 def test_folder_link_resolves_and_rejects_nonfolder_cycle_and_outside(self):
  from win95lx.explorer.namespace import folder_shortcut_destination,write_shortcut,Shortcut
  with tempfile.TemporaryDirectory() as home,tempfile.TemporaryDirectory() as outside:
   root=Path(home);folder=root/'Target';folder.mkdir();link=write_shortcut(root,'folder',Shortcut('path',str(folder)));self.assertEqual(folder_shortcut_destination(link,root),folder)
   file=root/'file';file.write_text('keep');bad=write_shortcut(root,'file',Shortcut('path',str(file)))
   with self.assertRaises(ValueError):folder_shortcut_destination(bad,root)
   external=write_shortcut(root,'outside',Shortcut('path',outside))
   with self.assertRaises(ValueError):folder_shortcut_destination(external,root)
   cycle=write_shortcut(root,'cycle',Shortcut('path',str(root/'Shortcut to cycle.desktop')))
   with self.assertRaises(ValueError):folder_shortcut_destination(cycle,root)
