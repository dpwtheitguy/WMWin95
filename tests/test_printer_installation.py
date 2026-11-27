import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.printer_installation import *
class Discovery:
    def getPrinters(self):return {'Office':{}}
    def getDevices(self,**kwargs):return {'ipp':{'device-info':'IPP backend'},'ipps':{},'ipp://printer.local/ipp/print':{'device-info':'Actual endpoint'},'file:///tmp/output':{},'ipp://user:secret@host/path':{}}
    def getPPDs(self,**kwargs):return {'sample.ppd':{'ppd-make':'Acme','ppd-make-and-model':'Acme Laser'}}
class InstallationTests(unittest.TestCase):
    def setUp(self):self.discovery=discover_installation(Discovery())
    def test_backend_advertisements_never_become_fake_printers(self):
        self.assertEqual(self.discovery.transports,('ipp','ipps'));self.assertEqual(len(self.discovery.endpoints),1);self.assertEqual(self.discovery.endpoints[0].uri,'ipp://printer.local/ipp/print')
    def test_actual_drivers_and_driverless_are_distinct(self):
        self.assertEqual({d.ident for d in self.discovery.drivers},{'everywhere','sample.ppd'});self.assertTrue(next(d for d in self.discovery.drivers if d.ident=='everywhere').driverless)
    def test_no_credential_file_or_malformed_target(self):
        for uri in('file:///tmp/page','http://host/path','ipp://user:password@host/path','ipp://host','ipp://host/path?password=x','ipp://host:0/path','ipp://host:99999/path','ipp://host/a b'):
            with self.assertRaises(PrinterError,msg=uri):validate_endpoint(uri)
    def test_case_insensitive_collision_precedes_any_mutation(self):
        with self.assertRaisesRegex(PrinterError,'already exists'):PrinterInstallPlan('office','ipp://host/path','everywhere','Office').validate(self.discovery)
    def test_driverless_requires_ipp_and_actual_driver_remains_present(self):
        with self.assertRaisesRegex(PrinterError,'requires'):PrinterInstallPlan('New','socket://host:9100','everywhere','New').validate(self.discovery)
        with self.assertRaisesRegex(PrinterError,'no longer available'):PrinterInstallPlan('New','ipp://host/path','removed.ppd','New').validate(self.discovery)
        self.assertEqual(PrinterInstallPlan('New','ipps://host/path','everywhere','New').validate(self.discovery).name,'New')
    def test_navigation_validation_and_back_preserve_typed_values(self):
        state=PrinterWizardState().next(self.discovery).next(self.discovery)
        with self.assertRaises(PrinterError):state.next(self.discovery)
        state=replace(state,endpoint='ipp://host/path',name='New').next(self.discovery).next(self.discovery);self.assertEqual(state.page,4);self.assertEqual(state.previous().endpoint,state.endpoint);self.assertFalse(state.plan().print_test_page)
    def test_discovery_failure_cannot_be_mistaken_for_empty_success(self):
        service=Discovery();service.getDevices=lambda **_:(_ for _ in()).throw(RuntimeError('Forbidden'))
        with self.assertRaisesRegex(PrinterError,'authorization'):discover_installation(service)

class MutableScheduler(Discovery):
    def __init__(self):self.rows={'Office':{'printer-info':'Office','device-uri':'ipp://old/print','printer-is-accepting-jobs':True,'printer-state':3}};self.actions=[];self.fail=None
    def getPrinters(self):return {n:dict(a)for n,a in self.rows.items()}
    def getPrinterAttributes(self,name,**kwargs):return dict(self.rows[name])
    def addPrinter(self,name,**attrs):
        self.actions.append(('add',name));self.rows[name]={'printer-info':attrs['info'],'device-uri':attrs['device'],'printer-is-accepting-jobs':False,'printer-state':5}
        if self.fail=='add-response':raise RuntimeError('Lost response')
        if self.fail=='readback':self.rows[name]['device-uri']='ipp://changed/print'
    def setPrinterShared(self,name,value):self.actions.append(('share',name,value));self.rows[name]['printer-is-shared']=value
    def enablePrinter(self,name):
        if self.fail=='enable':raise RuntimeError('Stopped')
        self.actions.append(('enable',name));self.rows[name]['printer-state']=3
    def acceptJobs(self,name):self.actions.append(('accept',name));self.rows[name]['printer-is-accepting-jobs']=True

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.connection=MutableScheduler();self.records=[];self.token='a'*32
        self.installer=PrinterInstaller(self.connection,lambda r:self.records.append(dict(r)),token=lambda:self.token)
        self.plan=PrinterInstallPlan('New','ipp://printer.local/ipp/print','everywhere','New Display Name')
    def test_creates_random_identity_with_human_name_and_ready_readback(self):
        before=self.connection.rows['Office'].copy();result=self.installer.install(self.plan)
        self.assertEqual(result.queue,'w95lx_'+self.token);self.assertEqual(result.description,'New Display Name');self.assertEqual(self.connection.rows['Office'],before)
        self.assertEqual([r['phase']for r in self.records],['intent','created','ready']);self.assertEqual(self.connection.rows[result.queue]['printer-state'],3)
    def test_description_collision_rejects_without_mutation(self):
        self.plan=replace(self.plan,description='oFFice')
        with self.assertRaisesRegex(PrinterError,'already exists'):self.installer.install(self.plan)
        self.assertEqual(self.connection.actions,[]);self.assertEqual(self.records,[])
    def test_random_identity_collision_rejects_without_overwriting(self):
        self.connection.rows['w95lx_'+self.token]={'printer-info':'Foreign'}
        with self.assertRaisesRegex(PrinterError,'already in use'):self.installer.install(self.plan)
        self.assertEqual(self.connection.actions,[])
    def test_journal_failure_before_mutation_preserves_existing_queues(self):
        self.installer.journal=lambda _:(_ for _ in()).throw(OSError('Full disk'))
        with self.assertRaises(OSError):self.installer.install(self.plan)
        self.assertEqual(self.connection.actions,[])
    def test_stale_driver_rejected_on_execution(self):
        with self.assertRaises(PrinterError):self.installer.install(replace(self.plan,driver='removed'))
        self.assertEqual(self.connection.actions,[])
    def test_partial_enable_error_keeps_created_queue_and_explicit_identity(self):
        self.connection.fail='enable'
        with self.assertRaises(PartialInstallation)as context:self.installer.install(self.plan)
        self.assertEqual(context.exception.queue,'w95lx_'+self.token);self.assertIn(context.exception.queue,self.connection.rows);self.assertEqual(self.records[-1]['phase'],'partial')
    def test_lost_add_response_reports_partial_without_second_add_or_delete(self):
        self.connection.fail='add-response'
        with self.assertRaises(PartialInstallation):self.installer.install(self.plan)
        self.assertEqual(self.connection.actions,[('add','w95lx_'+self.token)])
    def test_readback_mismatch_never_enables_or_deletes_changed_queue(self):
        self.connection.fail='readback'
        with self.assertRaises(PartialInstallation):self.installer.install(self.plan)
        self.assertEqual(self.connection.actions,[('add','w95lx_'+self.token)])
    def test_bad_identity_is_rejected(self):
        self.token='../Office'
        with self.assertRaises(PrinterError):self.installer.install(self.plan)
        self.assertEqual(self.connection.actions,[])
    def test_user_options_never_run_as_privileged_installer(self):
        result=self.installer.install(replace(self.plan,make_user_default=True,print_test_page=True))
        self.assertIsNone(result.test_job);self.assertEqual([a[0]for a in self.connection.actions],['add','share','enable','accept'])
    def test_journal_atomic_replace_reopen_and_invalid_identity(self):
        import tempfile,json
        with tempfile.TemporaryDirectory()as d:
            record={'queue':'w95lx_'+self.token,'phase':'intent'};write_installation_record(d,record)
            path=Path(d)/(record['queue']+'.json');self.assertEqual(json.loads(path.read_text()),record)
            record['phase']='ready';write_installation_record(d,record);self.assertEqual(json.loads(path.read_text())['phase'],'ready')
            with self.assertRaises(PrinterError):write_installation_record(d,{'queue':'../../bad'})
    def test_service_roundtrip_shape(self):
        self.assertEqual(decode_discovery(encode_discovery(discover_installation(self.connection))),discover_installation(self.connection))

class UsbEndpointTests(unittest.TestCase):
    def test_actual_usb_serial_uri_requires_exact_discovered_endpoint(self):
        address='usb://HP/DeskJet?serial=ABC123&interface=1'
        discovery=InstallationDiscovery((PrinterDriver('hp.ppd','HP','DeskJet'),),(PrinterEndpoint(address,'Attached DeskJet'),),('usb',),())
        plan=PrinterInstallPlan('DeskJet',address,'hp.ppd','DeskJet');self.assertEqual(plan.validate(discovery).endpoint,address)
        with self.assertRaisesRegex(PrinterError,'attached USB'):replace(plan,endpoint=address.replace('ABC123','OTHER')).validate(discovery)
    def test_usb_query_is_not_a_password_or_arbitrary_argument_channel(self):
        for address in('usb://HP/DeskJet?password=secret','usb://HP/DeskJet?serial=A&serial=B','usb://HP/DeskJet?serial=%0Asecret','ipp://host/print?serial=A'):
            with self.assertRaises(PrinterError):validate_endpoint(address)

class JournalFailureTests(unittest.TestCase):
    def setUp(self):TransactionTests.setUp(self)
    def test_journal_failure_after_add_retains_partial_identity(self):
        def fail(record):
            if record['phase']!='intent':raise OSError('Full disk after add')
        self.installer.journal=fail
        with self.assertRaises(PartialInstallation)as context:self.installer.install(self.plan)
        self.assertEqual(context.exception.queue,'w95lx_'+self.token)
        self.assertIn(context.exception.queue,self.connection.rows)

if __name__=='__main__':unittest.main()
