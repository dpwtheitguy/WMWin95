"""Scoped service contract; no live host network changes."""
import copy,json,sys,tempfile,unittest
from unittest.mock import patch,MagicMock
from types import SimpleNamespace
from pathlib import Path
from dataclasses import replace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.network_service import NetworkService, ServiceNetworkManager, encode_state, decode_state, validate_policy
from win95lx.control_panel.network_preferences import NetworkState,Connection,IPv4Config,NetworkError
UUID='15f427dd-57f1-4a02-9c2f-3764d6230565'
OTHER='25f427dd-57f1-4a02-9c2f-3764d6230565'

class Manager:
    def __init__(self):
        ip=IPv4Config(method='manual',address='198.18.255.1',netmask='255.255.255.252',never_default=True,route_search=('~win95lx-uat.invalid',))
        self.state=NetworkState('win95lx-dev',(Connection(UUID,'Owned','w95uat0','dummy',ip,False,True),));self.writes=0;self.fail=False;self.bad_readback=False;self.restore_failure=False;self.isolation='49995\n32760\ndisabled';self.adapters=()
    def preferences(self):return self.state
    def connection(self,identity,*args):return next(c for c in self.state.connections if c.uuid==identity)
    def run(self,*args):return self.isolation
    def apply(self,pending,baseline):
        self.writes+=1
        if self.fail:raise NetworkError('Activation failed.')
        rows={c.uuid:c for c in self.state.connections};rows.update({c.uuid:c for c in pending.connections});self.state=replace(self.state,connections=tuple(rows.values()))
        if self.bad_readback:self.bad_readback=False;self.state=replace(self.state,connections=tuple(replace(c,ipv4=replace(c.ipv4,address='198.18.255.3')) for c in self.state.connections))
    def restore(self,before):
        if self.restore_failure:raise NetworkError('Recovery failed.')
        self.state=before

class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.manager=Manager();self.policy={'schema':1,'peer_uid':1001,'profiles':[{'uuid':UUID,'device':'w95uat0','kind':'dummy','qa_only':True}]};self.service=NetworkService(self.manager,self.policy,guard=lambda:True)
        self.baseline=self.manager.state;self.pending=self.baseline.change_connection(UUID,ipv4=replace(self.baseline.connections[0].ipv4,address='198.18.255.2'))
    def request(self,pending=None,baseline=None):return {'operation':'apply','request_id':'a'*32,'baseline':encode_state(baseline or self.baseline),'pending':encode_state(pending or self.pending)}
    def test_roundtrip_plain_document(self):self.assertEqual(decode_state(encode_state(self.baseline)),self.baseline)
    def test_normal_scoped_apply(self):
        reply=self.service.operation(self.request());self.assertTrue(reply['ok']);self.assertEqual(self.manager.state.connections[0].ipv4.address,'198.18.255.2')
    def test_repeated_identical_request_not_reapplied(self):self.service.operation(self.request());self.service.operation(self.request());self.assertEqual(self.manager.writes,1)
    def test_request_id_payload_collision_rejected(self):
        self.service.operation(self.request());request=self.request();request['pending']['connections'][0]['ipv4']['address']='198.18.255.3'
        with self.assertRaises(NetworkError):self.service.operation(request)
    def test_guard_denial_precedes_writes(self):
        self.service.guard=lambda:False
        with self.assertRaises(NetworkError):self.service.operation(self.request())
        self.assertEqual(self.manager.writes,0)
    def test_unknown_operation_rejected(self):
        request=self.request();request['operation']='run'
        with self.assertRaises(ValueError):self.service.operation(request)
    def test_command_payload_rejected(self):
        request=self.request();request['command']='nmcli anything'
        with self.assertRaises(ValueError):self.service.operation(request)
    def test_unrelated_uuid_rejected(self):
        baseline=replace(self.baseline,connections=(replace(self.baseline.connections[0],uuid=OTHER),))
        with self.assertRaises(NetworkError):self.service.operation(self.request(baseline,baseline))
    def test_interface_substitution_rejected(self):
        pending=self.pending.change_connection(UUID,device='ens2')
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_kind_substitution_rejected(self):
        pending=self.pending.change_connection(UUID,kind='802-3-ethernet')
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_profile_addition_rejected(self):
        pending=replace(self.pending,connections=self.pending.connections+(replace(self.pending.connections[0],uuid=OTHER),))
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_profile_removal_rejected(self):
        with self.assertRaises(NetworkError):self.service.operation(self.request(replace(self.pending,connections=())))
    def test_hostname_change_rejected(self):
        with self.assertRaises(NetworkError):self.service.operation(self.request(replace(self.pending,hostname='Other')))
    def test_stale_hostname_rejected(self):
        self.manager.state=replace(self.manager.state,hostname='Changed')
        with self.assertRaises(NetworkError):self.service.operation(self.request())
    def test_stale_supported_state_rejected(self):
        self.manager.state=self.manager.state.change_connection(UUID,ipv4=replace(self.manager.state.connections[0].ipv4,address='198.18.255.3'))
        with self.assertRaises(NetworkError):self.service.operation(self.request())
    def test_stale_active_flag_cannot_be_spoofed(self):
        baseline=self.baseline.change_connection(UUID,active=False);pending=self.pending.change_connection(UUID,active=False)
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending,baseline))
    def test_routes_cannot_be_edited(self):
        pending=self.pending.change_connection(UUID,ipv4=replace(self.pending.connections[0].ipv4,routes='default via gateway'))
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_neverdefault_cannot_be_disabled(self):
        pending=self.pending.change_connection(UUID,ipv4=replace(self.pending.connections[0].ipv4,never_default=False))
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_qa_default_gateway_rejected(self):
        pending=self.pending.change_connection(UUID,ipv4=replace(self.pending.connections[0].ipv4,gateway='198.18.255.1'))
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_qa_autoconnect_rejected(self):
        with self.assertRaises(NetworkError):self.service.operation(self.request(self.pending.change_connection(UUID,autoconnect=True)))
    def test_qa_global_search_rejected(self):
        pending=self.pending.change_connection(UUID,ipv4=replace(self.pending.connections[0].ipv4,search=('example.invalid',)))
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_qa_missing_private_routing_properties_rejected(self):
        self.manager.isolation='254\n0\nauto'
        with self.assertRaises(NetworkError):self.service.operation(self.request())
    def test_sharing_address_mode_rejected(self):
        pending=self.pending.change_connection(UUID,ipv4=replace(self.pending.connections[0].ipv4,method='shared'))
        with self.assertRaises(NetworkError):self.service.operation(self.request(pending))
    def test_bad_readback_restores(self):
        self.manager.bad_readback=True
        with self.assertRaises(NetworkError):self.service.operation(self.request())
        self.assertEqual(self.manager.state,self.baseline)
    def test_failed_recovery_reported(self):
        self.manager.bad_readback=True;self.manager.restore_failure=True
        with self.assertRaisesRegex(NetworkError,'fully restored'):self.service.operation(self.request())
    def test_policy_requires_nonroot_uid(self):
        for uid in (0,-1,True,'1001'):
            policy=copy.deepcopy(self.policy);policy['peer_uid']=uid
            with self.subTest(uid=uid),self.assertRaises(ValueError):validate_policy(policy)
    def test_policy_qa_not_primary_adapter(self):
        policy=copy.deepcopy(self.policy);policy['profiles'][0]['device']='ens2'
        with self.assertRaises(ValueError):validate_policy(policy)
    def test_policy_no_unrecognized_fields(self):
        policy=copy.deepcopy(self.policy);policy['profiles'][0]['allow_shell']=True
        with self.assertRaises(ValueError):validate_policy(policy)
    def test_decode_rejects_extra_top_level(self):
        value=encode_state(self.baseline);value['run']='arbitrary'
        with self.assertRaises(ValueError):decode_state(value)
    def test_decode_boolean_not_string(self):
        value=encode_state(self.baseline);value['connections'][0]['active']='yes'
        with self.assertRaises(ValueError):decode_state(value)
    def test_request_cache_bounded(self):
        for n in range(70):
            request=self.request(self.manager.state,self.manager.state);request['request_id']=format(n,'032x');self.service.operation(request)
        self.assertEqual(len(self.service.requests),64)
    def test_client_adapter_cancel_does_not_call_service(self):
        class Client:
            def call(self,value):raise AssertionError('No write')
        adapter=ServiceNetworkManager(self.manager,Client());adapter.apply(self.baseline,self.baseline)
    def test_client_adapter_sends_only_changed_profile(self):
        other=replace(self.baseline.connections[0],uuid=OTHER,device='other');baseline=replace(self.baseline,connections=self.baseline.connections+(other,));pending=baseline.change_connection(UUID,ipv4=self.pending.connections[0].ipv4)
        calls=[]
        class Client:
            def call(self,value):calls.append(value)
        ServiceNetworkManager(self.manager,Client()).apply(pending,baseline)
        self.assertEqual([r['uuid']for r in calls[0]['pending']['connections']],[UUID])

    def test_success_removes_durable_journal(self):
        with tempfile.TemporaryDirectory()as root:
            journal=Path(root)/'pending.json';self.service.journal=journal;self.service.operation(self.request());self.assertFalse(journal.exists())
    def test_restored_failure_removes_journal(self):
        with tempfile.TemporaryDirectory()as root:
            journal=Path(root)/'pending.json';self.service.journal=journal;self.manager.bad_readback=True
            with self.assertRaises(NetworkError):self.service.operation(self.request())
            self.assertFalse(journal.exists())
    def test_partial_recovery_preserves_journal_and_blocks_retry(self):
        with tempfile.TemporaryDirectory()as root:
            journal=Path(root)/'pending.json';self.service.journal=journal;self.manager.bad_readback=True;self.manager.restore_failure=True
            with self.assertRaises(NetworkError):self.service.operation(self.request())
            self.assertTrue(journal.exists());writes=self.manager.writes
            with self.assertRaisesRegex(NetworkError,'interrupted'):self.service.operation(self.request())
            self.assertEqual(self.manager.writes,writes)
    def test_existing_journal_prevents_new_mutation(self):
        with tempfile.TemporaryDirectory()as root:
            journal=Path(root)/'pending.json';journal.write_text('{}');self.service.journal=journal
            with self.assertRaises(NetworkError):self.service.operation(self.request())
            self.assertEqual(self.manager.writes,0)
    def test_authorization_rejects_wrong_peer_uid_before_logind(self):
        import os,socket
        from win95lx.control_panel.network_service import active_local_peer
        one,two=socket.socketpair()
        try:self.assertFalse(active_local_peer(one,os.getuid()+1))
        finally:one.close();two.close()

    def authorization_fixture(self,*,active=1,remote=0,kind=b'x11',owner=1001,session_result=0):
        import ctypes,struct
        from win95lx.control_panel.network_service import active_local_peer
        session_buffer=ctypes.create_string_buffer(b'owned-session');kind_buffer=ctypes.create_string_buffer(kind)
        def session(fd,output):
            if session_result<0:return session_result
            ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.addressof(session_buffer);return 0
        def get_uid(name,output):ctypes.cast(output,ctypes.POINTER(ctypes.c_uint))[0]=owner;return 0
        def get_type(name,output):ctypes.cast(output,ctypes.POINTER(ctypes.c_void_p))[0]=ctypes.addressof(kind_buffer);return 0
        library=SimpleNamespace(sd_peer_get_session=MagicMock(side_effect=session),sd_session_get_uid=MagicMock(side_effect=get_uid),sd_session_get_type=MagicMock(side_effect=get_type),sd_session_is_active=MagicMock(return_value=active),sd_session_is_remote=MagicMock(return_value=remote))
        libc=SimpleNamespace(free=MagicMock())
        peer=SimpleNamespace(getsockopt=lambda *a:struct.pack('3i',123,1001,1001),fileno=lambda:7)
        with patch('ctypes.CDLL',side_effect=[library,libc]):return active_local_peer(peer,1001)
    def test_authorization_accepts_active_local_graphical_peer(self):self.assertTrue(self.authorization_fixture())
    def test_authorization_denies_remote_session(self):self.assertFalse(self.authorization_fixture(remote=1))
    def test_authorization_denies_inactive_session(self):self.assertFalse(self.authorization_fixture(active=0))
    def test_authorization_denies_tty_session(self):self.assertFalse(self.authorization_fixture(kind=b'tty'))
    def test_authorization_denies_mismatched_session_owner(self):self.assertFalse(self.authorization_fixture(owner=1002))
    def test_authorization_denies_no_logind_session(self):self.assertFalse(self.authorization_fixture(session_result=-61))
    def test_authorization_denies_logind_query_failure(self):self.assertFalse(self.authorization_fixture(active=-5))

    def socket_reply(self,payload):
        import socket,threading
        from win95lx.control_panel.network_service import NetworkServiceClient
        with tempfile.TemporaryDirectory()as root:
            path=Path(root)/'service.sock';server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(path));server.listen(1)
            def worker():
                try:
                    peer,_=server.accept()
                    with peer:
                        with peer.makefile('rb')as stream:stream.readline(65537)
                        try:peer.sendall(payload)
                        except BrokenPipeError:pass
                finally:server.close()
            thread=threading.Thread(target=worker);thread.start()
            try:return NetworkServiceClient(path).call(self.request())
            finally:thread.join(timeout=2)
    def test_client_socket_roundtrip(self):
        self.assertEqual(self.socket_reply(json.dumps({'ok':True,'value':encode_state(self.pending)}).encode()+b'\n'),self.pending)
    def test_client_socket_native_domain_error(self):
        with self.assertRaisesRegex(NetworkError,'Denied by policy'):self.socket_reply(b'{"ok":false,"error":"Denied by policy"}\n')
    def test_client_socket_missing_newline(self):
        with self.assertRaises(NetworkError):self.socket_reply(b'{"ok":true}')
    def test_client_socket_oversized_reply(self):
        with self.assertRaises(NetworkError):self.socket_reply(b'x'*65538+b'\n')
    def test_client_socket_malformed_json(self):
        with self.assertRaises(NetworkError):self.socket_reply(b'broken\n')
    def test_client_socket_missing_state(self):
        with self.assertRaises(NetworkError):self.socket_reply(b'{"ok":true}\n')

if __name__=='__main__':unittest.main()
