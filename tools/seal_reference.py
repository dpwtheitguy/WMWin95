#!/usr/bin/env python3
"""Import a PNG once, hash it, and prevent accidental overwrite."""
import argparse, hashlib, json, os, re
from pathlib import Path
from pixels import read

def main():
    p=argparse.ArgumentParser(); p.add_argument('image',type=Path); p.add_argument('screen'); p.add_argument('--metadata',type=Path,required=True); p.add_argument('--root',type=Path,default=Path('private/screenshots/reference')); a=p.parse_args()
    if not re.fullmatch('[a-z0-9-]+',a.screen): p.error('Use a lowercase screen ID')
    w,h,_=read(a.image)
    if (w,h)!=(800,600): p.error('Reference must be native 800x600')
    metadata=json.loads(a.metadata.read_text())
    for key in ('iso_sha256','vm_version','guest_version','color_depth','capture_method','steps','pointer_position'):
        if key not in metadata: p.error('Missing capture metadata: '+key)
    a.root.mkdir(parents=True,exist_ok=True); dest=a.root/a.screen; dest.mkdir(exist_ok=False)
    raw=a.image.read_bytes(); metadata.update({'sha256':hashlib.sha256(raw).hexdigest(),'width':w,'height':h,'screen':a.screen})
    (dest/'reference.png').write_bytes(raw); (dest/'capture.json').write_text(json.dumps(metadata,indent=2)+'\n')
    os.chmod(dest/'reference.png',0o444); os.chmod(dest/'capture.json',0o444); os.chmod(dest,0o555)
    print(dest)
if __name__=='__main__': main()
