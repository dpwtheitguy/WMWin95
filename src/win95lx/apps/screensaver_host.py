"""Asynchronous saver ownership for Display Properties and the desktop session.

Wine preparation, child waiting and bounded cleanup never execute on GTK's thread.
"""
from dataclasses import replace
from pathlib import Path
import ctypes
import json
import os
import subprocess
import threading
import time
from win95lx.control_panel.screensaver_preferences import ScreenSaverPreferences,ScreenSaverIdle


class SaverTasks:
    """Serialized owned runtime work; stale preparation cannot launch a child."""
    def __init__(self,runtime,dispatch=lambda callback:callback(),changed=lambda *_:None):
        self.runtime=runtime;self.dispatch=dispatch;self.changed=changed
        self.lock=threading.Lock();self.generation=0;self.closed=False;self.busy=False
    def _notify(self,status,error=None):
        generation=self.generation
        def deliver():
            if self.closed or generation!=self.generation:return
            if status in ('Ready.','The screen saver could not be started.'):self.busy=False
            self.changed(status,error)
        self.dispatch(deliver)
    def submit(self,identity,mode=None):
        self.generation+=1;generation=self.generation;self.busy=True
        self._notify('Preparing screen saver...')
        def work():
            error=None
            try:
                with self.lock:
                    if self.closed or generation!=self.generation:return
                    self.runtime.stop()
                    self.runtime.prepare(identity)
                    if self.closed or generation!=self.generation:return
                    if mode is not None:
                        process=self.runtime.launch(identity,mode=mode)
                        self._notify('Screen saver running.' if mode=='fullscreen' else 'Screen saver settings are open.')
                if mode is not None:
                    code=process.wait()
                    if generation==self.generation:
                        self.runtime.stop()
                        if code not in (0,18):raise RuntimeError('The screen saver closed unexpectedly.')
            except Exception as problem:error=problem
            finally:
                if generation==self.generation:
                    self._notify('Ready.' if error is None else 'The screen saver could not be started.',error)
        thread=threading.Thread(target=work,name='win95lx-saver-worker',daemon=True);thread.start();return thread
    def stop(self,close=False):
        self.generation+=1;generation=self.generation;self.busy=not close
        if close:self.closed=True
        def work():
            with self.lock:
                if not close and generation!=self.generation:return
                self.runtime.close() if close else self.runtime.stop()
            if not close and generation==self.generation:self._notify('Ready.')
        thread=threading.Thread(target=work,name='win95lx-saver-stop',daemon=True);thread.start();return thread


class X11Idle:
    """Measured server idle; no heuristic based on this app's event delivery."""
    class Info(ctypes.Structure):
        _fields_=[('window',ctypes.c_ulong),('state',ctypes.c_int),('kind',ctypes.c_int),('since',ctypes.c_ulong),('idle',ctypes.c_ulong),('mask',ctypes.c_ulong)]
    def __init__(self):
        self.x11=ctypes.CDLL('libX11.so.6');self.xss=ctypes.CDLL('libXss.so.1')
        self.x11.XOpenDisplay.argtypes=[ctypes.c_char_p];self.x11.XOpenDisplay.restype=ctypes.c_void_p
        self.x11.XDefaultRootWindow.argtypes=[ctypes.c_void_p];self.x11.XDefaultRootWindow.restype=ctypes.c_ulong
        self.x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
        self.xss.XScreenSaverQueryInfo.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(self.Info)];self.xss.XScreenSaverQueryInfo.restype=ctypes.c_int
        self.display=self.x11.XOpenDisplay(os.environ.get('DISPLAY','').encode())
        if not self.display:raise RuntimeError('Screen saver idle detection requires an X11 session.')
        self.root=self.x11.XDefaultRootWindow(self.display)
    def seconds(self):
        info=self.Info()
        if not self.xss.XScreenSaverQueryInfo(self.display,self.root,ctypes.byref(info)):raise RuntimeError('Screen saver idle detection is unavailable.')
        return info.idle/1000
    def close(self):
        if self.display:self.x11.XCloseDisplay(self.display);self.display=None


class ScreenSaverHost:
    def __init__(self,shell):
        from gi.repository import GLib
        from win95lx.apps.screensaver_ownership import SaverOwnership
        from win95lx.control_panel.screensaver_runtime import ScreenSaverCatalog,WineScreenSaverRuntime
        self.shell=shell;self.path=Path.home()/'.config/win95lx/screensaver.json'
        self.applied=ScreenSaverPreferences();self.pending=self.applied;self.error='';self.status='';self.focus='selection';self.popup=None;self.closed=False;self.wait_digits='';self.wait_key_time=0;self.capabilities={};self.return_focus=False;self.session_mode=None;self.idle_dismissing=False;self.listeners=[];self.return_focus_owner=shell
        self.catalog=None;self.runtime=None;self.tasks=None;self.idle=None;self.idle_source=None;self.scheduler_lock=threading.Lock();self.scheduler_inflight=False;self.owner_conflict=None;self.ownership=SaverOwnership();self.apply_generation=0;self.request_generation=0;self.request_waiting=False
        try:
            if self.path.exists():self.applied=ScreenSaverPreferences(**json.loads(self.path.read_text())).validate();self.pending=self.applied
            self.catalog=ScreenSaverCatalog.load(shell.assets/'screensavers/catalog.json')
            state=Path.home()/'.local/share/win95lx/screensavers'
            self.runtime=WineScreenSaverRuntime(self.catalog,state)
            self.tasks=SaverTasks(self.runtime,lambda callback:GLib.idle_add(lambda:(callback(),False)[1]),self.changed)
            self.idle_runtime=WineScreenSaverRuntime(self.catalog,state)
            self.idle=ScreenSaverIdle(self.idle_runtime,self.applied,lambda error:self._background_error(error))
            self.idle_source=GLib.timeout_add(1000,self.tick)
        except (OSError,ValueError,RuntimeError) as error:self.error='The screen saver library is unavailable.'
        rows=sorted(self.catalog.presentations.items(),key=lambda item:item[1]['label'].casefold()) if self.catalog else[]
        self.ids=('',*(identity for identity,row in rows));self.names=('(None)',*(row['label'] for identity,row in rows))
        if self.pending.saver and self.pending.saver not in self.ids:self.error='The selected screen saver is no longer installed.'
        shell.connect('destroy',lambda *_:self.close())
        def probe_owner():
            with self.scheduler_lock:state=self.ownership.refresh()
            self.owner_conflict=not state.ready
            if state.error:
                self.status=state.error
                GLib.idle_add(lambda:(self.shell.area.queue_draw(),False)[1])
        threading.Thread(target=probe_owner,name='win95lx-saver-owner',daemon=True).start()
        if self.applied.saver in self.ids and self.applied.saver and self.tasks:self.warm(self.applied.saver)
    @property
    def busy(self):return bool(self.request_waiting or self.tasks and self.tasks.busy)
    @property
    def dirty(self):return self.pending!=self.applied
    def changed(self,status,error=None):
        self.status='' if status=='Ready.' else status
        if error is not None:self.error='The screen saver could not be started. Check that the compatibility components are installed.'
        if status in ('Ready.','The screen saver could not be started.')and not self.request_waiting:self.session_mode=None
        if status=='Ready.' and self.return_focus:
            self.return_focus=False;self.restore_focus()
        self.shell.area.queue_draw()
        for callback in tuple(self.listeners):callback()
    def subscribe(self,callback):
        self.listeners.append(callback);return callback
    def unsubscribe(self,callback):
        if callback in self.listeners:self.listeners.remove(callback)
    def restore_focus(self):
        # A destroyed Wine child leaves PointerRoot focus without a window
        # manager. Restore our owner, but never steal focus from another app.
        try:
            x=ctypes.CDLL('libX11.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
            x.XGetInputFocus.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_int)];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
            x.XDefaultRootWindow.argtypes=[ctypes.c_void_p];x.XDefaultRootWindow.restype=ctypes.c_ulong
            display=x.XOpenDisplay(os.environ.get('DISPLAY','').encode());focus=ctypes.c_ulong();revert=ctypes.c_int()
            if not display:return
            try:
                root=x.XDefaultRootWindow(display)
                x.XGetInputFocus(display,ctypes.byref(focus),ctypes.byref(revert))
            finally:x.XCloseDisplay(display)
            owner=self.return_focus_owner
            if focus.value in (0,1,root) and owner.get_visible():
                from gi.repository import Gdk
                owner.get_window().focus(Gdk.CURRENT_TIME)
        except (OSError,AttributeError):pass
    def _background_error(self,error):
        from gi.repository import GLib
        GLib.idle_add(lambda:(self.changed('Screen saver unavailable.',error),False)[1])
    def select(self,index):
        self.pending=replace(self.pending,saver=self.ids[index]);self.error='';self.focus='selection'
        self.stop_preview()
        if self.pending.saver:
            available,reason=self.available('fullscreen')
            if available:self.warm(self.pending.saver)
            else:self.error=reason
        self.shell.area.queue_draw()
    def type_wait(self,digit):
        now=time.monotonic()
        if now-self.wait_key_time>1 or len(self.wait_digits)>=2:self.wait_digits=''
        self.wait_digits+=digit;self.wait_key_time=now
        self.set_wait(int(self.wait_digits))
    def set_wait(self,value):
        self.pending=replace(self.pending,wait_minutes=max(1,min(60,value)));self.focus='wait';self.shell.area.queue_draw()
    def available(self,mode,identity=None):
        identity=self.pending.saver if identity is None else identity
        if not identity:return False,'Select a screen saver first.'
        if self.runtime is None:return False,'The screen saver compatibility components are unavailable.'
        key=(identity,mode)
        if key not in self.capabilities:self.capabilities[key]=self.runtime.availability(identity,mode)
        return self.capabilities[key]
    def _submit_owned(self,identity,mode):
        # Grouped Wine prefixes need the idle instance's lease released before
        # preparing another package. Cancel stale queued requests before any IO.
        self.request_generation+=1;generation=self.request_generation;self.request_waiting=True
        def work():
            with self.scheduler_lock:
                if self.closed or generation!=self.request_generation:return
                if self.idle:self.idle.stop()
                if self.closed or generation!=self.request_generation:return
                self.session_mode=mode
                self.tasks.submit(identity,mode)
                if generation==self.request_generation:self.request_waiting=False
        thread=threading.Thread(target=work,name='win95lx-saver-request',daemon=True);thread.start();return thread
    def warm(self,identity):
        if self.tasks:return self._submit_owned(identity,None)
    def launch(self,mode,identity=None,owner=None):
        identity=self.pending.saver if identity is None else identity
        available,reason=self.available(mode,identity)
        if not available:
            self.error=reason;self.shell.area.queue_draw();return
        self.return_focus=True;self.return_focus_owner=owner or self.shell;self.session_mode=mode
        self._submit_owned(identity,mode)
    def stop_preview(self):
        self.request_generation+=1;self.request_waiting=False
        if self.tasks:self.tasks.stop()
    def cancel(self):
        self.pending=self.applied;self.error='';self.stop_preview()
        if self.applied.saver and self.tasks and not self.runtime.ready(self.applied.saver):self.warm(self.applied.saver)
        if self.popup:self.popup.finish(None);self.popup=None
    def daemon_running(self):
        return bool(self.ownership.state.mode)

    def _schedule_preferences(self,value,generation):
        def work():
            with self.scheduler_lock:
                if self.closed or generation!=self.apply_generation:return
                if self.idle:self.idle.configure(value)
        threading.Thread(target=work,name='win95lx-saver-apply',daemon=True).start()

    def restore_theme(self,applied,pending,contents):
        applied.validate();pending.validate()
        if contents is None:self.path.unlink(missing_ok=True)
        else:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_suffix('.tmp');temporary.write_bytes(contents);temporary.replace(self.path)
        self.apply_generation+=1;self.applied,self.pending=applied,pending
        self._schedule_preferences(applied,self.apply_generation)

    def apply(self):
        value=self.pending.validate()
        if not self.ownership.state.ready:raise ValueError(self.ownership.state.error or 'Screen saver settings are still being initialized. Please try again.')
        if value.saver:
            available,reason=self.available('fullscreen')
            if not available:raise ValueError(reason)
            if self.busy and self.session_mode is not None:raise ValueError('Close the screen saver preview or settings before applying these changes.')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps({'saver':value.saver,'wait_minutes':value.wait_minutes})+'\n');temporary.replace(self.path)
        self.apply_generation+=1;self.applied=value
        self._schedule_preferences(value,self.apply_generation)
    def dismiss_idle_input(self):
        if self.idle is None or self.idle.process is None:return False
        if not self.idle_dismissing:
            self.idle_dismissing=True
            def work():
                try:
                    with self.scheduler_lock:self.idle.stop()
                finally:self.idle_dismissing=False
            threading.Thread(target=work,name='win95lx-saver-dismiss',daemon=True).start()
        return True
    def tick(self):
        if self.closed:return False
        if self.scheduler_inflight:return True
        self.scheduler_inflight=True
        def work():
            reader=None
            try:
                with self.scheduler_lock:
                    if self.closed:return
                    owner=self.ownership.refresh();self.owner_conflict=not owner.ready
                    if self.idle and self.applied.saver:
                        inhibited=not owner.ready or owner.active or owner.external_inhibited or self.busy
                        reader=X11Idle()
                        if self.idle.process is not None and self.idle.process.poll() is not None:self.idle.stop()
                        self.idle.tick(reader.seconds(),inhibited=inhibited)
                    if owner.error and self.status!=owner.error:
                        self.status=owner.error
                        from gi.repository import GLib
                        GLib.idle_add(lambda:(self.shell.area.queue_draw(),False)[1])
            except Exception as error:self._background_error(error)
            finally:
                if reader:reader.close()
                self.scheduler_inflight=False
        threading.Thread(target=work,name='win95lx-saver-idle',daemon=True).start();return True
    def close(self):
        if self.closed:return
        self.closed=True;self.request_generation+=1;self.request_waiting=False
        if self.popup:self.popup.finish(None,restore_focus=False);self.popup=None
        if self.tasks:self.tasks.stop(close=True)
        def work():
            with self.scheduler_lock:
                if self.idle:self.idle.close()
                if hasattr(self,'idle_runtime'):self.idle_runtime.close()
                self.ownership.close()
        threading.Thread(target=work,name='win95lx-saver-close',daemon=True).start()


def host_for(shell):
    if not hasattr(shell,'screen_saver_host'):shell.screen_saver_host=ScreenSaverHost(shell)
    return shell.screen_saver_host
