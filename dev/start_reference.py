#!/usr/bin/env python3
"""Launch the offline original-media reference VM using a private virtual disk."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--accel',choices=['kvm','tcg'],default='kvm');p.add_argument('--icount', type=int, help='TCG instruction-clock shift for legacy timing');p.add_argument('--boot-cd',action='store_true',help='Boot the installation CD once; default boots installed disk');p.add_argument('--floppy',type=Path,help='Private writable boot image for legacy setup');a=p.parse_args();run=ROOT/'private/run';disk=ROOT/'private/vm/windows95.qcow2';iso=Path.home()/'Downloads/Windows 95C.iso';qmp=run/'windows95.qmp'
if qmp.exists():p.error('Reference VM socket already exists; inspect existing VM')
if not disk.exists():subprocess.run(['/usr/bin/qemu-img','create','-f','qcow2',str(disk),'2G'],check=True)
cmd=['/usr/bin/qemu-system-i386','-name','Win95LX Original Reference','-machine','pc-i440fx-8.2','-accel',a.accel,'-cpu','pentium','-m','64','-smp','1','-drive',f'file={disk},format=qcow2,if=ide,index=0','-drive',f'file={iso},media=cdrom,readonly=on,if=ide,index=2','-boot','order=c,once=a' if a.floppy else ('order=c,once=d' if a.boot_cd else 'order=c'),'-vga','cirrus','-nic','none','-rtc','base=1997-11-01T12:00:00','-display','none','-qmp',f'unix:{qmp},server=on,wait=off','-pidfile',str(run/'windows95.pid'),'-D',str(run/'windows95.log'),'-daemonize']
if a.icount is not None:
 if a.accel != 'tcg':p.error('--icount requires TCG')
 cmd+=['-icount', f'shift={a.icount},sleep=off']
if a.floppy:
 if ',' in str(a.floppy) or not a.floppy.is_file():p.error('Invalid private floppy path')
 cmd+=['-drive',f'file={a.floppy.resolve()},format=raw,if=floppy']
subprocess.run(cmd,check=True);(run/'windows95-launch.json').write_text(json.dumps({'command':cmd,'installed':False},indent=2)+'\n');print('Started offline original-media reference using',a.accel)
