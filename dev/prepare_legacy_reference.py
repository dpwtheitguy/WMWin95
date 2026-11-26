#!/usr/bin/env python3
"""Prepare a separate FAT16 reference disk using original DOS/Setup files.

Creates only new project-private files. No host mounts or vendor binary patches.
The existing OSR2.5 FAT32 disk cannot be used to boot Windows 95 RTM.
"""
import argparse,json,re,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
MTOOLS=Path('/tmp/win95lx-reference-tools/usr/bin')

def file_in(directory,name):return next(path for path in directory.iterdir() if path.name.casefold()==name.casefold())

def prepare(name,source,precopy,cabset,iso):
    if name not in ('rtm','osr1','osr2'):raise ValueError('Unknown reference profile')
    disk=ROOT/'private/vm'/f'windows95-{name}.qcow2'
    raw=ROOT/'private/reference-media'/f'windows95-{name}-setup.raw'
    staging=ROOT/'private/reference-media'/f'windows95-{name}-boot'
    if disk.exists() or raw.exists() or staging.exists():raise FileExistsError('Reference preparation already exists')
    staging.mkdir(parents=True)
    source_sys=file_in(cabset,'sys.com').read_bytes()
    marker=source_sys.find(b'MSWIN4.0')
    if marker<3:raise ValueError('The original FAT16 boot-sector template was not found')
    boot=source_sys[marker-3:marker-3+512]
    if boot[:1]!=b'\xeb' or boot[-2:]!=b'\x55\xaa':raise ValueError('Invalid original boot-sector template')
    (staging/'boot-sector.bin').write_bytes(boot)
    original=ROOT/'private/reference/classic-registry-check.raw'
    with original.open('rb') as stream:mbr=bytearray(stream.read(512))
    mbr[446:510]=bytes(64)
    sectors=1023*16*63-63
    mbr[446:462]=bytes((128,1,1,0,6,15,255,254))+struct.pack('<II',63,sectors)
    mbr[510:512]=b'\x55\xaa'
    with raw.open('xb') as stream:stream.truncate(512*1024*1024);stream.seek(0);stream.write(mbr)
    image=str(raw)+'@@32256'
    subprocess.run([str(MTOOLS/'mformat'),'-i',image,'-B',str(staging/'boot-sector.bin'),'-T',str(sectors),'-h','16','-n','63','-c','16','-H','63','-v','WIN95'+name.upper(),'::'],check=True)
    (staging/'IO.SYS').write_bytes(file_in(precopy,'winboot.sys').read_bytes())
    text='[Paths]\r\nWinDir=C:\\WINDOWS\r\nWinBootDir=C:\\WINDOWS\r\nHostWinBootDrv=C\r\n[Options]\r\nBootGUI=0\r\n'
    text+=';'+('x'*1050)+'\r\n';(staging/'MSDOS.SYS').write_bytes(text.encode('ascii'))
    (staging/'COMMAND.COM').write_bytes(file_in(precopy,'command.com').read_bytes())
    (staging/'HIMEM.SYS').write_bytes(file_in(cabset,'himem.sys').read_bytes())
    (staging/'CONFIG.SYS').write_bytes(b'DEVICE=C:\\HIMEM.SYS /TESTMEM:OFF\r\nDOS=HIGH\r\nFILES=40\r\nBUFFERS=20\r\n')
    (staging/'AUTOEXEC.BAT').write_bytes(b'@ECHO OFF\r\nPATH C:\\;C:\\WIN95;C:\\WINDOWS;C:\\WINDOWS\\COMMAND\r\nIF EXIST C:\\INSTALL.TAG GOTO DONE\r\nECHO Setup started>C:\\INSTALL.TAG\r\nC:\\WIN95\\SETUP.EXE C:\\MSBATCH.INF /is\r\n:DONE\r\n')
    # Existing user-supplied license data never enters logs, source or reports.
    licenses=(ROOT/'private/licenses/user-supplied-oem.json').read_text()
    product=re.search(r'\d{5}-OEM-\d{7}-\d{5}',licenses)
    if not product:raise ValueError('No private user-supplied OEM license available')
    batch='[Setup]\r\nExpress=1\r\nEBD=0\r\nInstallDir=C:\\WINDOWS\r\nProductID='+product[0].replace('-','')+'\r\nTimeZone=Pacific\r\n[NameAndOrg]\r\nDisplay=0\r\nName=Win95LX '+name.upper()+' Reference\r\nOrg=Win95LX\r\n[Network]\r\nDisplay=0\r\n'
    private_batch=staging/'MSBATCH.INF';private_batch.write_bytes(batch.encode('ascii'));private_batch.chmod(0o600)
    for filename in ('IO.SYS','MSDOS.SYS','COMMAND.COM','HIMEM.SYS','CONFIG.SYS','AUTOEXEC.BAT','MSBATCH.INF'):
        subprocess.run([str(MTOOLS/'mcopy'),'-i',image,str(staging/filename),'::/'+filename],check=True)
    subprocess.run([str(MTOOLS/'mattrib'),'-i',image,'+s','+h','+r','::/IO.SYS','::/MSDOS.SYS'],check=True)
    subprocess.run([str(MTOOLS/'mmd'),'-i',image,'::/WIN95'],check=True)
    for path in source.iterdir():
        if path.is_file():subprocess.run([str(MTOOLS/'mcopy'),'-i',image,str(path),'::/WIN95/'+path.name],check=True)
    subprocess.run(['qemu-img','convert','-O','qcow2',str(raw),str(disk)],check=True)
    command=['/usr/bin/qemu-system-i386','-name','Win95LX Windows 95 '+name.upper()+' Reference','-machine','pc-i440fx-8.2','-accel','tcg','-cpu','pentium','-m','64','-smp','1',
             '-drive',f'file={disk},format=qcow2,if=ide,index=0','-drive',f'file={iso.resolve()},media=cdrom,readonly=on,if=ide,index=2',
             '-boot','order=c','-vga','cirrus','-nic','none','-rtc','base=1997-11-01T12:00:00','-display','gtk,show-tabs=off,zoom-to-fit=off',
             '-qmp',f'unix:{ROOT}/private/run/windows95-{name}.qmp,server=on,wait=off','-pidfile',str(ROOT/'private/run'/f'windows95-{name}.pid'),'-icount','shift=5,sleep=on']
    # References remain offline. Original sound playback uses emulated hardware.
    if Path('/run/user/1000/pipewire-0').exists():command+=['-audiodev','pipewire,id=refaudio','-device','sb16,audiodev=refaudio']
    (ROOT/'private/run'/f'windows95-{name}-launch.json').write_text(json.dumps(command,indent=2)+'\n')
    print('Prepared separate FAT16 reference disk and visible profile:',name)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('name',choices=('rtm','osr1','osr2'));p.add_argument('--source',type=Path,required=True);p.add_argument('--precopy',type=Path,required=True);p.add_argument('--cabset',type=Path,required=True);p.add_argument('--iso',type=Path,required=True);a=p.parse_args();prepare(a.name,a.source,a.precopy,a.cabset,a.iso)
if __name__=='__main__':main()
