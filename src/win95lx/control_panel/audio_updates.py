"""Serialized, coalesced playback updates without blocking the GTK thread."""
from dataclasses import dataclass
import json,threading
from win95lx.control_panel.audio_preferences import Endpoint,PulseAudio,endpoints

@dataclass(frozen=True)
class AudioUpdate:
    sequence:int
    endpoint:Endpoint|None
    error:str|None=None

class PlaybackUpdates:
    """One worker owns backend calls; `post` marshals callbacks to the UI.

    Device identity is established by the initial asynchronous read. Later
    default changes reject stale popup intents. Closing drains the final intent
    but suppresses callbacks; callers must never wait_closed on the UI thread.
    Failure reconciles actual readback rather than blindly restoring state that
    another audio client might have changed.
    """
    def __init__(self,backend,post,callback,*,previous=None,error_callback=None):
        self.backend,self.post,self.callback=backend,post,callback;self.previous=previous;self.error_callback=error_callback
        self.condition=threading.Condition();self.pending={};self.sequence=0
        self.closing=False;self.failed=False;self.suppress=False;self.busy=True
        self.target=None;self.ratios={};self.last_written={};self.done=threading.Event()
        self.worker=threading.Thread(target=self._work,name='Win95LX-playback-update',daemon=True);self.worker.start()

    def submit(self,*,volume=None,muted=None):
        intent={}
        if volume is not None:
            if type(volume)is not int or not 0<=volume<=100:raise ValueError('Volume must be between0 and100.')
            intent['volume']=volume
        if muted is not None:
            if type(muted)is not bool:raise ValueError('Mute must be boolean.')
            intent['muted']=muted
        if not intent:raise ValueError('An audio update is required.')
        with self.condition:
            if self.closing or self.failed:raise RuntimeError('The audio update session has ended.')
            self.sequence+=1;self.pending.update(intent);self.condition.notify_all();return self.sequence

    def close(self,*,flush=True):
        with self.condition:
            self.suppress=True;self.closing=True;self.callback=None
            if not flush:self.pending={}
            self.condition.notify_all()

    def wait_closed(self,timeout=10):
        self.worker.join(timeout);return not self.worker.is_alive()
    def wait_idle(self,timeout=10):
        with self.condition:return self.condition.wait_for(lambda:not self.busy and not self.pending,timeout)

    def _read(self,*,discover=False):
        default=self.backend.run('get-default-sink').strip()
        devices=endpoints(json.loads(self.backend.run('--format=json','list','sinks')))
        if discover:self.target=default
        endpoint=next((device for device in devices if device.name==self.target),None)
        if endpoint is None:raise RuntimeError('The playback device is no longer available.')
        return default,endpoint

    def _publish(self,result):
        def deliver():
            with self.condition:suppress=self.suppress;callback=self.callback;error_callback=self.error_callback
            if not suppress and callback is not None:callback(result)
            elif suppress and result.error and result.sequence>0 and error_callback is not None:error_callback(result)
            return False
        with self.condition:suppress=self.suppress
        if not suppress or(result.error and result.sequence>0 and self.error_callback is not None):self.post(deliver)

    def _apply(self,intent):
        default,before=self._read()
        if default!=self.target:raise RuntimeError('The default playback device changed. Reopen Volume Control.')
        if max(before.channels,default=0)>0 and(before.name not in self.ratios or before.channels!=self.last_written.get(before.name)):
            self.ratios[before.name]=before.channels
        if 'volume'in intent:
            reference=Endpoint(before.name,before.description,self.ratios.get(before.name,before.channels),before.muted)
            channels=PulseAudio.scaled_channels(reference,intent['volume'])
            if channels!=before.channels:self.backend.run('set-sink-volume',before.name,*map(str,channels))
            self.last_written[before.name]=channels
        else:channels=before.channels
        muted=intent.get('muted',before.muted)
        if muted!=before.muted:self.backend.run('set-sink-mute',before.name,'1'if muted else'0')
        current,after=self._read()
        if current!=self.target:raise RuntimeError('The default playback device changed. Reopen Volume Control.')
        if after.channels!=channels or after.muted!=muted:raise RuntimeError('The audio service did not retain the requested settings.')
        return after

    def _work(self):
        sequence=0
        try:
            if self.previous is not None:
                self.previous.wait_closed(None);self.previous=None
            _,initial=self._read(discover=True);self._publish(AudioUpdate(0,initial))
            while True:
                with self.condition:
                    self.busy=False;self.condition.notify_all()
                    self.condition.wait_for(lambda:self.pending or self.closing)
                    if not self.pending and self.closing:return
                    intent,self.pending=self.pending,{};sequence=self.sequence;self.busy=True
                endpoint=self._apply(intent);self._publish(AudioUpdate(sequence,endpoint))
        except Exception as error:
            # Commands can fail after a server-side change. Reflect readback;
            # do not overwrite a newer external change with an uncertain undo.
            try:_,endpoint=self._read(discover=True)
            except Exception:endpoint=None
            with self.condition:sequence=max(sequence,self.sequence);self.failed=True;self.pending={};self.closing=True
            self._publish(AudioUpdate(sequence,endpoint,str(error)))
        finally:
            with self.condition:self.busy=False;self.condition.notify_all()
            self.done.set()
