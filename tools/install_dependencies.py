#!/usr/bin/env python3
"""Install manifest-selected packages in the guarded development guest only.

The installer is a maintenance entry point, never an applet click handler.
Default mode asks apt to simulate; --apply performs the reviewed installation.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
from check_dependencies import packages,ROOT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,default=ROOT/'config/installer-dependencies.json')
    parser.add_argument('--profile',default='windows95')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    document=json.loads(args.manifest.read_text())
    selected=packages(document,args.profile)
    subprocess.run(['/usr/lib/win95lx/require-guest'],check=True)
    if os.geteuid()!=0:raise SystemExit('Run through the authenticated guest maintenance installer.')
    release={}
    for line in Path('/etc/os-release').read_text().splitlines():
        if '=' in line:
            key,value=line.split('=',1);release[key]=value.strip('"')
    target=document['target']
    architecture=subprocess.check_output(['dpkg','--print-architecture'],text=True).strip()
    if (release.get('ID'),release.get('VERSION_ID'),architecture)!=(target['distribution'],target['version'],target['architecture']):
        raise SystemExit('This dependency profile does not match the guest OS/architecture.')
    foreign=sorted({package.split(':',1)[1] for package in selected if ':' in package})
    if any(arch not in target['foreign_architectures'] for arch in foreign):
        raise SystemExit('An undeclared package architecture was requested.')
    current=subprocess.check_output(['dpkg','--print-foreign-architectures'],text=True).split()
    for architecture in foreign:
        if architecture not in current:
            if not args.apply:raise SystemExit('Enable the declared foreign architecture with --apply before simulation.')
            subprocess.run(['dpkg','--add-architecture',architecture],check=True)
    environment={**os.environ,'DEBIAN_FRONTEND':'noninteractive'}
    if args.apply:subprocess.run(['apt-get','update','-qq'],env=environment,check=True)
    base=['apt-get','--no-install-recommends','--no-remove']
    subprocess.run([*base,'--simulate','install',*selected],env=environment,check=True)
    if args.apply:subprocess.run([*base,'install','-y',*selected],env=environment,check=True)

if __name__=='__main__':main()
