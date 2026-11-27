#!/usr/bin/env python3
"""Configured Plus reference icon overrides: independent, never autoloaded."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    import cairo
    from resources import extract
    from win95lx.assets.bitmap import icon_dib,BitmapFont
    from win95lx.shell.widgets import Painter
    from win95lx.shell.icon_labels import draw_icon_label
    from pixels import read,write
    from check_shortcut_visuals import LONG_TEXT
    library=ROOT/'private/cabsets/plus95/COOL.DLL';resources=list(extract(library.read_bytes()));font=BitmapFont((ROOT/'private/shell-assets/ms-sans-serif-8.fnt').read_bytes());overlay=cairo.ImageSurface.create_from_png(str(ROOT/'private/shell-assets/shell32-group-30.png'));records=[];comparisons=[];refs=[]
    cases=[('drive',1,6,75,77,'W95UAT Drive'),('folder',12,72,75,227,'W95UAT Folder'),('control',None,36,0,452,'W95UAT Control Panel'),('file',None,152,75,152,'W95UAT File')]
    for name,group,ident,cellx,y,text in cases:
        if group is not None:
            raw=next(data for kind,key,lang,data,fmt in resources if kind==3 and key==ident);w,h,pixels=icon_dib(raw);write(args.output/(name+'-source.png'),w,h,pixels);base=cairo.ImageSurface.create_from_png(str(args.output/(name+'-source.png')));records.append({'source':'COOL.DLL','group':group,'image':ident,'bits':4,'size':[w,h],'source_sha256':hashlib.sha256(library.read_bytes()).hexdigest()})
        else:base=cairo.ImageSurface.create_from_png(str(ROOT/f'private/shell-assets/shell32-group-{ident}.png'))
        for selected in(False,True):
            ref=ROOT/'private/screenshots'/('shortcut-plus-'+name+'-selected-20261127.png'if selected else'shortcut-plus-neutral-20261127.png');refs.append(ref);nw,nh,native=read(ref);surface=cairo.ImageSurface(cairo.FORMAT_RGB24,75,75);p=Painter(cairo.Context(surface),font);p.fill(0,0,75,75,(0,128,128))
            if selected:p.selected_image(base,21,0)
            else:p.image(base,21,0)
            p.image(overlay,21,0);draw_icon_label(p,text,37,36,desktop=True,selected=selected,focused=selected)
            namepart=name+('-selected'if selected else'-normal');path=args.output/(namepart+'.png');surface.write_to_png(str(path));_,_,actual=read(path);expected=[native[(y+yy)*nw+cellx+xx]for yy in range(75)for xx in range(75)];write(args.output/(namepart+'-native.png'),75,75,expected);difference=sum(a!=b for a,b in zip(actual,expected));assert difference==0,(namepart,difference);comparisons.append({'name':namepart,'differing_pixels':difference,'native_rect':[cellx,y,75,75]})
    base=cairo.ImageSurface.create_from_png(str(ROOT/'private/shell-assets/shell32-group-152.png'))
    for mode,selected,active,file in [('normal',False,True,'shortcut-plus-neutral'),('selected',True,True,'shortcut-plus-long-selected'),('inactive',True,False,'shortcut-plus-long-inactive')]:
        ref=ROOT/'private/screenshots'/(file+'-20261127.png');refs.append(ref);nw,nh,native=read(ref);surface=cairo.ImageSurface(cairo.FORMAT_RGB24,75,150);p=Painter(cairo.Context(surface),font);p.fill(0,0,75,150,(0,128,128))
        if selected and active:p.selected_image(base,21,0)
        else:p.image(base,21,0)
        p.image(overlay,21,0);metrics=draw_icon_label(p,LONG_TEXT,37,36,desktop=True,selected=selected,focused=selected,active=active);path=args.output/('long-'+mode+'.png');surface.write_to_png(str(path));_,_,actual=read(path);expected=[native[(377+yy)*nw+75+xx]for yy in range(150)for xx in range(75)];difference=sum(a!=b for a,b in zip(actual,expected));assert difference==0,('long',mode,difference);comparisons.append({'name':'long-'+mode,'differing_pixels':difference,'lines':len(metrics['lines'])})
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),list(set(refs))),'profile':'Configured Plus reference, explicit COOL.DLL Shell Icons overrides; not all Plus installations','comparisons':comparisons,'private_assets':records,'registry_sha256':hashlib.sha256((ROOT/'private/reference-tools/shortcut-visual-20261127/plus-registry.json').read_bytes()).hexdigest(),'failed':0,'scope':'Component profile only; no product preset registered or asset autoload. No16px acceptance.'};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
