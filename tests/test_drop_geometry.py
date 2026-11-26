from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.shell.drop_geometry import contains,drag_started,folder_drop_rect


class NativeDropGeometry(unittest.TestCase):
    def test_short_label_accepts_measured_margins(self):
        rect=folder_drop_rect(33,77,28)
        for point in ((42,94),(88,94),(66,76),(66,128)):
            self.assertTrue(contains(rect,*point),point)
        for point in ((40,94),(90,94),(66,74),(66,130)):
            self.assertFalse(contains(rect,*point),point)

    def test_drag_requires_measured_movement(self):
        self.assertFalse(drag_started(2,0))
        self.assertFalse(drag_started(0,-3))
        self.assertTrue(drag_started(4,0))
        self.assertTrue(drag_started(0,-4))

    def test_long_labels_expand_within_their_cell(self):
        left,top,width,height=folder_drop_rect(100,100,200)
        self.assertEqual(width,75)
        self.assertEqual(height,54)
        self.assertLessEqual(left,116)
        self.assertTrue(contains((left,top,width,height),132,120))
