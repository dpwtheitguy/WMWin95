"""Stage original Fonts folder/preview frames and font-type icons privately."""
import hashlib
from pathlib import Path
from resources import extract
from pixels import read,write
from win95lx.assets.bitmap import icon_dib,word
ROOT=Path(__file__).resolve().parents[1]
def stage(output):
    output.mkdir(parents=True,exist_ok=True);rows=[];base=ROOT/'private/screenshots/fonts-20261126'
    for source_name,dest,rect,clear in (
        ('classic-fonts-default.png','fonts-folder-frame.png',(66,66,600,411),(6,44,588,342)),
        ('classic-font-preview-attempt2.png','fonts-preview-frame.png',(215,79,371,414),(6,62,342,345)),
    ):
        source=base/source_name;sw,sh,pixels=read(source);x,y,w,h=rect
        if x+w>sw or y+h>sh:raise ValueError('Font reference crop exceeds the framebuffer.')
        image=[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)]
        cx,cy,cw,ch=clear
        for yy in range(cy,cy+ch):image[yy*w+cx:yy*w+cx+cw]=[(255,255,255,255)]*cw
        if dest=='fonts-folder-frame.png':
            for yy in range(393,406):image[yy*w+6:yy*w+580]=[(192,192,192,255)]*574
        write(output/dest,w,h,image)
        rows.append({'source':str(source.relative_to(ROOT)),'type':'SCREEN_CAPTURE_CONTROL','profile':'classic','rectangle':list(rect),'dynamic_content_removed':[list(clear)]+([[6,393,574,13]] if dest=='fonts-folder-frame.png' else []),'output':dest,'reference_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    source=ROOT/'private/cabsets/windows95/fontext.dll';resources=list(extract(source.read_bytes()))
    for ident,name in ((1,'folder'),(2,'truetype'),(3,'bitmap'),(4,'opentype')):
        group=next(data for kind,key,lang,data,fmt in resources if kind==14 and key==ident)
        entries=[group[6+i*14:20+i*14] for i in range(word(group,4))]
        for size in (16,32):
            entry=next(e for e in entries if e[:2]==bytes((size,size)));image_id=word(entry,12)
            raw=next(data for kind,key,lang,data,fmt in resources if kind==3 and key==image_id)
            w,h,pixels=icon_dib(raw);filename=f'fonts-{name}-{size}.png';write(output/filename,w,h,pixels)
            rows.append({'source':'fontext.dll','type':'GROUP_ICON','id':ident,'image_id':image_id,'output':filename,'dimensions':[w,h],'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    for original,name in (('times.ttf','fonts-preview-serif.ttf'),('arial.ttf','fonts-source-arial.ttf'),('arialbd.ttf','fonts-source-arial-bold.ttf')):
        source=ROOT/'private/cabsets/windows95'/original;dest=output/name;dest.write_bytes(source.read_bytes())
        rows.append({'source':original,'type':'FONT','output':dest.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
    return rows
