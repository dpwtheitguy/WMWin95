#!/usr/bin/env python3
"""Read installer package requirements and optionally audit installed versions.

Read-only: package installation belongs to the installer, never the UI.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def packages(document, profile):
    if document.get('schema')!=1:raise ValueError('Unsupported dependency manifest.')
    groups=document['profiles'][profile]
    result=set()
    for name in groups:
        for package in document['groups'][name]['packages']:
            if not isinstance(package,str) or not re.fullmatch(r'[a-z0-9][a-z0-9+.-]*(?::[a-z0-9]+)?',package):
                raise ValueError('Invalid distribution package name.')
            result.add(package)
    return sorted(result)


def installed_record(output,package,native_arch):
    target=package.split(':',1)[1] if ':' in package else native_arch
    for line in output.splitlines():
        fields=line.split('\t')
        if len(fields)==3 and fields[0]=='installed' and fields[2] in (target,'all'):
            return fields[1],fields[2]
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'config/installer-dependencies.json')
    parser.add_argument('--profile',default='windows95')
    parser.add_argument('--check-installed',action='store_true')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    document=json.loads(args.manifest.read_text())
    selected=packages(document,args.profile)
    # Validate all profiles, including groups outside the selected runtime.
    for profile in document['profiles']:packages(document,profile)
    if not args.check_installed:
        print('\n'.join(selected));return
    rows=[]
    native_arch=subprocess.run(['dpkg','--print-architecture'],capture_output=True,text=True,check=True).stdout.strip()
    for package in selected:
        found=subprocess.run(['dpkg-query','-W','-f=${db:Status-Status}\t${Version}\t${Architecture}\n',package],capture_output=True,text=True,check=False)
        record=installed_record(found.stdout,package,native_arch) if found.returncode==0 else None
        rows.append({'package':package,'installed':record is not None,'version':record[0]if record else None,'architecture':record[1]if record else None})
    report={'schema':1,'profile':args.profile,'manifest_sha256':__import__('hashlib').sha256(args.manifest.read_bytes()).hexdigest(),'packages':rows,'missing':[row['package']for row in rows if not row['installed']]}
    text=json.dumps(report,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')
    if report['missing']:raise SystemExit(1)

if __name__=='__main__':main()
