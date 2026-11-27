#!/usr/bin/env python3
"""Open the prepared Windows 98 reference visibly and offline, never auto-restore."""
import argparse,json,os,socket,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def command(profile='se-community'):
    if profile!='se-community':raise ValueError('Unknown prepared Windows 98 profile')
    disk=ROOT/'private/vm/windows98-se-community.qcow2'
    if not disk.exists():raise FileNotFoundError('Prepare the private disk first.')
    iso=ROOT/'private/reference-media/windows98-se-candidate.iso';run=ROOT/'private/run'
    args=['qemu-system-i386','-name','Win95LX Windows 98 SE Reference (community image)',
        '-machine','pc-i440fx-8.2','-accel','tcg','-cpu','pentium','-m','128','-smp','1',
        '-drive',f'file={disk},format=qcow2,if=ide,index=0','-boot','order=c','-vga','cirrus','-nic','none',
        '-rtc','base=1999-06-01T12:00:00','-display','gtk,show-tabs=off,zoom-to-fit=off',
        '-qmp',f'unix:{run}/windows98-se.qmp,server=on,wait=off','-pidfile',str(run/'windows98-se.pid')]
    if iso.exists():args+=['-drive',f'file={iso},format=raw,media=cdrom,readonly=on,if=ide,index=2']
    if Path('/run/user/1000/pipewire-0').exists():args+=['-audiodev','pipewire,id=refaudio','-device','sb16,audiodev=refaudio']
    return args

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dry-run',action='store_true');p.add_argument('--restore-snapshot');a=p.parse_args()
    args=command();run=ROOT/'private/run';endpoint=run/'windows98-se.qmp'
    (run/'windows98-se-launch.json').write_text(json.dumps(args,indent=2)+'\n')
    if a.restore_snapshot:args+=['-loadvm',a.restore_snapshot]
    if a.dry_run:print(json.dumps(args,indent=2));return
    if endpoint.exists():
        client=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        try:client.connect(str(endpoint));print('Windows 98 reference is already running.');return
        except ConnectionRefusedError:endpoint.unlink()
        finally:client.close()
    with (run/'windows98-se-console.log').open('ab') as log:
        process=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,
            env={**os.environ,'GDK_BACKEND':'x11','GDK_SCALE':'1'})
    for _ in range(100):
        if endpoint.exists():print('Opened visible offline Windows 98 SE reference.');return
        if process.poll() is not None:raise SystemExit('Reference launch failed; inspect private/run/windows98-se-console.log')
        time.sleep(.1)
    raise SystemExit('The reference control socket did not open.')
if __name__=='__main__':main()
