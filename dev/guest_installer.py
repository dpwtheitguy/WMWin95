#!/usr/bin/env python3
"""Query/confirm the official installer, only inside the QEMU development guest."""
import argparse,http.client,json,socket
from pathlib import Path
p=argparse.ArgumentParser(); p.add_argument('action',choices=['status','confirm']); a=p.parse_args()
if Path('/sys/class/dmi/id/sys_vendor').read_text().strip()!='QEMU':p.error('Run inside the QEMU guest only')
class UnixHTTP(http.client.HTTPConnection):
    def connect(self):self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); self.sock.settimeout(10); self.sock.connect('/run/subiquity/socket')
c=UnixHTTP('localhost')
if a.action=='confirm':c.request('POST','/meta/confirm?tty=%22%2Fdev%2Ftty1%22',body=b'',headers={'Content-Type':'application/json'})
else:c.request('GET','/meta/status')
r=c.getresponse(); body=r.read().decode(); print(r.status,body)
if r.status>=400:raise SystemExit(1)
