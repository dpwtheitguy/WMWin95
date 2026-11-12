#!/usr/bin/env python3
"""Print a local, network-isolated QEMU launch plan; never execute it."""
import argparse, json, os, shlex, shutil
from pathlib import Path

def plan(iso,disk,accel,boot_floppy=None):
    if accel not in ('kvm','tcg'): raise ValueError('Unsupported accelerator')
    command=['qemu-system-i386','-name','Win95LX Reference','-machine','pc','-accel',accel,'-cpu','pentium','-smp','1','-m','64','-vga','cirrus','-nic','none','-drive',f'file={disk},format=qcow2,if=ide,index=0','-drive',f'file={iso},media=cdrom,readonly=on,if=ide,index=2','-boot','order=a' if boot_floppy else 'order=c','-rtc','base=localtime','-monitor','stdio','-device','sb16','-display','gtk,zoom-to-fit=off']
    if boot_floppy: command+=['-drive',f'file={boot_floppy},format=raw,if=floppy,readonly=on']
    return command

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--iso',type=Path,required=True); p.add_argument('--disk',type=Path,default=Path('private/vm/win95.qcow2')); p.add_argument('--accel',choices=['kvm','tcg'],default='kvm'); p.add_argument('--boot-floppy',type=Path); a=p.parse_args()
    for value in (a.iso,a.disk,a.boot_floppy):
        if value and ',' in str(value): p.error('QEMU drive paths cannot contain commas')
    command=plan(a.iso.resolve(),a.disk.resolve(),a.accel,a.boot_floppy.resolve() if a.boot_floppy else None)
    status={'qemu':shutil.which('qemu-system-i386'),'qemu_img':shutil.which('qemu-img'),'kvm_device':Path('/dev/kvm').exists(),'kvm_access':os.access('/dev/kvm',os.R_OK|os.W_OK),'iso_exists':a.iso.is_file(),'disk_exists':a.disk.is_file(),'boot_floppy_exists':a.boot_floppy.is_file() if a.boot_floppy else None,'command':command,'executed':False}
    print(json.dumps(status,indent=2)); print('\n# Review only. Create disk only if absent:'); print(shlex.join(['qemu-img','create','-f','qcow2',str(a.disk.resolve()),'2G'])); print(shlex.join(command))
if __name__=='__main__': main()
