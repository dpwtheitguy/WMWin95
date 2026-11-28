"""Bounded data-only importer for complete Windows95/Plus theme INI files.

No registry, program, DLL or shell directive is interpreted. Media are local
references; ICO variants are decoded into a content-addressed user cache.
"""
from copy import deepcopy
import configparser
import hashlib
import os
from pathlib import Path
import re
import struct
import tempfile
import zlib
from win95lx.control_panel.theme_store import MAX_DEFINITION,theme_name,validate_definition

CURSORS=dict(zip(('arrow','help','appstarting','wait','crosshair','ibeam','nwpen','no','sizens','sizewe','sizenwse','sizenesw','sizeall','uparrow'),('arrow','help','busy','wait','cross','beam','pen','no','size4','size3','size2','size1','move','up')))
ICONS={'computer':('20d04fe0-3aea-1069-a2d8-08002b30309d','defaultvalue',16),'network':('208d2c60-3aea-1069-a2d7-08002b30309d','defaultvalue',17),'recycle-empty':('645ff040-5081-101b-9f08-00aa002f954e','empty',20),'recycle-full':('645ff040-5081-101b-9f08-00aa002f954e','full',21)}


def _text(value):
    value=value.strip()
    return value[1:-1]if len(value)>=2 and value[0]==value[-1]=='"'else value


def _ini(data):
    if not isinstance(data,bytes)or len(data)>MAX_DEFINITION:raise ValueError('The theme definition is too large.')
    try:
        if data.startswith((b'\xff\xfe',b'\xfe\xff')):text=data.decode('utf-16')
        else:
            try:text=data.decode('utf-8-sig')
            except UnicodeDecodeError:text=data.decode('cp1252')
        if '\0'in text:raise ValueError('Invalid theme text.')
        parser=configparser.ConfigParser(interpolation=None,strict=True,allow_no_value=True)
        parser.read_string(text)
        if parser.defaults():raise ValueError('The theme contains unsupported inherited settings.')
        sections={}
        for name in parser.sections():
            key=name.casefold()
            if key in sections:raise ValueError('The theme contains conflicting sections.')
            sections[key]={option:_text(value)for option,value in parser[name].items()if value is not None}
        if len(sections)>160 or sum(map(len,sections.values()))>512:raise ValueError('The theme contains too many settings.')
        if any(key.startswith('win95lx.')for key in sections):raise ValueError('The Win95LX theme definition is invalid or unsupported.')
        return sections
    except (UnicodeError,configparser.Error)as error:raise ValueError('The theme definition cannot be read.')from error


class LocalAssets:
    def __init__(self,folder,assets=None):self.folder=Path(folder).resolve();self.assets=Path(assets).resolve()if assets else None
    def _case_path(self,path):
        path=Path(path)
        if path.exists():return path.resolve()
        parent=path.parent
        if not parent.is_dir():parent=self._case_path(parent)
        if not parent.is_dir():raise ValueError('A theme asset folder is unavailable.')
        entries=list(parent.iterdir())
        if len(entries)>10000:raise ValueError('The theme asset folder is too large.')
        matches=[item for item in entries if item.name.casefold()==path.name.casefold()]
        if len(matches)!=1:raise ValueError('A theme asset is missing or has an ambiguous file name.')
        return matches[0].resolve()
    def resolve(self,value,extensions,limit):
        if not isinstance(value,str)or any(ord(char)<32 for char in value)or len(value)>4096:raise ValueError('Invalid theme asset filename.')
        value=value.strip()
        if len(value)>=2 and value[0]==value[-1]=='"':value=value[1:-1]
        if not value:raise ValueError('The theme asset filename is empty.')
        if value.startswith('\\\\')or re.match(r'^[a-z][a-z0-9+.-]*://',value,re.I):raise ValueError('Theme assets must be available on a local disk.')
        lower=value.casefold();system=None
        if lower.startswith('%themedir%'):candidate=self.folder/value[10:].lstrip('\\/').replace('\\','/')
        elif lower.startswith('%windir%'):
            tail=value[8:].lstrip('\\/').replace('\\','/');filename=Path(tail).name
            if self.assets:
                if Path(filename).suffix.casefold()=='.wav':
                    installed={'the microsoft sound.wav':'mssound.wav'}.get(filename.casefold(),filename.casefold())
                    system=self.assets/('sound-'+installed)
                elif Path(filename).suffix.casefold()=='.bmp':
                    from win95lx.control_panel.wallpaper import BITMAPS
                    mapped=next((file for label,file in BITMAPS.items()if filename.casefold()in(file.casefold(),label.casefold()+'.bmp')),filename.casefold())
                    system=self.assets/('wallpaper-'+mapped)
            if system is None or not system.is_file():raise ValueError('A Windows system asset is not available. Put a local copy beside the theme and use %ThemeDir%.')
            candidate=system
        elif '%'in value:raise ValueError('The theme uses an unsupported asset folder variable.')
        elif re.match(r'^[a-z]:',value,re.I):
            if value[:2].casefold()!='c:':raise ValueError('Only local C: drive paths can be imported.')
            candidate=Path('/'+value[2:].lstrip('\\/').replace('\\','/'))
        else:candidate=Path(value.replace('\\','/'));candidate=candidate if candidate.is_absolute()else self.folder/candidate
        if any(part=='..'for part in candidate.parts):raise ValueError('The theme asset path leaves its declared folder.')
        if candidate.suffix.casefold()not in extensions:raise ValueError('The theme asset has an unsupported file type.')
        try:path=self._case_path(candidate)
        except (ValueError,OSError,RecursionError):raise ValueError("The theme asset '"+candidate.name[:100]+"' is missing or has conflicting file names.")from None
        if not path.is_file()or path.stat().st_size>limit:raise ValueError('A theme asset is unavailable or too large.')
        return path


def _png(width,height,pixels):
    def chunk(kind,value):return struct.pack('>I',len(value))+kind+value+struct.pack('>I',zlib.crc32(kind+value)&0xffffffff)
    raw=b''.join(b'\0'+bytes(channel for pixel in pixels[y*width:(y+1)*width]for channel in pixel)for y in range(height))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')


def _read_asset(path,limit):
    with Path(path).open('rb')as stream:data=stream.read(limit+1)
    if len(data)>limit:raise ValueError('A theme asset is too large.')
    return data


def icon_variants(path,cache):
    from win95lx.assets.bitmap import icon_dib
    data=_read_asset(path,1024*1024)
    if len(data)<6 or struct.unpack_from('<HH',data)!=(0,1):raise ValueError('The theme icon is not a Windows ICO file.')
    count=struct.unpack_from('<H',data,4)[0]
    if not 1<=count<=128 or len(data)<6+16*count:raise ValueError('The theme icon directory is incomplete.')
    choices={16:[],32:[]}
    for index in range(count):
        width,height,colors,reserved,planes,bits,length,offset=struct.unpack_from('<BBBBHHII',data,6+16*index)
        if width not in choices or height!=width:continue
        if offset<6+16*count or offset+length>len(data)or length<40:raise ValueError('The theme icon image is incomplete.')
        raw=data[offset:offset+length]
        if struct.unpack_from('<Iii',raw)!=(40,width,height*2):raise ValueError('The theme icon uses an unsupported image format.')
        depth=struct.unpack_from('<H',raw,14)[0]
        if depth not in (1,4,8,24,32):continue
        choices[width].append((depth,raw))
    result={};prepared=[]
    for size,label in ((32,'large'),(16,'small')):
        if not choices[size]:raise ValueError('The theme icon must include original16 and32pixel images.')
        depth,raw=min(choices[size],key=lambda row:(8,4,32,24,1).index(row[0]))
        width,height,pixels=icon_dib(raw);payload=_png(width,height,pixels)
        destination=Path(cache)/(hashlib.sha256(data).hexdigest()+'-'+str(size)+'.png');prepared.append((destination,payload));result[label]=str(destination.absolute())
    return result,prepared


def _wallpaper_size(path):
    with path.open('rb')as stream:data=stream.read(256*1024)
    size=None
    if data.startswith(b'\x89PNG\r\n\x1a\n')and len(data)>=24:size=struct.unpack_from('>II',data,16)
    elif data.startswith(b'BM')and len(data)>=26:size=tuple(abs(item)for item in struct.unpack_from('<ii',data,18))
    elif data.startswith(b'\xff\xd8'):
        index=2
        while index+4<=len(data):
            if data[index]!=255:break
            marker=data[index+1];index+=2
            if marker in (0xd8,0xd9):continue
            length=int.from_bytes(data[index:index+2],'big')
            if length<2 or index+length>len(data):break
            if marker in (0xc0,0xc1,0xc2)and length>=7:
                height,width=struct.unpack_from('>HH',data,index+3);size=width,height;break
            index+=length
    if size is None or not all(0<value<=8192 for value in size)or size[0]*size[1]>32*1024*1024:raise ValueError('The theme wallpaper has an unsupported or excessive image size.')


def appearance_components(sections,baseline_colors=None):
    from win95lx.control_panel.theme_appearance import DEFAULT_COLORS,parse_metrics
    value={}
    if 'control panel\\colors'in sections:
        known={name.casefold():name for name in DEFAULT_COLORS};colors=deepcopy(baseline_colors or DEFAULT_COLORS)
        for key,text in sections['control panel\\colors'].items():
            if key not in known:continue
            try:colors[known[key]]=[int(item)for item in text.split()]
            except ValueError:raise ValueError('Invalid theme color.')from None
        from win95lx.control_panel.theme_appearance import validate_colors
        value['colors']=validate_colors(colors)
    metrics=sections.get('metrics',sections.get('control panel\\desktop\\windowmetrics',{}))
    if metrics.get('nonclientmetrics')or metrics.get('iconmetrics'):
        try:
            nonclient=bytes(int(item)for item in metrics['nonclientmetrics'].split());icon=bytes(int(item)for item in metrics['iconmetrics'].split())
            value['fonts'],value['metrics']=parse_metrics(nonclient,icon)
        except (KeyError,ValueError,struct.error):raise ValueError('The theme has invalid Windows95 font or metric records.')from None
    return value


def read_legacy_appearance(data):
    """Build-time reuse of the exact typed native color/metric decoder."""
    return appearance_components(_ini(data))


def import_theme(data,path,baseline,cache,assets=None):
    """Return a typed full definition; inspect all assets before writing caches."""
    from win95lx.control_panel.sound_preferences import KEYS,wave_details
    from win95lx.assets.cursors import decode
    from win95lx.control_panel.theme_preferences import screensaver_association
    from win95lx.control_panel.theme_appearance import DEFAULT_COLORS,parse_metrics
    sections=_ini(data);path=Path(path);resolver=LocalAssets(path.parent,assets)
    desktop=sections.get('control panel\\desktop');cursors=sections.get('control panel\\cursors')
    event_sections={name:values for name,values in sections.items()if name.startswith('appevents\\schemes\\apps\\')and name.endswith('\\.current')}
    if desktop is None or cursors is None or not event_sections:raise ValueError('The theme must include desktop, pointer and sound settings.')
    if not set(CURSORS)<=set(cursors):raise ValueError('The theme must include all Windows95 pointer roles.')
    value={key:deepcopy(baseline[key])for key in ('wallpaper','pointers','sounds')}
    filename=desktop.get('wallpaper','').strip();mode=desktop.get('tilewallpaper','0').strip()
    if mode not in ('0','1')or desktop.get('wallpaperstyle','').strip()not in ('','0'):raise ValueError('The theme uses unsupported wallpaper placement.')
    wall=resolver.resolve(filename,{'.bmp','.jpg','.jpeg','.png'},64*1024*1024)if filename else None
    if wall:_wallpaper_size(wall)
    pattern=desktop.get('pattern','').strip();rows=[0]*8
    if pattern and pattern.casefold()!='(none)':
        try:rows=[int(item)for item in pattern.split()]
        except ValueError:raise ValueError('Invalid theme desktop pattern.')from None
        if len(rows)!=8 or any(not 0<=item<=255 for item in rows):raise ValueError('Invalid theme desktop pattern.')
    value['wallpaper']={'file':str(wall)if wall else'','mode':'tile'if mode=='1'else'center','pattern':'(None)'if not any(rows)else'Custom','pattern_rows':rows}
    overrides={}
    for native,role in CURSORS.items():
        filename=cursors[native].strip()
        if filename:
            cursor=resolver.resolve(filename,{'.cur','.ani'},16*1024*1024)
            try:decode(_read_asset(cursor,16*1024*1024))
            except (ValueError,struct.error,IndexError,RecursionError):raise ValueError('The theme pointer file cannot be read.')from None
            overrides[role]=str(cursor)
    value['pointers']={'scheme':'(None)','overrides':overrides}
    events=dict(value['sounds']['events']);keys={key.casefold():key for key in KEYS};recognized=0
    for section,settings in event_sections.items():
        parts=section.split('\\');event=parts[-2].casefold();application=parts[-3].casefold()
        if event not in keys or not(application=='.default'and event!='emptyrecyclebin' or application=='explorer'and event=='emptyrecyclebin'):continue
        recognized+=1
        filename=settings.get('defaultvalue','').strip()
        sound=resolver.resolve(filename,{'.wav'},64*1024*1024)if filename else None
        if sound:
            try:wave_details(sound)
            except (ValueError,struct.error):raise ValueError('The theme sound file cannot be read.')from None
        events[keys[event]]=str(sound)if sound else''
    value['sounds']={'scheme':''if recognized else value['sounds']['scheme'],'events':events}
    value.update(appearance_components(sections,baseline.get('colors')))
    prepared=[];icons={};resets=0
    for role,(clsid,key,default_index)in ICONS.items():
        settings=sections.get('clsid\\{'+clsid+'}\\defaulticon')
        if settings is None:continue
        text=settings.get(key,'').strip();filename,separator,index=text.rpartition(',')
        if not separator:filename,index=text,'0'
        try:number=int(index)
        except ValueError:raise ValueError('The theme icon index is invalid.')from None
        if re.fullmatch(r'%windir%\\?system\\cool\.dll',filename,re.I)and number==default_index:resets+=1;continue
        if number!=0:raise ValueError('Only the first image group in an ICO file can be imported.')
        source=resolver.resolve(filename,{'.ico'},1024*1024);icons[role],images=icon_variants(source,cache);prepared.extend(images)
    if icons or resets:
        if resets and resets!=4:raise ValueError('The theme mixes unsupported system and custom icon groups.')
        value['icons']=icons
    boot=sections.get('boot',{})
    if 'scrnsave.exe'in boot:
        value['screensaver']=screensaver_association(boot['scrnsave.exe'])
    if desktop.get('screensaveactive','1').strip()not in ('0','1'):raise ValueError('Invalid theme screen saver state.')
    if desktop.get('screensaveactive','1').strip()=='0':value['screensaver']={'saver':''}
    value=validate_definition(value)
    if prepared:
        cache=Path(cache);cache.mkdir(parents=True,exist_ok=True,mode=0o700)
        if cache.is_symlink()or not cache.is_dir():raise ValueError('The theme image cache is unavailable.')
        for destination,payload in prepared:
            if destination.is_symlink():raise ValueError('The theme image cache is redirected.')
            if destination.is_file()and destination.stat().st_size==len(payload)and _read_asset(destination,len(payload))==payload:continue
            temporary=None
            try:
                with tempfile.NamedTemporaryFile(dir=cache,prefix='.icon-',delete=False)as stream:temporary=Path(stream.name);stream.write(payload)
                temporary.replace(destination)
            finally:
                if temporary is not None:temporary.unlink(missing_ok=True)
    return theme_name(path.stem),value
