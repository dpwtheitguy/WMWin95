"""Cookie ownership never mutates session lock configuration."""
import sys
from pathlib import Path as _BootstrapPath
sys.path.insert(0,str(_BootstrapPath(__file__).resolve().parents[1]/'src'))
import unittest
from win95lx.apps.screensaver_ownership import SaverOwnership
class Bus:
    def __init__(self):self.identity=(':1.20',123);self.locking=False;self.is_active=False;self.rows=[];self.calls=[];self.next=100;self.fail=False;self.closed=False
    def owner(self):return self.identity
    def lock_policy(self):return self.locking
    def active(self,owner):return self.is_active
    def inhibitors(self,owner):return self.rows
    def acquire(self,owner,mode,reason):
        if self.fail:raise RuntimeError('denied')
        self.next+=1;self.calls.append(('acquire',owner,mode,self.next));return self.next
    def release(self,*args):self.calls.append(('release',*args))
    def close(self):self.closed=True
class OwnershipTests(unittest.TestCase):
    def make(self):
        bus=Bus();owner=SaverOwnership(address='test',display=':9',bus_factory=lambda _:bus,display_check=lambda *_:True);return owner,bus
    def test_without_idle_lock_uses_scoped_inhibit(self):
        owner,bus=self.make();state=owner.refresh();self.assertTrue(state.ready);self.assertEqual(state.mode,'Inhibit');owner.close();self.assertEqual(bus.calls[-1][2],'Inhibit');self.assertTrue(bus.closed)
    def test_automatic_lock_uses_throttle_never_inhibit(self):
        owner,bus=self.make();bus.locking=True;self.assertEqual(owner.refresh().mode,'Throttle');self.assertFalse(any('Inhibit'in row for row in bus.calls))
    def test_policy_enabling_lock_releases_inhibit_first(self):
        owner,bus=self.make();owner.refresh();bus.calls.clear();bus.locking=True;owner.refresh();self.assertEqual([row[0]for row in bus.calls],['release','acquire']);self.assertEqual(bus.calls[0][2],'Inhibit')
    def test_policy_disabling_lock_acquires_before_release(self):
        owner,bus=self.make();bus.locking=True;owner.refresh();bus.calls.clear();bus.locking=False;owner.refresh();self.assertEqual([row[0]for row in bus.calls],['acquire','release'])
    def test_manual_activation_is_respected_without_deactivation(self):
        owner,bus=self.make();bus.is_active=True;self.assertTrue(owner.refresh().active);self.assertTrue(all(row[0]in('acquire','release')for row in bus.calls))
    def test_external_inhibitor_blocks_custom_animation(self):
        owner,bus=self.make();bus.rows=['Application="Player"; Reason="Movie";'];self.assertTrue(owner.refresh().external_inhibited)
    def test_own_inhibit_is_not_treated_as_external(self):
        owner,bus=self.make();bus.rows=['Application="Win95LX"; Reason="'+owner.reason+'";'];self.assertFalse(owner.refresh().external_inhibited)
    def test_daemon_restart_does_not_reuse_cookie(self):
        owner,bus=self.make();owner.refresh();old=owner.cookie;bus.identity=(':1.21',123);owner.refresh();self.assertNotEqual(owner.cookie,old);self.assertEqual(bus.calls[-1][1],':1.21')
    def test_no_owner_does_not_autostart_daemon(self):
        owner,bus=self.make();bus.identity=None;self.assertTrue(owner.refresh().ready);self.assertFalse(bus.calls)
    def test_other_display_owner_is_untouched(self):
        owner,bus=self.make();owner.display_check=lambda *_:False;self.assertTrue(owner.refresh().ready);self.assertFalse(bus.calls)
    def test_acquire_failure_fails_closed_and_closes_connection(self):
        owner,bus=self.make();bus.fail=True;state=owner.refresh();self.assertFalse(state.ready);self.assertTrue(state.error);self.assertTrue(bus.closed)
    def test_repeated_refresh_does_not_reacquire(self):
        owner,bus=self.make();owner.refresh();owner.refresh();self.assertEqual(len(bus.calls),1)
    def test_missing_bus_and_existing_daemon_is_not_success(self):
        owner=SaverOwnership(address='',display=':9',daemon_check=lambda _:True);self.assertFalse(owner.refresh().ready)
    def test_no_bus_and_no_owner_keeps_local_idle_available(self):
        owner=SaverOwnership(address='',display=':9',daemon_check=lambda _:False);self.assertTrue(owner.refresh().ready)
    def test_close_is_idempotent(self):
        owner,bus=self.make();owner.refresh();owner.close();count=len(bus.calls);owner.close();self.assertEqual(len(bus.calls),count)
    def test_unreadable_lock_policy_uses_safe_throttle(self):
        owner,bus=self.make()
        def denied():raise PermissionError('read denied')
        bus.lock_policy=denied;state=owner.refresh();self.assertTrue(state.ready);self.assertEqual(state.mode,'Throttle')
if __name__=='__main__':unittest.main()
