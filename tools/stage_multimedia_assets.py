"""Stage independently reviewed classic Multimedia property-sheet captures."""
import hashlib
from pathlib import Path
from pixels import read,write
ROOT=Path(__file__).resolve().parents[1]
def stage(output):
    output.mkdir(parents=True,exist_ok=True)
    rows=[]
    for tab in ('audio','video','midi','cd-music','advanced'):
        source=ROOT/'private/screenshots/cpl-20261126/classic-reviewed-run2'/f'multimedia-{tab}.png'
        sw,sh,pixels=read(source);x,y,w,h=22,22,366,448
        if x+w>sw or y+h>sh:raise ValueError('Native Multimedia bounds exceed the capture.')
        dest=f'multimedia-{tab}-frame.png';write(output/dest,w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
        rows.append({'source':str(source.relative_to(ROOT)),'profile':'classic','type':'SCREEN_CAPTURE_CONTROL','rectangle':[x,y,w,h],'output':dest,'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    from resources import extract
    from win95lx.assets.bitmap import icon_dib,word
    source=ROOT/'private/cabsets/windows95/sndvol32.exe';resources=list(extract(source.read_bytes()))
    for ident,name in ((304,'volume-icon.png'),(303,'volume-muted-icon.png')):
        group=next(data for kind,key,lang,data,fmt in resources if kind==14 and key==ident)
        entries=[group[6+i*14:20+i*14] for i in range(word(group,4))]
        entry=next(e for e in entries if e[:2]==bytes((16,16)))
        raw=next(data for kind,key,lang,data,fmt in resources if kind==3 and key==word(entry,12))
        w,h,pixels=icon_dib(raw);write(output/name,w,h,pixels)
        rows.append({'source':'sndvol32.exe','type':'GROUP_ICON','id':ident,'output':name,'dimensions':[w,h],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    return rows
