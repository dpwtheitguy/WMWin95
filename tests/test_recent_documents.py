from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.recent_documents import LIMIT,RecentDocuments


class RecentDocumentHistory(unittest.TestCase):
    def test_successful_files_deduplicate_persist_and_expire(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            history=RecentDocuments(root/'history.json')
            files=[]
            for index in range(LIMIT+2):
                path=root/f'{index:02d}.txt'
                path.write_text(str(index))
                files.append(path)
                history.add(path)
            self.assertEqual(len(history.paths()),LIMIT)
            self.assertNotIn(files[0],history.paths())
            history.add(files[3])
            self.assertEqual(history.paths()[0],files[3])
            self.assertEqual(len(history.paths()),LIMIT)
            reloaded=RecentDocuments(history.path)
            self.assertEqual(history.paths(),reloaded.paths())
            files[3].unlink()
            self.assertNotIn(files[3],history.entries())
            history.add(root/'missing.txt')
            self.assertNotIn(root/'missing.txt',history.paths())

    def test_bad_history_can_be_replaced_by_a_successful_open(self):
        with TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/'history.json'
            path.write_text('invalid json')
            document=root/'A.txt'
            document.write_text('a')
            history=RecentDocuments(path)
            self.assertEqual(history.entries(),[])
            history.add(document)
            self.assertEqual(history.entries(),[document])
