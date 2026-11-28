"""Async lifecycle gates independent of the Wine runtime implementation."""
import sys
from pathlib import Path as _BootstrapPath
sys.path.insert(0,str(_BootstrapPath(__file__).resolve().parents[1]/'src'))
import threading,time,unittest
from win95lx.apps.screensaver_host import SaverTasks

class Process:
    def __init__(self):self.done=threading.Event()
    def wait(self):self.done.wait(2);return 0

class Runtime:
    def __init__(self):self.preparing=threading.Event();self.prepared=threading.Event();self.process=None;self.calls=[];self.fail=False
    def prepare(self,name):
        self.calls.append(('prepare',name));self.preparing.set();self.prepared.wait(2)
        if self.fail:raise RuntimeError('missing Wine')
    def launch(self,name,mode):self.calls.append(('launch',name,mode));self.process=Process();return self.process
    def stop(self):
        self.calls.append(('stop',))
        if self.process:self.process.done.set();self.process=None
    def close(self):self.calls.append(('close',));self.stop()

class AsyncSaverTests(unittest.TestCase):
    def wait_for(self,predicate):
        end=time.monotonic()+2
        while time.monotonic()<end:
            if predicate():return
            time.sleep(.005)
        self.fail('worker completion timed out')
    def test_prepare_runs_off_caller_and_cancel_prevents_launch(self):
        runtime=Runtime();tasks=SaverTasks(runtime);started=time.monotonic();worker=tasks.submit('nature','fullscreen')
        self.assertLess(time.monotonic()-started,.1);self.assertTrue(runtime.preparing.wait(1))
        stopping=tasks.stop();runtime.prepared.set();worker.join(1);stopping.join(1)
        self.assertFalse(any(row[0]=='launch'for row in runtime.calls));self.assertFalse(tasks.busy)
    def test_stop_can_interrupt_waiting_fullscreen_child(self):
        runtime=Runtime();runtime.prepared.set();tasks=SaverTasks(runtime);worker=tasks.submit('stars','fullscreen')
        self.wait_for(lambda:runtime.process is not None);started=time.monotonic();stopping=tasks.stop();self.assertLess(time.monotonic()-started,.1)
        stopping.join(1);worker.join(1);self.assertFalse(worker.is_alive());self.assertIsNone(runtime.process)
    def test_configuration_completion_releases_owned_runtime(self):
        runtime=Runtime();runtime.prepared.set();events=[];tasks=SaverTasks(runtime,changed=lambda *v:events.append(v));worker=tasks.submit('nature','configure')
        self.wait_for(lambda:runtime.process is not None);runtime.process.done.set();worker.join(1)
        self.assertFalse(tasks.busy);self.assertEqual(events[-1],('Ready.',None));self.assertIsNone(runtime.process)
    def test_prepare_failure_restores_reusable_state(self):
        runtime=Runtime();runtime.fail=True;runtime.prepared.set();events=[];tasks=SaverTasks(runtime,changed=lambda *v:events.append(v));tasks.submit('nature','fullscreen').join(1)
        self.assertFalse(tasks.busy);self.assertIsInstance(events[-1][1],RuntimeError);self.assertFalse(any(row[0]=='launch'for row in runtime.calls))
    def test_destroy_during_preparation_does_not_launch_or_notify(self):
        runtime=Runtime();events=[];tasks=SaverTasks(runtime,changed=lambda *v:events.append(v));worker=tasks.submit('nature','fullscreen');runtime.preparing.wait(1)
        closing=tasks.stop(close=True);count=len(events);runtime.prepared.set();closing.join(1);worker.join(1)
        self.assertEqual(len(events),count);self.assertIn(('close',),runtime.calls);self.assertFalse(any(row[0]=='launch'for row in runtime.calls))
    def test_rapid_replacement_only_launches_latest(self):
        runtime=Runtime();tasks=SaverTasks(runtime);first=tasks.submit('nature','fullscreen');runtime.preparing.wait(1);second=tasks.submit('stars','fullscreen');runtime.prepared.set();first.join(1)
        self.wait_for(lambda:runtime.process is not None);tasks.stop().join(1);second.join(1)
        self.assertEqual([row[1]for row in runtime.calls if row[0]=='launch'],['stars'])
    def test_ready_only_after_owner_dispatch_runs(self):
        runtime=Runtime();runtime.prepared.set();queued=[];tasks=SaverTasks(runtime,dispatch=queued.append)
        tasks.submit('nature').join(1);self.assertTrue(tasks.busy)
        for callback in queued:callback()
        self.assertFalse(tasks.busy)
    def test_stale_queued_ready_cannot_clear_new_generation(self):
        runtime=Runtime();runtime.prepared.set();queued=[];tasks=SaverTasks(runtime,dispatch=queued.append)
        tasks.submit('nature').join(1);old=list(queued);queued.clear()
        runtime.prepared.clear();worker=tasks.submit('stars');runtime.preparing.wait(1)
        for callback in old:callback()
        self.assertTrue(tasks.busy)
        runtime.prepared.set();worker.join(1)
        for callback in queued:callback()
        self.assertFalse(tasks.busy)
    def test_unexpected_exit_is_reported_after_owned_cleanup(self):
        runtime=Runtime();runtime.prepared.set();original=runtime.launch
        def launch(name,mode):
            process=original(name,mode);process.wait=lambda:5;return process
        runtime.launch=launch;events=[];tasks=SaverTasks(runtime,changed=lambda *v:events.append(v))
        tasks.submit('nature','fullscreen').join(1)
        self.assertIsNone(runtime.process);self.assertFalse(tasks.busy);self.assertIsInstance(events[-1][1],RuntimeError)

class HostPreferenceGenerationTests(unittest.TestCase):
    def host(self,directory):
        from pathlib import Path
        from win95lx.apps.screensaver_host import ScreenSaverHost
        from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences
        host=ScreenSaverHost.__new__(ScreenSaverHost);host.path=Path(directory)/'saver.json';host.closed=False;host.apply_generation=1;host.scheduler_lock=threading.Lock();host.applied=host.pending=ScreenSaverPreferences()
        class Idle:
            def __init__(self):self.values=[];self.done=threading.Event()
            def configure(self,value):self.values.append(value);self.done.set()
        host.idle=Idle();return host
    def test_stale_apply_worker_cannot_overwrite_newer_selection(self):
        import tempfile
        from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences
        with tempfile.TemporaryDirectory()as directory:
            host=self.host(directory);old=ScreenSaverPreferences('old',10);new=ScreenSaverPreferences('new',20)
            with host.scheduler_lock:
                host._schedule_preferences(old,1);host.apply_generation=2;host._schedule_preferences(new,2)
            self.assertTrue(host.idle.done.wait(1));self.assertEqual(host.idle.values,[new])
    def test_theme_restore_preserves_exact_bytes_and_display_pending(self):
        import tempfile
        from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences
        with tempfile.TemporaryDirectory()as directory:
            host=self.host(directory);applied=ScreenSaverPreferences('before',17);pending=ScreenSaverPreferences('display-pending',23);contents=b'{"wait_minutes":17,"saver":"before"}\n'
            host.restore_theme(applied,pending,contents);self.assertTrue(host.idle.done.wait(1))
            self.assertEqual(host.path.read_bytes(),contents);self.assertEqual(host.applied,applied);self.assertEqual(host.pending,pending);self.assertEqual(host.idle.values,[applied])
    def test_theme_restore_removes_new_file_when_previously_absent(self):
        import tempfile
        from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences
        with tempfile.TemporaryDirectory()as directory:
            host=self.host(directory);host.path.write_text('new');value=ScreenSaverPreferences();host.restore_theme(value,value,None)
            self.assertTrue(host.idle.done.wait(1));self.assertFalse(host.path.exists())


class HostGroupedWarmupTests(unittest.TestCase):
    def host(self):
        from win95lx.apps.screensaver_host import ScreenSaverHost
        host=ScreenSaverHost.__new__(ScreenSaverHost);host.closed=False;host.request_generation=0;host.request_waiting=False;host.scheduler_lock=threading.Lock();host.calls=[];host.session_mode=None
        class Idle:
            def stop(self):host.calls.append('idle-stop')
        class Tasks:
            busy=False
            def submit(self,identity,mode):host.calls.append(('submit',identity,mode))
            def stop(self):host.calls.append('task-stop')
        host.idle=Idle();host.tasks=Tasks();return host
    def test_group_warmup_releases_idle_lease_before_prepare(self):
        host=self.host();thread=host.warm('nature');thread.join(1)
        self.assertEqual(host.calls,['idle-stop',('submit','nature',None)]);self.assertFalse(host.request_waiting)
    def test_only_latest_queued_request_can_touch_runtime(self):
        host=self.host()
        with host.scheduler_lock:first=host.warm('old');second=host.warm('new')
        first.join(1);second.join(1)
        self.assertEqual(host.calls,['idle-stop',('submit','new',None)])
    def test_cancel_queued_request_prevents_late_prepare(self):
        host=self.host()
        with host.scheduler_lock:thread=host.warm('nature');host.stop_preview()
        thread.join(1);self.assertEqual(host.calls,['task-stop']);self.assertFalse(host.busy)

if __name__=='__main__':unittest.main()
