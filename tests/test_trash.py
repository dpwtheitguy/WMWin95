from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.trash import TrashStore


class RecycleBin(unittest.TestCase):
    def test_delete_restore_collision_and_distinct_names(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            trash=TrashStore(root/'trash')
            path=root/'A %.txt'
            path.write_text('one')
            name=trash.put(path)
            self.assertFalse(path.exists())
            self.assertEqual(trash.entries()[0][1],path)
            path.write_text('two')
            with self.assertRaises(FileExistsError):
                trash.restore(name)
            self.assertEqual(path.read_text(),'two')
            self.assertEqual((trash.files/name).read_text(),'one')
            second=trash.put(path)
            self.assertNotEqual(name,second)
            trash.restore(name)
            self.assertEqual(path.read_text(),'one')
            trash.delete(second)
            self.assertFalse(trash.entries())

    def test_folder_round_trip_preserves_nested_files(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'Source'/'Nested').mkdir(parents=True)
            (root/'Source'/'Nested'/'file.txt').write_text('data')
            trash=TrashStore(root/'trash')
            name=trash.put(root/'Source')
            trash.restore(name)
            self.assertEqual((root/'Source/Nested/file.txt').read_text(),'data')
