#!/usr/bin/env python3
"""Stage the original MAIN.CPL double-click test AVI as private lossless frames."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from resources import extract
from pixels import write
from win95lx.assets.rle8 import decode

def chunks(data):
 pos=0
 while pos+8<=len(data):
  tag=data[pos:pos+4];length=struct.unpack_from('<I',data,pos+4)[0];value=data[pos+8:pos+8+length]
  if len(value)!=length:raise ValueError('Truncated AVI chunk.')
  yield tag,value
  if tag in (b'RIFF',b'LIST'):yield from chunks(value[4:])
  pos+=8+length+(length%2)

def main(output=None):
 source=ROOT/'private/cabsets/windows95/main.cpl';avi=next(d for k,i,l,d,f in extract(source.read_bytes()) if k=='AVI' and i==100)
 parts=list(chunks(avi));header=next(d for k,d in parts if k==b'strf');width,height=struct.unpack_from('<ii',header,4)
 assert struct.unpack_from('<H',header,14)[0]==8 and struct.unpack_from('<I',header,16)[0]==1
 palette=[(header[i+2],header[i+1],header[i],255) for i in range(40,len(header),4)]
 output=Path(output) if output is not None else ROOT/'private/shell-assets';output.mkdir(parents=True,exist_ok=True);previous=None;count=0
 for tag,frame in parts:
  if tag!=b'00dc':continue
  previous=decode(frame,width,height,previous);write(output/f'mouse-test-{count:02}.png',width,height,[palette[index][:3]+(0 if palette[index][:3]==(0,255,255) else 255,) for index in previous]);count+=1
 period=struct.unpack_from('<I',next(d for k,d in parts if k==b'avih'))[0]
 (output/'mouse-test-animation.json').write_text(json.dumps({'frames':count,'period_ms':round(period/1000),'source':'main.cpl','resource':['AVI',100],'source_sha256':hashlib.sha256(avi).hexdigest()})+'\n')
 print('Staged',count,'original double-click animation frames.')
if __name__=='__main__':main()
