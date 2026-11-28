"""Stage private Plus95 theme wallpaper and measured native dialog evidence."""
import hashlib
import json
import re
import sys
import struct
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from win95lx.control_panel.theme_preferences import installed_names,native_256_component,original_screensaver


def stage(output):
    import cairo
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    source = ROOT/'private/cabsets/plus95'
    inf = ROOT/'private/reference/media/plus/PLUS.INF'
    names = installed_names(inf.read_text(encoding='cp1252'))
    labels = {short.casefold(): Path(long).stem for short, long in re.findall(
        r'([\w~]+\.THM)<([^>]+)>', inf.read_text(encoding='cp1252'), re.I)}
    catalog = {}; records = []
    for theme in sorted(source.glob('*.THM')):
        if theme.name == 'DEFAULT.THM': continue
        text = theme.read_text(encoding='cp1252')
        section = re.search(r'(?im)^\[Control Panel\\Desktop\]\s*\n([^\[]*)', text)
        if not section: raise ValueError('Missing desktop component: ' + theme.name)
        wallpaper = re.search(r'(?im)^Wallpaper=%ThemeDir%([^\r\n]+)', section.group(1))
        if not wallpaper: raise ValueError('Missing theme wallpaper: ' + theme.name)
        original = source/names[wallpaper.group(1).casefold()]
        dest = 'theme-wallpaper-' + original.name.lower()
        (output/dest).write_bytes(original.read_bytes())
        label = labels[theme.name.casefold()]
        catalog[label] = {'wallpaper': {'file': dest, 'mode': 'tile' if re.search(r'(?im)^TileWallpaper=1\s*$', section.group(1)) else 'center'},
                          'pointers': 'Plus! / ' + label, 'sounds': 'Plus! / ' + label}
        saver=original_screensaver(theme)
        if saver is not None:catalog[label]['screensaver']=saver
        records.append({'source': str(theme.relative_to(ROOT)), 'sha256': hashlib.sha256(theme.read_bytes()).hexdigest(),
                        'wallpaper_source': str(original.relative_to(ROOT)), 'wallpaper_sha256': hashlib.sha256(original.read_bytes()).hexdigest(), 'output': dest})
    # Original THEMES.EXE conversion output, independently exported from the
    # prepared Plus8bpp reference. Preserve JPEG source and native raster apart.
    native_root=ROOT/'private/reference-tools/themes-batch-export-v2-20261127/W95THM2'
    log=native_root/'CATALOG.TXT';lines=log.read_text(encoding='cp1252').splitlines()
    if lines[0].strip()!='bits=8 width=800 height=600':raise ValueError('Native theme conversion profile changed.')
    native={}
    for line in lines[1:]:
        index,label,source_path,dest,success=line.split('\t')
        if success.strip()!='1':continue
        original=native_root/('T'+index.zfill(2)+'.BMP')
        raw=original.read_bytes()
        if struct.unpack_from('<IiiHHI',raw,14)!=(40,800,600,1,8,0):raise ValueError('Unexpected native theme bitmap.')
        key=label.casefold()
        if key in native and native[key].read_bytes()!=raw:raise ValueError('Ambiguous repeated native conversion.')
        native[key]=original
    for label,theme in catalog.items():
        original=native.get(label.casefold())
        if original is None:raise ValueError('Missing native converted wallpaper: '+label)
        filename='theme-native-800x600-8-'+original.name.lower()
        (output/filename).write_bytes(original.read_bytes())
        # QEMU8.2's original VGA DAC expands six-bit components by repeating
        # the low bit (vga_int.h c6_to_8), not by rescaling 0..63 to 0..255.
        # Keep the Windows logical-palette BMP alongside this named physical
        # framebuffer-profile derivative; no screenshot pixels supply artwork.
        physical=bytearray(original.read_bytes())
        for offset in range(54,54+256*4,4):
            for channel in range(3):
                physical[offset+channel]=native_256_component(physical[offset+channel])
        physical_filename=filename[:-4]+'-vga6.bmp'
        (output/physical_filename).write_bytes(physical)
        theme['wallpaper']['native_256']={'file':physical_filename,'logical_file':filename,'profile':'plus-ie4-800x600-8bpp-qemu-vga6','width':800,'height':600}
        records.append({'source':str(original.relative_to(ROOT)), 'sha256':hashlib.sha256(original.read_bytes()).hexdigest(), 'output':physical_filename,'type':'DERIVED_VGA6_PALETTE','profile':'plus-ie4-800x600-8bpp-qemu-vga6','algorithm_source':'https://github.com/qemu/qemu/blob/v8.2.2/hw/display/vga_int.h#L146-L152','scope':'Only logical palette→six-bit physical DAC expansion; bitmap indices/layout unchanged. Not a reference baseline.'})
        records.append({'source':str(original.relative_to(ROOT)), 'sha256':hashlib.sha256(original.read_bytes()).hexdigest(), 'output':filename,'type':'NATIVE_THEME_CONVERSION','profile':'plus-ie4-800x600-8bpp','original_source':theme['wallpaper']['file'],'metadata_source':str(log.relative_to(ROOT)),'metadata_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'scope':'Generated by original THEMES.EXE/MSJPEG32 on800x6008bpp, not a screenshot baseline.'})
    capture = ROOT/'private/themes-20261127/native-settled.png'
    image = cairo.ImageSurface.create_from_png(str(capture))
    cropped = cairo.ImageSurface(cairo.FORMAT_RGB24, 591, 449)
    context = cairo.Context(cropped); context.set_source_surface(image, -104, -62); context.paint()
    cropped.write_to_png(str(output/'themes-main-frame.png'))
    # Product preview layer, not a modified reference: preserve original sample
    # window/icon pixels while making the desktop background transparent.
    preview_source=ROOT/'private/themes-20261127/native-current-clean.png'
    preview_image=cairo.ImageSurface.create_from_png(str(preview_source))
    overlay=cairo.ImageSurface(cairo.FORMAT_ARGB32,393,333)
    cr=cairo.Context(overlay);cr.set_source_surface(preview_image,-119,-129);cr.paint()
    data=overlay.get_data();stride=overlay.get_stride()
    for y in range(333):
        for x in range(393):
            offset=y*stride+x*4
            label_background=any(left<=x<left+width and top<=y<top+height for left,top,width,height in ((35,74,65,13),(11,141,113,13),(38,208,60,13)))
            if not label_background and bytes(data[offset:offset+4])==bytes((128,128,0,255)):
                data[offset:offset+4]=bytes(4)
    overlay.mark_dirty()
    # Pointer was moved outside before this independent raw capture; no painted
    # cleanup may erase neighboring sample-control borders.
    overlay.write_to_png(str(output/'themes-preview-current-layer.png'))
    disabled=cairo.ImageSurface(cairo.FORMAT_RGB24,13,13)
    check_context=cairo.Context(disabled);check_context.set_source_surface(image,-542,-247);check_context.paint()
    disabled.write_to_png(str(output/'themes-check-disabled-checked.png'))
    records.append({'source':str(capture.relative_to(ROOT)), 'sha256':hashlib.sha256(capture.read_bytes()).hexdigest(), 'output':'themes-check-disabled-checked.png', 'type':'SCREEN_CAPTURE_CONTROL','rect':[542,247,13,13],'state':'checked disabled'})
    for filename, kind, scope in (('themes-main-frame.png','SCREEN_CAPTURE_CONTROL','Native dialog frame; dynamic controls repainted.'),('themes-preview-current-layer.png','DERIVED_PRODUCT_ART','Original pointer-free default preview samples with teal transparency outside opaque label unions; not reference baseline.')):
        original=capture if filename=='themes-main-frame.png' else preview_source
        records.append({'source':str(original.relative_to(ROOT)), 'sha256':hashlib.sha256(original.read_bytes()).hexdigest(), 'output':filename, 'type':kind, 'scope':scope, 'rect':[104,62,591,449] if filename=='themes-main-frame.png' else [119,129,393,333], 'pointer_cleanup':None})
    from resources import extract
    from win95lx.assets.bitmap import icon_dib,word
    from pixels import write
    library=source/'THEMES.CPL';resources=list(extract(library.read_bytes()))
    group=next(d for k,j,l,d,f in resources if k==14 and j==101)
    entries=[group[6+i*14:20+i*14] for i in range(word(group,4))]
    for size in (16,32):
        entry=next(e for e in entries if e[:2]==bytes((size,size)))
        ident=word(entry,12);raw=next(d for k,j,l,d,f in resources if k==3 and j==ident)
        width,height,pixels=icon_dib(raw);filename=f'cpl-themes-{size}.png'
        write(output/filename,width,height,pixels)
        records.append({'source':str(library.relative_to(ROOT)), 'sha256':hashlib.sha256(library.read_bytes()).hexdigest(), 'type':'GROUP_ICON','id':101,'image_id':ident,'output':filename,'dimensions':[width,height]})
    records.append({'source':str(inf.relative_to(ROOT)), 'sha256':hashlib.sha256(inf.read_bytes()).hexdigest(), 'output':'themes-library.json','type':'DERIVED_MANIFEST'})
    (output/'themes-library.json').write_text(json.dumps({'themes':catalog,'description':'Personalize your computer.','description_provenance':{'source':'THEMES.CPL','resource_type':'STRING','block':1,'string_index':3},'provenance':records,'native':{'source':str(capture.relative_to(ROOT)), 'sha256':hashlib.sha256(capture.read_bytes()).hexdigest(),'rect':[104,62,591,449]}},indent=2)+'\n')
    return records

if __name__ == '__main__': print(json.dumps(stage(ROOT/'private/theme-assets-qa'), indent=2))
