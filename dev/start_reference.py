#!/usr/bin/env python3
"""Launch the offline original-media reference VM using a private virtual disk."""
import argparse,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('--accel',choices=['kvm','tcg'],default='kvm');p.add_argument('--icount', type=int, help='TCG instruction-clock shift for legacy timing');p.add_argument('--boot-cd',action='store_true',help='Boot the installation CD once; default boots installed disk');p.add_argument('--floppy',type=Path,help='Private writable boot image for legacy setup');p.add_argument('--window', action='store_true', help='Open an interactive window on the host desktop');p.add_argument('--snapshot', help='Resume an existing internal VM snapshot');a=p.parse_args();run=ROOT/'private/run';disk=ROOT/'private/vm/windows95.qcow2';iso=Path.home()/'Downloads/Windows 95C.iso';qmp=run/'windows95.qmp'
if qmp.exists():p.error('Reference VM socket already exists; inspect existing VM')
if not disk.exists():subprocess.run(['/usr/bin/qemu-img','create','-f','qcow2',str(disk),'2G'],check=True)
cmd=['/usr/bin/qemu-system-i386','-name','Win95LX Original Reference','-machine','pc-i440fx-8.2','-accel',a.accel,'-cpu','pentium','-m','64','-smp','1','-drive',f'file={disk},format=qcow2,if=ide,index=0','-drive',f'file={iso},media=cdrom,readonly=on,if=ide,index=2','-boot','order=c,once=a' if a.floppy else ('order=c,once=d' if a.boot_cd else 'order=c'),'-vga','cirrus','-nic','none','-rtc','base=1997-11-01T12:00:00','-display','gtk,show-tabs=off,zoom-to-fit=off' if a.window else 'none','-qmp',f'unix:{qmp},server=on,wait=off','-pidfile',str(run/'windows95.pid'),'-D',str(run/'windows95.log')]
if a.icount is not None:
 if a.accel != 'tcg':p.error('--icount requires TCG')
 cmd+=['-icount', f'shift={a.icount},sleep=off']
if a.floppy:
 if ',' in str(a.floppy) or not a.floppy.is_file():p.error('Invalid private floppy path')
 cmd+=['-drive',f'file={a.floppy.resolve()},format=raw,if=floppy']
if a.snapshot:
    cmd += ['-loadvm', a.snapshot]
if a.window:
    environment = os.environ.copy()
    if environment.get('DISPLAY'):
        environment.update(GDK_BACKEND='x11', GDK_SCALE='1')
    with (run/'windows95-console.log').open('ab') as log:
        process = subprocess.Popen(cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                   start_new_session=True, env=environment)
    for _ in range(50):
        if qmp.exists():
            break
        if process.poll() is not None:
            p.exit(1, f'QEMU exited. See {run / "windows95-console.log"}\n')
        time.sleep(0.1)
    else:
        p.exit(1, f'QEMU did not open its control socket. See {run / "windows95-console.log"}\n')
else:
    cmd.append('-daemonize')
    subprocess.run(cmd, check=True)
(run/'windows95-launch.json').write_text(json.dumps({'command':cmd,'installed':False},indent=2)+'\n')
print('Started offline original-media reference using', a.accel)
