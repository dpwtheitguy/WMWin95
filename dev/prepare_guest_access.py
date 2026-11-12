#!/usr/bin/env python3
"""Stage guest-only SSH access and enable loopback-forwarded Linux guest networking."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'tools')); from qmp import QMP
run=ROOT/'private/run'; stage=ROOT/'private/provision'; stage.mkdir(parents=True,exist_ok=True); os.chmod(stage,0o700)
key=run/'guest_ed25519'
if not key.exists(): subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-f',str(key)],check=True)
pub=key.with_suffix('.pub').read_text().strip()
script='''#!/bin/sh
set -eu
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
printf '%s\\n' 'PUBLIC_KEY' >> "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
sudo apt-get update
sudo env DEBIAN_FRONTEND=noninteractive apt-get -o Dpkg::Options::=--force-confold install -y openssh-server
sudo mkdir -p /etc/ssh/sshd_config.d
printf '%s\\n' 'PasswordAuthentication no' 'PermitRootLogin no' | sudo tee /etc/ssh/sshd_config.d/90-win95lx-dev.conf
sudo systemctl restart ssh
printf '\\nWin95LX guest SSH ready\\n'
'''.replace('PUBLIC_KEY',pub)
(stage/'access.sh').write_text(script)
q=QMP(run/'xubuntu.qmp')
try:
    q.call('netdev_add',{'type':'user','id':'devnet','hostfwd':[{'str':'tcp:127.0.0.1:22295-:22'}]})
    q.call('device_add',{'driver':'virtio-net-pci','netdev':'devnet','id':'devnic'})
finally:q.close()
log=(run/'provision-http.log').open('ab'); proc=subprocess.Popen([sys.executable,'-m','http.server','18095','--bind','127.0.0.1','--directory',str(stage)],stdout=log,stderr=log,start_new_session=True); (run/'provision-http.pid').write_text(str(proc.pid)+'\n')
print('Staged access.sh and loopback-only provision server. Linux guest SSH forward: 127.0.0.1:22295')
