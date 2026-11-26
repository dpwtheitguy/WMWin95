#!/usr/bin/env python3
"""Stage original IE4 template metadata and mono Verdana from a private reference extract."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from resources import extract

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=ROOT/'private/webview-research');p.add_argument('--output',type=Path,default=ROOT/'private/shell-assets');a=p.parse_args()
    from PIL import Image,ImageDraw,ImageFont
    a.output.mkdir(parents=True,exist_ok=True)
    templates={};sources={}
    for name in ('mycomp','folder','controlp','printers'):
        path=a.source/(name+'.htt');data=path.read_bytes();text=data.decode('cp1252')
        templates[name]={'strings':dict(re.findall(r'var\s+(L_\w+)\s*=\s*"([^"]*)"',text)),
                         'source_sha256':hashlib.sha256(data).hexdigest()}
        sources[name+'.htt']=hashlib.sha256(data).hexdigest()
    dll=a.source/'shell32-installed.dll';sources[dll.name]=hashlib.sha256(dll.read_bytes()).hexdigest()
    inf=next(d for t,i,l,d,f in extract(dll.read_bytes()) if t=='REGINST' and i=='REGINST').decode('cp1252')
    tips={name:value for name,value in re.findall(r'^(\w+_IT)\s*=\s*"([^"]*)"',inf,re.M)}
    (a.output/'webview-strings.json').write_text(json.dumps({'templates':templates,'infotips':tips,'sources':sources},indent=2)+'\n')
    for weight,filename in (('regular','verdana.ttf'),('bold','verdanab.ttf')):
        path=a.source/filename;f=ImageFont.truetype(str(path),11,layout_engine=ImageFont.Layout.BASIC)
        glyphs={}
        for code in range(32,256):
            char=bytes([code]).decode('cp1252',errors='replace')
            advance=round(f.getlength(char,mode="1"));im=Image.new('1',(max(advance+3,18),16),1)
            ImageDraw.Draw(im).text((0,0),char,font=f,fill=0)
            points=[(x,y) for y in range(16) for x in range(im.width) if not im.getpixel((x,y))]
            glyphs[char]=[advance,points]
        (a.output/f'webview-verdana-{weight}.json').write_text(json.dumps({'height':13,'glyphs':glyphs,'source':filename,'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pixel_size':11,'raster':'FreeType monochrome BASIC'}))
    print(json.dumps({'templates':len(templates),'infotips':len(tips),'font_weights':2}))
if __name__=='__main__':main()
