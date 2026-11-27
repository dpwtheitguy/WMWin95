import os,stat,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx import guest_identity as guest
class IdentityTests(unittest.TestCase):
    def run_case(self,marker=None,vendor='QEMU',hostname='win95lx-dev',mode=0o100644,uid=0):
        identity='1234567890abcdef1234567890abcdef'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);v=root/'vendor';v.write_text(vendor);m=root/'machine-id';m.write_text(identity);p=root/'marker'
            if marker is not None:p.write_text(identity if marker is True else marker)
            real_stat=Path.stat
            def metadata(path,*args,**kwargs):
                info=real_stat(path,*args,**kwargs)
                return SimpleNamespace(st_mode=mode,st_uid=uid) if path==p else info
            with patch.object(guest,'VENDOR',v),patch.object(guest,'MACHINE_ID',m),patch.object(guest,'MARKER',p),patch.object(Path,'stat',metadata),patch.object(guest.os,'uname',return_value=SimpleNamespace(nodename=hostname)):
                return guest.is_development_guest()
    def test_renamed_installed_guest_remains_the_same_os(self):self.assertTrue(self.run_case(marker=True,hostname='MY-WINDOWS-PC'))
    def test_wrong_machine_marker_is_rejected_even_with_old_hostname(self):self.assertFalse(self.run_case(marker='a'*32))
    def test_non_qemu_host_is_not_guest(self):self.assertFalse(self.run_case(marker=True,vendor='Other'))
    def test_user_or_world_writable_marker_is_rejected(self):
        self.assertFalse(self.run_case(marker=True,uid=1001));self.assertFalse(self.run_case(marker=True,mode=0o100666))
    def test_bootstrap_requires_original_hostname(self):self.assertTrue(self.run_case());self.assertFalse(self.run_case(hostname='other'))
if __name__=='__main__':unittest.main()
