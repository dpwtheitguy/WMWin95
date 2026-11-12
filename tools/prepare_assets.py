#!/usr/bin/env python3
"""Build a private, provenance-preserving shell asset bundle from original media."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src')); sys.path.insert(0,str(ROOT/'tools'))
from resources import extract
from pixels import read,write
from win95lx.assets.bitmap import BitmapFont,icon_dib,rle4_bitmap,word
source=ROOT/'private/cabsets/windows95'; output=ROOT/'private/shell-assets'; output.mkdir(parents=True,exist_ok=True); records=[]
for kind,ident,lang,data,fmt in extract((source/'sserife.fon').read_bytes()):
    if kind==8:
        font=BitmapFont(data)
        if font.points==8:
            dest=output/'ms-sans-serif-8.fnt'; dest.write_bytes(data); records.append({'source':'sserife.fon','type':'FONT','id':ident,'output':dest.name,'sha256':hashlib.sha256(data).hexdigest(),'face':font.face,'height':font.height}); break
for name in ('arrow', 'beam', 'busy', 'cross', 'help', 'move', 'no', 'size1', 'size2', 'size3', 'size4', 'up', 'wait'):
    filename = f'{name}_1.cur'
    cursor = (source / filename).read_bytes()
    offset = int.from_bytes(cursor[18:22], 'little')
    width, height, pixels = icon_dib(cursor[offset:])
    write(output / f'{name}.png', width, height, pixels)
    (output / f'{name}-cursor.json').write_text(json.dumps({
        'hotspot': [word(cursor, 10), word(cursor, 12)], 'source': filename,
    }) + '\n')
    records.append({'source': filename, 'type': 'CURSOR', 'output': f'{name}.png',
                    'sha256': hashlib.sha256(cursor).hexdigest(), 'dimensions': [width, height]})
startup = source / 'mssound.wav'
if startup.is_file():
    data = startup.read_bytes()
    (output / 'startup.wav').write_bytes(data)
    records.append({'source': startup.name, 'type': 'WAVE', 'output': 'startup.wav',
                    'sha256': hashlib.sha256(data).hexdigest()})
all_resources=list(extract((source/'shell32.dll').read_bytes())); icons={ident:data for kind,ident,lang,data,fmt in all_resources if kind==3}; previews=[]
for kind,ident,lang,data,fmt in all_resources:
    if kind!=14:continue
    entries=[data[6+i*14:20+i*14] for i in range(word(data,4))]
    if ident==36:
        small=next((entry for entry in entries if entry[:2]==bytes((16,16)) and word(entry,6)==4),None)
        if small is not None:
            image_id=word(small,12)
            sw,sh,sp=icon_dib(icons[image_id])
            name=f'shell32-small-{ident}.png'
            write(output/name,sw,sh,sp)
            records.append({'source':'shell32.dll','type':'GROUP_ICON','id':ident,'image_id':image_id,'output':name,'sha256':hashlib.sha256(icons[image_id]).hexdigest(),'dimensions':[sw,sh]})
    chosen=next((e for e in entries if e[0]==32 and e[1]==32 and word(e,6)==4),None)
    if chosen is None:chosen=next((e for e in entries if e[0]==32 and e[1]==32),None)
    if chosen is None:continue
    icon_id=word(chosen,12)
    try:w,h,pixels=icon_dib(icons[icon_id])
    except ValueError:continue
    name=f'shell32-group-{ident}.png';write(output/name,w,h,pixels); records.append({'source':'shell32.dll','type':'GROUP_ICON','id':ident,'image_id':icon_id,'output':name,'sha256':hashlib.sha256(icons[icon_id]).hexdigest(),'dimensions':[w,h]}); previews.append((ident,w,h,pixels))
# Explorer's Start flag is an opaque DIB. Wrap it in an all-opaque
# icon mask so the shared decoder can read the original 16-color bitmap.
flag=next(data for kind,ident,lang,data,fmt in extract((source/'explorer.exe').read_bytes()) if kind==2 and ident==143)
flag_dib=bytearray(flag)
struct.pack_into('<i',flag_dib,8,32)
flag_width,flag_height,flag_pixels=icon_dib(flag_dib+bytes(64))
# The 256-color reference maps this palette entry to bright blue.
flag_pixels=[(0,0,255,alpha) if (red,green,blue)==(0,0,191) else (red,green,blue,alpha)
             for red,green,blue,alpha in flag_pixels]
write(output/'start-flag.png',flag_width,flag_height,flag_pixels)
records.append({'source':'explorer.exe','type':'BITMAP','id':143,'output':'start-flag.png','sha256':hashlib.sha256(flag).hexdigest(),'dimensions':[flag_width,flag_height],'palette_mapping':{'0000bf':'0000ff'}})
explorer_resources=list(extract((source/'explorer.exe').read_bytes()))
banner=next(data for kind,ident,lang,data,fmt in explorer_resources if kind==2 and ident==157)
w,h,pixels=rle4_bitmap(banner)
write(output/'start-banner.png',w,h,pixels)
records.append({'source':'explorer.exe','type':'BITMAP','id':157,'output':'start-banner.png','sha256':hashlib.sha256(banner).hexdigest(),'dimensions':[w,h]})
computer_group=next(data for kind,ident,lang,data,fmt in explorer_resources if kind==14 and ident==100)
for size in (16,32):
    variants=[computer_group[i:i+14] for i in range(6,6+14*word(computer_group,4),14)]
    entry=next(e for e in variants if e[:2]==bytes((size,size)) and word(e,6)==4)
    image_id=word(entry,12)
    data=next(data for kind,ident,lang,data,fmt in explorer_resources if kind==3 and ident==image_id)
    w,h,pixels=icon_dib(data)
    name=f'my-computer-{size}.png'
    write(output/name,w,h,pixels)
    records.append({'source':'explorer.exe','type':'GROUP_ICON','id':100,'image_id':image_id,'output':name,'sha256':hashlib.sha256(data).hexdigest(),'dimensions':[w,h]})

for program, group_id in (('notepad', 2), ('wordpad', 154), ('calc', 'SC'), ('winmine', 100)):
    filename = f'{program}.exe'
    resources = list(extract((source / filename).read_bytes()))
    group = next(data for kind, ident, _, data, _ in resources if kind == 14 and ident == group_id)
    entries = [group[i:i+14] for i in range(6, 6 + 14 * word(group, 4), 14)]
    entry = next(entry for entry in entries if entry[:2] == bytes((16, 16)))
    image_id = word(entry, 12)
    data = next(data for kind, ident, _, data, _ in resources if kind == 3 and ident == image_id)
    w, h, pixels = icon_dib(data)
    name = f'accessory-{program}.png'
    write(output / name, w, h, pixels)
    records.append({'source': filename, 'type': 'GROUP_ICON', 'id': group_id,
                    'image_id': image_id, 'output': name,
                    'sha256': hashlib.sha256(data).hexdigest(), 'dimensions': [w, h]})

# Desktop Update replaces these three menu icons. Recover their masks from
# two native captures of the same row against gray and selected blue.
reference=ROOT/'private/screenshots/interactive-20261110/original-start-programs-800.png'
captures=ROOT/'private/screenshots/start-development-20261110'
if reference.is_file():
    width,_,unselected=read(reference)
    for label,y in (('favorites',278),('settings',350),('find',386)):
        selected_path=captures/f'reference-{label}.png'
        if not selected_path.is_file():
            continue
        selected_width,_,selected=read(selected_path)
        if width!=800 or selected_width!=width or selected[(y+15)*width+26][:3]!=(0,0,128):
            raise ValueError(f'Invalid selected reference row for {label}')
        pixels=[]
        for yy in range(y,y+32):
            for x in range(31,63):
                index=yy*width+x
                pixel=unselected[index]
                if pixel!=selected[index]:
                    if pixel[:3]!=(192,192,192) or selected[index][:3]!=(0,0,128):
                        raise ValueError(f'Unexpected selection color in {label} icon')
                    pixel=(0,0,0,0)
                pixels.append(pixel)
        name=f'start-{label}.png'
        write(output/name,32,32,pixels)
        records.append({'source':'Windows 95 Desktop Update reference','type':'SCREEN_CAPTURE_ICON','output':name,'dimensions':[32,32],'rectangle':[31,y,32,32],'unselected_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),'selected_sha256':hashlib.sha256(selected_path.read_bytes()).hexdigest()})
# The fixed Start button face uses the original two rendered states.
for state,capture in (('up','original-clean-800.png'),('down','original-start-programs-800.png')):
    path=reference.with_name(capture)
    if path.is_file():
        width,height,pixels=read(path)
        if (width,height)!=(800,600):
            raise ValueError(f'Invalid reference size for Start button {state}')
        button=[pixels[y*width+x] for y in range(576,598) for x in range(2,56)]
        name=f'start-button-{state}.png'
        write(output/name,54,22,button)
        records.append({'source':'Windows 95 Desktop Update reference','type':'SCREEN_CAPTURE_BUTTON','output':name,'dimensions':[54,22],'rectangle':[2,576,54,22],'reference_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
for state in ('poweroff', 'reboot', 'dos'):
    path = captures / f'reference-shutdown-{state}.png'
    if path.is_file():
        width, height, pixels = read(path)
        if (width, height) != (800, 600):
            raise ValueError(f'Invalid shutdown reference size for {state}')
        x, y, w, h = 238, 160, 322, 172
        crop = [pixel for row in range(y, y+h)
                for pixel in pixels[row*width+x:row*width+x+w]]
        name = f'shutdown-{state}.png'
        write(output/name, w, h, crop)
        records.append({'source': 'Windows 95 Desktop Update reference', 'type': 'SCREEN_CAPTURE_DIALOG',
                        'output': name, 'dimensions': [w, h], 'rectangle': [x, y, w, h],
                        'reference_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

# Display Properties uses the Control Panel applet icon, not a folder icon.
applet_resources=list(extract((source/'desk.cpl').read_bytes()))
applet_images={ident:data for kind,ident,lang,data,fmt in applet_resources if kind==3}
group=next(data for kind,ident,lang,data,fmt in applet_resources if kind==14 and ident==100)
variants=[group[i:i+14] for i in range(6,6+14*word(group,4),14)]
display=next(entry for entry in variants if entry[:2]==bytes((32,32)) and word(entry,6)==4)
image_id=word(display,12)
data=applet_images[image_id]
w,h,pixels=icon_dib(data)
write(output/'display-applet.png',w,h,pixels)
records.append({'source':'desk.cpl','type':'GROUP_ICON','id':100,'image_id':image_id,'output':'display-applet.png','sha256':hashlib.sha256(data).hexdigest(),'dimensions':[w,h]})
font=BitmapFont((output/'ms-sans-serif-8.fnt').read_bytes()); cols=12; cellw=64; cellh=54; width=cols*cellw; height=((len(previews)+cols-1)//cols)*cellh; canvas=[(192,192,192,255)]*(width*height)
for index,(ident,w,h,pixels) in enumerate(previews):
    x=(index%cols)*cellw+16; y=(index//cols)*cellh+2
    for yy in range(h):
        for xx in range(w):
            px=pixels[yy*w+xx]
            if px[3]:canvas[(y+yy)*width+x+xx]=px
    tx=x
    for c in str(ident):
        advance,points=font.glyph(c)
        for xx,yy in points:canvas[(y+34+yy)*width+tx+xx]=(0,0,0,255)
        tx+=advance
write(output/'contact-sheet.png',width,height,canvas)
(output/'manifest.json').write_text(json.dumps({'assets':records,'original_media_sha256':'c13b6bad0dcbd4f13c3d840d2b7efe939c6d4e40b1c63f086a5f92edfb1e9b77'},indent=2)+'\n');print('Prepared',len(records),'private assets')
