"""Original Plus95 icon variants and .THM CLSID associations, kept private."""
import configparser,hashlib,json,struct,sys,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from win95lx.control_panel.theme_preferences import installed_names
from win95lx.assets.bitmap import icon_dib
from pixels import write

ROLES={'computer':('20D04FE0-3AEA-1069-A2D8-08002B30309D','DefaultValue'),
       'network':('208D2C60-3AEA-1069-A2D7-08002B30309D','DefaultValue'),
       'recycle-empty':('645FF040-5081-101B-9F08-00AA002F954E','empty'),
       'recycle-full':('645FF040-5081-101B-9F08-00AA002F954E','full')}


def decode_variant(data,size,depth=8):
    if len(data)<6 or struct.unpack_from('<HH',data)!=(0,1):raise ValueError('Not an icon file.')
    count=struct.unpack_from('<H',data,4)[0];choices=[]
    if count>128 or len(data)<6+16*count:raise ValueError('The icon directory is incomplete.')
    for i in range(count):
        w,h,colors,reserved,planes,bits,length,offset=struct.unpack_from('<BBBBHHII',data,6+16*i)
        if (w,h)!=(size,size):continue
        if offset<6+16*count or offset+length>len(data)or length<40:raise ValueError('The icon image is incomplete.')
        raw=data[offset:offset+length];actual_depth=struct.unpack_from('<H',raw,14)[0]
        choices.append((actual_depth,raw,i))
    matching=next((v for v in choices if v[0]==depth),None)
    if matching is None:raise ValueError('The original icon variant is unavailable.')
    bits,raw,index=matching;w,h,pixels=icon_dib(raw)
    if (w,h)!=(size,size):raise ValueError('Icon image geometry changed.')
    return w,h,pixels,index,bits


def stage(output):
    output=Path(output);source=ROOT/'private/cabsets/plus95';inf=ROOT/'private/reference/media/plus/PLUS.INF'
    text=inf.read_text(encoding='cp1252');labels={short.casefold():Path(long).stem for short,long in re.findall(r'([\w~]+\.THM)<([^>]+)>',text,re.I)}
    names=installed_names(text);catalog=json.loads((output/'themes-library.json').read_text());records=[]
    for row in catalog['provenance']:
        if 'wallpaper_source'not in row:continue
        definition=ROOT/row['source'];parser=configparser.ConfigParser(interpolation=None,strict=False,allow_no_value=True)
        parser.read_string(definition.read_text(encoding='cp1252'));sections={s.casefold():parser[s]for s in parser.sections()}
        label=labels[definition.name.casefold()];theme=catalog['themes'][label];theme['icons']={}
        for role,(clsid,key)in ROLES.items():
            value=sections['clsid\\{'+clsid.casefold()+'}\\defaulticon'][key]
            location,separator,index=value.rpartition(',')
            if not separator:location,index=value,'0'
            if index.strip()!='0'or not location.casefold().startswith('%themedir%'):raise ValueError('Unsupported original theme icon association.')
            original=source/names[location[len('%ThemeDir%'):].casefold()];raw=original.read_bytes();pair={}
            for size,kind in ((32,'large'),(16,'small')):
                # Preserve both original color variants for later profile work.
                for depth in (8,4):
                    try:w,h,pixels,entry,bpp=decode_variant(raw,size,depth)
                    except ValueError as error:
                        if str(error)=='The original icon variant is unavailable.':continue
                        raise
                    dest=f'theme-icon-{original.stem.lower()}-{size}-{depth}.png';write(output/dest,w,h,pixels)
                    records.append({'source':str(original.relative_to(ROOT)),'source_sha256':hashlib.sha256(raw).hexdigest(),'definition':row['source'],'definition_sha256':row['sha256'],'type':'ICO_VARIANT','role':role,'entry':entry,'bpp':bpp,'dimensions':[w,h],'output':dest,'scope':'Original icon resource, not whole native-renderer pixel acceptance.'})
                    pair.setdefault(kind,dest)
            if set(pair)!={'large','small'}:raise ValueError('The original theme icon lacks a usable size.')
            theme['icons'][role]=pair
    catalog['icon_provenance']=records;(output/'themes-library.json').write_text(json.dumps(catalog,indent=2)+'\n');return records
