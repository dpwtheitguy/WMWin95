"""Windows event schemes and bounded WAV inspection; no shell execution."""
from dataclasses import dataclass,field,replace
from pathlib import Path
import struct

# Labels and mappings from the original MOTOWN.INF and MMOPT.INF.
EVENTS=(
 ('Windows',None),('Asterisk','SystemAsterisk'),('Close program','Close'),
 ('Critical Stop','SystemHand'),('Default sound','.Default'),('Exclamation','SystemExclamation'),
 ('Exit Windows','SystemExit'),('Maximize','Maximize'),('Menu command','MenuCommand'),
 ('Menu popup','MenuPopup'),('Minimize','Minimize'),('Open program','Open'),
 ('Program error','AppGPFault'),('Question','SystemQuestion'),('Restore Down','RestoreDown'),
 ('Restore Up','RestoreUp'),('Start Windows','SystemStart'),('Windows Explorer',None),
 ('Empty Recycle Bin','EmptyRecycleBin'))
KEYS=frozenset(key for _,key in EVENTS if key)
DEFAULT={key:'' for key in KEYS}
DEFAULT.update({key:'sound-chord.wav' for key in ('SystemHand','SystemQuestion','SystemExclamation','SystemAsterisk')})
DEFAULT.update({'.Default':'sound-ding.wav','EmptyRecycleBin':'sound-ding.wav','SystemExit':'sound-tada.wav','SystemStart':'sound-mssound.wav'})
BUILTINS={'Windows Default':DEFAULT,'No Sounds':{key:'' for key in KEYS}}

@dataclass(frozen=True)
class SoundPreferences:
    scheme:str='Windows Default'
    events:dict=field(default_factory=lambda:dict(DEFAULT))
    schemes:dict=field(default_factory=dict)
    def validate(self):
        if not isinstance(self.scheme,str) or len(self.scheme)>80:raise ValueError('Invalid scheme name.')
        if not isinstance(self.schemes,dict) or len(self.schemes)>128:raise ValueError('Invalid saved sound schemes.')
        for mapping in (self.events,*self.schemes.values()):
            if not isinstance(mapping,dict) or set(mapping)!=KEYS:raise ValueError('Invalid event mapping.')
            for value in mapping.values():
                if not isinstance(value,str) or '\0' in value or len(value)>4096:raise ValueError('Invalid sound filename.')
                if value and not Path(value).is_absolute() and (Path(value).name!=value or not value.startswith('sound-') or not value.endswith('.wav')):raise ValueError('Choose a WAV file.')
        if any(not isinstance(name,str) or not name.strip() or len(name)>80 or name in BUILTINS for name in self.schemes):raise ValueError('Choose a different scheme name.')
        return self
    def select(self,name,factory=None):
        mappings={**(factory or BUILTINS),**self.schemes}
        if name not in mappings:raise ValueError('Unknown sound scheme.')
        return replace(self,scheme=name,events=dict(mappings[name])).validate()
    def assign(self,event,value):
        if event not in KEYS:raise ValueError('Select an event first.')
        return replace(self,scheme='',events={**self.events,event:str(value)}).validate()
    def save_scheme(self,name):
        name=name.strip()
        return replace(self,scheme=name,schemes={**self.schemes,name:dict(self.events)}).validate()
    def delete_scheme(self,name):
        if name not in self.schemes:raise ValueError('Built-in schemes cannot be deleted.')
        saved=dict(self.schemes);del saved[name]
        return replace(self,scheme='',schemes=saved).validate()

def sound_path(value,assets):return Path(value) if Path(value).is_absolute() else assets/value

def wave_details(path):
    # Read only the metadata: a user-supplied file must not allocate its payload.
    with Path(path).open('rb') as stream:
        header=stream.read(12)
        if len(header)!=12 or header[:4]!=b'RIFF' or header[8:]!=b'WAVE':raise ValueError('This is not a Windows WAV sound file.')
        end=struct.unpack_from('<I',header,4)[0]+8;actual=stream.seek(0,2)
        if end>actual or end<36:raise ValueError('The WAV sound file is incomplete.')
        stream.seek(12);fmt=None;data_size=None
        while stream.tell()+8<=end:
            kind,size=struct.unpack('<4sI',stream.read(8));position=stream.tell()
            if position+size>end:raise ValueError('The WAV sound file is incomplete.')
            if kind==b'fmt ':
                if size<16:raise ValueError('The WAV format is incomplete.')
                fmt=struct.unpack('<HHIIHH',stream.read(16))
            if kind==b'data':data_size=size
            stream.seek(position+size+(size&1))
        if not fmt or data_size is None:raise ValueError('The WAV sound file has no audio data.')
        encoding,channels,rate,byte_rate,align,bits=fmt
        if encoding not in (1,2,3,6,7,17) or not 1<=channels<=32 or not 1000<=rate<=768000 or not byte_rate or not align:raise ValueError('This WAV audio format is not supported.')
        return {'format':encoding,'channels':channels,'sample_rate':rate,'bits':bits,'duration':data_size/byte_rate,'bytes':data_size}

class SoundBackend:
    def __init__(self,assets):self.assets=assets;self.value=SoundPreferences()
    def preferences(self):return self.value
    def snapshot(self):return self.value
    def restore(self,value):self.value=value
    def apply(self,value):
        value.validate()
        for filename in set(value.events.values()):
            if filename:wave_details(sound_path(filename,self.assets))
        self.value=value
