import sys,unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.explorer.tree_model import FolderTree,DirectorySource,Entry,LoadRequest,LoadResult

class FolderTreeTests(unittest.TestCase):
    def populate(self,tree,key,names):
        request=tree.request_expand(key);self.assertIsNotNone(request);self.assertTrue(tree.apply(LoadResult(request,tuple(Entry(name) for name in names))))
    def test_first_expansion_is_lazy_and_drawing_does_no_io(self):
        tree=FolderTree()
        with patch('pathlib.Path.iterdir',side_effect=AssertionError('Paint performed I/O')):
            self.assertEqual(tree.page(0,20)[0].status,'unloaded')
            request=tree.key('Right');self.assertEqual(request.key,());self.assertEqual(tree.page(0,20)[0].status,'loading')
        self.assertTrue(tree.apply(LoadResult(request,(Entry('Alpha'),))))
        self.assertIsNone(tree.request_expand(()));self.assertEqual(len(tree.page(0,20)),2)
    def test_windows_have_independent_selection_expansion_and_scroll(self):
        left,right=FolderTree(),FolderTree();self.populate(left,(),('A','B'));left.select(('B',));left.scroll=8
        self.assertEqual(right.selected,());self.assertEqual(right.expanded,set());self.assertEqual(right.scroll,0)
    def test_right_left_and_visible_row_navigation(self):
        tree=FolderTree();self.populate(tree,(),('A','B'));tree.key('Right');self.assertEqual(tree.selected,('A',))
        request=tree.key('Right');tree.apply(LoadResult(request,(Entry('child'),)));tree.key('Right');self.assertEqual(tree.selected,('A','child'))
        tree.key('Left');self.assertEqual(tree.selected,('A',));tree.key('Left');self.assertNotIn(('A',),tree.expanded)
        tree.key('Down');self.assertEqual(tree.selected,('B',));tree.key('End');self.assertEqual(tree.selected,('B',));tree.key('Home');self.assertEqual(tree.selected,())
    def test_collapsing_parent_selects_parent_and_late_load_does_not_reopen(self):
        tree=FolderTree();self.populate(tree,(),('A',));tree.select(('A',));request=tree.request_expand(('A',));tree.collapse(())
        self.assertEqual(tree.selected,());tree.apply(LoadResult(request,(Entry('child'),)));self.assertNotIn((),tree.expanded);self.assertEqual(len(tree.page(0,20)),1)
    def test_refresh_discards_stale_callback_and_removes_deleted_subtree(self):
        tree=FolderTree();self.populate(tree,(),('A',));self.populate(tree,('A',),('child',));tree.select(('A','child'))
        old=tree.request_expand((),refresh=True);new=tree.request_expand((),refresh=True)
        self.assertFalse(tree.apply(LoadResult(old,(Entry('wrong'),))));self.assertTrue(tree.apply(LoadResult(new,(Entry('B'),))))
        self.assertEqual(tree.selected,());self.assertNotIn(('A','child'),tree.nodes)
    def test_removed_and_recreated_key_never_accepts_old_load_token(self):
        tree=FolderTree();self.populate(tree,(),('A',));old=tree.request_expand(('A',))
        refresh=tree.request_expand((),refresh=True);tree.apply(LoadResult(refresh,()))
        refresh=tree.request_expand((),refresh=True);tree.apply(LoadResult(refresh,(Entry('A'),)))
        new=tree.request_expand(('A',));self.assertNotEqual(new.generation,old.generation)
        self.assertFalse(tree.apply(LoadResult(old,(Entry('wrong'),))))
        self.assertTrue(tree.apply(LoadResult(new,(Entry('right'),))))
    def test_error_is_retryable_and_failed_refresh_keeps_previous_children(self):
        tree=FolderTree();self.populate(tree,(),('A',));request=tree.request_expand((),refresh=True)
        tree.apply(LoadResult(request,error='access-denied'));self.assertEqual(tree.nodes[()].error,'access-denied');self.assertIn(('A',),tree.nodes)
        retry=tree.request_expand(());self.assertIsNotNone(retry);self.assertTrue(tree.apply(LoadResult(retry,())))
    def test_blocked_cycle_cannot_request_expansion(self):
        tree=FolderTree();request=tree.request_expand(());tree.apply(LoadResult(request,(Entry('loop',True,'folder-cycle'),)))
        tree.select(('loop',));self.assertIsNone(tree.key('Right'));self.assertNotIn(('loop',),tree.expanded)
    def test_invalid_keys_and_duplicate_results_do_not_mutate_tree(self):
        tree=FolderTree()
        for key in (('..',),('/tmp',),('bad/name',),('',)):
            with self.assertRaises(ValueError):tree.request_expand(key)
        request=tree.request_expand(())
        with self.assertRaises(ValueError):tree.apply(LoadResult(request,(Entry('A'),Entry('A'))))
        self.assertEqual(len(tree.nodes),1)
    def test_viewport_slice_skips_no_directory_and_large_flat_listing(self):
        tree=FolderTree();self.populate(tree,(),tuple(f'Folder{i:05}' for i in range(10000)))
        page=tree.page(9996,20);self.assertEqual(len(page),5);self.assertEqual(page[-1].label,'Folder09999')
        with self.assertRaises(ValueError):tree.page(-1,4)
    def test_source_lists_only_direct_folders_with_native_casefold_order(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            for name in ('zeta','Alpha','.hidden'):(root/name).mkdir()
            (root/'Alpha/deeper').mkdir();(root/'text.txt').write_text('not a folder')
            source=DirectorySource(root);request=LoadRequest((),1);result=source.scan(request)
            self.assertEqual([e.name for e in result.entries],['Alpha','zeta']);self.assertEqual(result.error,'')
            self.assertEqual([e.name for e in source.scan(LoadRequest((),2,True)).entries],['.hidden','Alpha','zeta'])
    def test_source_handles_links_cycles_missing_and_outside_root(self):
        with TemporaryDirectory() as d,TemporaryDirectory() as outside:
            root=Path(d);(root/'A').mkdir();(root/'linked').symlink_to(root/'A',target_is_directory=True);(root/'A/back').symlink_to(root,target_is_directory=True)
            (root/'escape').symlink_to(outside,target_is_directory=True);(root/'broken').symlink_to(root/'missing')
            source=DirectorySource(root);result=source.scan(LoadRequest((),1))
            self.assertEqual([e.name for e in result.entries],['A','linked']);self.assertTrue(result.entries[1].link)
            cycle=source.scan(LoadRequest(('A',),1));self.assertEqual(cycle.entries[0].blocked,'folder-cycle')
            self.assertEqual(source.scan(LoadRequest(('A','back'),1)).error,'folder-cycle')
            self.assertEqual(source.scan(LoadRequest(('escape',),1)).error,'outside-root')
            self.assertEqual(source.scan(LoadRequest(('gone',),1)).error,'folder-missing')
    def test_source_permission_failure_has_no_linux_path_in_error(self):
        with TemporaryDirectory() as d:
            source=DirectorySource(d)
            with patch('pathlib.Path.iterdir',side_effect=PermissionError('/private/secret')):
                result=source.scan(LoadRequest((),1));self.assertEqual(result.error,'access-denied');self.assertEqual(result.entries,())

if __name__=='__main__':unittest.main()
