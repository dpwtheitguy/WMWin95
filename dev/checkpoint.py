#!/usr/bin/env python3
"""Create an offline internal snapshot of the Linux development VM only."""
import argparse,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('name');a=p.parse_args()
if not re.fullmatch('[a-zA-Z0-9_-]+',a.name):p.error('Use a simple checkpoint name')
pidfile=ROOT/'private/run/xubuntu.pid'
if pidfile.exists():
    try:os.kill(int(pidfile.read_text()),0)
    except ProcessLookupError:pass
    else:p.error('Shut down the VM before creating an offline checkpoint')
disk=ROOT/'private/vm/xubuntu.qcow2';subprocess.run(['/usr/bin/qemu-img','snapshot','-c',a.name,str(disk)],check=True)
r=subprocess.run(['/usr/bin/qemu-img','info','--output=json',str(disk)],capture_output=True,text=True,check=True);(ROOT/'reports/linux-checkpoint.json').write_text(r.stdout);print('Created offline checkpoint:',a.name)
