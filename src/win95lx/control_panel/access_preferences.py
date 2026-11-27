"""Session XKB AccessX controls, independently testable before applet integration.

No global config writes or elevated permissions. Xwayland is not claimed to
configure the compositor's physical keyboard. UI and persistence are separate.
"""
from dataclasses import dataclass,fields
import ctypes as C,ctypes.util,os

REPEAT=1;SLOW=2;BOUNCE=4;STICKY=8;MOUSE=16;MOUSE_ACCEL=32;ACCESS_KEYS=64;TIMEOUT=128;FEEDBACK=256
ENABLED=1<<31;ALL_CONTROLS=0xF8001FFF;CONTROL_COMPONENT=64;CORE_KEYBOARD=256
TWO_KEYS=64;LATCH_LOCK=128;STICKY_FEEDBACK=32;INDICATOR_FEEDBACK=16;FEATURE_FEEDBACK=4
OWN_BOOLEAN=SLOW|BOUNCE|STICKY|MOUSE|MOUSE_ACCEL|ACCESS_KEYS|TIMEOUT
OWN_OPTIONS=TWO_KEYS|LATCH_LOCK|STICKY_FEEDBACK|INDICATOR_FEEDBACK|FEATURE_FEEDBACK

class AccessibilityError(RuntimeError):pass

class _Mods(C.Structure):_fields_=[('mask',C.c_ubyte),('real_mods',C.c_ubyte),('vmods',C.c_ushort)]
class _Controls(C.Structure):
    _fields_=[('mk_dflt_btn',C.c_ubyte),('num_groups',C.c_ubyte),('groups_wrap',C.c_ubyte),('internal',_Mods),('ignore_lock',_Mods),('enabled_ctrls',C.c_uint),
        *[(name,C.c_ushort) for name in ('repeat_delay','repeat_interval','slow_keys_delay','debounce_delay','mk_delay','mk_interval','mk_time_to_max','mk_max_speed')],
        ('mk_curve',C.c_short),*[(name,C.c_ushort) for name in ('ax_options','ax_timeout','axt_opts_mask','axt_opts_values')],('axt_ctrls_mask',C.c_uint),('axt_ctrls_values',C.c_uint),('per_key_repeat',C.c_ubyte*32)]
class _Description(C.Structure):
    _fields_=[('dpy',C.c_void_p),('flags',C.c_ushort),('device_spec',C.c_ushort),('min_key_code',C.c_ubyte),('max_key_code',C.c_ubyte),('ctrls',C.POINTER(_Controls)),
        *[(name,C.c_void_p) for name in ('server','map','indicators','names','compat','geom')]]

@dataclass(frozen=True)
class AccessPreferences:
    sticky:bool=False
    sticky_lock:bool=True
    two_keys_disable:bool=True
    sticky_feedback:bool=False
    slow:bool=False
    slow_ms:int=300
    bounce:bool=False
    bounce_ms:int=300
    toggle_feedback:bool=False
    feature_feedback:bool=False
    keyboard_shortcuts:bool=False
    mouse:bool=False
    mouse_acceleration:bool=True
    mouse_delay_ms:int=160
    mouse_interval_ms:int=40
    mouse_time_to_max:int=30
    mouse_max_speed:int=30
    mouse_curve:int=0
    automatic_reset:bool=False
    reset_seconds:int=300
    def validate(self):
        for field in fields(self):
            value=getattr(self,field.name)
            if field.type is bool and type(value) is not bool:raise ValueError('Invalid accessibility option: '+field.name)
        for name,low,high in (('slow_ms',1,65535),('bounce_ms',1,65535),('mouse_delay_ms',1,65535),('mouse_interval_ms',1,65535),('mouse_time_to_max',1,65535),('mouse_max_speed',1,65535),('mouse_curve',-1000,1000),('reset_seconds',1,65535)):
            if type(getattr(self,name)) is not int or not low<=getattr(self,name)<=high:raise ValueError('Invalid accessibility timing: '+name)
        return self
    @classmethod
    def from_controls(cls,c):
        flags=c.enabled_ctrls;options=c.ax_options
        # Some disabled controls have zero server defaults. Keep the saved raw
        # state untouched; present valid edit defaults for enabling them later.
        return cls(sticky=bool(flags&STICKY),sticky_lock=bool(options&LATCH_LOCK),two_keys_disable=bool(options&TWO_KEYS),sticky_feedback=bool(flags&FEEDBACK and options&STICKY_FEEDBACK),
            slow=bool(flags&SLOW),slow_ms=c.slow_keys_delay or 300,bounce=bool(flags&BOUNCE),bounce_ms=c.debounce_delay or 300,
            toggle_feedback=bool(flags&FEEDBACK and options&INDICATOR_FEEDBACK),feature_feedback=bool(flags&FEEDBACK and options&FEATURE_FEEDBACK),keyboard_shortcuts=bool(flags&ACCESS_KEYS),
            mouse=bool(flags&MOUSE),mouse_acceleration=bool(flags&MOUSE_ACCEL),mouse_delay_ms=c.mk_delay or 160,mouse_interval_ms=c.mk_interval or 40,mouse_time_to_max=c.mk_time_to_max or 30,mouse_max_speed=c.mk_max_speed or 30,mouse_curve=c.mk_curve,
            automatic_reset=bool(flags&TIMEOUT),reset_seconds=c.ax_timeout or 300).validate()

BOOL_FIELDS={'sticky':STICKY,'slow':SLOW,'bounce':BOUNCE,'mouse':MOUSE,'mouse_acceleration':MOUSE_ACCEL,'keyboard_shortcuts':ACCESS_KEYS,'automatic_reset':TIMEOUT}
OPTION_FIELDS={'sticky_lock':LATCH_LOCK,'two_keys_disable':TWO_KEYS,'sticky_feedback':STICKY_FEEDBACK,'toggle_feedback':INDICATOR_FEEDBACK,'feature_feedback':FEATURE_FEEDBACK}
VALUE_FIELDS={'slow_ms':('slow_keys_delay',SLOW),'bounce_ms':('debounce_delay',BOUNCE),'mouse_delay_ms':('mk_delay',MOUSE_ACCEL),'mouse_interval_ms':('mk_interval',MOUSE_ACCEL),'mouse_time_to_max':('mk_time_to_max',MOUSE_ACCEL),'mouse_max_speed':('mk_max_speed',MOUSE_ACCEL),'mouse_curve':('mk_curve',MOUSE_ACCEL),'reset_seconds':('ax_timeout',TIMEOUT)}

def patch_controls(current,pending,baseline):
    """Return a merged copy and protocol mask, preserving every unrelated bit."""
    pending.validate();baseline.validate();result=_Controls.from_buffer_copy(bytes(current));mask=0
    for name,bit in BOOL_FIELDS.items():
        if getattr(pending,name)!=getattr(baseline,name):
            result.enabled_ctrls=(result.enabled_ctrls|bit) if getattr(pending,name) else (result.enabled_ctrls&~bit);mask|=ENABLED|bit
    for name,bit in OPTION_FIELDS.items():
        if getattr(pending,name)!=getattr(baseline,name):
            result.ax_options=(result.ax_options|bit) if getattr(pending,name) else (result.ax_options&~bit);mask|=STICKY|FEEDBACK
    feedback_fields=('sticky_feedback','toggle_feedback','feature_feedback')
    if any(getattr(pending,name)!=getattr(baseline,name) for name in feedback_fields):
        # Existing other AccessX feedback options must continue working.
        for name in feedback_fields:
            bit=OPTION_FIELDS[name];result.ax_options=(result.ax_options|bit) if getattr(pending,name) else (result.ax_options&~bit)
        needs_feedback=result.ax_options&0xF3F
        result.enabled_ctrls=(result.enabled_ctrls|FEEDBACK) if needs_feedback else (result.enabled_ctrls&~FEEDBACK);mask|=ENABLED|FEEDBACK
    for name,(target,bit) in VALUE_FIELDS.items():
        newly_enabled=any(bit==control and getattr(pending,flag) and not getattr(baseline,flag) for flag,control in BOOL_FIELDS.items())
        if getattr(pending,name)!=getattr(baseline,name) or newly_enabled and getattr(result,target)==0:
            setattr(result,target,getattr(pending,name));mask|=bit
    # Reset only this applet's enabled controls. Leave repeat keys, overlays,
    # group locks, and other clients' timeout policy outside the owned mask.
    if pending.automatic_reset and (not baseline.automatic_reset or pending.reset_seconds!=baseline.reset_seconds):
        result.axt_ctrls_mask|=STICKY|SLOW|BOUNCE|MOUSE;result.axt_ctrls_values&=~(STICKY|SLOW|BOUNCE|MOUSE);mask|=TIMEOUT
    return result,mask

class XKBAccess:
    def __init__(self,display=None,guard=None):
        self.display_name=display or os.environ.get('DISPLAY','');self.guard=guard
        if not self.display_name:raise AccessibilityError('An X11 keyboard session is required.')
        if os.environ.get('WAYLAND_DISPLAY'):raise AccessibilityError('Physical keyboard accessibility on Wayland requires compositor integration; Xwayland controls cannot configure it.')
        name=ctypes.util.find_library('X11')
        if not name:raise AccessibilityError('The X11 keyboard library is unavailable.')
        self.lib=C.CDLL(name)
        specs={'XOpenDisplay':([C.c_char_p],C.c_void_p),'XCloseDisplay':([C.c_void_p],C.c_int),'XSync':([C.c_void_p,C.c_int],C.c_int),
            'XkbAllocKeyboard':([],C.POINTER(_Description)),'XkbGetControls':([C.c_void_p,C.c_ulong,C.POINTER(_Description)],C.c_int),
            'XkbQueryExtension':([C.c_void_p,*([C.POINTER(C.c_int)]*5)],C.c_int),'XkbGetKeyboard':([C.c_void_p,C.c_uint,C.c_uint],C.POINTER(_Description)),
            'XkbSetControls':([C.c_void_p,C.c_ulong,C.POINTER(_Description)],C.c_int),'XkbFreeKeyboard':([C.POINTER(_Description),C.c_uint,C.c_int],None)}
        for key,(args,result) in specs.items():fn=getattr(self.lib,key);fn.argtypes=args;fn.restype=result
    def _open(self):
        display=self.lib.XOpenDisplay(self.display_name.encode())
        if not display:raise AccessibilityError('The X11 keyboard session could not be opened.')
        values=[C.c_int() for _ in range(3)]+[C.c_int(1),C.c_int(0)]
        if not self.lib.XkbQueryExtension(display,*[C.byref(v) for v in values]):self.lib.XCloseDisplay(display);raise AccessibilityError('This X11 server does not provide keyboard accessibility controls.')
        return display
    def snapshot(self):
        display=self._open();desc=None
        try:
            desc=self.lib.XkbAllocKeyboard()
            if not desc:raise AccessibilityError('Keyboard description could not be allocated.')
            desc.contents.dpy=display;desc.contents.device_spec=CORE_KEYBOARD
            status=self.lib.XkbGetControls(display,ALL_CONTROLS,desc)
            if status or not desc.contents.ctrls:raise AccessibilityError('Keyboard accessibility settings could not be read.')
            return bytes(desc.contents.ctrls.contents)
        finally:
            if desc:self.lib.XkbFreeKeyboard(desc,0x7f,1)
            self.lib.XCloseDisplay(display)
    def preferences(self):return AccessPreferences.from_controls(_Controls.from_buffer_copy(self.snapshot()))
    def _allowed(self):
        if self.guard is None:
            from win95lx.guest_identity import is_development_guest
            allowed=is_development_guest()
        else:allowed=self.guard()
        if not allowed:raise AccessibilityError('Accessibility changes are available in the installed Win95LX session.')
    def _write(self,data,mask):
        self._allowed()
        if not isinstance(data,(bytes,bytearray)) or len(data)!=C.sizeof(_Controls):raise AccessibilityError('The keyboard-control snapshot is damaged.')
        if type(mask) is not int or mask<=0 or mask&~ALL_CONTROLS:raise AccessibilityError('The keyboard-control selection is invalid.')
        data=bytes(data);display=self._open();desc=None
        try:
            desc=self.lib.XkbAllocKeyboard()
            if not desc:raise AccessibilityError('Keyboard description could not be allocated.')
            desc.contents.dpy=display;desc.contents.device_spec=CORE_KEYBOARD
            status=self.lib.XkbGetControls(display,ALL_CONTROLS,desc)
            if status or not desc.contents.ctrls:raise AccessibilityError('Keyboard accessibility settings could not be read.')
            C.memmove(desc.contents.ctrls,data,C.sizeof(_Controls))
            if not self.lib.XkbSetControls(display,mask,desc):raise AccessibilityError('The X11 keyboard settings could not be applied.')
            self.lib.XSync(display,0)
        finally:
            if desc:self.lib.XkbFreeKeyboard(desc,0x7f,1)
            self.lib.XCloseDisplay(display)
    def apply(self,pending,baseline=None):
        self._allowed();pending.validate();before=self.snapshot();current=_Controls.from_buffer_copy(before);actual=AccessPreferences.from_controls(current);baseline=baseline or actual
        if actual!=baseline:raise AccessibilityError('Keyboard accessibility changed while this window was open. Reopen it before applying changes.')
        merged,mask=patch_controls(current,pending,baseline);self.last_mask=mask
        if not mask:return
        try:
            self._write(bytes(merged),mask)
            if self.preferences()!=pending:raise AccessibilityError('The X11 server did not retain the requested accessibility settings.')
        except Exception as error:
            try:
                self._write(before,mask)
                if self.snapshot()!=before:raise AccessibilityError('Restored keyboard state does not match the original snapshot.')
            except Exception as rollback:raise AccessibilityError('The accessibility change failed and the previous keyboard state could not be fully restored.') from rollback
            raise AccessibilityError('The accessibility change failed. The previous keyboard state was restored.') from error

    def restore(self,before):
        """Restore only fields touched by this backend's preceding transaction."""
        self._allowed();mask=getattr(self,'last_mask',0)
        if mask:self._write(before,mask)
        expected=AccessPreferences.from_controls(_Controls.from_buffer_copy(before))
        if self.preferences()!=expected:raise AccessibilityError('The previous accessibility settings could not be verified after restoration.')

class AccessController:
    """Read live session state; persist successful Apply for later login reuse."""
    def __init__(self,path,backend):self.path=path;self.backend=backend;self.applied=self.pending=backend.preferences()
    def cancel(self):self.pending=self.applied
    def apply(self):
        from win95lx.control_panel.preferences import save_preferences
        self.pending.validate();before=self.backend.snapshot();activated=False
        try:
            self.backend.apply(self.pending,self.applied);activated=True
            save_preferences(self.pending,self.path)
        except Exception as error:
            if not activated:raise
            try:self.backend.restore(before)
            except Exception as rollback:raise AccessibilityError('The accessibility changes could not be saved or fully restored. Reopen Accessibility to check the current settings.') from rollback
            if isinstance(error,OSError):raise AccessibilityError('The settings could not be saved. The previous accessibility settings have been restored.') from error
            raise error
        self.applied=self.pending

def apply_saved_session(path,backend):
    """Explicit login integration hook; merely opening the applet never calls it."""
    import json
    value=AccessPreferences(**json.loads(path.read_text())).validate();backend.apply(value,backend.preferences());return value
