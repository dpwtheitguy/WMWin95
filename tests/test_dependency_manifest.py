import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('dependency_checker',Path(__file__).resolve().parents[1]/'tools/check_dependencies.py')
checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)

class DependencyAuditTests(unittest.TestCase):
    def test_unqualified_multiarch_library_selects_native(self):
        rows='installed\t1-foreign\ti386\ninstalled\t1-native\tamd64\n'
        self.assertEqual(checker.installed_record(rows,'libgl1','amd64'),('1-native','amd64'))
    def test_explicit_foreign_library_selects_foreign(self):
        rows='installed\t1-native\tamd64\ninstalled\t1-foreign\ti386\n'
        self.assertEqual(checker.installed_record(rows,'libgl1:i386','amd64'),('1-foreign','i386'))
    def test_architecture_independent_package(self):
        self.assertEqual(checker.installed_record('installed\t2\tall\n','wine','amd64'),('2','all'))
    def test_only_foreign_copy_does_not_satisfy_native_requirement(self):
        self.assertIsNone(checker.installed_record('installed\t2\ti386\n','libgl1','amd64'))
    def test_removed_package_not_accepted(self):
        self.assertIsNone(checker.installed_record('config-files\t2\tamd64\n','libgl1','amd64'))

if __name__=='__main__':unittest.main()
