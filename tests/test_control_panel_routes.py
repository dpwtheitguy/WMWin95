import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.catalog import implemented,entries,targets
from win95lx.shell.run_dialog import resolve_command
class ControlPanelRoutes(unittest.TestCase):
    def test_every_available_applet_has_one_route_and_native_run_alias(self):
        applets=implemented();self.assertEqual(len({x.key for x in applets}),len(applets))
        for applet in applets:
            self.assertEqual(targets()[applet.label],applet.key)
            self.assertEqual(resolve_command(applet.native_command),('open',applet.key))
        self.assertEqual(len(entries()),len(applets))
    def test_multimedia_and_sounds_are_distinct_original_entry_points(self):
        self.assertEqual(resolve_command('control mmsys.cpl'),('open','multimedia'))
        self.assertEqual(resolve_command('CONTROL.EXE MMSYS.CPL @1'),('open','sounds'))
        self.assertEqual(resolve_command('mmsys.cpl'),('open','multimedia'))
    def test_arguments_cannot_escape_the_applet_allowlist(self):
        for command in ('control mmsys.cpl; reboot','control mmsys.cpl @2','control ../../bad.cpl','control "mmsys.cpl" $(bad)'):
            self.assertIsNone(resolve_command(command))
if __name__=='__main__':unittest.main()
