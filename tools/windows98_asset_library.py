#!/usr/bin/env python3
"""Export version-separated Win98/Plus98 icon files and native PNG previews.

Original executables are read as data, never run. Full raw resources and loose
assets are separately retained by tools/resources.py. Unsupported PNG decoding
never removes the original multi-image ICO or the source resource.
"""
import argparse,hashlib,json,struct,sys,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from resources import extract
from pixels import write
from win95lx.assets.bitmap import icon_dib,word

def export(source,output,extensions=None):
    executable_extensions=set(extensions or ('.exe','.dll','.cpl','.drv','.fon','.scr','.ocx','.acm','.ax','.vbx'))
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);rows=[];bitmaps=[];loose=[];errors=[]
    for path in sorted(source.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(source)
        if extensions is None and path.suffix.lower() in ('.bmp','.gif','.jpg','.jpeg','.png','.ico','.cur','.ani','.wav','.rmi','.mid','.avi','.ttf','.fnt','.fon','.the','.theme','.thm'):
            dest=output/'loose'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
            loose.append({'source':str(relative),'file':str(dest.relative_to(output)),'sha256':hashlib.sha256(dest.read_bytes()).hexdigest()})
        if path.suffix.lower() not in executable_extensions:continue
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest()
        try:resources=list(extract(data))
        except (ValueError,struct.error,IndexError,UnicodeError) as error:
            errors.append({'source':str(relative),'error':str(error)});continue
        icons={(ident,lang):bits for kind,ident,lang,bits,fmt in resources if kind==3}
        for kind,ident,lang,bits,fmt in resources:
            if kind==2:
                try:
                    header=struct.unpack_from('<I',bits)[0]
                    if header==12:
                        bpp=struct.unpack_from('<H',bits,10)[0];colors=(1<<bpp) if bpp<=8 else 0;offset=14+header+colors*3
                    elif header>=40:
                        bpp=struct.unpack_from('<H',bits,14)[0];compression=struct.unpack_from('<I',bits,16)[0];colors=struct.unpack_from('<I',bits,32)[0] or ((1<<bpp) if bpp<=8 else 0)
                        offset=14+header+colors*4+(12 if header==40 and compression==3 else 16 if header==40 and compression==6 else 0)
                    else:raise ValueError('Unsupported bitmap header')
                    folder=output/relative/'bitmaps';folder.mkdir(parents=True,exist_ok=True)
                    bmp=folder/(str(ident).encode().hex()+'-'+str(lang).encode().hex()+'.bmp')
                    bmp.write_bytes(struct.pack('<2sIHHI',b'BM',14+len(bits),0,0,offset)+bits)
                    bitmaps.append({'source':str(relative),'source_sha256':digest,'identifier':ident,'language':lang,'bmp':str(bmp.relative_to(output)),'sha256':hashlib.sha256(bmp.read_bytes()).hexdigest()})
                except (ValueError,struct.error,IndexError) as error:errors.append({'source':str(relative),'bitmap':ident,'error':str(error)})
            if kind!=14:continue
            folder=output/relative/'icons';folder.mkdir(parents=True,exist_ok=True)
            name=str(ident).encode().hex()+'-'+str(lang).encode().hex();entries=[]
            try:
                count=word(bits,4)
                if len(bits)<6+count*14:raise ValueError('Truncated group icon')
                for index in range(count):
                    entry=bits[6+index*14:20+index*14];icon=icons.get((word(entry,12),lang))
                    if icon is None:icon=next((v for (i,l),v in icons.items() if i==word(entry,12)),None)
                    if icon is None:raise ValueError('Missing icon payload')
                    entries.append((entry,icon))
                offset=6+len(entries)*16;directory=bytearray(struct.pack('<HHH',0,1,len(entries)))
                for entry,icon in entries:
                    directory+=entry[:8]+struct.pack('<II',len(icon),offset);offset+=len(icon)
                ico=folder/(name+'.ico');ico.write_bytes(directory+b''.join(icon for entry,icon in entries))
                previews=[]
                for index,(entry,icon) in enumerate(entries):
                    try:
                        width,height,pixels=icon_dib(icon);png=folder/(name+f'-{index}-{width}x{height}.png');write(png,width,height,pixels);previews.append(str(png.relative_to(output)))
                    except (ValueError,struct.error,IndexError,ZeroDivisionError) as error:
                        errors.append({'source':str(relative),'group':ident,'image':index,'error':str(error),'original_ico_preserved':True})
                rows.append({'source':str(relative),'source_sha256':digest,'group':ident,'language':lang,'ico':str(ico.relative_to(output)),
                    'ico_sha256':hashlib.sha256(ico.read_bytes()).hexdigest(),'image_count':len(entries),'png_previews':previews})
            except (ValueError,struct.error,IndexError) as error:errors.append({'source':str(relative),'group':ident,'error':str(error)})
    report={'source':str(source.resolve()),'icons':rows,'errors':errors,'ico_files':len(rows),'png_previews':sum(len(r['png_previews']) for r in rows),'bitmap_files':len(bitmaps),'bitmaps':bitmaps,'loose_assets':loose,'loose_asset_files':len(loose)}
    (output/'inventory.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({key:report[key] for key in ('ico_files','png_previews','bitmap_files','loose_asset_files')}));return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--only-extensions',nargs='+',help='Optional executable suffix subset for a supplementary library');a=p.parse_args()
    if not a.output.resolve().is_relative_to((ROOT/'private').resolve()):p.error('Original assets must remain private.')
    export(a.source,a.output,a.only_extensions)
if __name__=='__main__':main()
