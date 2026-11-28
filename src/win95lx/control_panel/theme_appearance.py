"""Semantic system appearance; artwork is never recolored by RGB substitution.

Original LOGFONT records are decoded as data, never executed. Providers expose
transactional snapshots and persist canonical values for the next session.
"""
from copy import deepcopy
from pathlib import Path
import json
import struct

COLOR_NAMES = tuple('ActiveTitle Background Hilight HilightText TitleText Window WindowText Scrollbar InactiveTitle Menu WindowFrame MenuText ActiveBorder InactiveBorder AppWorkspace ButtonFace ButtonShadow GrayText ButtonText InactiveTitleText ButtonHilight ButtonDkShadow ButtonLight InfoText InfoWindow'.split())
_DEFAULT_VALUES = [(0,0,128),(0,128,128),(0,0,128),(255,255,255),(255,255,255),(255,255,255),(0,0,0),(192,192,192),(128,128,128),(192,192,192),(0,0,0),(0,0,0),(192,192,192),(192,192,192),(128,128,128),(192,192,192),(128,128,128),(128,128,128),(0,0,0),(192,192,192),(255,255,255),(0,0,0),(192,192,192),(0,0,0),(255,255,225)]
DEFAULT_COLORS = dict(zip(COLOR_NAMES, map(list,_DEFAULT_VALUES)))
FONT_ROLES = ('caption','small_caption','menu','status','message','icon')
FONT_DEFAULT = dict(family='MS Sans Serif',height=-11,width=0,weight=400,italic=False,underline=False,strikeout=False,charset=0,pitch_family=0)
DEFAULT_FONTS = {role:dict(FONT_DEFAULT,weight=700 if role in ('caption','small_caption') else 400,height=-8 if role=='small_caption' else -11) for role in FONT_ROLES}
DEFAULT_METRICS = dict(border_width=1,scroll_width=13,scroll_height=13,caption_width=18,caption_height=18,small_caption_width=15,small_caption_height=15,menu_width=18,menu_height=18,icon_spacing_x=75,icon_spacing_y=75,icon_wrap=True)

def _keys(value,keys,label):
    if not isinstance(value,dict) or set(value)!=set(keys):raise ValueError('Invalid '+label+' fields.')

def _integer(value,low,high,label):
    if type(value) is not int or not low<=value<=high:raise ValueError('Invalid '+label+'.')
    return value

def validate_colors(value):
    _keys(value,COLOR_NAMES,'system color')
    result={}
    for key,rgb in value.items():
        if not isinstance(rgb,(list,tuple)) or len(rgb)!=3:raise ValueError('Invalid RGB color.')
        result[key]=[_integer(channel,0,255,'color channel') for channel in rgb]
    return result

def validate_fonts(value):
    _keys(value,FONT_ROLES,'system font');result={}
    for role,record in value.items():
        if not isinstance(record,dict) or set(record)-set(FONT_DEFAULT) or not {'family','height'}<=set(record):raise ValueError('Invalid font fields.')
        font=dict(FONT_DEFAULT,**record)
        if not isinstance(font['family'],str) or not 1<=len(font['family'])<=31 or any(ord(c)<32 for c in font['family']):raise ValueError('Invalid font family.')
        if not _integer(font['height'],-96,96,'font height'):raise ValueError('Font height cannot be zero.')
        for key,high in (('width',96),('weight',1000),('charset',255),('pitch_family',255)):_integer(font[key],0,high,key)
        for key in ('italic','underline','strikeout'):
            if type(font[key]) is not bool:raise ValueError('Invalid font style.')
        result[role]=font
    return result

def validate_metrics(value):
    _keys(value,DEFAULT_METRICS,'window metric');result={}
    for key,item in value.items():
        if key=='icon_wrap':
            if type(item) is not bool:raise ValueError('Invalid icon wrapping flag.')
            result[key]=item
        else:result[key]=_integer(item,16 if key.startswith('icon_spacing') else 1,512 if key.startswith('icon_spacing') else 128,key)
    return result

def _logfont(data,offset):
    height,width,escape,orientation,weight=struct.unpack_from('<5i',data,offset)
    if escape or orientation:raise ValueError('Rotated system fonts are unsupported.')
    flags=data[offset+20:offset+28]
    if any(v not in (0,1) for v in flags[:3]):raise ValueError('Invalid LOGFONT flags.')
    family=data[offset+28:offset+60].split(b'\0',1)[0].decode('cp1252')
    return dict(family=family,height=height,width=width,weight=weight,italic=bool(flags[0]),underline=bool(flags[1]),strikeout=bool(flags[2]),charset=flags[3],pitch_family=flags[7])

def parse_metrics(nonclient,icon):
    """Decode Win95 NONCLIENTMETRICSA340 + ICONMETRICSA76 exactly."""
    if len(nonclient)!=340 or len(icon)!=76 or struct.unpack_from('<I',nonclient)[0]!=340 or struct.unpack_from('<I',icon)[0]!=76:raise ValueError('Invalid Windows 95 metric record size.')
    offsets={'border_width':4,'scroll_width':8,'scroll_height':12,'caption_width':16,'caption_height':20,'small_caption_width':84,'small_caption_height':88,'menu_width':152,'menu_height':156}
    metrics={key:struct.unpack_from('<i',nonclient,offset)[0] for key,offset in offsets.items()}
    x,y,wrap=struct.unpack_from('<3i',icon,4)
    if wrap not in (0,1):raise ValueError('Invalid icon wrapping value.')
    metrics.update(icon_spacing_x=x,icon_spacing_y=y,icon_wrap=bool(wrap))
    fonts={role:_logfont(nonclient,offset) for role,offset in zip(FONT_ROLES[:5],(24,92,160,220,280))}
    fonts['icon']=_logfont(icon,16)
    return validate_fonts(fonts),validate_metrics(metrics)

VALIDATORS={'colors':validate_colors,'fonts':validate_fonts,'metrics':validate_metrics}
DEFAULTS={'colors':DEFAULT_COLORS,'fonts':DEFAULT_FONTS,'metrics':DEFAULT_METRICS}

class Appearance:
    """Process-local live values. Callback failure restores prior live state."""
    def __init__(self):self.values=deepcopy(DEFAULTS);self.listeners=[];self.font_resolver=None
    def color(self,role):return tuple(self.values['colors'][role])
    def metric(self,name):return self.values['metrics'][name]
    def font(self,role,fallback):
        record=self.values['fonts'][role]
        if record==DEFAULT_FONTS[role]:return fallback
        if self.font_resolver is None:raise ValueError('The selected system font is unavailable.')
        return self.font_resolver(record,fallback)
    def update(self,component,value):
        candidate=VALIDATORS[component](value);old=self.values[component]
        if component=='fonts' and candidate!=DEFAULT_FONTS:
            if self.font_resolver is None:raise ValueError('The selected system fonts are unavailable.')
            for record in candidate.values():self.font_resolver(record,None)
        self.values[component]=candidate
        try:
            for listener in tuple(self.listeners):listener()
        except Exception:
            self.values[component]=old
            for listener in tuple(self.listeners):
                try:listener()
                except Exception:pass
            raise

appearance=Appearance()

def load_session(config, font_library, runtime=None):
    """Recover each saved component independently without blocking desktop startup."""
    runtime=runtime or appearance
    runtime.values=deepcopy(DEFAULTS)
    errors=[]
    try:
        runtime.font_resolver=FontLibrary(font_library)
    except (OSError,ValueError,KeyError,TypeError) as error:
        runtime.font_resolver=None
        errors.append(('font-library',str(error)))
    for component in VALIDATORS:
        try:AppearanceProvider(component,Path(config)/('theme-'+component+'.json'),runtime).load()
        except (OSError,ValueError,KeyError,TypeError) as error:
            errors.append((component,str(error)))
    return errors

class AppearanceProvider:
    def __init__(self,component,path,runtime=None):
        if component not in VALIDATORS:raise ValueError('Unknown appearance component.')
        self.component=component;self.path=Path(path);self.runtime=runtime or appearance
    def export_current(self):return deepcopy(self.runtime.values[self.component])
    capture=export_current
    def snapshot(self):return self.export_current(),self.path.read_bytes() if self.path.exists() else None
    def apply(self,value):
        candidate=VALIDATORS[self.component](value);old=self.snapshot()
        try:
            self.runtime.update(self.component,candidate)
            self.path.parent.mkdir(parents=True,exist_ok=True)
            temporary=self.path.with_name(self.path.name+'.tmp');temporary.write_text(json.dumps(candidate,sort_keys=True)+'\n');temporary.replace(self.path)
        except Exception:self.restore(old);raise
    def restore(self,snapshot):
        value,stored=snapshot;self.runtime.update(self.component,value)
        if stored is None:self.path.unlink(missing_ok=True)
        else:self.path.parent.mkdir(parents=True,exist_ok=True);self.path.write_bytes(stored)
    def load(self):
        if self.path.exists():self.runtime.update(self.component,json.loads(self.path.read_text()))
    def matches(self,value):return self.export_current()==VALIDATORS[self.component](value)

class RasterFont:
    """Monochrome Cairo/FreeType glyph adapter for installed original TTF faces.

    Uses the original font family registered with process-local Fontconfig.
    Rasterization is Linux FreeType; pixel equivalence with GDI is measured
    separately and is not implied by using the original font file.
    """
    def __init__(self,record):
        import cairo
        self.record=record;self.face=record['family'];self.glyphs={}
        self.height=abs(record['height']);self.ascent=self.height;self.points=self.height*72/96
        self.surface=cairo.ImageSurface(cairo.FORMAT_A8,256,256);self.cr=cairo.Context(self.surface)
        options=cairo.FontOptions();options.set_antialias(cairo.ANTIALIAS_NONE);options.set_hint_style(cairo.HINT_STYLE_FULL);options.set_hint_metrics(cairo.HINT_METRICS_ON);self.cr.set_font_options(options)
        self.cr.select_font_face(self.face,cairo.FONT_SLANT_ITALIC if record['italic'] else cairo.FONT_SLANT_NORMAL,cairo.FONT_WEIGHT_BOLD if record['weight']>=600 else cairo.FONT_WEIGHT_NORMAL)
        self.cr.set_font_size(self.height)
        ascent,descent,cell,_,_=self.cr.font_extents();self.ascent=int(round(ascent));self.height=max(1,int(round(cell)))
    def glyph(self,char):
        import cairo
        if char not in self.glyphs:
            self.cr.set_operator(cairo.OPERATOR_CLEAR);self.cr.paint();self.cr.set_operator(cairo.OPERATOR_OVER);self.cr.set_source_rgba(1,1,1,1)
            self.cr.move_to(32,self.ascent);self.cr.show_text(char);self.surface.flush()
            extent=self.cr.text_extents(char);advance=max(0,int(round(extent.x_advance)));width=self.record['width'] or advance
            data=self.surface.get_data();stride=self.surface.get_stride();points=[]
            for y in range(min(255,self.height)):
                for x in range(-32,min(128,max(advance+4,16))):
                    byte=data[y*stride+x+32]
                    if (byte if isinstance(byte,int) else byte[0]):points.append((round(x*width/advance) if advance and self.record['width'] else x,y))
            if self.record['underline']:points.extend((x,min(self.height-1,self.ascent+1)) for x in range(width))
            if self.record['strikeout']:points.extend((x,max(0,self.ascent//2)) for x in range(width))
            self.glyphs[char]=(width,tuple(points))
        return self.glyphs[char]
    def width(self,text,bold=False):return sum(self.glyph(c)[0]+int(bold) for c in text)

class FontLibrary:
    """Register verified library files only in this process; no host installation."""
    def __init__(self,root):
        import ctypes
        self.root=Path(root).resolve();self.cache={};self.families=set()
        library=ctypes.CDLL('libfontconfig.so.1');library.FcConfigGetCurrent.restype=ctypes.c_void_p
        library.FcConfigAppFontAddFile.argtypes=(ctypes.c_void_p,ctypes.c_char_p);library.FcConfigAppFontAddFile.restype=ctypes.c_int
        inventory=json.loads((self.root/'inventory.json').read_text())
        rows=inventory if isinstance(inventory,list) else inventory.get('fonts',inventory.get('files',[]))
        for row in rows:
            if not row.get('readable'):continue
            path=(self.root/row['file']).resolve()
            if not path.is_relative_to(self.root) or not path.is_file():continue
            if path.suffix.casefold() not in ('.ttf','.otf'):continue
            if library.FcConfigAppFontAddFile(library.FcConfigGetCurrent(),str(path).encode()):
                self.families.update(face['family'].casefold() for face in row.get('faces',[]))
    def __call__(self,record,fallback):
        if record==FONT_DEFAULT and fallback is not None:return fallback
        if record['family'].casefold() not in self.families:
            if record['family'].casefold()=='ms sans serif':
                if fallback is None:return None
                return BitmapScaledFont(fallback,record)
            raise ValueError('The original font is unavailable: '+record['family'])
        key=json.dumps(record,sort_keys=True)
        if key not in self.cache:self.cache[key]=RasterFont(record)
        return self.cache[key]


class BitmapScaledFont:
    """Nearest-pixel sizing of the original MS Sans Serif bitmap fallback."""
    def __init__(self,base,record):
        self.base=base;self.record=record;self.height=max(1,round(base.height*abs(record['height'])/11));self.ascent=round(base.ascent*self.height/base.height);self.face=base.face;self.glyphs={}
    def glyph(self,char):
        if char not in self.glyphs:
            advance,points=self.base.glyph(char);scale=self.height/self.base.height
            width=self.record['width'] or max(1,round(advance*scale));occupied=set(points);out=[]
            for y in range(self.height):
                for x in range(width):
                    if (min(advance-1,int(x*advance/width)),min(self.base.height-1,int(y/scale))) in occupied:out.append((x,y))
            if self.record['italic']:out=[(x+max(0,(self.ascent-y)//4),y) for x,y in out]
            if self.record['weight']>=600:out=list(set(out)|{(x+1,y) for x,y in out});width+=1
            if self.record['underline']:out.extend((x,min(self.height-1,self.ascent+1))for x in range(width))
            if self.record['strikeout']:out.extend((x,self.ascent//2)for x in range(width))
            self.glyphs[char]=(width,tuple(out))
        return self.glyphs[char]
    def width(self,text,bold=False):return sum(self.glyph(c)[0]+int(bold) for c in text)
