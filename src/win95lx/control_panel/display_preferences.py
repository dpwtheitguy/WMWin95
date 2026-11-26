"""Persist Win95LX rendering preferences independently of the guest's X11 depth."""

from dataclasses import asdict, dataclass
from functools import lru_cache
import json

PALETTES = ('16 Color', '256 Color', 'High Color (16 bit)', 'True Color (24 bit)')
FONT_SIZES = ('Small Fonts', 'Large Fonts', 'Other...')


@dataclass(frozen=True)
class DisplayPreferences:
    palette: int = 1
    dpi: int = 96
    tray: bool = False

    @classmethod
    def load(cls, path):
        try:
            settings = cls(**json.loads(path.read_text()))
            if (type(settings.palette) is int and 0 <= settings.palette < len(PALETTES)
                    and type(settings.dpi) is int and 96 <= settings.dpi <= 120
                    and type(settings.tray) is bool):
                return settings
        except (OSError, ValueError, TypeError):
            pass
        return cls()

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix('.tmp')
        temporary.write_text(json.dumps(asdict(self))+'\n')
        temporary.replace(path)


def color_surface(surface, palette):
    """Apply the selected palette to an entire opaque rendered surface."""
    import cairo
    from array import array

    if palette == 3:
        return surface
    width, height = surface.get_width(), surface.get_height()
    if palette == 2:
        converted = cairo.ImageSurface(cairo.FORMAT_RGB16_565, width, height)
        context = cairo.Context(converted)
        context.set_source_surface(surface, 0, 0)
        context.paint()
        return converted
    from win95lx.assets.native_palette import convert
    accelerated=convert(surface,palette)
    if accelerated is not None:return accelerated
    surface.flush()
    values = array('I')
    values.frombytes(surface.get_data())
    unique = set(values)
    if palette == 1 and len(unique) <= 256:
        return surface
    if palette == 0:
        mapping = {value: packed_color(nearest_vga((value>>20)&15,(value>>12)&15,(value>>4)&15))
                   for value in unique}
    else:
        mapping = {value: packed_color(color_256(value)) for value in unique}
    pixels = array('I',(mapping[value] for value in values))
    return cairo.ImageSurface.create_for_data(pixels, cairo.FORMAT_RGB24, width, height)


def packed_color(color):
    red,green,blue = color
    return red<<16 | green<<8 | blue


@lru_cache(maxsize=65536)
def color_256(value):
    color = (value>>16&255,value>>8&255,value&255)
    if color in VGA:
        return color
    # Reserve the classic UI colors, with a 216-color cube and a gray ramp.
    cube = tuple(round(channel/51)*51 for channel in color)
    gray = round(sum(color)/3/255*23)*255//23
    options = (*VGA,cube,(gray,gray,gray))
    return min(options,key=lambda candidate:sum((before-after)**2 for before,after in zip(color,candidate)))


def install_palette_filter(widget, preferences):
    """Quantize GTK accessory/dialog contents after children have rendered."""
    import cairo
    state = []

    def before(_widget, context):
        palette = preferences()
        state.append(palette)
        if palette != 3:
            context.push_group()
        return False

    def after(_widget, context):
        palette = state.pop()
        if palette == 3:
            return False
        pattern = context.pop_group()
        image = cairo.ImageSurface(cairo.FORMAT_RGB24,widget.get_allocated_width(),widget.get_allocated_height())
        canvas = cairo.Context(image)
        canvas.set_source(pattern)
        canvas.paint()
        context.set_source_surface(color_surface(image,palette),0,0)
        context.paint()
        return False

    widget.connect('draw',before)
    widget.connect_after('draw',after)


VGA = ((0,0,0),(128,0,0),(0,128,0),(128,128,0),
       (0,0,128),(128,0,128),(0,128,128),(192,192,192),
       (128,128,128),(255,0,0),(0,255,0),(255,255,0),
       (0,0,255),(255,0,255),(0,255,255),(255,255,255))


@lru_cache(maxsize=4096)
def nearest_vga(red, green, blue):
    return min(VGA, key=lambda color: sum((sample*17-value)**2
                                         for sample,value in zip((red,green,blue),color)))
