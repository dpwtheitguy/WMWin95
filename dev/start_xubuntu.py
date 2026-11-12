#!/usr/bin/env python3
"""Launch a private Xubuntu KVM guest. Never attaches physical disks or host folders."""
import argparse,json,os,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(); p.add_argument('--iso',type=Path,default=Path.home()/'Downloads/xubuntu-24.04.5-minimal-amd64.iso'); p.add_argument('--boot-iso',action='store_true',help='Boot installer ISO once; default boots installed virtual disk'); p.add_argument('--window', action='store_true', help='Open an interactive QEMU window on the host desktop'); a=p.parse_args()
if a.boot_iso and not a.iso.is_file():p.error('ISO missing')
if a.boot_iso and ',' in str(a.iso):p.error('ISO path contains unsupported comma')
vm=ROOT/'private/vm'; run=ROOT/'private/run'; vm.mkdir(parents=True,exist_ok=True); run.mkdir(parents=True,exist_ok=True); os.chmod(run,0o700)
disk=vm/'xubuntu.qcow2'; qmp=run/'xubuntu.qmp'; pid=run/'xubuntu.pid'
if qmp.exists():p.error('QMP socket exists; inspect running guest before starting another')
if not disk.exists():subprocess.run(['/usr/bin/qemu-img','create','-f','qcow2',str(disk),'32G'],check=True)
cmd=['/usr/bin/qemu-system-x86_64','-name','Win95LX Development','-machine','pc-i440fx-8.2','-accel','kvm','-cpu','host','-m','4096','-smp','2','-drive',f'file={disk},format=qcow2,if=virtio','-drive',f'file={a.iso.resolve()},media=cdrom,readonly=on' if a.boot_iso else 'media=cdrom,readonly=on','-boot','order=c,once=d' if a.boot_iso else 'order=c','-nic','user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:22295-:22','-device','virtio-tablet-pci','-device','virtio-vga','-display', 'gtk,show-tabs=off,zoom-to-fit=on' if a.window else 'none','-qmp',f'unix:{qmp},server=on,wait=off','-pidfile',str(pid),'-D',str(run/'xubuntu.log')]
if a.window:
    runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
    if runtime_dir and (Path(runtime_dir) / 'pipewire-0').exists():
        cmd.extend(['-audiodev', 'pipewire,id=win95audio', '-device', 'ich9-intel-hda',
                    '-device', 'hda-output,audiodev=win95audio'])
    environment = os.environ.copy()
    if environment.get('DISPLAY'):
        # QEMU GTK's X11 backend works through XWayland on the development host.
        environment['GDK_BACKEND'] = 'x11'
        environment['GDK_SCALE'] = '1'
    with (run / 'xubuntu-console.log').open('ab') as log:
        process = subprocess.Popen(
            cmd, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True, env=environment,
        )
    for attempt in range(50):
        if qmp.exists():
            break
        if process.poll() is not None:
            p.exit(1, f'QEMU exited. See {run / "xubuntu-console.log"}\n')
        time.sleep(0.1)
    else:
        p.exit(1, f'QEMU did not open its control socket. See {run / "xubuntu-console.log"}\n')
else:
    cmd.append('-daemonize')
    subprocess.run(cmd, check=True)
(run / 'xubuntu-launch.json').write_text(
    json.dumps({'command': cmd, 'iso': str(a.iso.resolve()), 'disk': str(disk)}, indent=2) + '\n'
)
print('Started VM; QMP:', qmp)
