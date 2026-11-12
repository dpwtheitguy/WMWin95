#!/usr/bin/env python3
"""Repair missing DOS boot paths in the designated reference VM only."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from qmp import QMP
commands=[r'a:\attrib.exe -r -s -h c:\msdos.sys',r'if not exist c:\msdos.pre copy c:\msdos.sys c:\msdos.pre',r'if exist c:\config.sys copy c:\config.sys c:\config.pre',r'if exist c:\autoexec.bat copy c:\autoexec.bat c:\autoexec.pre',r'if not exist c:\oakcdrom.sys copy a:\oakcdrom.sys c:\oakcdrom.sys',r'if not exist c:\mscdex.exe copy a:\mscdex.exe c:\mscdex.exe']
files=json.loads((ROOT/'dev/reference_boot_contents.json').read_text())
base=[sys.executable,str(ROOT/'tools/qmp.py'),'--socket',str(ROOT/'private/run/windows95.qmp')]
def send(action,text):subprocess.run(base+[action,text],check=True,stdout=subprocess.DEVNULL)
def command(text):send('type',text);send('key','ret')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apply',action='store_true',help='Apply only at the reference DOS command prompt')
args=parser.parse_args()
if not args.apply:
    print(json.dumps({'commands':commands,'files':files,'warning':'Requires the designated reference VM at a DOS prompt; not a general installer'},indent=2))
    raise SystemExit()
q=QMP(ROOT/'private/run/windows95.qmp')
try:
    if q.call('query-name').get('name')!='Win95LX Original Reference':
        raise SystemExit('Not the designated reference VM')
finally:q.close()
for text in commands:command(text)
for path,text in files.items():
    for index,line in enumerate(text.splitlines()):
        command('echo '+line+('>' if index==0 else '>>')+path)
(ROOT/'reports/reference-boot-paths.json').write_text(json.dumps({'reason':'MSDOS.SYS contained only ;FORMAT and no Windows paths after interrupted OEM setup','commands':commands,'files':files,'vendor_binaries_modified':False,'original_boot_files_backed_up':True},indent=2)+'\n')
print('Prepared reference boot paths with backups; no vendor binaries modified.')
