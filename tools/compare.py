#!/usr/bin/env python3
"""Exact RGBA comparison. Exit 0 identical, 1 differences, 2 invalid inputs."""
import argparse, hashlib, json, shutil
from pathlib import Path
from pixels import read,write

def compare(reference,actual,masks):
    w,h,a=read(reference); aw,ah,b=read(actual)
    if (w,h)!=(aw,ah): raise ValueError('Image dimensions differ')
    excluded=set()
    for mask in masks:
        if not mask.get('reason','').strip(): raise ValueError('Every mask requires a reason')
        x,y,mw,mh=mask['rect']
        if not all(type(v)==int for v in (x,y,mw,mh)) or min(x,y)<0 or min(mw,mh)<=0 or x+mw>w or y+mh>h: raise ValueError('Invalid mask rectangle')
        excluded.update(yy*w+xx for yy in range(y,y+mh) for xx in range(x,x+mw))
    if len(excluded)==w*h: raise ValueError('Masks exclude the entire image')
    changed=[i for i in range(w*h) if i not in excluded and a[i]!=b[i]]
    diff=[(0,0,0,255) if i in excluded or a[i]==b[i] else (255,0,255,255) for i in range(w*h)]
    bbox=None
    if changed: bbox=[min(i%w for i in changed),min(i//w for i in changed),max(i%w for i in changed)+1,max(i//w for i in changed)+1]
    return {'width':w,'height':h,'differing_pixels':len(changed),'compared_pixels':w*h-len(excluded),'masked_pixels':len(excluded),'differing_percent':100*len(changed)/(w*h-len(excluded)),'bbox_xyxy_exclusive':bbox,'passed':not changed},diff

def main():
    p=argparse.ArgumentParser(); p.add_argument('config',type=Path); p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    try:
        cfg=json.loads(args.config.read_text()); ref=(args.config.parent/cfg['reference']).resolve(); actual=(args.config.parent/cfg['actual']).resolve()
        digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
        if digest(ref)!=cfg['reference_sha256']: raise ValueError('Reference hash differs from sealed configuration')
        result,diff=compare(ref,actual,cfg.get('masks',[])); args.output.mkdir(parents=True,exist_ok=False)
        result.update({'reference_sha256':digest(ref),'actual_sha256':digest(actual),'config':cfg})
        write(args.output/'diff.png',result['width'],result['height'],diff)
        shutil.copyfile(args.config,args.output/'config.json')
        (args.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result)); return 0 if result['passed'] else 1
    except (ValueError,KeyError,OSError) as e: p.exit(2,str(e)+'\n')
if __name__=='__main__': raise SystemExit(main())
