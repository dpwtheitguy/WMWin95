"""Original Windows 95 wallpaper names and guest display preferences."""

import json
from pathlib import Path

# Base and optional bitmap sections in the Windows 95 OSR 2.5 setup INFs.
BITMAPS = {
    'Black Thatch': 'thatch2.bmp',
    'Blue Rivets': 'rivets2.bmp',
    'Bubbles': 'bubbles.bmp',
    'Carved Stone': 'egypt.bmp',
    'Circles': 'circles.bmp',
    'Clouds': 'clouds.bmp',
    'Forest': 'forest.bmp',
    'Gold Weave': 'gator.bmp',
    'Houndstooth': 'hounds.bmp',
    'Metal Links': 'mesh.bmp',
    'Pinstripe': 'pstripe.bmp',
    'Red Blocks': '3dblocks.bmp',
    'Sandstone': 'sand.bmp',
    'Stitches': 'weave2.bmp',
    'Straw Mat': 'bamboo.bmp',
    'Tiles': 'redtile.bmp',
    'Triangles': 'pyramid2.bmp',
    'Waves': 'halftone.bmp',
}


class Wallpaper:
    def __init__(self, available, path=None):
        self.names = ('(None)', *[name for name, file in BITMAPS.items() if file in available])
        self.path = path or Path.home() / '.config' / 'win95lx' / 'wallpaper.json'
        self.name, self.mode = '(None)', 'center'
        self.custom = {}
        self.pattern = '(None)'
        self.pattern_rows = (0,)*8
        try:
            settings = json.loads(self.path.read_text())
        except (OSError, ValueError):
            return
        if isinstance(settings, dict):
            custom = settings.get('custom',{})
            if isinstance(custom,dict):
                self.custom = {label:path for label,path in custom.items()
                               if isinstance(label,str) and isinstance(path,str) and Path(path).is_absolute()}
                self.names += tuple(label for label in self.custom if label not in self.names)
            rows = settings.get('pattern_rows')
            if isinstance(rows,list) and len(rows)==8 and all(type(value) is int and 0<=value<256 for value in rows):
                self.pattern_rows = tuple(rows)
                self.pattern = str(settings.get('pattern','Custom'))
            if settings.get('name') in self.names:
                self.name = settings['name']
            if settings.get('mode') in ('center', 'tile'):
                self.mode = settings['mode']

    def register(self, path):
        path = Path(path).resolve()
        label = path.name
        if label in self.names and self.custom.get(label) != str(path):
            label = f'{path.name} ({path.parent.name})'
        self.custom[label] = str(path)
        if label not in self.names:
            self.names += (label,)
        return label

    def apply(self, name, mode, pattern=None, rows=None):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        pattern = self.pattern if pattern is None else pattern
        rows = self.pattern_rows if rows is None else tuple(rows)
        temp.write_text(json.dumps({'name':name,'mode':mode,'custom':self.custom,
                                    'pattern':pattern,'pattern_rows':rows})+'\n')
        temp.replace(self.path)
        self.name, self.mode = name, mode
        self.pattern, self.pattern_rows = pattern, rows


def paint_wallpaper(painter, image, mode, x, y, width, height):
    """Paint at native pixels and keep wallpaper inside the requested bounds."""
    if image is None:
        return
    import cairo

    cr = painter.cr
    cr.save()
    cr.rectangle(x, y, width, height)
    cr.clip()
    if mode == 'tile':
        pattern = cairo.SurfacePattern(image)
        pattern.set_extend(cairo.EXTEND_REPEAT)
        pattern.set_matrix(cairo.Matrix(x0=-x, y0=-y))
        cr.set_source(pattern)
        cr.paint()
    else:
        painter.image(image, x+(width-image.get_width())//2, y+(height-image.get_height())//2)
    cr.restore()


def paint_pattern(painter, rows, x, y, width, height):
    import cairo
    from win95lx.shell.widgets import BLACK, TEAL

    if not any(rows):
        return
    tile = cairo.ImageSurface(cairo.FORMAT_RGB24,8,8)
    from win95lx.shell.widgets import Painter
    p = Painter(cairo.Context(tile),painter.font)
    p.fill(0,0,8,8,TEAL)
    for row,bits in enumerate(rows):
        for column in range(8):
            if bits & (128>>column):
                p.fill(column,row,1,1,BLACK)
    painter.cr.save()
    painter.cr.rectangle(x,y,width,height)
    painter.cr.clip()
    pattern = cairo.SurfacePattern(tile)
    pattern.set_extend(cairo.EXTEND_REPEAT)
    pattern.set_filter(cairo.FILTER_NEAREST)
    pattern.set_matrix(cairo.Matrix(x0=-x,y0=-y))
    painter.cr.set_source(pattern)
    painter.cr.paint()
    painter.cr.restore()
