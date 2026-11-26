"""Optional accelerated palette path; pure Python remains the fallback."""
import ctypes,os
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def _library():
    module=Path(__file__).resolve()
    paths=[module.with_name('libpalette.so'),module.parents[3]/'private/native/libpalette.so']
    if os.environ.get('WIN95LX_PALETTE_LIBRARY'):paths.insert(0,Path(os.environ['WIN95LX_PALETTE_LIBRARY']))
    for path in paths:
        if not path.is_file():continue
        try:
            lib=ctypes.CDLL(str(path))
            if lib.win95lx_palette_abi()!=1:continue
            lib.win95lx_palette_over_256.argtypes=[ctypes.c_void_p,ctypes.c_size_t]
            lib.win95lx_palette_convert.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_int]
            return lib
        except (OSError,AttributeError):continue
    return None

def library():return None if os.environ.get('WIN95LX_PALETTE_DISABLE')=='1' else _library()

def convert(surface,palette):
    """Return None to use the reference Python implementation."""
    lib=library()
    if lib is None or surface.get_stride()!=surface.get_width()*4:return None
    import cairo
    from array import array
    surface.flush();count=surface.get_width()*surface.get_height();buffer=surface.get_data()
    source=ctypes.addressof(ctypes.c_ubyte.from_buffer(buffer))
    if palette==1 and lib.win95lx_palette_over_256(source,count)==0:return surface
    values=array('I',[0])*count
    if lib.win95lx_palette_convert(source,values.buffer_info()[0],count,palette)!=0:return None
    return cairo.ImageSurface.create_for_data(values,cairo.FORMAT_RGB24,surface.get_width(),surface.get_height())
