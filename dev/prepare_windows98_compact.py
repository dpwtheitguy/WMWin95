#!/usr/bin/env python3
"""Copy a reference filesystem to a new 8GB FAT32 image; preserve original disks.

Uses original boot-sector code and mtools, without mounting or running vendor
programs on the host. Long filenames, timestamps and attributes are preserved.
The smaller partition avoids enormous legacy DOS/FAT scans of the community
image's 100GB volume. This is a compatibility migration, not a stock baseline.
"""
import os,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BIN=Path('/tmp/win95lx-reference-tools/usr/bin')
def main():
    source=ROOT/'private/reference-media/windows98-se-original-inspection.raw'
    target=ROOT/'private/vm/windows98-se-compact.raw';destination=target.with_suffix('.qcow2')
    if target.exists() or destination.exists():raise FileExistsError('Compact reference already exists')
    with source.open('rb') as f:
        mbr=bytearray(f.read(512));start=struct.unpack_from('<I',mbr,454)[0]*512;f.seek(start);boot=f.read(512);f.seek(start+2*512);second_stage=f.read(512)
    if boot[3:11]!=b'MSWIN4.1' or boot[82:90]!=b'FAT32   ':raise ValueError('Expected original Win98 FAT32 boot code')
    staging=ROOT/'private/windows98-tools';sector=staging/'fat32-original-boot.bin';sector.write_bytes(boot)
    count=8*1024**3//512-63
    mbr[446:510]=bytes(64);mbr[446:462]=bytes((128,1,1,0,12,254,255,255))+struct.pack('<II',63,count)
    with target.open('xb') as f:f.truncate(8*1024**3);f.seek(0);f.write(mbr)
    image=str(target)+'@@32256'
    subprocess.run([str(BIN/'mformat'),'-i',image,'-B',str(sector),'-F','-T',str(count),'-h','255','-n','63','-c','16','-H','63','-v','WIN98REF','::'],check=True)
    # Win98 FAT32 bootstrap includes a second code sector (and its backup).
    # Preserve the new BPB/FSInfo from mformat, copying only original code.
    with target.open('r+b') as f:
        for sector_number in (2,8):f.seek(32256+sector_number*512);f.write(second_stage)
    config=staging/'compact-mtoolsrc'
    config.write_text(f'drive c: file="{source}" offset={start}\ndrive d: file="{target}" offset=32256\n')
    env={**os.environ,'MTOOLSRC':str(config)}
    # Copy boot file first, before the rest of the root tree.
    subprocess.run([str(BIN/'mcopy'),'-p','-m','c:/IO.SYS','d:/IO.SYS'],env=env,check=True)
    subprocess.run([str(BIN/'mcopy'),'-s','-p','-m','-o','c:/*','d:/'],env=env,check=True)
    # The archived image has an obsolete tape detector that faults under QEMU.
    # Keep its complete original binary as a reversible backup, not a patch.
    subprocess.run([str(BIN/'mren'),'-i',image,'::/WINDOWS/SYSTEM/IOSUBSYS/DRVWQ117.VXD','DRVWQ117.BAK'],check=True)
    subprocess.run(['qemu-img','convert','-f','raw','-O','qcow2',str(target),str(destination)],check=True)
    print('Created new compact reference; source unchanged:',destination)
if __name__=='__main__':main()
