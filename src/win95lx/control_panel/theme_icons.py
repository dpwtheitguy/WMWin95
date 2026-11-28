"""Per-user original theme icon overrides; no executable icon providers."""
from copy import deepcopy
import json
from pathlib import Path
import struct

ROLES={'computer':'computer','network':'network-neighborhood','recycle-empty':32,'recycle-full':33}
SIZES={'large':32,'small':16}


def validate_icons(value):
    if not isinstance(value,dict)or set(value)-ROLES.keys():raise ValueError('The theme icon selection is not valid.')
    result={}
    for role,pair in value.items():
        if not isinstance(pair,dict)or set(pair)!=set(SIZES):raise ValueError('The theme icon sizes are incomplete.')
        result[role]={}
        for size,pixels in SIZES.items():
            filename=pair[size]
            if not isinstance(filename,str)or '\0'in filename or not Path(filename).is_absolute():raise ValueError('The theme icon filename is not valid.')
            path=Path(filename)
            if not path.is_file()or path.stat().st_size>1024*1024:raise ValueError('The theme icon cannot be found or is too large.')
            with path.open('rb')as stream:header=stream.read(24)
            if len(header)!=24 or header[:8]!=b'\x89PNG\r\n\x1a\n'or header[12:16]!=b'IHDR'or struct.unpack('>II',header[16:24])!=(pixels,pixels):raise ValueError('The theme icon does not have the required dimensions.')
            result[role][size]=str(path.resolve())
    return result


def apply_icons(shell,value):
    import cairo
    value=validate_icons(value)
    # Decode every candidate before changing any image mapping.
    loaded={role:{size:cairo.ImageSurface.create_from_png(pair[size])for size in SIZES}for role,pair in value.items()}
    if not hasattr(shell,'_theme_icon_defaults'):
        shell._theme_icon_defaults={role:{'large':shell.images.get(key),'small':shell.small_images.get(key)}for role,key in ROLES.items()}
    for role,key in ROLES.items():
        for size,mapping in (('large',shell.images),('small',shell.small_images)):
            image=loaded.get(role,shell._theme_icon_defaults[role]).get(size)
            if image is None:mapping.pop(key,None)
            else:mapping[key]=image
    shell.theme_icon_values=deepcopy(value)
    if hasattr(shell,'area'):shell.area.queue_draw()


def load_icons(shell,path=None):
    import cairo
    path=Path(path)if path else Path.home()/'.config/win95lx/theme-icons.json'
    apply_icons(shell,{})
    if path.exists():
        try:
            saved=json.loads(path.read_text())
            if not isinstance(saved,dict)or set(saved)!={'version','icons'}or saved['version']!=1:raise ValueError('Unknown theme icon settings.')
            apply_icons(shell,saved['icons'])
        except (OSError,ValueError,RuntimeError,cairo.Error)as error:
            # Invalid/missing custom artwork must not prevent the desktop boot.
            print('Could not load saved theme icons: '+str(error),flush=True)


def atomic_bytes(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);temporary=path.with_suffix('.tmp')
    try:temporary.write_bytes(data);temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)


class IconThemeProvider:
    def __init__(self,shell,path):self.shell,self.path=shell,Path(path)
    def export_current(self):return deepcopy(getattr(self.shell,'theme_icon_values',{}))
    capture=export_current
    def snapshot(self):return self.export_current(),self.path.read_bytes()if self.path.exists()else None
    def apply(self,value):
        apply_icons(self.shell,value)
        atomic_bytes(self.path,(json.dumps({'version':1,'icons':self.export_current()},sort_keys=True)+'\n').encode())
    def restore(self,state):
        value,data=state;apply_icons(self.shell,value)
        if data is None:self.path.unlink(missing_ok=True)
        else:atomic_bytes(self.path,data)
