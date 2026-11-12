#!/usr/bin/env python3
"""Prepare a private Xubuntu autoinstall for the disposable project VM only."""
import hashlib,json,os,secrets,subprocess
from pathlib import Path
root=Path(__file__).resolve().parents[1]; run=root/'private/run'; pub=(run/'guest_ed25519.pub').read_text().strip(); credentials=run/'development-credentials.json'
if credentials.exists():raise SystemExit('Credentials already exist; review existing installation before preparing another.')
password=secrets.token_urlsafe(24); fd=os.open(credentials,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
with os.fdopen(fd,'w') as f:json.dump({'guest':'Win95LX Development VM','username':'developer','password':password},f,indent=2); f.write('\n')
hashed=subprocess.run(['openssl','passwd','-6','-stdin'],input=password+'\n',capture_output=True,text=True,check=True).stdout.strip()
config={'autoinstall':{'version':1,'refresh-installer':{'update':False},'locale':'en_US.UTF-8','keyboard':{'layout':'us'},'timezone':'America/Los_Angeles','source':{'id':'xubuntu-desktop-minimal'},'identity':{'hostname':'win95lx-dev','realname':'Win95LX Developer','username':'developer','password':hashed},'ssh':{'install-server':True,'allow-pw':False,'authorized-keys':[pub]},'storage':{'layout':{'name':'direct','match':{'path':'/dev/vda'}}},'packages':['python3-cairo','python3-gi-cairo','python3-pil','python3-pefile','cabextract','build-essential','git'],'shutdown':'reboot'}}
p=root/'private/provision/autoinstall.yaml'; p.write_text(json.dumps(config,indent=2)+'\n'); os.chmod(p,0o600); print('Prepared private installer config and mode-0600 developer credentials; secrets not printed.')
