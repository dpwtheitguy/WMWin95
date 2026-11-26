"""Original CUR/ANI decoding and staged cursor timelines, without GTK imports."""
from dataclasses import dataclass
from functools import lru_cache
import json,struct
from pathlib import Path
from win95lx.assets.bitmap import icon_dib,word

@dataclass
class Frame:
    width:int
    height:int
    pixels:list
    hotspot:tuple
    invert:tuple=()


def dib_frame(data,hotspot):
    if len(data)<16:raise ValueError('Truncated cursor bitmap.')
    width,combined=struct.unpack_from('<ii',data,4)
    if not 0<width<=256 or not 0<abs(combined)<=512:raise ValueError('Invalid cursor dimensions.')
    w,h,pixels=icon_dib(data)
    if w>256 or h>256 or not 0<=hotspot[0]<w or not 0<=hotspot[1]<h:raise ValueError('Invalid cursor dimensions or hotspot.')
    invert=tuple((i%w,i//w) for i,p in enumerate(pixels) if p==(255,255,255,0))
    pixels=[(0,0,0,255) if p==(255,255,255,0) else p for p in pixels]
    return Frame(w,h,pixels,tuple(hotspot),invert)


def cur_frame(data):
    if len(data)<22 or word(data,0)!=0 or word(data,2) not in (1,2):raise ValueError('Invalid cursor directory.')
    count=word(data,4)
    if not count or len(data)<6+count*16:raise ValueError('Truncated cursor directory.')
    entries=[data[6+i*16:22+i*16] for i in range(count)]
    entry=next((e for e in entries if e[:2]==b'\x20\x20'),entries[0])
    size,offset=struct.unpack_from('<II',entry,8)
    if offset+size>len(data):raise ValueError('Truncated cursor image.')
    hotspot=(word(entry,4),word(entry,6)) if word(data,2)==2 else (0,0)
    return dib_frame(data[offset:offset+size],hotspot)


def chunks(data):
    pos=0
    while pos+8<=len(data):
        tag=data[pos:pos+4];n=struct.unpack_from('<I',data,pos+4)[0]
        # Some original Plus95 ANI files count the RIFF header in this size.
        if pos==0 and tag==b'RIFF' and n==len(data):n-=8
        value=data[pos+8:pos+8+n]
        if len(value)!=n:raise ValueError('Truncated ANI chunk.')
        yield tag,value
        if tag in (b'RIFF',b'LIST'):yield from chunks(value[4:])
        pos+=8+n+(n%2)


def decode(data):
    if len(data)>16*1024*1024:raise ValueError('Cursor is too large.')
    if data[:4]!=b'RIFF':return [cur_frame(data)],[0],[1000]
    if data[8:12]!=b'ACON':raise ValueError('Not an animated cursor.')
    parts=list(chunks(data));header=next((d for k,d in parts if k==b'anih'),None)
    if header is None or len(header)<36:raise ValueError('Missing ANI header.')
    size,nframes,nsteps,w,h,bpp,planes,rate,flags=struct.unpack_from('<9I',header)
    if not 0<nframes<=1024 or not 0<nsteps<=4096 or not flags&1:raise ValueError('Unsupported ANI header.')
    frames=[cur_frame(d) for k,d in parts if k==b'icon']
    if len(frames)!=nframes:raise ValueError('ANI frame count mismatch.')
    def integers(tag,default):
        block=next((d for k,d in parts if k==tag),None)
        if block is None:return default
        if len(block)!=nsteps*4:raise ValueError('ANI timeline length mismatch.')
        return list(struct.unpack('<'+'I'*nsteps,block))
    sequence=integers(b'seq ',list(range(nsteps)))
    rates=integers(b'rate',[rate]*nsteps)
    if len(sequence)!=nsteps or any(i>=nframes for i in sequence) or any(not 0<r<=3600 for r in rates):raise ValueError('Invalid ANI timeline.')
    return frames,sequence,[r*1000/60 for r in rates]


class PointerLibrary:
    def __init__(self,assets):
        self.assets=Path(assets);path=self.assets/'pointer-schemes.json'
        self.data=json.loads(path.read_text()) if path.exists() else {'schemes':{},'assets':{}}
    @property
    def names(self):return tuple(self.data['schemes'])
    def definition(self,scheme,role):
        mapping=self.data['schemes'].get(scheme,self.data['schemes'].get('(None)',{}))
        asset=mapping.get(role)
        if asset is None:raise ValueError('The pointer scheme is not installed.')
        return self.data['assets'][asset]
    def frame(self,scheme,role,elapsed_ms=0):
        definition=self.definition(scheme,role);sequence=definition['sequence'];rates=definition['durations_ms']
        remainder=elapsed_ms%sum(rates)
        for index,duration in enumerate(rates):
            if remainder<duration:break
            remainder-=duration
        return definition['frames'][sequence[index]]
    def animated(self,scheme):
        return any(len(self.definition(scheme,role)['sequence'])>1 for role in self.data['schemes'].get(scheme,{}))
