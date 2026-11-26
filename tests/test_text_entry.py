import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.text_entry import TextEntry

class EntryTests(unittest.TestCase):
    def test_selected_text_replaces_then_caret_edits(self):
        entry=TextEntry('My Computer');entry.select_all();entry.key('c','C')
        entry.key('colon',':');entry.key('slash','/');self.assertEqual(entry.text,'C:/')
        entry.key('Left');entry.key('BackSpace');self.assertEqual(entry.text,'C/')
        entry.key('Home');entry.key('Delete');self.assertEqual(entry.text,'/')
    def test_shift_selection_and_control_a(self):
        entry=TextEntry('folder',6,6);entry.key('Left',shift=True);entry.key('Left',shift=True)
        self.assertEqual(entry.selection,[4,6]);entry.key('x','X');self.assertEqual(entry.text,'foldX')
        entry.key('a',ctrl=True);entry.key('Delete');self.assertEqual(entry.text,'')
