#!/usr/bin/env python3
"""Deploy source/private assets to the project guest over key-only SSH, then launch."""
import argparse,io,subprocess,tarfile,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--user',choices=['xubuntu','developer'],default='developer');p.add_argument('--launch',action='store_true',help='Launch under an already logged-in matching guest account');a=p.parse_args()
subprocess.run([sys.executable,'-m','unittest','discover','-s','tests'],cwd=ROOT,check=True)
ssh=['ssh','-i',str(ROOT/'private/run/guest_ed25519'),'-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(ROOT/('private/run/installed_known_hosts' if a.user=='developer' else 'private/run/known_hosts')),'-p','22295',a.user+'@127.0.0.1']
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
    for folder in ('src','private/shell-assets'):
        archive.add(ROOT/folder,arcname=folder,filter=lambda info:None if '__pycache__' in info.name else info)
subprocess.run(ssh+['mkdir -p "$HOME/win95lx-preview"; tar -xzf - -C "$HOME/win95lx-preview"'],input=buffer.getvalue(),check=True)
command='cd "$HOME/win95lx-preview"; nohup env DISPLAY=:0 XDG_SESSION_TYPE=x11 PYTHONPATH="$HOME/win95lx-preview/src" python3 -m win95lx.shell.app --assets "$HOME/win95lx-preview/private/shell-assets" > "$HOME/win95lx-preview/shell.log" 2>&1 < /dev/null &'
if a.launch:subprocess.run(ssh+[command],check=True)
print('Deployed shell preview to guest account',a.user,'; launch requested:',a.launch)
