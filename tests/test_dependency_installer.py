import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import install_dependencies as installer

class DependencyInstallerTests(unittest.TestCase):
    def exercise(self,*,apply=False,os_id='ubuntu',uid=0,deny_guard=False):
        calls=[]
        with tempfile.TemporaryDirectory() as directory:
            manifest=Path(directory)/'manifest.json'
            manifest.write_text(json.dumps({'schema':1,'target':{'distribution':'ubuntu','version':'24.04','architecture':'amd64','foreign_architectures':['i386']},'groups':{'saver':{'packages':['wine32:i386']}},'profiles':{'windows95':['saver']}}))
            original=Path.read_text
            def read(path,*args,**kwargs):
                if str(path)=='/etc/os-release':return 'ID='+os_id+'\nVERSION_ID="24.04"\n'
                return original(path,*args,**kwargs)
            def run(command,**kwargs):
                calls.append(command)
                if deny_guard:raise subprocess.CalledProcessError(1,command)
            def output(command,**kwargs):return 'amd64\n' if command[-1]=='--print-architecture' else 'i386\n'
            with patch.object(sys,'argv',['installer','--manifest',str(manifest)]+(['--apply']if apply else [])),patch.object(Path,'read_text',read),patch.object(installer.os,'geteuid',return_value=uid),patch.object(installer.subprocess,'run',side_effect=run),patch.object(installer.subprocess,'check_output',side_effect=output):
                try:installer.main()
                finally:self.calls=calls
        return calls
    def test_default_only_simulates_after_guest_guard(self):
        calls=self.exercise()
        self.assertEqual(calls[0],['/usr/lib/win95lx/require-guest'])
        self.assertEqual(len(calls),2)
        self.assertIn('--simulate',calls[1]);self.assertIn('--no-remove',calls[1])
    def test_apply_simulates_before_install(self):
        calls=self.exercise(apply=True)
        self.assertEqual(calls[1],['apt-get','update','-qq'])
        self.assertIn('--simulate',calls[2]);self.assertNotIn('--simulate',calls[3])
        self.assertIn('--no-remove',calls[3]);self.assertIn('wine32:i386',calls[3])
    def test_guest_guard_failure_never_calls_apt(self):
        with self.assertRaises(subprocess.CalledProcessError):self.exercise(deny_guard=True)
        self.assertEqual(len(self.calls),1)
    def test_wrong_os_never_calls_apt(self):
        with self.assertRaises(SystemExit):self.exercise(os_id='debian')
        self.assertEqual(len(self.calls),1)
    def test_nonroot_never_calls_apt(self):
        with self.assertRaises(SystemExit):self.exercise(uid=1001)
        self.assertEqual(len(self.calls),1)

if __name__=='__main__':unittest.main()
