"""Cache correctness uses disposable files, never the project asset bundle."""
import importlib.util,json,os,sys,tempfile,time,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from asset_cache import StageCache

class AssetCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.output=self.root/'bundle';self.store=self.root/'cache';self.source=self.root/'source';self.source.mkdir();self.input=self.source/'input';self.input.write_bytes(b'first');self.calls=0
    def cache(self,force=False):return StageCache(self.output,self.store,force)
    def build(self):
        self.calls+=1;(self.output/'image').write_bytes(self.input.read_bytes());return [{'output':'image','kind':'test'}]
    def run_stage(self,cache=None,**kwargs):return(cache or self.cache()).run('render',self.build,dependencies=[self.source],**kwargs)
    def test_hit_preserves_json_result(self):
        result=self.run_stage();cache=self.cache();self.assertEqual(self.run_stage(cache),result);self.assertEqual(self.calls,1);self.assertEqual(cache.report[-1]['status'],'hit')
    def test_source_content_invalidates(self):self.run_stage();self.input.write_bytes(b'other');self.run_stage();self.assertEqual(self.calls,2)
    def test_mtime_alone_does_not_invalidate(self):
        self.run_stage();os.utime(self.input,(1,1));self.run_stage();self.assertEqual(self.calls,1)
    def test_restored_mtime_cannot_hide_content_change(self):
        self.run_stage();old=self.input.stat();self.input.write_bytes(b'other');os.utime(self.input,ns=(old.st_atime_ns,old.st_mtime_ns));self.run_stage();self.assertEqual(self.calls,2)
    def test_new_file_invalidates_recursive_tree(self):self.run_stage();(self.source/'new').write_bytes(b'new');self.run_stage();self.assertEqual(self.calls,2)
    def test_removed_file_invalidates_recursive_tree(self):
        other=self.source/'other';other.write_bytes(b'yes');self.run_stage();other.unlink();self.run_stage();self.assertEqual(self.calls,2)
    def test_renamed_identical_file_invalidates(self):self.run_stage();self.input.rename(self.source/'renamed');self.input=self.source/'renamed';self.run_stage();self.assertEqual(self.calls,2)
    def test_absent_input_becoming_present_invalidates(self):
        absent=self.root/'optional';cache=self.cache();cache.run('x',self.build,dependencies=[absent]);absent.write_bytes(b'font');cache.run('x',self.build,dependencies=[absent]);self.assertEqual(self.calls,2)
    def test_absent_input_name_is_fingerprinted(self):
        cache=self.cache();cache.run('x',self.build,dependencies=[self.root/'missing-a']);cache.run('x',self.build,dependencies=[self.root/'missing-b']);self.assertEqual(self.calls,2)
    def test_optional_input_disappearing_invalidates(self):
        absent=self.root/'optional';absent.write_text('yes');cache=self.cache();cache.run('x',self.build,dependencies=[absent]);absent.unlink();cache.run('x',self.build,dependencies=[absent]);self.assertEqual(self.calls,2)
    def test_font_palette_reference_code_changes_invalidate(self):
        for filename in ('font.fnt','palette.json','reference.bmp','builder.py'):
            with self.subTest(filename=filename):
                path=self.source/filename;path.write_text('old');before=self.calls;self.run_stage();path.write_text('new');self.run_stage();self.assertEqual(self.calls,before+2)
    def test_conditions_invalidate(self):self.run_stage(conditions={'palette':16});self.run_stage(conditions={'palette':256});self.assertEqual(self.calls,2)
    def test_condition_key_order_not_significant(self):self.run_stage(conditions={'a':1,'b':2});self.run_stage(conditions={'b':2,'a':1});self.assertEqual(self.calls,1)
    def test_force_bypasses_read_cache(self):self.run_stage();cache=self.cache(True);self.run_stage(cache);self.assertEqual(self.calls,2);self.assertEqual(cache.report[-1]['reason'],'forced')
    def test_missing_output_restored_without_builder(self):
        self.run_stage();(self.output/'image').unlink();self.run_stage();self.assertEqual(self.calls,1);self.assertEqual((self.output/'image').read_bytes(),b'first')
    def test_tampered_output_restored_without_builder(self):
        self.run_stage();(self.output/'image').write_bytes(b'corrupt');self.run_stage();self.assertEqual(self.calls,1);self.assertEqual((self.output/'image').read_bytes(),b'first')
    def test_deleted_bundle_is_recreated(self):
        import shutil
        self.run_stage();shutil.rmtree(self.output);self.run_stage();self.assertEqual(self.calls,1);self.assertTrue((self.output/'image').exists())
    def test_corrupt_blob_rebuilds(self):
        self.run_stage();blob=next((self.store/'blobs').iterdir());blob.write_bytes(b'broken');cache=self.cache();self.run_stage(cache);self.assertEqual(self.calls,2);self.assertEqual(cache.report[-1]['reason'],'cache-corrupt')
    def test_missing_blob_rebuilds(self):
        self.run_stage();next((self.store/'blobs').iterdir()).unlink();self.run_stage();self.assertEqual(self.calls,2)
    def test_corrupt_metadata_rebuilds(self):
        self.run_stage();next((self.store/'entries/render').iterdir()).write_text('broken');self.run_stage();self.assertEqual(self.calls,2)
    def test_metadata_path_escape_not_replayed(self):
        self.run_stage();entry=next((self.store/'entries/render').iterdir());data=json.loads(entry.read_text());data['deleted']=['../personal'];entry.write_text(json.dumps(data));personal=self.root/'personal';personal.write_text('keep');self.run_stage();self.assertEqual(personal.read_text(),'keep');self.assertEqual(self.calls,2)
    def test_entry_ownership_exposed_absolute(self):
        cache=self.cache();self.run_stage(cache);self.assertEqual(cache.stage_outputs['render'],[self.output/'image']);self.assertEqual(cache.stage_deleted['render'],[])
    def test_hit_ownership_exposed(self):
        self.run_stage();cache=self.cache();self.run_stage(cache);self.assertEqual(cache.stage_outputs['render'],[self.output/'image'])
    def test_identical_rewrite_is_owned_without_declared_record(self):
        cache=self.cache();(self.output/'same').write_text('same')
        cache.run('same',lambda:(self.output/'same').write_text('same'))
        self.assertIn(self.output/'same',cache.stage_outputs['same'])
    def test_declared_unchanged_output_owned(self):
        cache=self.cache();(self.output/'same').write_text('same');cache.run('same',lambda:[{'output':'same'}]);self.assertIn(self.output/'same',cache.stage_outputs['same'])
    def test_nested_declared_output(self):
        cache=self.cache();(self.output/'same').write_text('same');cache.run('same',lambda:{'records':[{'output':str(self.output/'same')}]});self.assertIn(self.output/'same',cache.stage_outputs['same'])
    def test_failed_builder_never_publishes(self):
        cache=self.cache()
        def fail():(self.output/'partial').write_text('partial');raise RuntimeError('failed')
        with self.assertRaises(RuntimeError):cache.run('failed',fail)
        self.assertEqual(list((self.store/'entries/failed').glob('*.json')),[]);self.assertEqual(cache.report[-1]['status'],'failed')
    def test_failure_retry_runs_builder(self):
        cache=self.cache()
        with self.assertRaises(RuntimeError):cache.run('retry',lambda:(_ for _ in ()).throw(RuntimeError('fail')))
        cache.run('retry',self.build);self.assertEqual(self.calls,1);self.assertEqual(cache.report[-1]['status'],'miss')
    def test_invalid_json_result_never_publishes(self):
        cache=self.cache()
        with self.assertRaises(TypeError):cache.run('invalid',lambda:object())
        self.assertEqual(list((self.store/'entries/invalid').glob('*.json')),[])
    def test_missing_declared_output_never_publishes(self):
        cache=self.cache()
        with self.assertRaises(ValueError):cache.run('missing',lambda:[{'output':'missing'}])
        self.assertEqual(list((self.store/'entries/missing').glob('*.json')),[])
    def test_stage_name_escape_rejected(self):
        with self.assertRaises(ValueError):self.cache().run('../stage',self.build)
    def test_returned_path_escape_rejected(self):
        with self.assertRaises(ValueError):self.cache().run('bad',lambda:[{'output':'../personal'}])
    def test_cache_inside_bundle_rejected(self):
        with self.assertRaises(ValueError):StageCache(self.output,self.output/'cache')
    def test_bundle_inside_cache_rejected(self):
        with self.assertRaises(ValueError):StageCache(self.store/'bundle',self.store)
    def test_output_symlink_cannot_escape(self):
        cache=self.cache();personal=self.root/'personal';personal.write_text('keep');(self.output/'link').symlink_to(personal)
        with self.assertRaises(ValueError):self.run_stage(cache)
        self.assertEqual(personal.read_text(),'keep')
    def test_hit_cannot_follow_directory_symlink(self):
        cache=self.cache()
        def build():(self.output/'folder').mkdir();(self.output/'folder/file').write_text('safe')
        cache.run('nested',build)
        import shutil
        shutil.rmtree(self.output/'folder');outside=self.root/'outside';outside.mkdir();(self.output/'folder').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):cache.run('nested',build)
        self.assertFalse((outside/'file').exists())
    def test_file_permission_restored(self):
        self.run_stage();mode=(self.output/'image').stat().st_mode&0o777;(self.output/'image').chmod(0o600);self.run_stage();self.assertEqual((self.output/'image').stat().st_mode&0o777,mode)
    def test_upstream_content_invalidates(self):
        upstream=self.root/'catalog';upstream.write_text('old');self.run_stage(upstream=[upstream]);upstream.write_text('new');self.run_stage(upstream=[upstream]);self.assertEqual(self.calls,2)
    def test_midbuild_dependency_change_not_cached(self):
        cache=self.cache()
        def builder():self.build();self.input.write_bytes(b'new');return [{'output':'image'}]
        cache.run('changing',builder,dependencies=[self.source]);self.assertFalse(cache.report[-1]['cached']);self.assertEqual(list((self.store/'entries/changing').glob('*.json')),[])
    def test_midbuild_unowned_upstream_change_not_cached(self):
        cache=self.cache();up=self.root/'up';up.write_text('old')
        def builder():self.build();up.write_text('new');return [{'output':'image'}]
        cache.run('changing',builder,upstream=[up]);self.assertFalse(cache.report[-1]['cached'])
    def test_later_stage_catalog_mutation_restores_intermediate(self):
        counters={'first':0,'second':0}
        def first():counters['first']+=1;(self.output/'catalog').write_text('A');return [{'output':'catalog'}]
        def second():counters['second']+=1;assert(self.output/'catalog').read_text()=='A';(self.output/'catalog').write_text('AB');return [{'output':'catalog'}]
        for iteration in range(2):
            cache=self.cache();cache.run('first',first);cache.run('second',second,upstream=cache.stage_outputs['first']);self.assertEqual((self.output/'catalog').read_text(),'AB')
        self.assertEqual(counters,{'first':1,'second':1})
    def test_deleted_artifact_replayed(self):
        cache=self.cache();(self.output/'obsolete').write_text('old')
        def remove():(self.output/'obsolete').unlink()
        cache.run('remove',remove);self.assertEqual(cache.stage_deleted['remove'],[self.output/'obsolete']);(self.output/'obsolete').write_text('later');cache.run('remove',remove);self.assertFalse((self.output/'obsolete').exists())
    def test_unrelated_output_preserved(self):
        self.run_stage();(self.output/'personal').write_text('keep');self.run_stage();self.assertEqual((self.output/'personal').read_text(),'keep')

    def test_classic_ie4_classic_same_filename_restores_correct_profile(self):
        profile=['classic'];calls=[]
        def builder():
            calls.append(profile[0]);(self.output/'explorer.png').write_bytes(('original-'+profile[0]).encode());return [{'output':'explorer.png','profile':profile[0]}]
        for expected in ('classic','ie4','classic'):
            profile[0]=expected;cache=self.cache();value=cache.run('explorer',builder,dependencies=[self.source],conditions={'profile':expected})
            self.assertEqual((self.output/'explorer.png').read_bytes(),('original-'+expected).encode());self.assertEqual(value[0]['profile'],expected)
        self.assertEqual(calls,['classic','ie4']);self.assertEqual(cache.report[-1]['status'],'hit')
    def test_two_stages_same_inputs_never_cross_restore_asset_path_or_profile(self):
        calls={'classic':0,'ie4':0}
        def builder(profile):
            def build():
                calls[profile]+=1;(self.output/(profile+'.png')).write_bytes(profile.encode());return [{'output':profile+'.png','profile':profile}]
            return build
        for iteration in range(2):
            cache=self.cache()
            for profile in ('classic','ie4'):
                value=cache.run('stage-'+profile,builder(profile),dependencies=[self.source],conditions={'profile':profile})
                self.assertEqual(value[0]['output'],profile+'.png');self.assertEqual((self.output/(profile+'.png')).read_bytes(),profile.encode())
            if iteration==0:
                (self.output/'classic.png').write_bytes(b'ie4');(self.output/'ie4.png').write_bytes(b'classic')
        self.assertEqual(calls,{'classic':1,'ie4':1})
    def test_swapped_metadata_stage_name_rejected_and_rebuilt(self):
        self.run_stage();entry=next((self.store/'entries/render').iterdir());value=json.loads(entry.read_text());value['name']='different-stage';entry.write_text(json.dumps(value));cache=self.cache();self.run_stage(cache)
        self.assertEqual(self.calls,2);self.assertEqual(cache.report[-1]['reason'],'cache-corrupt');self.assertEqual((self.output/'image').read_bytes(),b'first')
    def test_swapped_metadata_fingerprint_rejected_and_rebuilt(self):
        self.run_stage();entry=next((self.store/'entries/render').iterdir());value=json.loads(entry.read_text());value['fingerprint']='0'*64;entry.write_text(json.dumps(value));cache=self.cache();self.run_stage(cache)
        self.assertEqual(self.calls,2);self.assertEqual(cache.report[-1]['reason'],'cache-corrupt');self.assertEqual((self.output/'image').read_bytes(),b'first')

    def test_json_result_key_insertion_order_preserved_on_miss_and_hit(self):
        def builder():
            self.build();return {'zeta':1,'alpha':2,'middle':{'tail':3,'first':4},'output':'image'}
        for expected_status in ('miss','hit'):
            cache=self.cache();result=cache.run('ordered',builder,dependencies=[self.source])
            self.assertEqual(list(result),['zeta','alpha','middle','output']);self.assertEqual(list(result['middle']),['tail','first']);self.assertEqual(cache.report[-1]['status'],expected_status)
        self.assertEqual(self.calls,1)
    def test_manifest_bytes_built_from_result_equal_legacy_cold_and_hit(self):
        legacy={'zeta':'first','alpha':'second','nested':{'last':1,'first':2},'output':'image'}
        expected=json.dumps(legacy,indent=2).encode()
        def builder():self.build();return legacy
        for iteration in range(2):
            cache=self.cache();result=cache.run('manifest-source',builder,dependencies=[self.source]);manifest=self.output/'manifest.json';manifest.write_text(json.dumps(result,indent=2))
            self.assertEqual(manifest.read_bytes(),expected)
        self.assertEqual(self.calls,1)

if __name__=='__main__':unittest.main()
