import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.edit_commands import EditContext,edit_rows
from win95lx.explorer.file_operations import FileClipboard
from win95lx.explorer.presentation import DriveView

class EditTests(unittest.TestCase):
    def rows(self,**kwargs):return {r[2]:r[3] for r in edit_rows(EditContext(**kwargs)) if r}
    def test_empty_selection_disables_cut_and_copy(self):
        for entries in (0,5):
            rows=self.rows(entries=entries);self.assertFalse(rows['cut']);self.assertFalse(rows['copy'])
    def test_single_and_multi_selection_enable_transfer(self):
        for count in (1,5):
            rows=self.rows(selected=count,entries=5);self.assertTrue(rows['cut']);self.assertTrue(rows['copy'])
    def test_protected_namespace_selection_is_not_transferable(self):
        rows=self.rows(selected=1,selection_transferable=False);self.assertFalse(rows['cut']);self.assertFalse(rows['copy'])
    def test_clipboard_and_destination_gate_both_paste_variants(self):
        for clipboard in (False,True):
            for writable in (False,True):
                rows=self.rows(clipboard=clipboard,destination_writable=writable)
                self.assertEqual(rows['paste'],clipboard and writable);self.assertEqual(rows['paste-shortcut'],clipboard and writable)
    def test_empty_folder_selection_commands_are_disabled(self):
        for entries in (0,7):
            rows=self.rows(entries=entries);self.assertEqual(rows['select-all'],bool(entries));self.assertEqual(rows['invert'],bool(entries))
    def test_undo_not_advertised_without_a_safe_operation_journal(self):
        self.assertFalse(self.rows(selected=1,clipboard=True)['undo'])
    def test_copy_same_folder_repeat_preserves_original(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'report.txt').write_text('original');view=DriveView(root)
            clip=FileClipboard((Path('report.txt'),))
            for _ in range(2):
                result,errors=clip.transfer(view,Path('.'));self.assertFalse(errors);self.assertEqual(result,clip)
            self.assertEqual((root/'Copy of report.txt').read_text(),'original')
            self.assertEqual((root/'Copy (2) of report.txt').read_text(),'original')
    def test_cut_only_moves_on_paste_and_clears_successful_sources(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'dest').mkdir();source=root/'a.txt';source.write_text('a');view=DriveView(root)
            clip=FileClipboard((Path('a.txt'),),True);self.assertTrue(source.exists())
            result,errors=clip.transfer(view,Path('dest'));self.assertFalse(errors);self.assertFalse(result.sources)
            self.assertFalse(source.exists());self.assertEqual((root/'dest/a.txt').read_text(),'a')
    def test_failed_cut_retains_source_and_clipboard(self):
        with TemporaryDirectory() as folder:
            root=Path(folder);(root/'dest').mkdir();(root/'a').write_text('source');(root/'dest/a').write_text('target')
            clip=FileClipboard((Path('a'),),True);result,errors=clip.transfer(DriveView(root),Path('dest'))
            self.assertTrue(errors);self.assertEqual(result,clip);self.assertEqual((root/'a').read_text(),'source');self.assertEqual((root/'dest/a').read_text(),'target')
