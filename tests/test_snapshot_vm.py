import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dev'))
from snapshot_vm import save_checkpoint
class FakeQMP:
    def __init__(self,media=None,error='',existing=False):self.media=media or [];self.error=error;self.saved=existing;self.calls=[]
    def call(self,command,args=None):
        self.calls.append((command,args))
        if command=='query-block':return self.media
        if args['command-line']=='info snapshots':return '1 safe 0 B' if self.saved else 'No snapshots'
        self.saved=not bool(self.error);return self.error
class SnapshotTests(unittest.TestCase):
    def test_save_verified(self):self.assertTrue(save_checkpoint(FakeQMP(),'safe')['verified'])
    def test_monitor_error_is_failure(self):
        with self.assertRaises(RuntimeError):save_checkpoint(FakeQMP(error='Error: failed'),'safe')
    def test_existing_checkpoint_preserved(self):
        q=FakeQMP(existing=True)
        with self.assertRaises(ValueError):save_checkpoint(q,'safe')
        self.assertFalse(any(c[1] and c[1].get('command-line','').startswith('savevm ') for c in q.calls))
    def test_writable_raw_media_not_ejected(self):
        q=FakeQMP([{'device':'floppy0','inserted':{'drv':'raw','ro':False}}])
        with self.assertRaises(RuntimeError):save_checkpoint(q,'safe')
        self.assertEqual(len(q.calls),1)
    def test_monitor_injection_rejected(self):
        q=FakeQMP()
        for value in ('bad\nquit','../bad','', 'bad name'):
            with self.assertRaises(ValueError):save_checkpoint(q,value)
        self.assertEqual(q.calls,[])
if __name__=='__main__':unittest.main()
