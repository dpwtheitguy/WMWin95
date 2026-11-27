import json,sys,tempfile,unittest
from pathlib import Path
from dataclasses import replace
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.addremove_preferences import *

def fixture():
 return Catalogue((Component('desktop.patterns','Desktop patterns','desktop','Patterns',True,''),Component('explorer.future','Future feature','explorer','Not bound',False,'Runtime binding unavailable.')), (Programme('desktop-enhancements','Desktop Enhancements',(),True),Programme('demo','Managed demo',('win95lx-demo',))))
class Service:
 mutable=True;reason='No service'
 def __init__(self):
  self.state=snapshot((InstalledProgramme('desktop-enhancements','Desktop Enhancements',True,(),True),InstalledProgramme('demo','Managed demo',False)),(('desktop.patterns',False),('explorer.future',None)),123);self.calls=[];self.reads=0;self.fail=False;self.ignore=False;self.restore_fail=False
 def snapshot(self,catalogue):self.reads+=1;return self.state
 def execute(self,features,programmes,before,cancel):
  self.calls.append(('execute',features,programmes))
  if not self.ignore:
   current=self.state.with_changes(features,programmes);self.state=snapshot(current.programmes,current.features,123)
  if self.fail:raise RuntimeError('Injected service failure')
 def restore(self,before,features,programmes):
  self.calls.append(('restore',features,programmes))
  if self.restore_fail:raise SetupError('Injected recovery failure')
  current=self.state.with_changes(tuple((k,before.feature(k)) for k,_ in features),tuple((k,next(p.installed for p in before.programmes if p.id==k)) for k,_ in programmes));self.state=snapshot(current.programmes,current.features,123)
class AddRemoveTests(unittest.TestCase):
 def setup_controller(self):
  service=Service();backend=SetupBackend(fixture(),service);controller=SetupController(backend);controller.load();return service,backend,controller
 def test_root_catalogue_is_read_only_and_uses_existing_ids(self):
  data=json.loads((Path(__file__).resolve().parents[1]/'config/functional-profiles.json').read_text());c=Catalogue.from_data(data)
  self.assertEqual(len(c.components),len(data['features'])+len(data['presets']));self.assertTrue(all(not f.available for f in c.components));self.assertEqual(c.programmes[0].id,'desktop-enhancements')
 def test_catalogue_cache_reads_configuration_once_until_explicit_refresh(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'profiles.json';p.write_text(json.dumps({'schema_version':1,'features':[],'presets':[]}));load_catalogue.cache_clear();first=load_catalogue(str(p));p.unlink();self.assertIs(load_catalogue(str(p)),first)
 def test_snapshot_cache_has_no_repeated_service_query(self):
  s,b,c=self.setup_controller();self.assertEqual(s.reads,1)
  for _ in range(100):self.assertIs(b.preferences(),c.applied)
  self.assertEqual(s.reads,1);b.preferences(True);self.assertEqual(s.reads,2)
 def test_managed_reader_only_queries_allowlisted_packages(self):
  run=Mock(return_value=SimpleNamespace(returncode=0,stdout='win95lx-demo\t1.2\tinstalled\nlibc6\t9\tinstalled\n'))
  state=ReadOnlyPackages(run).snapshot(fixture());args=run.call_args.args[0]
  self.assertEqual(args[-2:],['--','win95lx-demo']);self.assertEqual(args[0],'dpkg-query');self.assertNotIn('shell',run.call_args.kwargs)
  self.assertEqual([p.id for p in state.programmes],['desktop-enhancements','demo']);self.assertTrue(state.programmes[1].installed);self.assertNotIn('libc6',str(state.programmes));self.assertIsNone(state.feature('desktop.patterns'))
 def test_partial_managed_package_set_is_not_reported_installed(self):
  catalogue=Catalogue((),(Programme('demo','Demo',('one','two')),));run=Mock(return_value=SimpleNamespace(returncode=1,stdout='one\t1\tinstalled\n'));state=ReadOnlyPackages(run).snapshot(catalogue);self.assertFalse(state.programmes[0].installed)
 def test_builtin_only_inventory_avoids_any_subprocess(self):
  run=Mock();state=ReadOnlyPackages(run).snapshot(Catalogue(()));run.assert_not_called();self.assertTrue(state.programmes[0].builtin and state.programmes[0].installed)
 def test_bad_ids_package_names_duplicates_and_schema_are_rejected(self):
  for ident in ('../bad','--remove','A space','x;rm'):
   with self.assertRaises(ValueError):Programme(ident,'Bad',('safe',)).validate()
  for package in ('--remove','evil;script','/tmp/x','bad name','UPPER'):
   with self.assertRaises(ValueError):Programme('demo','Demo',(package,)).validate()
  with self.assertRaises(ValueError):Catalogue((fixture().components[0],)*2).validate()
  with self.assertRaises(ValueError):Catalogue.from_data({'schema_version':True})
 def test_unavailable_features_cannot_be_toggled_or_saved(self):
  s,b,c=self.setup_controller()
  with self.assertRaisesRegex(SetupError,'binding'):c.set_feature('explorer.future',True)
  self.assertEqual(c.pending,c.applied);self.assertEqual(s.calls,[])
 def test_unknown_component_and_programme_are_refused(self):
  s,b,c=self.setup_controller()
  with self.assertRaises(SetupError):c.set_feature('unknown',True)
  with self.assertRaises(SetupError):c.set_programme('unknown',True)
  self.assertEqual(s.calls,[])
 def test_noop_and_cancel_do_not_call_installer(self):
  s,b,c=self.setup_controller();c.apply();self.assertEqual(s.calls,[]);c.set_feature('desktop.patterns',True);c.cancel();self.assertEqual(c.pending,c.applied);self.assertEqual(s.calls,[])
 def test_builtin_cannot_be_removed(self):
  s,b,c=self.setup_controller()
  with self.assertRaisesRegex(SetupError,'built-in'):c.set_programme('desktop-enhancements',False)
  self.assertEqual(s.calls,[])
 def test_readonly_service_cannot_apply_or_expose_working_toggle(self):
  b=SetupBackend(fixture(),ReadOnlyPackages(Mock(return_value=SimpleNamespace(returncode=1,stdout=''))));c=SetupController(b);c.load()
  with self.assertRaisesRegex(SetupError,'not installed'):c.set_feature('desktop.patterns',True)
  self.assertEqual(c.pending,c.applied)
 def test_apply_uses_typed_ids_and_authoritative_snapshot(self):
  s,b,c=self.setup_controller();c.set_feature('desktop.patterns',True);c.set_programme('demo',True);c.apply()
  self.assertTrue(c.applied.feature('desktop.patterns'));self.assertTrue(c.applied.programmes[1].installed);self.assertEqual(s.calls,[('execute',(('desktop.patterns',True),),(('demo',True),))]);self.assertEqual(c.pending,c.applied)
 def test_stale_external_state_refused_before_mutation(self):
  s,b,c=self.setup_controller();c.set_feature('desktop.patterns',True);s.state=replace(s.state,generation='external')
  with self.assertRaisesRegex(SetupError,'changed while'):c.apply()
  self.assertEqual(s.calls,[])
 def test_cancellation_before_commit_has_no_service_write(self):
  s,b,c=self.setup_controller();c.set_feature('desktop.patterns',True);cancel=Event();cancel.set()
  with self.assertRaises(SetupCancelled):c.apply(cancel)
  self.assertEqual(s.calls,[])
 def test_partial_service_failure_restores_only_requested_ids(self):
  s,b,c=self.setup_controller();before=c.applied;c.set_feature('desktop.patterns',True);s.fail=True
  with self.assertRaisesRegex(SetupError,'Previous components were restored'):c.apply()
  self.assertEqual(s.state.features,before.features);self.assertEqual(c.applied,before);self.assertEqual(s.calls[-1],('restore',(('desktop.patterns',True),),()))
 def test_wrong_successful_readback_is_failure_not_fake_saved_setting(self):
  s,b,c=self.setup_controller();c.set_feature('desktop.patterns',True);s.ignore=True
  with self.assertRaisesRegex(SetupError,'were restored'):c.apply()
  self.assertFalse(c.applied.feature('desktop.patterns'));self.assertTrue(c.pending.feature('desktop.patterns'))
 def test_failed_recovery_is_explicit_and_invalidates_cached_state(self):
  s,b,c=self.setup_controller();c.set_feature('desktop.patterns',True);s.fail=True;s.restore_fail=True
  with self.assertRaisesRegex(SetupError,'could not be fully restored'):c.apply()
  self.assertIsNone(b.cached);self.assertTrue(b.preferences().feature('desktop.patterns'));self.assertFalse(c.applied.feature('desktop.patterns'))
 def test_cancel_during_service_triggers_scoped_recovery(self):
  s,b,c=self.setup_controller();event=Event();original=s.execute
  def execute(*args):original(*args);event.set()
  s.execute=execute;c.set_feature('desktop.patterns',True)
  with self.assertRaisesRegex(SetupError,'were restored'):c.apply(event)
  self.assertFalse(s.state.feature('desktop.patterns'))
 def test_malformed_bool_does_not_change_pending(self):
  s,b,c=self.setup_controller()
  with self.assertRaises(ValueError):c.set_feature('desktop.patterns','yes')
  self.assertEqual(c.pending,c.applied)
