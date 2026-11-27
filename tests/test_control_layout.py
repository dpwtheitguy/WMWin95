import sys
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from win95lx.control_panel.display_settings import slider_center, slider_index
from win95lx.display_modes import DISPLAY_MODES, set_resolution
from win95lx.shell.combo_box import ComboBox
from win95lx.shell.system_menu import options
from win95lx.shell.menu_layout import explorer_menubar, popup_width, NOTEPAD_HELP_ROWS, NOTEPAD_HELP_WIDTH
from win95lx.shell.desktop_icons import DesktopIcons, desktop_file_slots
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.shell.taskbar import BUTTON_GAP, START_X, button_width, title_that_fits


class Font:
    @staticmethod
    def width(text, bold=False):
        return len(text) * (7 if bold else 6)


class ControlLayout(unittest.TestCase):
    def test_explorer_text_origins_and_adjacent_hit_targets(self):
        entries = list(explorer_menubar(Font()))
        self.assertEqual([entry[1] for entry in entries], [24, 55, 89, 128, 157, 217])
        for (_, x, left, width), (_, _, next_left, _) in zip(entries, entries[1:]):
            self.assertLessEqual(left, x)
            self.assertLess(x, left+width)
            self.assertEqual(left+width, next_left)
        self.assertEqual(popup_width(Font(), ['Close', 'Select All']), 100)

    def test_help_topics_and_about_fit_in_native_popup(self):
        topics, separator, about = NOTEPAD_HELP_ROWS
        self.assertIsNone(separator)
        self.assertNotEqual(topics[1], about[1])
        self.assertLessEqual(popup_width(Font(), [topics[1:], about[1:]]), NOTEPAD_HELP_WIDTH)

    def test_desktop_file_positions_persist(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'desktop-icons.json'
            icons = DesktopIcons(path)
            slots = list(desktop_file_slots([('Projects', True), ('note.txt', False)], 600))
            self.assertEqual(slots[0], ('Projects', True, (0, 77)))
            icons.move('file:Projects', (90, 120))
            self.assertEqual(DesktopIcons(path).position('file:Projects', 800, 600), (90,120))
            self.assertEqual(icons.position('file:note.txt', 800, 600, slots[1][2]), slots[1][2])

    def test_new_desktop_icons_avoid_moved_system_icons(self):
        slots = list(desktop_file_slots([('Source', True), ('Target', True)], 600,
                                       [(0,2),(0,90)]))
        self.assertEqual([point for _,_,point in slots], [(0,227),(0,302)])

    def test_desktop_native_pitch_fits_wrapped_labels_and_new_columns(self):
        entries=[('Long file name '+str(i),False) for i in range(9)]
        points=[point for _,_,point in desktop_file_slots(entries,600,[(0,2)])]
        self.assertEqual(points[:3],[(0,77),(0,152),(0,227)])
        self.assertEqual(points[6:9],[(75,2),(75,77),(75,152)])
        # Two native 13-pixel text lines at y+36 fit before the next row.
        self.assertLess(36+2*13,75)
        self.assertEqual(DesktopIcons.clamp(999,999,800,600),(725,497))

    def test_active_randr_mode_skips_reconfiguration(self):
        with patch('win95lx.display_modes._run', return_value=(
                'Virtual-1 connected primary 800x600+0+0\n   800x600 60.00*+\n')) as run:
            set_resolution(800,600)
            run.assert_called_once_with('xrandr','--query')

    def test_combo_rows_and_keyboard_endpoints(self):
        combo = ComboBox(('Center', 'Tile'))
        combo.open()
        self.assertTrue(combo.focused and combo.expanded)
        combo.step(-1)
        self.assertEqual(combo.value, 0)
        combo.step(1)
        combo.step(1)
        self.assertEqual(combo.value, 1)
        self.assertEqual([combo.row_at(0, y, 75) for y in (20, 21, 22, 34, 35, 47, 48)],
                         [None, None, 0, 0, 1, 1, None])
        self.assertIsNone(combo.row_at(75, 22, 75))

    def test_system_menu_profiles(self):
        def available(**profile):
            return [command for command, _, _, enabled in options(**profile) if enabled]

        self.assertEqual(available(resizable=True, minimizable=True, maximized=False),
                         ['move', 'size', 'minimize', 'maximize', 'close'])
        self.assertEqual(available(resizable=False, minimizable=True, maximized=False),
                         ['move', 'minimize', 'close'])
        self.assertEqual(available(resizable=True, minimizable=True, maximized=True),
                         ['restore', 'minimize', 'close'])

    def test_resolution_slider_reaches_every_mode(self):
        count = len(DISPLAY_MODES)
        for index in range(count):
            # More modes than native track pixels can share a detent. Dragging
            # chooses the nearest; the app's arrow keys traverse all modes.
            self.assertLessEqual(abs(slider_index(slider_center(index,count),count)-index),1)
        self.assertEqual(slider_index(0, count), 0)
        self.assertEqual(slider_index(500, count), count-1)

    def test_scrollbar_stops_and_round_trip(self):
        bar = VerticalScrollbar(92, 14)
        self.assertEqual((bar.thumb_top(0), bar.thumb_top(14)), (16, 55))
        for index in range(15):
            self.assertEqual(bar.value_at(bar.thumb_top(index)), index)
        self.assertEqual(bar.value_at(-200), 0)
        self.assertEqual(bar.value_at(200), 14)

    def test_task_buttons_fit_with_room_for_tray(self):
        self.assertEqual(button_width(3, 725), 160)
        width = button_width(10, 725)
        self.assertLessEqual(START_X+10*width+9*BUTTON_GAP, 725)
        self.assertEqual(title_that_fits(Font(), 'Document - WordPad', 63, True), 'Docume...')


if __name__ == '__main__':
    unittest.main()
