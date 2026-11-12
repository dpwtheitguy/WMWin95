#!/usr/bin/env python3
"""Print a Xubuntu development VM launch plan, without creating or booting anything."""
import argparse,shlex
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('--iso',type=Path,required=True); p.add_argument('--disk',type=Path,default=Path('private/vm/xubuntu.qcow2')); p.add_argument('--accel',choices=['kvm','tcg'],default='kvm'); a=p.parse_args()
for path in (a.iso,a.disk):
    if ',' in str(path): p.error('Drive paths cannot contain commas')
print('# Create disk only if absent; this script does not execute commands:')
print(shlex.join(['qemu-img','create','-f','qcow2',str(a.disk.resolve()),'32G']))
print(shlex.join(['qemu-system-x86_64','-name','Win95LX Development','-machine','pc','-accel',a.accel,'-m','4096','-smp','2','-drive',f'file={a.disk.resolve()},format=qcow2,if=virtio','-drive',f'file={a.iso.resolve()},media=cdrom,readonly=on','-boot','order=d','-nic','user,model=virtio-net-pci','-vga','std','-display','gtk,zoom-to-fit=off','-monitor','stdio']))
