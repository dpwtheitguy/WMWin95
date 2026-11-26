#!/usr/bin/env python3
"""Read IE4 templates/fonts from an offline private FAT disk copy using mcopy."""
import argparse,hashlib,json,struct,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('image',type=Path);p.add_argument('--mcopy',default='mcopy');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=False)
 with a.image.open('rb') as f:mbr=f.read(512)
 if mbr[510:512]!=b'\x55\xaa':raise ValueError('Not an MBR image')
 partitions=[mbr[446+i*16:462+i*16] for i in range(4)]
 partition=next(part for part in partitions if part[4] in (1,4,6,11,12,14))
 offset=struct.unpack_from('<I',partition,8)[0]*512
 paths=[('WEB/'+name+'.HTT',name+'.htt') for name in ('MYCOMP','FOLDER','CONTROLP','PRINTERS')]
 paths += [('SYSTEM/SHELL32.DLL','shell32-installed.dll'),('FONTS/VERDANA.TTF','verdana.ttf'),('FONTS/VERDANAB.TTF','verdanab.ttf')]
 records=[]
 for source,destination in paths:
  path=a.output/destination.lower()
  subprocess.run([a.mcopy,'-i',str(a.image)+f'@@{offset}','::/WINDOWS/'+source,str(path)],check=True)
  records.append({'source':'C:/WINDOWS/'+source,'output':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 (a.output/'provenance.json').write_text(json.dumps({'partition_offset':offset,'files':records},indent=2)+'\n')
 print(json.dumps({'extracted':len(records),'output':str(a.output)}))
if __name__=='__main__':main()
