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
# Retain every original cursor size/scheme for the Mouse applet, without
# silently scaling the small artwork into a different native size.
for path in sorted(source.glob('*.cur')):
    cursor=path.read_bytes()
    offset=int.from_bytes(cursor[18:22],'little')
    width,height,pixels=icon_dib(cursor[offset:])
    name='pointer-'+path.stem
    write(output/(name+'.png'),width,height,pixels)
    (output/(name+'.json')).write_text(json.dumps({'hotspot':[word(cursor,10),word(cursor,12)],'source':path.name})+'\n')
    records.append({'source':path.name,'type':'CURSOR','output':name+'.png',
                    'sha256':hashlib.sha256(cursor).hexdigest(),'dimensions':[width,height]})
for path in sorted(source.glob('*.ani')):
    (output/path.name).write_bytes(path.read_bytes())
    records.append({'source':path.name,'type':'ANIMATED_CURSOR','output':path.name,
                    'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
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
    for size, suffix in ((16, ''), (32, '-32')):
        variants = [entry for entry in entries if entry[:2] == bytes((size, size))]
        entry = next((entry for entry in variants if word(entry, 6) == 4),
                     variants[0] if variants else None)
        if entry is None:
            continue
        image_id = word(entry, 12)
        data = next(data for kind, ident, _, data, _ in resources if kind == 3 and ident == image_id)
        w, h, pixels = icon_dib(data)
        name = f'accessory-{program}{suffix}.png'
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

from win95lx.control_panel.wallpaper import BITMAPS

for label, filename in BITMAPS.items():
    path = source / filename
    if path.is_file():
        data = path.read_bytes()
        name = f'wallpaper-{filename}'
        (output / name).write_bytes(data)
        records.append({'source': filename, 'type': 'WALLPAPER', 'label': label,
                        'output': name, 'sha256': hashlib.sha256(data).hexdigest()})

for state in ('clean', 'clouds'):
    path = captures / f'reference-background-{state}-v2.png'
    if path.is_file():
        width, height, pixels = read(path)
        if (width, height) != (800, 600):
            raise ValueError(f'Invalid Background reference size for {state}')
        w, h = 404, 448
        image = [pixel for row in range(h) for pixel in pixels[row*width:row*width+w]]
        name = f'background-frame-{state}.png'
        write(output/name, w, h, image)
        records.append({'source': 'Windows 95 Display Properties reference', 'type': 'SCREEN_CAPTURE_DIALOG',
                        'output': name, 'dimensions': [w, h], 'rectangle': [0, 0, w, h],
                        'reference_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

for state, rect in {
    'open': (96,131,426,263), 'save': (96,131,426,263), 'close': (270,245,266,126),
    'about': (126,163,348,283),
    'missing': (234,245,338,126), 'overwrite': (257,237,291,139),
}.items():
    path = captures/('native-notepad-about.png' if state == 'about' else f'native-notepad-{state}-dialog.png')
    if path.is_file():
        width, _, pixels = read(path)
        x, y, w, h = rect
        name = f'file-dialog-{state}.png'
        write(output/name, w, h, [pixel for row in range(y,y+h)
                                 for pixel in pixels[row*width+x:row*width+x+w]])
        records.append({'source': 'Windows 95 Notepad reference', 'type': 'SCREEN_CAPTURE_DIALOG',
                        'output': name, 'rectangle': list(rect), 'dimensions': [w,h],
                        'reference_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

file_controls = captures/'native-notepad-missing-dialog.png'
if file_controls.is_file():
    width, _, pixels = read(file_controls)
    for state, (x,y,w,h) in {'up': (389,157,23,22), 'folder': (179,159,17,17)}.items():
        name = f'file-dialog-{state}.png'
        write(output/name, w, h, [pixel for row in range(y,y+h)
                                 for pixel in pixels[row*width+x:row*width+x+w]])
        records.append({'source': 'Windows 95 Notepad Open reference', 'type': 'SCREEN_CAPTURE_CONTROL',
                        'output': name, 'rectangle': [x,y,w,h], 'dimensions': [w,h],
                        'reference_sha256': hashlib.sha256(file_controls.read_bytes()).hexdigest()})

wordpad_reference = captures/'reference-wordpad.png'
if wordpad_reference.is_file():
    width,_,pixels = read(wordpad_reference)
    controls = {'ruler': (114,213,592,23), 'family-field':(118,187,240,21),
                'size-field':(366,187,50,21),'left-active':(526,187,23,22), 'editor-top':(114,236,592,2)}
    for name,x in (('find',251),('cut',282),('copy',305),('paste',328),('undo',351)):
        controls['disabled-'+name]=(x,157,23,22)
    for control,(x,y,w,h) in controls.items():
        name = f'wordpad-native-{control}.png'
        write(output/name,w,h,[pixel for row in range(y,y+h) for pixel in pixels[row*width+x:row*width+x+w]])
        records.append({'source':'Windows 95 wordpad.exe reference','type':'SCREEN_CAPTURE_CONTROL',
                        'output':name,'dimensions':[w,h],'rectangle':[x,y,w,h],
                        'reference_sha256':hashlib.sha256(wordpad_reference.read_bytes()).hexdigest()})

pattern_reference = captures/'native-pattern-clean.png'
if pattern_reference.is_file():
    width,_,pixels = read(pattern_reference)
    x,y,w,h = 25,43,318,206
    name = 'desktop-pattern-dialog.png'
    write(output/name,w,h,[pixel for row in range(y,y+h) for pixel in pixels[row*width+x:row*width+x+w]])
    records.append({'source':'Windows 95 Pattern dialog','type':'SCREEN_CAPTURE_DIALOG','output':name,
                    'dimensions':[w,h],'rectangle':[x,y,w,h],'pointer_position':[400,300],
                    'reference_sha256':hashlib.sha256(pattern_reference.read_bytes()).hexdigest()})

checked_path = captures/'native-notepad-wordwrap-checked.png'
unchecked_path = captures/'native-notepad-wordwrap-unchecked.png'
if checked_path.is_file() and unchecked_path.is_file():
    width,height,pixels = read(checked_path)
    _,_,unchecked = read(unchecked_path)
    points = [(x,y) for y in range(230,251) for x in range(82,103)
              if pixels[y*width+x] != unchecked[y*width+x] and pixels[y*width+x][:3]==(0,0,0)]
    left,top = min(x for x,y in points),min(y for x,y in points)
    w,h = max(x for x,y in points)-left+1,max(y for x,y in points)-top+1
    image = [(0,0,0,255) if (left+x,top+y) in points else (0,0,0,0)
             for y in range(h) for x in range(w)]
    name = 'menu-check.png'
    write(output/name,w,h,image)
    records.append({'source':'Windows 95 Notepad Edit menu','type':'SCREEN_CAPTURE_CONTROL','output':name,
                    'dimensions':[w,h],'rectangle':[left,top,w,h],
                    'reference_sha256':hashlib.sha256(checked_path.read_bytes()).hexdigest()})

checkbox_reference = captures/'native-settings-checkbox.png'
if checkbox_reference.is_file():
    width, _, pixels = read(checkbox_reference)
    x,y,w,h = 90,446,13,13
    name = 'display-settings-checkbox-checked.png'
    write(output/name,w,h,[pixel for row in range(y,y+h) for pixel in pixels[row*width+x:row*width+x+w]])
    records.append({'source':'Windows 95 Display Properties checkbox', 'type':'SCREEN_CAPTURE_CONTROL',
                    'output':name, 'dimensions':[w,h], 'rectangle':[x,y,w,h],
                    'reference_sha256':hashlib.sha256(checkbox_reference.read_bytes()).hexdigest()})

settings_path = captures / 'native-settings-clean.png'
settings_idle_path = captures / 'reference-display-settings-native.png'
if settings_path.is_file() and settings_idle_path.is_file():
    width, height, pixels = read(settings_path)
    idle_width, idle_height, idle_pixels = read(settings_idle_path)
    if (width, height) != (800, 600) or (idle_width, idle_height) != (800, 600):
        raise ValueError('Unexpected Display Settings reference dimensions')
    x, y, w, h = 66, 66, 404, 448
    frame = [pixel for row in range(y, y+h) for pixel in pixels[row*width+x:row*width+x+w]]
    enabled = [pixel for row in range(415, 438) for pixel in frame[row*w+320:row*w+395]]
    write(output/'display-settings-apply.png', 75, 23, enabled)
    records.append({'source': 'Windows 95 Display Properties Settings reference',
                    'type': 'SCREEN_CAPTURE_BUTTON', 'output': 'display-settings-apply.png',
                    'rectangle': [x+320, y+415, 75, 23], 'dimensions': [75, 23],
                    'reference_sha256': hashlib.sha256(settings_path.read_bytes()).hexdigest()})
    # The clean capture has an unapplied wallpaper change. Use the idle Apply artwork.
    for row in range(415, 438):
        frame[row*w+320:row*w+395] = idle_pixels[row*idle_width+320:row*idle_width+395]
    name = 'display-settings.png'
    write(output/name, w, h, frame)
    records.append({'source': 'Windows 95 Display Properties Settings reference',
                    'type': 'SCREEN_CAPTURE_DIALOG', 'output': name, 'dimensions': [w, h],
                    'rectangle': [x, y, w, h],
                    'reference_sha256': hashlib.sha256(settings_path.read_bytes()).hexdigest(),
                    'idle_reference_sha256': hashlib.sha256(settings_idle_path.read_bytes()).hexdigest()})

path = captures / 'native-explorer-menu-clean.png'
if path.is_file():
    width, height, pixels = read(path)
    if (width, height) != (800, 600):
        raise ValueError('Unexpected Explorer reference size')
    for part, x, w in (('left', 4, 242), ('middle', 246, 1), ('right', 466, 42)):
        y, h = 22, 32
        data = [pixel for row in range(y, y+h)
                for pixel in pixels[row*width+x:row*width+x+w]]
        name = f'explorer-menu-{part}.png'
        write(output/name, w, h, data)
        records.append({'source': 'Windows 95 compact My Computer reference', 'type': 'SCREEN_CAPTURE_MENU',
                        'output': name, 'dimensions': [w, h], 'rectangle': [x, y, w, h],
                        'reference_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

path = captures/'native-independent-folders-compact.png'
mask_path = output/'shell32-group-4.png'
if path.is_file() and mask_path.is_file():
    width, _, pixels = read(path)
    w,h,mask = read(mask_path)
    x,y = 49,77
    image = [pixels[(y+row)*width+x+col][:3]+(mask[row*w+col][3],)
             for row in range(h) for col in range(w)]
    name = 'explorer-folder-32.png'
    write(output/name,w,h,image)
    records.append({'source': 'Windows 95 IE4 compact folder reference',
                    'type': 'SCREEN_CAPTURE_ICON', 'output': name, 'dimensions': [w,h],
                    'rectangle': [x,y,w,h], 'alpha_mask': mask_path.name,
                    'reference_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

# Preserve original named 8x8 desktop patterns from Setup's control.ini entries.
import re
shell_inf = (source/'shell.inf').read_text(encoding='cp1252')
strings = dict(re.findall(r'^([A-Za-z]+Desc)\s*=\s*"([^"]+)"',shell_inf,re.M))
patterns = {}
for key,values in re.findall(r'control.ini,Patterns,,"%([A-Za-z]+Desc)%=([0-9 ]+)"',shell_inf):
    rows = [int(value) for value in values.split()]
    if len(rows)==8:
        patterns[strings.get(key,key)] = rows
name = 'desktop-patterns.json'
(output/name).write_text(json.dumps(patterns,indent=2)+'\n')
records.append({'source':'shell.inf','type':'DESKTOP_PATTERNS','output':name,
                'sha256':hashlib.sha256((source/'shell.inf').read_bytes()).hexdigest()})

left_hover = captures/'native-drop-hover-86-94.png'
right_hover = captures/'native-drop-hover-42-94.png'
mask_path = output/'shell32-group-4.png'
if left_hover.is_file() and right_hover.is_file() and mask_path.is_file():
    width,_,left_pixels = read(left_hover)
    _,_,right_pixels = read(right_hover)
    w,h,mask = read(mask_path)
    x,y = 49,77
    selected = [(left_pixels if column<16 else right_pixels)[(y+row)*width+x+column][:3]+
                (mask[row*w+column][3],) for row in range(h) for column in range(w)]
    name = 'explorer-folder-selected-32.png'
    write(output/name,w,h,selected)
    records.append({'source':'Windows 95 folder drop highlight','type':'SCREEN_CAPTURE_ICON','output':name,
                    'dimensions':[w,h],'rectangle':[x,y,w,h],
                    'references':[{'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                                  for path in (left_hover,right_hover)],'alpha_mask':mask_path.name})

user_resources = list(extract((source/'user.exe').read_bytes()))
user_icons = {ident:data for kind,ident,lang,data,fmt in user_resources if kind==3}
for kind,ident,lang,data,fmt in user_resources:
    if kind != 14 or ident not in (101,102,103,104):
        continue
    entry = next(data[offset:offset+14] for offset in range(6,6+14*word(data,4),14)
                 if data[offset:offset+2] == bytes((32,32)) and word(data,offset+6)==4)
    dib = user_icons[word(entry,12)]
    width,height,image = icon_dib(dib)
    name = f'message-icon-{ident}.png'
    write(output/name,width,height,image)
    records.append({'source':'user.exe','type':'GROUP_ICON','id':ident,'output':name,
                    'dimensions':[width,height],'sha256':hashlib.sha256(dib).hexdigest()})

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
# Original IE4 Explorer controls; independently captured with the pointer outside artwork.
full_explorer = captures/'native-computer-web-full.png'
if full_explorer.is_file():
    width,_,pixels = read(full_explorer)
    parts = {'web-computer':(4,118,85,85), 'web-heading':(110,136,160,25), 'web-description':(20,218,165,32), 'file-pressed':(11,22,32,19),
             'toolbar-grip':(0,42,8,46), 'toolbar-end':(630,42,1,46), 'address-left':(0,88,76,26),
             'address-middle':(150,88,1,26), 'address-right':(776,88,24,26), 'toolbar-right':(798,42,2,46),
             'toolbar-top-right':(758,42,42,1), 'toolbar-bottom-right':(793,87,7,1)}
    for label,left,right in (('back',8,75),('forward',75,144),('up',144,204),
                             ('cut',204,262),('copy',262,316),('paste',316,374),
                             ('undo',374,435),('delete',435,493),
                             ('properties',493,553),('views',553,630)):
        parts['toolbar-'+label]=(left,42,right-left,46)
    for label,(x,y,w,h) in parts.items():
        name='explorer-'+label+'.png'
        write(output/name,w,h,[pixel for row in range(y,y+h) for pixel in pixels[row*width+x:row*width+x+w]])
        records.append({'source':'Windows 95 IE4 My Computer','type':'SCREEN_CAPTURE_CONTROL',
                        'output':name,'rectangle':[x,y,w,h],
                        'reference_sha256':hashlib.sha256(full_explorer.read_bytes()).hexdigest()})

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
control_reference=captures/'native-control-web-header.png'
if control_reference.is_file():
    width,_,pixels=read(control_reference)
    for name,(x,y,w,h) in {'control-web-computer':(4,118,85,85),'control-web-heading':(110,136,180,25),
                          'control-toolbar-back':(8,42,67,46),'control-toolbar-up':(144,42,60,46)}.items():
        filename='explorer-'+name+'.png'
        write(output/filename,w,h,[v for row in range(y,y+h) for v in pixels[row*width+x:row*width+x+w]])
        records.append({'source':'installed IE4 Control Panel','type':'SCREEN_CAPTURE_CONTROL','output':filename,
                        'rectangle':[x,y,w,h],'reference_sha256':hashlib.sha256(control_reference.read_bytes()).hexdigest()})
for filename in ('webview-strings.json','webview-verdana-regular.json','webview-verdana-bold.json'):
    path=output/filename
    if path.is_file():
        data=json.loads(path.read_text())
        records.append({'source':'installed OSR2.5 IE4 reference','type':'WEBVIEW_METADATA' if filename=='webview-strings.json' else 'FONT',
                        'output':filename,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                        'original_sources':data.get('sources',data.get('source_sha256'))})
mouse_resources=list(extract((source/'main.cpl').read_bytes()))
group=next(data for kind,ident,lang,data,fmt in mouse_resources if kind==14 and ident==100)
image_id=word(group[6:20],12)
mouse_bits=next(data for kind,ident,lang,data,fmt in mouse_resources if kind==3 and ident==image_id)
w,h,pixels=icon_dib(mouse_bits);write(output/'mouse-icon.png',w,h,pixels)
write(output/'mouse-icon-small.png',16,16,[pixels[(yy*2)*w+xx*2] for yy in range(16) for xx in range(16)])
records.append({'source':'main.cpl','type':'DERIVED_ICON','id':100,'output':'mouse-icon-small.png','transform':'32-to-16 nearest-neighbor','sha256':hashlib.sha256(mouse_bits).hexdigest()})
records.append({'source':'main.cpl','type':'GROUP_ICON','id':100,'image_id':image_id,'output':'mouse-icon.png','sha256':hashlib.sha256(mouse_bits).hexdigest(),'dimensions':[w,h]})
for name,reference,rect in (
    ('buttons','native-mouse-buttons-clean.png',(44,44,404,448)),
    ('pointers','native-mouse-pointers-probe.png',(0,0,404,448)),
    ('motion','native-mouse-motion-probe.png',(0,0,404,448)),
    ('general','native-mouse-general-probe.png',(0,0,404,448))):
    source_path=ROOT/'private/screenshots/start-development-20261110'/reference
    if source_path.is_file():
        sw,sh,pixels=read(source_path);x,y,w,h=rect
        write(output/f'mouse-{name}-frame.png',w,h,[pixels[(y+yy)*sw+x+xx] for yy in range(h) for xx in range(w)])
        records.append({'source':reference,'type':'SCREEN_CAPTURE_CONTROL','output':f'mouse-{name}-frame.png',
                        'rectangle':rect,'reference_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest()})
from stage_mouse_animation import main as stage_mouse_animation
stage_mouse_animation()
for path in sorted(output.glob('mouse-test-*')):
    records.append({'source':'MAIN.CPL AVI 100','type':'ANIMATION_FRAME','output':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
from stage_pointer_schemes import main as stage_pointer_schemes
stage_pointer_schemes()
pointer_catalog=json.loads((output/'pointer-schemes.json').read_text())
for key,definition in pointer_catalog['assets'].items():
    for frame in definition['frames']:
        for filename in (frame['file'],str(Path(frame['file']).with_suffix('.json'))):
            records.append({'source':definition['source'],'type':'CURSOR_FRAME','output':filename,
                            'source_sha256':definition['source_sha256'],'sha256':hashlib.sha256((output/filename).read_bytes()).hexdigest()})
from stage_control_panel_assets import stage as stage_control_panel_assets
records.extend(stage_control_panel_assets(output))
from stage_multimedia_assets import stage as stage_multimedia_assets
records.extend(stage_multimedia_assets(output))
from stage_sound_library import stage as stage_sound_library
records.extend(stage_sound_library(output))
from stage_command_button_assets import stage as stage_command_button_assets
records.extend(stage_command_button_assets(output))
from stage_accessibility_assets import stage as stage_accessibility_assets
records.extend(stage_accessibility_assets(output))
from stage_namespace_drop_assets import stage as stage_namespace_drop_assets
records.extend(stage_namespace_drop_assets(output))
from stage_printers_assets import stage as stage_printers_assets
records.extend(stage_printers_assets(output))
from stage_theme_assets import stage as stage_theme_assets
records.extend(stage_theme_assets(output))
from stage_theme_icons import stage as stage_theme_icons
records.extend(stage_theme_icons(output))
from stage_theme_appearance import stage as stage_theme_appearance
records.extend(stage_theme_appearance(output))
from stage_theme_customization_assets import stage as stage_theme_customization_assets
records.extend(stage_theme_customization_assets(output))
from stage_screen_saver_ui import stage as stage_screen_saver_ui
records.extend(stage_screen_saver_ui(output))
from stage_screensaver_assets import stage_bundle as stage_screensaver_bundle
saver_catalog=stage_screensaver_bundle(output/'screensavers')
for profile,definition in saver_catalog.get('font_profiles',{}).items():
    for filename,digest in definition['files'].items():
        records.append({'source':'private/cabsets/windows95/'+filename,'type':'SCREENSAVER_FONT_PROFILE',
                        'profile':profile,'output':'screensavers/'+definition['directory']+'/'+filename,
                        'sha256':digest})
for identity,presentation in saver_catalog['presentations'].items():
    for entry in presentation['provenance']:
        records.append({'source':entry['source'],'type':'SCREENSAVER_PACKAGE',
                        'presentation':identity,'output':'screensavers/'+presentation['directory']+'/'+entry['installed'],
                        'sha256':entry['sha256']})
records.append({'source':'original Windows95 and Plus95 private assets','type':'SCREENSAVER_CATALOG',
                'output':'screensavers/catalog.json',
                'sha256':hashlib.sha256((output/'screensavers/catalog.json').read_bytes()).hexdigest()})
theme_library=json.loads((output/'themes-library.json').read_text())
descriptions=json.loads((output/'cpl-descriptions.json').read_text())
descriptions['Desktop Themes']=theme_library['description']
(output/'cpl-descriptions.json').write_text(json.dumps(descriptions,indent=2)+'\n')
records.append({'source':'private/cabsets/plus95/THEMES.CPL','type':'STRING','id':3,
                'output':'cpl-descriptions.json','source_sha256':hashlib.sha256((ROOT/'private/cabsets/plus95/THEMES.CPL').read_bytes()).hexdigest()})
from stage_fonts_assets import stage as stage_fonts_assets
records.extend(stage_fonts_assets(output))
from collect_font_library import collect as collect_font_library
font_library=collect_font_library(output/'font-library')
for row in font_library['fonts']:
    records.append({'source':row['source'],'profile':row['product'],'type':'FONT_COLLECTION','output':'font-library/'+row['file'],'source_sha256':row['sha256'],'faces':len(row['faces']),'readable':row['readable']})
records.append({'source':'original Windows95 and Plus95 private assets','type':'CURSOR_CATALOG','output':'pointer-schemes.json',
                'sha256':hashlib.sha256((output/'pointer-schemes.json').read_bytes()).hexdigest()})
(output/'manifest.json').write_text(json.dumps({'assets':records,'original_media_sha256':'c13b6bad0dcbd4f13c3d840d2b7efe939c6d4e40b1c63f086a5f92edfb1e9b77'},indent=2)+'\n');print('Prepared',len(records),'private assets')
