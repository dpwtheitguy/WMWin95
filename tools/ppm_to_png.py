#!/usr/bin/env python3
"""Convert QEMU monitor screendump P6 PPM to PNG without scaling."""
import argparse,re
from pathlib import Path
from pixels import write

def convert(source,dest):
    b=source.read_bytes(); match=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255(?:\r\n|\s)',b)
    if not match: raise ValueError('Expected QEMU P6 PPM (255 max value, no comments)')
    w,h=map(int,match.groups()); raw=b[match.end():]
    if len(raw)!=w*h*3: raise ValueError('PPM pixel length mismatch')
    if dest.exists(): raise FileExistsError(dest)
    write(dest,w,h,[tuple(raw[i:i+3])+(255,) for i in range(0,len(raw),3)])
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('source',type=Path); p.add_argument('dest',type=Path); a=p.parse_args(); convert(a.source,a.dest)
