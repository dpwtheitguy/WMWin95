import ctypes as C,os,sys,unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from win95lx.control_panel.access_preferences import (AccessPreferences,AccessController,apply_saved_session,AccessibilityError,XKBAccess,_Controls,patch_controls,REPEAT,SLOW,BOUNCE,STICKY,MOUSE,FEEDBACK,ENABLED,STICKY_FEEDBACK,INDICATOR_FEEDBACK,FEATURE_FEEDBACK,ACCESS_KEYS,TIMEOUT,MOUSE_ACCEL)

def controls():
    c=_Controls();c.enabled_ctrls=REPEAT|1024;c.ax_options=0x800;c.repeat_delay=500;c.repeat_interval=30;c.slow_keys_delay=300;c.debounce_delay=300;c.mk_delay=160;c.mk_interval=40;c.mk_time_to_max=30;c.mk_max_speed=30;c.mk_curve=0;c.ax_timeout=300;c.axt_ctrls_mask=1024;c.axt_ctrls_values=1024;c.per_key_repeat[5]=173;return c

class FakeXKB(XKBAccess):
    def __init__(self):self.current=bytes(controls());self.guard=lambda:True;self.writes=[];self.reject=False;self.fail=False;self.fail_rollback=False
    def snapshot(self):return self.current
    def _write(self,data,mask):
        self._allowed();self.writes.append((data,mask))
        if self.fail and len(self.writes)==1:raise AccessibilityError('write failed')
        if self.fail_rollback and len(self.writes)>1:raise AccessibilityError('rollback failed')
        if self.reject and len(self.writes)==1:return
        self.current=data

class AccessTests(unittest.TestCase):
    def test_strict_flags_and_timing_boundaries(self):
        for changes in ({'sticky':1},{'slow_ms':0},{'bounce_ms':65536},{'mouse_curve':1001},{'reset_seconds':True},{'mouse_interval_ms':-1}):
            with self.assertRaises(ValueError):replace(AccessPreferences(),**changes).validate()
        replace(AccessPreferences(),slow_ms=65535,mouse_curve=-1000).validate()
    def test_noop_has_no_protocol_writes(self):
        b=FakeXKB();p=b.preferences();b.apply(p,p);self.assertEqual(b.writes,[])
    def test_changed_sticky_preserves_repeat_layout_and_unknown_options(self):
        c=controls();before=AccessPreferences.from_controls(c);after,mask=patch_controls(c,replace(before,sticky=True),before)
        self.assertTrue(after.enabled_ctrls&STICKY);self.assertTrue(after.enabled_ctrls&REPEAT);self.assertEqual(after.repeat_delay,500);self.assertEqual(after.per_key_repeat[5],173);self.assertEqual(after.ax_options,0x800)
        self.assertEqual(mask,ENABLED|STICKY)
    def test_slow_and_bounce_timing_are_independent(self):
        c=controls();p=AccessPreferences.from_controls(c);after,mask=patch_controls(c,replace(p,slow=True,slow_ms=700,bounce_ms=250),p)
        self.assertEqual(after.slow_keys_delay,700);self.assertEqual(after.debounce_delay,250);self.assertEqual(c.slow_keys_delay,300);self.assertTrue(mask&SLOW);self.assertTrue(mask&BOUNCE)
    def test_newly_enabled_zero_delay_gets_valid_edit_default(self):
        c=controls();c.slow_keys_delay=0;p=AccessPreferences.from_controls(c);after,mask=patch_controls(c,replace(p,slow=True),p)
        self.assertEqual(after.slow_keys_delay,300);self.assertTrue(mask&SLOW)
    def test_feedback_activation_does_not_enable_dormant_owned_options(self):
        c=controls();c.ax_options=FEATURE_FEEDBACK;p=AccessPreferences.from_controls(c);self.assertFalse(p.feature_feedback)
        after,mask=patch_controls(c,replace(p,toggle_feedback=True),p)
        self.assertTrue(after.enabled_ctrls&FEEDBACK);self.assertTrue(after.ax_options&INDICATOR_FEEDBACK);self.assertFalse(after.ax_options&FEATURE_FEEDBACK)
    def test_disabling_owned_feedback_preserves_unrelated_feedback(self):
        c=controls();c.enabled_ctrls|=FEEDBACK;c.ax_options|=STICKY_FEEDBACK;p=AccessPreferences.from_controls(c)
        after,mask=patch_controls(c,replace(p,sticky_feedback=False),p)
        self.assertFalse(after.ax_options&STICKY_FEEDBACK);self.assertTrue(after.ax_options&0x800);self.assertTrue(after.enabled_ctrls&FEEDBACK)
    def test_timeout_preserves_other_clients_policy_and_shortcuts(self):
        c=controls();p=AccessPreferences.from_controls(c);after,mask=patch_controls(c,replace(p,automatic_reset=True,reset_seconds=600),p)
        self.assertTrue(after.enabled_ctrls&TIMEOUT,MOUSE_ACCEL);self.assertEqual(after.ax_timeout,600);self.assertTrue(after.axt_ctrls_mask&1024);self.assertTrue(after.axt_ctrls_values&1024)
        self.assertFalse(after.axt_ctrls_mask&ACCESS_KEYS);self.assertFalse(after.axt_ctrls_values&(STICKY|MOUSE|SLOW|BOUNCE))
    def test_mouse_timing_preserves_keyboard_repeat_and_unrelated_bits(self):
        c=controls();p=AccessPreferences.from_controls(c);after,mask=patch_controls(c,replace(p,mouse=True,mouse_delay_ms=200,mouse_interval_ms=20,mouse_curve=-500),p)
        self.assertTrue(after.enabled_ctrls&MOUSE);self.assertEqual(after.mk_delay,200);self.assertEqual(after.mk_interval,20);self.assertEqual(after.mk_curve,-500);self.assertEqual(after.repeat_delay,c.repeat_delay);self.assertTrue(mask&MOUSE_ACCEL)
    def test_apply_verifies_server_readback(self):
        b=FakeXKB();before=b.preferences();pending=replace(before,sticky=True);b.apply(pending,before);self.assertEqual(b.preferences(),pending);self.assertEqual(len(b.writes),1)
    def test_server_rejection_restores_exact_snapshot(self):
        b=FakeXKB();before=b.snapshot();b.reject=True
        with self.assertRaisesRegex(AccessibilityError,'was restored'):b.apply(replace(b.preferences(),sticky=True),b.preferences())
        self.assertEqual(b.snapshot(),before);self.assertEqual(len(b.writes),2)
    def test_write_failure_restores_and_rollback_failure_is_honest(self):
        b=FakeXKB();before=b.snapshot();b.fail=True
        with self.assertRaisesRegex(AccessibilityError,'was restored'):b.apply(replace(b.preferences(),sticky=True))
        self.assertEqual(b.snapshot(),before)
        b=FakeXKB();b.fail=True;b.fail_rollback=True
        with self.assertRaisesRegex(AccessibilityError,'could not be fully restored'):b.apply(replace(b.preferences(),sticky=True))
    def test_external_change_aborts_before_write(self):
        b=FakeXKB();baseline=b.preferences();c=_Controls.from_buffer_copy(b.current);c.enabled_ctrls|=STICKY;b.current=bytes(c)
        with self.assertRaisesRegex(AccessibilityError,'changed while'):b.apply(replace(baseline,mouse=True),baseline)
        self.assertEqual(b.writes,[])
    def test_other_applet_repeat_change_is_preserved_without_false_conflict(self):
        backend=FakeXKB();baseline=backend.preferences();current=_Controls.from_buffer_copy(backend.snapshot());current.repeat_delay=900;current.repeat_interval=50;current.enabled_ctrls|=2048;backend.current=bytes(current)
        backend.apply(replace(baseline,sticky=True),baseline);after=_Controls.from_buffer_copy(backend.snapshot());self.assertEqual(after.repeat_delay,900);self.assertEqual(after.repeat_interval,50);self.assertTrue(after.enabled_ctrls&2048)
    def test_guest_guard_rejects_even_a_noop_before_mutation(self):
        b=FakeXKB();p=b.preferences();b.guard=lambda:False
        with self.assertRaisesRegex(AccessibilityError,'installed Win95LX'):b.apply(p,p)
        self.assertEqual(b.writes,[])
    def test_native_write_bounds_are_checked_before_opening_a_display(self):
        backend=object.__new__(XKBAccess);backend.guard=lambda:True
        for data,mask in ((b'',ENABLED),(b'x'*83,ENABLED),(b'x'*85,ENABLED),('x'*84,ENABLED),(bytes(84),-1),(bytes(84),1<<26)):
            with self.assertRaises(AccessibilityError):backend._write(data,mask)
    def test_startup_fixture_guard_rejects_other_displays_and_non_xvfb_processes(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dev'))
        from check_accessibility import owned_display_guard
        with patch.dict(os.environ,{'DISPLAY':':987','GDK_BACKEND':'x11'},clear=True):
            self.assertFalse(owned_display_guard(':0',os.getpid()));self.assertFalse(owned_display_guard(':987',None));self.assertFalse(owned_display_guard(':987',os.getpid()))
            os.environ['WAYLAND_DISPLAY']='wayland-test';self.assertFalse(owned_display_guard(':987',os.getpid()))
    def test_missing_x11_and_wayland_are_explicit_unavailable(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(AccessibilityError,'X11'):XKBAccess()
        with patch.dict(os.environ,{'DISPLAY':':999','WAYLAND_DISPLAY':'wayland-test','GDK_BACKEND':'x11'},clear=True):
            with self.assertRaisesRegex(AccessibilityError,'Wayland'):XKBAccess()



class AccessPersistenceTests(unittest.TestCase):
    def test_apply_persists_actual_changes_and_reopen_reads_live_state(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'access.json';backend=FakeXKB();controller=AccessController(path,backend);controller.pending=replace(controller.pending,sticky=True);controller.apply()
            self.assertTrue(json.loads(path.read_text())['sticky']);self.assertTrue(AccessController(path,backend).applied.sticky)
    def test_cancel_has_no_write_or_persistence(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'access.json';backend=FakeXKB();controller=AccessController(path,backend);controller.pending=replace(controller.pending,sticky=True);controller.cancel()
            self.assertEqual(controller.pending,controller.applied);self.assertFalse(path.exists());self.assertEqual(backend.writes,[])
    def test_save_failure_restores_settings_without_exposing_local_path(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            backend=FakeXKB();before=backend.snapshot();controller=AccessController(Path(directory)/'access.json',backend);controller.pending=replace(controller.pending,sticky=True)
            with patch('win95lx.control_panel.preferences.save_preferences',side_effect=OSError('Sensitive /home/user/path')):
                with self.assertRaisesRegex(AccessibilityError,'could not be saved') as error:controller.apply()
            self.assertNotIn('/home/',str(error.exception));self.assertEqual(backend.snapshot(),before);self.assertFalse(controller.applied.sticky)
    def test_stale_saved_file_does_not_override_live_state_on_open(self):
        import tempfile,json
        from dataclasses import asdict
        with tempfile.TemporaryDirectory() as directory:
            backend=FakeXKB();path=Path(directory)/'access.json';path.write_text(json.dumps(asdict(replace(backend.preferences(),sticky=True))))
            controller=AccessController(path,backend);self.assertFalse(controller.applied.sticky);self.assertEqual(backend.writes,[])
            apply_saved_session(path,backend);self.assertTrue(backend.preferences().sticky)
    def test_damaged_or_invalid_saved_profile_never_mutates_session(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'access.json';backend=FakeXKB()
            for text in ('{bad','{"sticky": 1}','{"unknown": true}'):
                path.write_text(text)
                with self.assertRaises((ValueError,TypeError)):apply_saved_session(path,backend)
                self.assertEqual(backend.writes,[])
    def test_backend_failure_does_not_run_a_second_outer_rollback(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            backend=FakeXKB();backend.fail=True;controller=AccessController(Path(directory)/'access.json',backend);controller.pending=replace(controller.pending,sticky=True)
            with self.assertRaises(AccessibilityError):controller.apply()
            self.assertEqual(len(backend.writes),2)


def run_xkb_input_probe():
    import ctypes as C,ctypes.util,time,json,os
    from dataclasses import replace
    from win95lx.control_panel.access_preferences import XKBAccess,ALL_CONTROLS
    class Key(C.Structure):
     _fields_=[('type',C.c_int),('serial',C.c_ulong),('send_event',C.c_int),('display',C.c_void_p),('window',C.c_ulong),('root',C.c_ulong),('subwindow',C.c_ulong),('time',C.c_ulong),('x',C.c_int),('y',C.c_int),('x_root',C.c_int),('y_root',C.c_int),('state',C.c_uint),('keycode',C.c_uint),('same_screen',C.c_int)]
    class Event(C.Union):_fields_=[('key',Key),('pad',C.c_long*24)]
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'dev'))
    from check_accessibility import owned_display_guard
    owned=os.environ.get('WIN95LX_OWNED_XVFB_DISPLAY');pid=int(os.environ.get('WIN95LX_OWNED_XVFB_PID','0'))
    if not owned_display_guard(owned,pid):raise RuntimeError('The input probe requires its parent-owned Xvfb display.')
    b=XKBAccess(display=owned,guard=lambda:owned_display_guard(owned,pid));x=b.lib
    specs={'XDefaultRootWindow':([C.c_void_p],C.c_ulong),'XCreateSimpleWindow':([C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_uint,C.c_ulong,C.c_ulong],C.c_ulong),'XSelectInput':([C.c_void_p,C.c_ulong,C.c_long],C.c_int),'XMapWindow':([C.c_void_p,C.c_ulong],C.c_int),'XSetInputFocus':([C.c_void_p,C.c_ulong,C.c_int,C.c_ulong],C.c_int),'XPending':([C.c_void_p],C.c_int),'XNextEvent':([C.c_void_p,C.POINTER(Event)],C.c_int),'XStringToKeysym':([C.c_char_p],C.c_ulong),'XKeysymToKeycode':([C.c_void_p,C.c_ulong],C.c_ubyte),'XQueryPointer':([C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),*[C.POINTER(C.c_int)]*4,C.POINTER(C.c_uint)],C.c_int)}
    for name,(args,result) in specs.items():f=getattr(x,name);f.argtypes=args;f.restype=result
    xt=C.CDLL(ctypes.util.find_library('Xtst'));xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong];xt.XTestFakeKeyEvent.restype=C.c_int
    d=x.XOpenDisplay(os.environ['DISPLAY'].encode());root=x.XDefaultRootWindow(d);win=x.XCreateSimpleWindow(d,root,0,0,200,100,0,0,0);x.XSelectInput(d,win,3);x.XMapWindow(d,win);x.XSetInputFocus(d,win,2,0);x.XSync(d,0)
    raw=b.snapshot();base=b.preferences();checks=[]
    def code(name):return x.XKeysymToKeycode(d,x.XStringToKeysym(name.encode()))
    def key(name,down):assert xt.XTestFakeKeyEvent(d,code(name),down,0);x.XSync(d,0)
    def tap(name):key(name,1);key(name,0)
    def events():
     time.sleep(.03);x.XSync(d,0);result=[]
     while x.XPending(d):
      e=Event();x.XNextEvent(d,C.byref(e))
      if e.key.type==2:result.append((e.key.keycode,e.key.state))
     return result
    def setp(**values):b.apply(replace(b.preferences(),**values),b.preferences());events()
    def pointer():
     rr=C.c_ulong();child=C.c_ulong();rx=C.c_int();ry=C.c_int();wx=C.c_int();wy=C.c_int();mask=C.c_uint();assert x.XQueryPointer(d,root,C.byref(rr),C.byref(child),C.byref(rx),C.byref(ry),C.byref(wx),C.byref(wy),C.byref(mask));return rx.value,ry.value
    try:
     setp(sticky=True,sticky_lock=False,slow=False,bounce=False,mouse=False,keyboard_shortcuts=False,automatic_reset=False)
     tap('Shift_L');tap('a');tap('b');e=events();print('sticky events',e,flush=True);assert next(state for k,state in e if k==code('a'))&1;assert not next(state for k,state in e if k==code('b'))&1;checks.append('StickyKeys modifier latch applies to one following key')
     setp(sticky=False);setp(sticky=True,sticky_lock=True,two_keys_disable=True)
     tap('Shift_L');tap('Shift_L');tap('a');tap('b');locked=events();assert next(state for k,state in locked if k==code('a'))&1;assert next(state for k,state in locked if k==code('b'))&1;tap('Shift_L');tap('c');assert not next(state for k,state in events() if k==code('c'))&1;checks.append('StickyKeys double modifier locks across keys and another press unlocks')
     key('Shift_L',1);key('Control_L',1);key('Control_L',0);key('Shift_L',0);events();assert not b.preferences().sticky;checks.append('Two simultaneous modifiers actually disable StickyKeys')
     setp(sticky=False,slow=True,slow_ms=200)
     tap('c');e=events();assert not any(k==code('c') for k,s in e);key('c',1);time.sleep(.27);key('c',0);e=events();print('slow events',e,flush=True);assert any(k==code('c') for k,s in e);checks.append('SlowKeys rejects brief press and accepts held key')
     setp(slow=False,bounce=True,bounce_ms=250)
     tap('d');tap('d');e=events();print('bounce events',e,flush=True);assert sum(k==code('d') for k,s in e)==1;time.sleep(.28);tap('d');assert any(k==code('d') for k,s in events());checks.append('BounceKeys rejects rapid repeat and accepts after delay')
     setp(bounce=False,mouse=True,mouse_delay_ms=50,mouse_interval_ms=20,mouse_acceleration=True)
     before=pointer();key('KP_6',1);time.sleep(.3);key('KP_6',0);after=pointer();print('mouse',before,after,flush=True);assert after[0]>before[0];checks.append('MouseKeys moves actual isolated pointer using keypad')
     setp(mouse=False,sticky=True,automatic_reset=True,reset_seconds=2);tap('e');events();time.sleep(3.2);print('timeout',b.preferences().sticky,flush=True);assert not b.preferences().sticky;checks.append('AccessX timeout disables StickyKeys after idle')
     print(json.dumps({'checks':checks,'display':os.environ['DISPLAY'],'actual_xkb_effects':True},indent=2))
    finally:
     for name in ('Shift_L','Control_L','a','b','c','d','KP_6'):key(name,0)
     b._write(raw,ALL_CONTROLS);assert b.snapshot()==raw;x.XCloseDisplay(d)


class IsolatedXKBInputTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('WIN95LX_XKB_UAT')=='1','Opt-in isolated Xvfb input regression')
    def test_real_accessx_controls_filter_input_move_pointer_and_timeout(self):
        import json,select,shutil,subprocess,tempfile
        executable=shutil.which('Xvfb')
        if not executable:self.skipTest('Xvfb is unavailable')
        readfd,writefd=os.pipe();server=None
        try:
            server=subprocess.Popen([executable,'-displayfd',str(writefd),'-screen','0','800x600x24','-nolisten','tcp','-noreset'],pass_fds=(writefd,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            os.close(writefd);writefd=None
            if not select.select([readfd],[],[],5)[0]:self.fail('Owned isolated Xvfb did not become ready')
            number=os.read(readfd,32).decode().strip();self.assertTrue(number.isdigit())
            env={key:value for key,value in os.environ.items() if key!='WAYLAND_DISPLAY'};env.update(DISPLAY=':'+number,WIN95LX_OWNED_XVFB_DISPLAY=':'+number,WIN95LX_OWNED_XVFB_PID=str(server.pid),GDK_BACKEND='x11',PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--xkb-input-child'],env=env,capture_output=True,text=True,timeout=20)
            evidence=os.environ.get('WIN95LX_ACCESS_EVIDENCE')
            if evidence:
                directory=Path(evidence);directory.mkdir(parents=True,exist_ok=True);(directory/'actual-input.log').write_text(result.stdout+'\n'+result.stderr)
            self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)
            self.assertIn('"actual_xkb_effects": true',result.stdout)
        finally:
            os.close(readfd)
            if writefd is not None:os.close(writefd)
            if server:
                server.terminate()
                try:server.communicate(timeout=3)
                except subprocess.TimeoutExpired:server.kill();server.communicate()

if __name__=='__main__':
    if sys.argv[1:]==['--xkb-input-child']:run_xkb_input_probe()
    else:unittest.main()
