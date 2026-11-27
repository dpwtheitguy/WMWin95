import copy,queue,sys,threading,time,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
from win95lx.control_panel.audio_preferences import PulseAudio
from win95lx.control_panel.audio_updates import PlaybackUpdates
from test_audio_preferences import FakePulse

class UpdatesTests(unittest.TestCase):
    def setUp(self):self.sessions=[]
    def tearDown(self):
        for session in self.sessions:session.close();self.assertTrue(session.wait_closed(3));self.assertFalse(session.worker.is_alive())
    def session(self,fake=None,run=None):
        fake=fake or FakePulse();messages=[];q=queue.Queue();session=PlaybackUpdates(PulseAudio(run or fake.run),q.put,messages.append);self.sessions.append(session)
        self.assertTrue(session.wait_idle(3));self.drain(q);return fake,session,q,messages
    @staticmethod
    def drain(q):
        while not q.empty():q.get_nowait()()
    def test_initial_read_is_sink_only_and_async(self):
        entered=threading.Event();release=threading.Event();fake=FakePulse()
        def run(*args):entered.set();release.wait(2);return fake.run(*args)
        q=queue.Queue();start=time.monotonic();session=PlaybackUpdates(PulseAudio(run),q.put,lambda _:None);self.sessions.append(session)
        self.assertLess(time.monotonic()-start,.05);self.assertTrue(entered.wait(1));release.set();self.assertTrue(session.wait_idle(2))
        self.assertEqual(fake.calls,[('get-default-sink',),('--format=json','list','sinks')])
    def test_latest_pending_volume_and_mute_survive_coalescing(self):
        fake,session,q,messages=self.session();sources=copy.deepcopy(fake.rows['sources']);defaults=fake.default.copy()
        entered=threading.Event();release=threading.Event();original=session.backend.run
        def run(*args):
            if args[0]=='set-sink-volume'and not entered.is_set():entered.set();release.wait(2)
            return original(*args)
        session.backend.run=run;session.submit(volume=10);self.assertTrue(entered.wait(1))
        for value in range(101):session.submit(volume=value)
        sequence=session.submit(volume=73,muted=False);release.set();self.assertTrue(session.wait_idle(3));self.drain(q)
        writes=[c for c in fake.calls if c[0]=='set-sink-volume'];self.assertEqual(len(writes),2)
        endpoint=messages[-1].endpoint;self.assertEqual(endpoint.channels,(47841,23920));self.assertFalse(endpoint.muted);self.assertEqual(messages[-1].sequence,sequence)
        self.assertEqual(fake.rows['sources'],sources);self.assertEqual(fake.default,defaults)
    def test_zero_restore_and_many_changes_preserve_canonical_balance(self):
        fake,session,q,messages=self.session()
        for value in(0,100,*range(1,100),100):session.submit(volume=value);self.assertTrue(session.wait_idle(2))
        self.drain(q);self.assertEqual(messages[-1].endpoint.channels,(65536,32768))
    def test_external_balance_change_is_respected(self):
        fake,session,q,messages=self.session();session.submit(volume=20);self.assertTrue(session.wait_idle(2))
        fake.run('set-sink-volume','speaker','10000','30000');session.submit(volume=100);self.assertTrue(session.wait_idle(2));self.drain(q)
        self.assertEqual(messages[-1].endpoint.channels,(21845,65536))
    def test_changed_default_rejects_stale_intent_without_writes(self):
        fake,session,q,messages=self.session();fake.calls=[];fake.default['sink']='headphones';before=copy.deepcopy(fake.rows)
        session.submit(volume=1);self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertTrue(messages[-1].error);self.assertEqual(messages[-1].endpoint.name,'headphones');self.assertEqual(fake.rows,before)
        self.assertFalse(any(c[0].startswith('set-')for c in fake.calls))
    def test_missing_device_reports_failure_and_worker_exits(self):
        fake,session,q,messages=self.session();fake.rows['sinks']=[];session.submit(volume=1);self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertIsNone(messages[-1].endpoint);self.assertTrue(messages[-1].error)
    def test_failure_before_write_reconciles_original_state(self):
        fake,session,q,messages=self.session();fake.fail='set-sink-volume';session.submit(volume=1);self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertTrue(messages[-1].error);self.assertEqual(messages[-1].endpoint.channels,(65536,32768))
    def test_partial_write_failure_reads_actual_without_clobbering_external_value(self):
        fake=FakePulse();original=fake.run
        def run(*args):
            result=original(*args)
            if args[0]=='set-sink-volume':original('set-sink-volume','speaker','44444','22222');raise RuntimeError('Failure after accepted write')
            return result
        fake,session,q,messages=self.session(fake,run);session.submit(volume=1);self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertTrue(messages[-1].error);self.assertEqual(messages[-1].endpoint.channels,(44444,22222))
        self.assertEqual(len([c for c in fake.calls if c[0]=='set-sink-volume']),2,'No speculative rollback may overwrite the external update')
    def test_close_flushes_latest_and_suppresses_already_queued_callbacks(self):
        fake,session,q,messages=self.session();messages.clear();session.submit(volume=34,muted=False);session.close();self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertEqual(messages,[]);endpoint=session.backend.inventory()['sinks'][0];self.assertEqual(endpoint.percent,34);self.assertFalse(endpoint.muted)
        with self.assertRaises(RuntimeError):session.submit(volume=1)
    def test_close_can_drop_unsent_updates_and_has_no_worker_leak(self):
        entered=threading.Event();release=threading.Event();fake=FakePulse()
        def run(*args):entered.set();release.wait(2);return fake.run(*args)
        q=queue.Queue();session=PlaybackUpdates(PulseAudio(run),q.put,lambda _:None);self.sessions.append(session);self.assertTrue(entered.wait(1))
        session.submit(volume=2);session.close(flush=False);release.set();self.assertTrue(session.wait_closed(2));self.assertFalse(any(c[0].startswith('set-')for c in fake.calls))
    def test_reopened_session_waits_for_old_flush_then_latest_wins(self):
        fake,old,q,messages=self.session();entered=threading.Event();release=threading.Event();run=old.backend.run
        def blocked(*args):
            if args[0]=='set-sink-volume'and not entered.is_set():entered.set();release.wait(2)
            return run(*args)
        old.backend.run=blocked;old.submit(volume=10);self.assertTrue(entered.wait(1));old.submit(volume=20);old.close()
        second=PlaybackUpdates(PulseAudio(fake.run),q.put,messages.append,previous=old);self.sessions.append(second);second.submit(volume=80);second.close()
        release.set();self.assertTrue(second.wait_closed(3));self.assertTrue(old.wait_closed(1))
        self.assertEqual(second.backend.inventory()['sinks'][0].percent,80)
        self.assertIsNone(second.previous);self.assertIsNone(second.callback);self.assertIsNone(old.callback)
    def test_closed_failed_write_notifies_separate_error_owner_once(self):
        entered=threading.Event();release=threading.Event();fake=FakePulse();q=queue.Queue();messages=[];errors=[]
        def run(*args):
            if args[0]=='set-sink-volume':entered.set();release.wait(2);raise RuntimeError('Rejected')
            return fake.run(*args)
        session=PlaybackUpdates(PulseAudio(run),q.put,messages.append,error_callback=errors.append);self.sessions.append(session);self.assertTrue(session.wait_idle(2));self.drain(q);messages.clear()
        session.submit(volume=1);self.assertTrue(entered.wait(1));session.close();release.set();self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertEqual(messages,[]);self.assertEqual(len(errors),1);self.assertEqual(errors[0].endpoint.percent,100)
    def test_closed_initial_read_only_failure_has_no_error_notification(self):
        entered=threading.Event();release=threading.Event();q=queue.Queue();messages=[];errors=[]
        def run(*args):entered.set();release.wait(2);raise RuntimeError('Unavailable')
        session=PlaybackUpdates(PulseAudio(run),q.put,messages.append,error_callback=errors.append);self.sessions.append(session);self.assertTrue(entered.wait(1));session.close();release.set();self.assertTrue(session.wait_closed(2));self.drain(q)
        self.assertEqual(messages,[]);self.assertEqual(errors,[])
    def test_invalid_updates_rejected_without_writes(self):
        fake,session,q,messages=self.session()
        for values in({'volume':True},{'volume':101},{'muted':1},{}):
            with self.assertRaises(ValueError):session.submit(**values)
        self.assertFalse(any(c[0].startswith('set-')for c in fake.calls))
if __name__=='__main__':unittest.main()
