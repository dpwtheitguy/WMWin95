import sys,unittest
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.network_preferences import (IPv4Config,Connection,NetworkState,NetworkController,NetworkManager,NetworkError,
    MODIFY,CONTROL,HOSTNAME,FIELDS,parse_connection,prefix_from_mask,valid_hostname,split_escaped)
UUID='15f427dd-57f1-4a02-9c2f-3764d6230565'

def profile(ip=None,**values):return Connection(UUID,'Test: connection','w95uat0','dummy',ip or IPv4Config(method='manual',address='192.0.2.10',netmask='255.255.255.0'),**values)
def format_profile(c):
    values={'connection.id':c.name,'connection.uuid':c.uuid,'connection.interface-name':c.device,'connection.type':c.kind,'connection.autoconnect':'yes' if c.autoconnect else 'no',**c.ipv4.properties()}
    return '\n'.join(str(values[name]).replace('\\','\\\\').replace(':','\\:') for name in FIELDS)

class FakeNM:
    def __init__(self,c=None):self.value=c or profile(active=True);self.calls=[];self.permit=True;self.fail_activate=False;self.fail_restore=False;self.host='win95lx-dev'
    def __call__(self,*args):
        self.calls.append(args)
        if args[:2]==('-g',','.join(FIELDS)):return format_profile(self.value)
        if args[:2]==('-t','--escape') and 'permissions' in args:return '\n'.join(name+':'+('yes' if self.permit else 'auth') for name in (MODIFY,CONTROL,HOSTNAME))
        if args[:3]==('connection','modify','uuid'):
            fields=dict(zip(args[4::2],args[5::2]));current={name:value for name,value in zip(FIELDS,format_profile(self.value).split('\n'))};current.update(fields)
            if self.fail_restore and fields.get('ipv4.addresses')=='192.0.2.10/24':raise NetworkError('restore failed')
            self.value=parse_connection('\n'.join(current[name] for name in FIELDS),True)
            return ''
        if args[:2]==('connection','up'):
            if self.fail_activate:self.fail_activate=False;raise NetworkError('activation failed')
            return ''
        if args[:2]==('general','hostname'):
            if len(args)>2:self.host=args[2]
            return self.host
        raise AssertionError(args)

class NetworkPreferenceTests(unittest.TestCase):
    def test_ipv4_mask_validation_and_host_boundaries(self):
        self.assertEqual(prefix_from_mask('255.255.255.0'),24);self.assertEqual(prefix_from_mask('255.255.255.255'),32)
        for mask in ('255.0.255.0','0.0.0.0','garbage'):
            with self.assertRaises(ValueError):prefix_from_mask(mask)
        for value in ('0.0.0.0','224.0.0.1','255.255.255.255','192.0.2.999'):
            with self.assertRaises(ValueError):IPv4Config(method='manual',address=value,netmask='255.255.255.0').validate()
    def test_manual_requires_address_and_mask(self):
        for p in (IPv4Config(method='manual'),IPv4Config(address='192.0.2.1'),IPv4Config(netmask='255.255.255.0')):
            with self.assertRaises(ValueError):p.validate()
    def test_auto_selection_discards_old_manual_addresses(self):
        p=IPv4Config(method='manual',address='192.0.2.10',netmask='255.255.255.0',extra_addresses=('192.0.2.11/24',)).set_method('auto')
        self.assertEqual(p.properties()['ipv4.addresses'],'');self.assertEqual(p.method,'auto')
    def test_disable_manual_dns_keeps_dhcp_dns_enabled(self):
        p=IPv4Config();self.assertEqual(p.properties()['ipv4.ignore-auto-dns'],'no')
        p=replace(p,manual_dns=True,dns=('192.0.2.53',));self.assertEqual(p.properties()['ipv4.ignore-auto-dns'],'yes')
    def test_existing_additional_addresses_routes_and_route_domains_roundtrip(self):
        p=IPv4Config(method='manual',address='192.0.2.10',netmask='255.255.255.0',extra_addresses=('192.0.2.11/24',),dns=('192.0.2.53',),search=('example.invalid',),route_search=('~win95lx-uat.invalid','~.'),routes='{ ip = 198.51.100.0/24, nh = 192.0.2.2 }')
        c=profile(p);actual=parse_connection(format_profile(c));self.assertEqual(actual.ipv4,p)
    def test_dns_and_name_validation(self):
        for p in (replace(IPv4Config(),dns=('bad',)),replace(IPv4Config(),search=('bad name',)),replace(IPv4Config(),route_search=('bad.invalid',))):
            with self.assertRaises(ValueError):p.validate()
        for name in ('-bad','bad-','space name','a'*16):
            with self.assertRaises(ValueError):valid_hostname(name)
        self.assertEqual(valid_hostname('PC-001'),'PC-001')
    def test_nm_escaped_names_do_not_split_fields(self):
        self.assertEqual(split_escaped(r'ethernet:Name\: office:back\\slash'),['ethernet','Name: office','back\\slash'])
        c=profile();self.assertEqual(parse_connection(format_profile(c)).name,c.name)
    def test_hostname_existing_long_value_does_not_prevent_reading_network(self):
        self.assertEqual(NetworkState('a-long-existing-hostname.example.invalid',(profile(),)).validate().hostname,'a-long-existing-hostname.example.invalid')
    def test_noop_does_not_mutate_profiles(self):
        run=FakeNM();backend=NetworkManager(run,lambda:True);s=NetworkState(run.host,(run.value,));backend.apply(s,s)
        self.assertEqual(run.calls,[])
    def test_apply_writes_only_edited_fields_then_reactivates_owned_profile(self):
        run=FakeNM();backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(run.value,));new=before.change_connection(UUID,ipv4=replace(run.value.ipv4,address='192.0.2.22',manual_dns=True,dns=('192.0.2.53',),search=('example.invalid',)))
        backend.apply(new,before);self.assertEqual(run.value.ipv4.address,'192.0.2.22')
        commands=[c for c in run.calls if c[:2]==('connection','modify')];self.assertEqual(len(commands),1)
        command=commands[0];self.assertNotIn('ipv4.routes',command);self.assertNotIn('ipv6.method',command);self.assertNotIn('--ask',command)
        self.assertTrue(any(c[:2]==('connection','up') for c in run.calls))
    def test_inactive_profile_edit_does_not_activate_it(self):
        run=FakeNM(profile(active=False));backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(run.value,));new=before.change_connection(UUID,ipv4=replace(run.value.ipv4,address='192.0.2.22'))
        backend.apply(new,before);self.assertFalse(any(c[:2]==('connection','up') for c in run.calls))
    def test_permission_auth_is_refused_before_any_mutation_or_prompt(self):
        run=FakeNM();run.permit=False;backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(run.value,));new=before.change_connection(UUID,ipv4=replace(run.value.ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'No password prompt'):backend.apply(new,before)
        self.assertFalse(any(c[0]=='connection' for c in run.calls))
    def test_activation_failure_restores_previous_profile_and_connection(self):
        run=FakeNM();old=run.value;run.fail_activate=True;backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(old,));new=before.change_connection(UUID,ipv4=replace(old.ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'activation failed'):backend.apply(new,before)
        self.assertEqual(run.value.ipv4,old.ipv4)
    def test_failed_restore_is_not_reported_as_success(self):
        run=FakeNM();run.fail_activate=True;run.fail_restore=True;backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(run.value,));new=before.change_connection(UUID,ipv4=replace(run.value.ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'could not be fully restored'):backend.apply(new,before)
    def test_external_changes_abort_before_writing(self):
        run=FakeNM();backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(run.value,));new=before.change_connection(UUID,ipv4=replace(run.value.ipv4,address='192.0.2.22'));run.value=replace(run.value,ipv4=replace(run.value.ipv4,address='192.0.2.33'))
        with self.assertRaisesRegex(NetworkError,'changed while'):backend.apply(new,before)
        self.assertFalse(any(c[:2]==('connection','modify') for c in run.calls))
    def test_guest_guard_prevents_host_mutation(self):
        run=FakeNM();backend=NetworkManager(run,lambda:False);s=NetworkState(run.host,(run.value,))
        with self.assertRaisesRegex(NetworkError,'installed Win95LX guest'):backend.apply(s,s)
        self.assertEqual(run.calls,[])
    def test_identity_edits_wait_for_stable_runtime_and_sharing_service(self):
        run=FakeNM();backend=NetworkManager(run,lambda:True);before=NetworkState(run.host,(run.value,))
        with self.assertRaisesRegex(NetworkError,'identity service'):backend.apply(replace(before,hostname='PC-001'),before)
        with self.assertRaisesRegex(NetworkError,'sharing service'):backend.apply(replace(before,workgroup='WORKGROUP'),before)
        self.assertEqual(run.calls,[])
    def test_real_hostname_backend_argument_is_bounded_and_no_shell(self):
        run=FakeNM();backend=NetworkManager(run,lambda:True);backend.identity_editable=True;before=NetworkState(run.host,(run.value,));backend.apply(replace(before,hostname='PC-001'),before)
        self.assertEqual(run.host,'PC-001');self.assertIn(('general','hostname','PC-001'),run.calls)
class NetworkControllerVerificationTests(unittest.TestCase):
    def test_failed_post_apply_read_restores_previous_authoritative_state(self):
        before=NetworkState('win95lx-dev',(profile(),))
        class Backend:
            def __init__(self):self.state=before;self.reads=0;self.restored=False
            def preferences(self):
                self.reads+=1
                if self.reads==2:raise NetworkError('read failed')
                return self.state
            def apply(self,pending,baseline):self.state=pending
            def restore(self,value):self.state=value;self.restored=True
        backend=Backend();controller=NetworkController(backend);controller.pending=before.change_connection(UUID,ipv4=replace(before.connections[0].ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'were restored'):controller.apply()
        self.assertEqual(backend.state,before);self.assertTrue(backend.restored);self.assertEqual(controller.applied,before)
    def test_failed_post_apply_rollback_is_not_claimed_successful(self):
        class Backend:
            def __init__(self):self.reads=0
            def preferences(self):
                self.reads+=1
                if self.reads>1:raise NetworkError('read failed')
                return NetworkState('win95lx-dev',(profile(),))
            def apply(self,*_):pass
            def restore(self,*_):raise NetworkError('restore failed')
        controller=NetworkController(Backend())
        with self.assertRaisesRegex(NetworkError,'fully restored'):controller.apply()

class NativeTemplateTests(unittest.TestCase):
    def test_bounded_win16_template_has_no_alignment_requirement(self):
        import struct
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
        from stage_network_assets import parse_win16_dialog
        header=struct.pack('<IBhhhh',0,1,0,0,100,100)+b'\0\0A\0'
        item=struct.pack('<hhhhHI',1,2,3,4,42,0)+b'\x80OK\0\0'
        result=parse_win16_dialog(header+item);self.assertEqual(result['controls'][0]['text'],'OK');self.assertEqual(result['controls'][0]['id'],42)
        for length in range(len(header+item)):
            with self.assertRaises((ValueError,struct.error)):parse_win16_dialog((header+item)[:length])

class IPv4EntryTests(unittest.TestCase):
    def test_typing_periods_and_three_digit_advance(self):
        from win95lx.control_panel.network_preferences import IPv4Entry
        e=IPv4Entry()
        for char in '192.0.2.10':e.key('',char)
        self.assertEqual(e.text,'192.0.2.10')
    def test_invalid_paste_and_out_of_range_are_atomic(self):
        from win95lx.control_panel.network_preferences import IPv4Entry
        e=IPv4Entry('192.0.2.10');e.focus(0)
        self.assertFalse(e.key('','999.1.2.3'));self.assertEqual(e.text,'192.0.2.10')
        self.assertTrue(e.key('','255'));self.assertEqual(e.index,1)
        e.focus(0);self.assertFalse(e.key('','256'));self.assertEqual(e.text,'255.0.2.10')
    def test_empty_fields_are_not_filled_or_mask_guessed(self):
        from win95lx.control_panel.network_preferences import IPv4Entry
        e=IPv4Entry();self.assertEqual(e.text,'');e.key('','1');self.assertEqual(e.text,'1...')
    def test_arrows_backspace_and_select_all(self):
        from win95lx.control_panel.network_preferences import IPv4Entry
        e=IPv4Entry('192.0.2.10');e.focus(1);e.key('Left');e.key('BackSpace')
        self.assertEqual(e.index,0);e.key('a',ctrl=True);e.key('','10');self.assertEqual(e.text,'10.0.2.10')

if __name__=='__main__':unittest.main()

class NetworkReadbackAcceptanceTests(unittest.TestCase):
    def test_successful_read_with_wrong_value_is_not_accepted(self):
        before=NetworkState('win95lx-dev',(profile(),))
        class Backend:
            def __init__(self):self.restored=None
            def preferences(self):return before
            def apply(self,pending,baseline):pass
            def restore(self,value):self.restored=value
        backend=Backend();controller=NetworkController(backend);controller.pending=before.change_connection(UUID,ipv4=replace(before.connections[0].ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'were restored'):controller.apply()
        self.assertEqual(backend.restored,before);self.assertEqual(controller.applied,before)
    def test_failed_readback_restores_only_edited_profile(self):
        other=replace(profile(),uuid='4c390e1e-c79e-4626-bbea-c95d9794010d',name='Untouched adapter')
        before=NetworkState('win95lx-dev',(profile(),other))
        class Backend:
            def __init__(self):self.reads=0;self.restored=None
            def preferences(self):
                self.reads+=1
                if self.reads>1:raise NetworkError('read failed')
                return before
            def apply(self,pending,baseline):pass
            def restore(self,value):self.restored=value
        backend=Backend();controller=NetworkController(backend);controller.pending=before.change_connection(UUID,ipv4=replace(before.connections[0].ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'were restored'):controller.apply()
        self.assertEqual(tuple(c.uuid for c in backend.restored.connections),(UUID,))
    def test_missing_edited_profile_after_apply_is_not_accepted(self):
        before=NetworkState('win95lx-dev',(profile(),))
        class Backend:
            def __init__(self):self.reads=0;self.restored=None
            def preferences(self):
                self.reads+=1;return before if self.reads==1 else replace(before,connections=())
            def apply(self,pending,baseline):pass
            def restore(self,value):self.restored=value
        backend=Backend();controller=NetworkController(backend);controller.pending=before.change_connection(UUID,ipv4=replace(before.connections[0].ipv4,address='192.0.2.22'))
        with self.assertRaisesRegex(NetworkError,'were restored'):controller.apply()
        self.assertEqual(backend.restored,before)
