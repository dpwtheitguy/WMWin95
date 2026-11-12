"""Dependency-free lossless RGB/RGBA PNG codec (8-bit, noninterlaced)."""
import struct, zlib
from pathlib import Path

def read(path):
    data=Path(path).read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n': raise ValueError('Expected PNG')
    pos=8; packed=b''
    while pos<len(data):
        n=struct.unpack_from('>I',data,pos)[0]; kind=data[pos+4:pos+8]; body=data[pos+8:pos+8+n]
        if zlib.crc32(kind+body)&0xffffffff!=struct.unpack_from('>I',data,pos+8+n)[0]: raise ValueError('PNG CRC mismatch')
        if kind==b'IHDR': w,h,depth,color,comp,filt,inter=struct.unpack('>IIBBBBB',body)
        if kind==b'IDAT': packed+=body
        if kind==b'IEND': break
        pos+=n+12
    if depth!=8 or color not in (2,6) or inter or comp or filt: raise ValueError('Use 8-bit RGB/RGBA noninterlaced PNG')
    channels=3 if color==2 else 4; stride=w*channels; raw=zlib.decompress(packed)
    if len(raw)!=h*(stride+1): raise ValueError('Invalid PNG data length')
    prev=bytearray(stride); pixels=[]
    for y in range(h):
        mode=raw[y*(stride+1)]; row=bytearray(raw[y*(stride+1)+1:(y+1)*(stride+1)])
        if mode>4: raise ValueError('Invalid PNG filter')
        for i in range(stride):
            a=row[i-channels] if i>=channels else 0; b=prev[i]; c=prev[i-channels] if i>=channels else 0
            p=a+b-c; distances=(abs(p-a),abs(p-b),abs(p-c)); paeth=(a,b,c)[distances.index(min(distances))]
            row[i]=(row[i]+(0,a,b,(a+b)//2,paeth)[mode])&255
        pixels.extend(tuple(row[i:i+channels])+( (255,) if channels==3 else () ) for i in range(0,stride,channels)); prev=row
    return w,h,pixels

def write(path,w,h,pixels):
    def chunk(kind,body): return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body)&0xffffffff)
    raw=b''.join(b'\0'+bytes(v for px in pixels[y*w:(y+1)*w] for v in px) for y in range(h))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
