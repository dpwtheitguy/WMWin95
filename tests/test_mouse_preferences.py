import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.mouse_preferences import MousePreferences,MouseController,SCHEMES,ROLES
class MouseTests(unittest.TestCase):
 def test_defaults_and_invalid_settings(self):
  with TemporaryDirectory() as f:
   path=Path(f)/'mouse.json';self.assertEqual(MousePreferences.load(path),MousePreferences())
   for value in ('{}','broken','{"speed":0}','{"left_handed":1}','{"scheme":"unknown"}'):
    path.write_text(value);self.assertEqual(MousePreferences.load(path),MousePreferences())
 def test_basic_default_and_correct_resize_role_order(self):
  self.assertEqual(MousePreferences().scheme,'(None)')
  self.assertIn('3D Pointers',SCHEMES);self.assertIn('Animated Hourglasses',SCHEMES)
  self.assertEqual(len(ROLES),14)
  self.assertEqual([role for role,label in ROLES[8:12]],['size4','size3','size2','size1'])
 def test_apply_cancel_and_restart(self):
  with TemporaryDirectory() as f:
   path=Path(f)/'mouse.json';backend=Mock();backend.snapshot.return_value=('before',);session=Mock();c=MouseController(path,backend,session)
   c.pending=replace(c.pending,left_handed=True,double_click_ms=100,speed=10,scheme=SCHEMES[2]);c.cancel()
   self.assertFalse(path.exists());backend.apply.assert_not_called()
   c.pending=replace(c.pending,left_handed=True,double_click_ms=900,speed=1);c.apply()
   self.assertEqual(MousePreferences.load(path),c.applied);session.assert_called_with(c.applied)
   self.assertEqual(MouseController(path,backend,session).pending,c.applied)
 def test_backend_failure_rolls_back_without_persisting(self):
  with TemporaryDirectory() as f:
   path=Path(f)/'mouse.json';backend=Mock();backend.snapshot.return_value=('before',);backend.apply.side_effect=RuntimeError('busy');session=Mock();c=MouseController(path,backend,session)
   c.pending=replace(c.pending,left_handed=True)
   with self.assertRaises(RuntimeError):c.apply()
   backend.restore.assert_called_with(('before',));self.assertFalse(path.exists());self.assertFalse(c.applied.left_handed)
 def test_save_failure_restores_backend_and_session(self):
  with TemporaryDirectory() as f:
   path=Path(f)/'blocked/mouse.json';path.parent.write_text('file');backend=Mock();session=Mock();c=MouseController(path,backend,session);c.pending=replace(c.pending,speed=10)
   with self.assertRaises(OSError):c.apply()
   backend.restore.assert_called_once();session.assert_called_with(c.applied);self.assertEqual(c.applied.speed,5)
 def test_boundaries_and_unknown_custom_roles(self):
  for change in ({'speed':11},{'speed':True},{'double_click_ms':99},{'double_click_ms':901},{'overrides':{'bad':'x'}}):
   with self.assertRaises(ValueError):replace(MousePreferences(),**change).validate()
