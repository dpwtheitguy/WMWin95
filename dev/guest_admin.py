#!/usr/bin/env python3
"""Run a reviewed guest script using authenticated sudo; never sudo on the host."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];p=argparse.ArgumentParser();p.add_argument('script',type=Path);a=p.parse_args()
ssh=['ssh','-i',str(ROOT/'private/run/guest_ed25519'),'-o','IdentitiesOnly=yes','-o','UserKnownHostsFile='+str(ROOT/'private/run/installed_known_hosts'),'-p','22295','developer@127.0.0.1']
subprocess.run(ssh+['cat > /home/developer/win95lx-reviewed-admin.sh; chmod 700 /home/developer/win95lx-reviewed-admin.sh'],input=a.script.read_bytes(),check=True)
password=json.loads((ROOT/'private/run/development-credentials.json').read_text())['password']
subprocess.run(ssh+['sudo -S -p "" /bin/sh /home/developer/win95lx-reviewed-admin.sh'],input=(password+'\n').encode(),check=True)
