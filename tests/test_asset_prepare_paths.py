import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('asset_prepare_tool',Path(__file__).resolve().parents[1]/'tools/prepare_assets.py');prepare=importlib.util.module_from_spec(spec);spec.loader.exec_module(prepare)

class AssetLocations(unittest.TestCase):
    def test_private_sibling_build_and_cache_allowed(self):
        root=prepare.ROOT/'private'
        prepare.validate_locations(root/'qa/build',root/'qa/cache',[root/'cabsets/windows95'])
    def test_output_cannot_be_source_or_source_parent(self):
        root=prepare.ROOT/'private';source=root/'cabsets/windows95'
        for output in(source,source/'generated',root/'cabsets'):
            with self.subTest(output=output),self.assertRaises(ValueError):prepare.validate_locations(output,root/'cache',[source])
    def test_cache_cannot_pollute_source(self):
        root=prepare.ROOT/'private';source=root/'cabsets/windows95'
        with self.assertRaises(ValueError):prepare.validate_locations(root/'qa',source/'cache',[source])
    def test_public_cache_rejected(self):
        with tempfile.TemporaryDirectory()as directory:
            with self.assertRaises(ValueError):prepare.validate_locations(prepare.ROOT/'private/qa',Path(directory),[])
    def test_uncached_mode_has_no_cache_path(self):
        prepare.validate_locations(prepare.ROOT/'private/qa',None,[])

if __name__=='__main__':unittest.main()
