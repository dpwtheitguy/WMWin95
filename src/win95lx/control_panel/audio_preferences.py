"""Transactional PulseAudio/PipeWire endpoint selection and master levels."""
from dataclasses import dataclass
import json,re,subprocess

@dataclass(frozen=True)
class AudioPreferences:
    playback:str=''
    recording:str=''
    playback_volume:int=100
    recording_volume:int=100
    tray:bool=False
    def validate(self):
        for value in (self.playback,self.recording):
            if not isinstance(value,str) or len(value)>512 or value.startswith('-') or any(ord(c)<32 for c in value):raise ValueError('Invalid audio device.')
        # Existing amplifications can exceed the native slider. Preserve them
        # on unrelated edits, while a deliberate slider edit is limited to100.
        if any(type(v) is not int or not 0<=v<=200 for v in (self.playback_volume,self.recording_volume)):raise ValueError('Volume must be between 0 and 200 percent.')
        if type(self.tray) is not bool:raise ValueError('Invalid volume icon preference.')
        return self


def merge_untouched_audio(pending,applied,live):
    """Unrelated edits must not replay levels changed by another application."""
    from dataclasses import replace
    values={}
    for field in ('playback','recording'):
        level=field+'_volume'
        if getattr(pending,field)==getattr(applied,field) and getattr(pending,level)==getattr(applied,level):
            values[field]=getattr(live,field);values[level]=getattr(live,level)
    return replace(pending,**values)

@dataclass(frozen=True)
class Endpoint:
    name:str
    description:str
    channels:tuple
    muted:bool
    monitor:bool=False
    @property
    def percent(self):return round(max(self.channels,default=0)*100/65536)


def endpoints(rows):
    result=[]
    if not isinstance(rows,list):raise ValueError('The audio service returned an invalid device list.')
    for row in rows:
        values=tuple(int(v['value']) for v in row.get('volume',{}).values())
        if not values:continue
        name=row.get('name','');AudioPreferences(playback=name).validate()
        monitor=row.get('properties',{}).get('device.class')=='monitor' or name.endswith('.monitor')
        result.append(Endpoint(name,str(row.get('description') or name),values,bool(row.get('mute')),monitor))
    return tuple(result)

class PulseAudio:
    def __init__(self,run=None):self.run=run or self.command;self.changed=set();self.channel_ratios={}
    @staticmethod
    def command(*args):return subprocess.run(['pactl',*args],check=True,capture_output=True,text=True,timeout=5).stdout
    def inventory(self):
        return {kind:endpoints(json.loads(self.run('--format=json','list',kind))) for kind in ('sinks','sources')}
    def snapshot(self):
        inventory=self.inventory()
        return {'devices':inventory,'playback':self.run('get-default-sink').strip(),'recording':self.run('get-default-source').strip()}
    def preferences(self):
        state=self.snapshot();devices=state['devices']
        sink=next((d for d in devices['sinks'] if d.name==state['playback']),next(iter(devices['sinks']),None))
        sources=tuple(d for d in devices['sources'] if not d.monitor)
        source=next((d for d in sources if d.name==state['recording']),next(iter(sources),None))
        return AudioPreferences(sink.name if sink else '',source.name if source else '',sink.percent if sink else 100,source.percent if source else 100).validate()
    @staticmethod
    def scaled_channels(endpoint,percent):
        peak=max(endpoint.channels,default=0);target=round(percent*65536/100)
        return tuple(round(v*target/peak) if peak else target for v in endpoint.channels)
    def level_channels(self,endpoint,percent):
        if max(endpoint.channels,default=0)>0:self.channel_ratios[endpoint.name]=endpoint.channels
        remembered=self.channel_ratios.get(endpoint.name)
        source=endpoint
        if not max(endpoint.channels,default=0) and remembered and len(remembered)==len(endpoint.channels):
            source=Endpoint(endpoint.name,endpoint.description,remembered,endpoint.muted,endpoint.monitor)
        return self.scaled_channels(source,percent)
    def apply(self,value):
        value.validate();state=self.snapshot();self.changed=set()
        for kind,field,level in (('sinks','playback',value.playback_volume),('sources','recording',value.recording_volume)):
            name=getattr(value,field)
            if not name:continue
            device=next((d for d in state['devices'][kind] if d.name==name and (kind=='sinks' or not d.monitor)),None)
            if device is None:raise ValueError('The selected audio device is no longer available. Refresh Multimedia Properties and choose an available device.')
            singular='sink' if kind=='sinks' else 'source'
            if state[field]!=name:
                self.changed.add((kind,name));self.run('set-default-'+singular,name)
            if device.percent!=level:
                self.changed.add((kind,name));self.run('set-'+singular+'-volume',name,*(str(v) for v in self.level_channels(device,level)))
    def restore(self,state):
        errors=[]
        for kind,field in (('sinks','playback'),('sources','recording')):
            singular='sink' if kind=='sinks' else 'source'
            if any(k==kind for k,n in self.changed):
                try:
                    if state[field]:self.run('set-default-'+singular,state[field])
                except (OSError,subprocess.SubprocessError,RuntimeError) as error:errors.append(error)
            for device in state['devices'][kind]:
                if (kind,device.name) not in self.changed:continue
                try:self.run('set-'+singular+'-volume',device.name,*(str(v) for v in device.channels))
                except (OSError,subprocess.SubprocessError,RuntimeError) as error:errors.append(error)
        self.changed=set()
        if errors:raise RuntimeError('The audio service could not restore every previous setting. Reopen Multimedia Properties to check the device levels.') from errors[0]

    def set_playback_volume(self,percent):
        if type(percent) is not int or not 0<=percent<=100:raise ValueError('Volume must be between 0 and 100 percent.')
        state=self.snapshot();device=next((d for d in state['devices']['sinks'] if d.name==state['playback']),None)
        if device is None:raise RuntimeError('No playback device is available.')
        self.run('set-sink-volume',device.name,*(str(v) for v in self.level_channels(device,percent)))
    def set_playback_mute(self,muted):
        if type(muted) is not bool:raise ValueError('Invalid mute setting.')
        state=self.snapshot()
        if not any(d.name==state['playback'] for d in state['devices']['sinks']):raise RuntimeError('No playback device is available.')
        self.run('set-sink-mute',state['playback'],'1' if muted else '0')
