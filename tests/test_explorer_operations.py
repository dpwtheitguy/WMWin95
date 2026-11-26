from pathlib import Path
from tempfile import TemporaryDirectory
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.file_operations import FileClipboard, child_name
from win95lx.explorer.presentation import DriveView


class ExplorerFileOperations(unittest.TestCase):
    def test_copy_move_and_existing_destination(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'target').mkdir()
            (root/'report.txt').write_text('original')
            paths = (Path('report.txt'),)
            view = DriveView(root)
            copied, errors = FileClipboard(paths).transfer(view, 'target')
            self.assertEqual(errors, [])
            self.assertEqual(copied.sources, paths)
            (root/'target/report.txt').write_text('other')
            cut = FileClipboard(paths, True)
            remaining, errors = cut.transfer(view, 'target')
            self.assertTrue(errors)
            self.assertEqual(remaining, cut)
            self.assertEqual((root/'report.txt').read_text(), 'original')
            self.assertEqual((root/'target/report.txt').read_text(), 'other')
            (root/'target/report.txt').unlink()
            remaining, errors = cut.transfer(view, 'target')
            self.assertFalse(errors)
            self.assertFalse(remaining.sources)
            self.assertFalse((root/'report.txt').exists())
            self.assertEqual((root/'target/report.txt').read_text(), 'original')

    def test_same_folder_copy_uses_native_numbered_names(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Readme.txt').write_text('original')
            clipboard = FileClipboard((Path('Readme.txt'),))
            for _ in range(2):
                _, errors = clipboard.transfer(DriveView(root),'.')
                self.assertFalse(errors)
            self.assertEqual((root/'Copy of Readme.txt').read_text(),'original')
            self.assertEqual((root/'Copy (2) of Readme.txt').read_text(),'original')
            self.assertEqual((root/'Readme.txt').read_text(),'original')

    def test_move_within_same_directory_is_a_noop(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'Folder').mkdir()
            (root/'note.txt').write_text('unchanged')
            sources = (Path('Folder'),Path('note.txt'))
            remaining, errors = FileClipboard(sources,True).transfer(DriveView(root),'.')
            self.assertFalse(errors)
            self.assertFalse(remaining.sources)
            self.assertTrue((root/'Folder').is_dir())
            self.assertEqual((root/'note.txt').read_text(),'unchanged')

    def test_directory_cannot_copy_into_itself(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'folder/subfolder').mkdir(parents=True)
            clipboard = FileClipboard((Path('folder'),))
            _, errors = clipboard.transfer(DriveView(root), 'folder/subfolder')
            self.assertTrue(errors)
            self.assertEqual(list((root/'folder/subfolder').iterdir()), [])
            for name in ('', '.', '..', 'bad/name', 'bad'+chr(0)+'name'):
                with self.assertRaises(ValueError):
                    child_name(name)


class IndependentFolderState(unittest.TestCase):
    def test_native_large_icon_grid_origins(self):
        from win95lx.explorer.drive_browser import DriveBrowser
        self.assertEqual(DriveBrowser.icon_position(0, 5), (5,1))
        self.assertEqual(DriveBrowser.icon_position(1, 5), (80,1))
        self.assertEqual(DriveBrowser.icon_position(5, 5), (5,76))

    def test_two_windows_keep_path_selection_and_scroll(self):
        from win95lx.explorer.drive_browser import DriveBrowser
        from win95lx.shell.model import DesktopState
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for folder in ('A', 'B'):
                (root/folder).mkdir()
                for index in range(30):
                    (root/folder/f'{index:02d}.txt').touch()
            state = DesktopState()
            state.open('drive', Path('A'))
            first = state.active
            first.browser = DriveBrowser(root)
            first.browser.navigate('A')
            first.browser.selection = {'01.txt'}
            first.browser.scroll = 2
            state.open('drive', Path('B'))
            second = state.active
            second.browser = DriveBrowser(root)
            second.browser.navigate('B')
            second.browser.selection = {'03.txt'}
            second.browser.scroll = 1
            state.open('drive', Path('A'))
            self.assertIs(state.active, first)
            self.assertEqual((first.browser.directory, first.browser.selection, first.browser.scroll),
                             (Path('A'), {'01.txt'}, 2))
            self.assertEqual((second.browser.directory, second.browser.selection, second.browser.scroll),
                             (Path('B'), {'03.txt'}, 1))

    def test_refresh_preserves_surviving_selection_and_scroll(self):
        from win95lx.explorer.drive_browser import DriveBrowser
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(30):
                (root/f'{index:02d}.txt').touch()
            browser = DriveBrowser(root)
            browser.navigate('.')
            browser.selection = {'01.txt', '02.txt'}
            browser.anchor = '01.txt'
            browser.scroll = 2
            (root/'01.txt').unlink()
            browser.refresh()
            self.assertEqual(browser.selection, {'02.txt'})
            self.assertIsNone(browser.anchor)
            self.assertEqual(browser.scroll, 2)
