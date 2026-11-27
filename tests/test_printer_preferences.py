import copy,sys,tempfile,unittest,subprocess
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.printer_preferences import Printers,PrinterError,queue_name,public_uri

class FakeCups:
    def __init__(self,path):
        self.path=path;self.rows={'Office':{'printer-info':'Office Printer','printer-state':3,'printer-is-accepting-jobs':True,'device-uri':'ipp://user:secret@printer.local/ipp/print'},'Other':{'printer-state':5}}
        self.job_rows={4:{'job-printer-uri':'ipp://localhost/printers/Office','job-name':'Document','job-originating-user-name':'win95','job-state':4,'job-k-octets':2},5:{'job-printer-uri':'ipp://localhost/printers/Other','job-originating-user-name':'win95','job-state':3},6:{'job-printer-uri':'ipp://localhost/printers/Office','job-originating-user-name':'someone','job-state':3}}
        self.admin=False;self.fail_default=False;self.calls=[];self.printed=None
    def getPrinters(self):return self.rows
    def getDests(self):
        name='Office'
        if self.path.exists()and not self.fail_default:
            for line in self.path.read_text().splitlines():
                if line.startswith('Default '):name=line.split()[1]
        return {(None,None):SimpleNamespace(name=name)}
    def adminGetServerSettings(self):
        if not self.admin:raise RuntimeError(0x403,'Forbidden')
        return {}
    def getJobs(self,**kwargs):return {ident:attrs for ident,attrs in self.job_rows.items()if not kwargs.get('my_jobs')or attrs.get('job-originating-user-name')=='win95'}
    def getJobAttributes(self,ident,**kwargs):return self.job_rows[ident]
    def cancelJob(self,ident,**kwargs):self.calls.append(('cancel',ident));self.job_rows.pop(ident)
    def printFile(self,name,path,title,options):self.printed=Path(path).read_bytes();self.calls.append(('print',name,title,options));return 10
    def disablePrinter(self,name,reason):self.calls.append(('pause',name));self.rows[name]['printer-state']=5
    def enablePrinter(self,name):self.calls.append(('resume',name));self.rows[name]['printer-state']=3

class PrinterTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/'.cups/lpoptions';self.fake=FakeCups(self.path);self.backend=Printers(self.fake,options_path=self.path,user='win95')
    def tearDown(self):self.directory.cleanup()
    def test_inventory_default_states_and_redacted_uri(self):
        values=self.backend.inventory();self.assertEqual([p.name for p in values],['Office','Other']);self.assertTrue(values[0].default);self.assertEqual(values[1].status,'Paused');self.assertEqual(values[0].uri,'ipp://printer.local/ipp/print');self.assertEqual(self.fake.calls,[])
    def test_user_default_preserves_existing_options_and_system_queues(self):
        self.path.parent.mkdir();self.path.write_text('# settings\nDefault Office media=A4 sides=two-sided-long-edge\nDest Other copies=2\n')
        before=copy.deepcopy(self.fake.rows);self.backend.set_default('Other')
        self.assertEqual(self.path.read_text(),'# settings\nDest Office media=A4 sides=two-sided-long-edge\nDefault Other copies=2\n');self.assertEqual(self.fake.rows,before);self.assertTrue(self.backend.printer('Other').default)
    def test_rejected_default_restores_exact_previous_file(self):
        self.path.parent.mkdir();self.path.write_bytes(b'Default Office media=A4\n');before=self.path.read_bytes();self.fake.fail_default=True
        with self.assertRaises(PrinterError):self.backend.set_default('Other')
        self.assertEqual(self.path.read_bytes(),before);self.assertFalse(list(self.path.parent.glob('.lpoptions-*')))
    def test_rejected_first_default_does_not_leave_new_file(self):
        self.fake.fail_default=True
        with self.assertRaises(PrinterError):self.backend.set_default('Other')
        self.assertFalse(self.path.exists())
    def test_symlink_preferences_and_invalid_names_cannot_write(self):
        target=Path(self.directory.name)/'outside';target.write_text('unchanged');self.path.parent.mkdir();self.path.symlink_to(target)
        with self.assertRaises(PrinterError):self.backend.set_default('Other')
        self.assertEqual(target.read_text(),'unchanged')
        for name in('',None,'../Office','-option','name\nline','two words'):
            with self.assertRaises(ValueError):queue_name(name)
    def test_jobs_are_scoped_and_only_own_can_be_canceled_without_admin(self):
        self.assertEqual([j.ident for j in self.backend.jobs('Office')],[4,6]);self.backend.cancel('Office',4)
        for ident in(5,6):
            with self.assertRaises(PrinterError):self.backend.cancel('Office',ident)
        self.assertEqual(self.fake.calls,[('cancel',4)])
    def test_capability_checks_gray_queue_administration_by_actual_access(self):
        self.assertFalse(self.backend.capabilities().administration)
        with self.assertRaises(PrinterError):self.backend.pause('Office',True)
        self.assertEqual(self.fake.calls,[]);self.fake.admin=True;self.assertFalse(self.backend.capabilities().administration);self.backend=Printers(self.fake,options_path=self.path,user='win95',administration=True);self.backend.pause('Office',True);self.assertEqual(self.backend.printer('Office').state,5);self.backend.pause('Office',False);self.assertEqual(self.backend.printer('Office').state,3)
    def test_testpage_is_spooled_and_temp_source_removed(self):
        captured=[];run=self.fake.printFile
        def print_file(name,path,title,options):captured.append(Path(path));return run(name,path,title,options)
        self.fake.printFile=print_file;self.assertEqual(self.backend.print_test_page('Office'),10);self.assertIn(b'Windows Printer Test Page',self.fake.printed);self.assertFalse(captured[0].exists())
        self.fake.rows['Office']['printer-is-accepting-jobs']=False
        with self.assertRaises(PrinterError):self.backend.print_test_page('Office')
    def test_testpage_is_valid_postscript_and_escapes_printer_description(self):
        self.fake.rows['Office']['printer-info']='Office (A)\\printer'
        self.backend.print_test_page('Office')
        self.assertIn(b'findfont 18 scalefont',self.fake.printed)
        self.assertIn(b'findfont 12 scalefont',self.fake.printed)
        result=subprocess.run(['gs','-q','-dBATCH','-dNOPAUSE','-sDEVICE=nullpage','-'],input=self.fake.printed,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())
    def test_actual_authorization_failure_is_native_error_and_preserves_job(self):
        def denied(*args,**kwargs):raise RuntimeError(0x403,'Forbidden')
        self.fake.cancelJob=denied
        with self.assertRaisesRegex(PrinterError,'Access is denied'):self.backend.cancel('Office',4)
        self.assertIn(4,self.fake.job_rows)
    def test_private_job_summaries_still_list_destination_and_own_documents(self):
        original=self.fake.getJobs
        self.fake.getJobs=lambda **kwargs:{ident:{'job-uri':'ipp://localhost/jobs/'+str(ident)}for ident in original(**kwargs)}
        self.fake.getJobAttributes=lambda ident,**kwargs:{key:value for key,value in self.fake.job_rows[ident].items()if key not in('job-originating-user-name','job-name')}
        jobs=self.backend.jobs('Office');self.assertEqual([j.ident for j in jobs],[4,6]);self.assertEqual(jobs[0].owner,'win95');self.assertEqual(jobs[0].title,'Untitled');self.assertEqual(jobs[1].owner,'')
        self.backend.cancel('Office',4)
        with self.assertRaises(PrinterError):self.backend.cancel('Office',6)
    def test_missing_printer_and_ipv6_uri(self):
        with self.assertRaises(PrinterError):self.backend.printer('Missing')
        self.assertEqual(public_uri('ipp://user:secret@[::1]:631/printers/test'),'ipp://[::1]:631/printers/test')
if __name__=='__main__':unittest.main()
