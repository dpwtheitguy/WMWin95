"""Pixel geometry and rendering for a classic vertical scrollbar."""

from dataclasses import dataclass
from functools import lru_cache

@lru_cache(maxsize=1)
def _track_tile():
    import cairo
    tile=cairo.ImageSurface(cairo.FORMAT_RGB24,2,2)
    cr=cairo.Context(tile);cr.set_source_rgb(192/255,192/255,192/255);cr.paint()
    cr.set_source_rgb(1,1,1);cr.rectangle(0,0,1,1);cr.rectangle(1,1,1,1);cr.fill()
    return tile

def draw_track(p,x,y,width,height,style="classic"):
    """Explicit control-owned trough; never inherit the surrounding white pane.

    ``window`` is reserved for independently measured native control tracks.
    The default is the classic system gray/white one-pixel stipple.
    """
    if style not in ("classic","window"):raise ValueError("Unknown scrollbar track style")
    if width<=0 or height<=0:return
    if style=="window":
        from win95lx.shell.widgets import LIGHT
        p.fill(x,y,width,height,LIGHT);return
    import cairo
    pattern=cairo.SurfacePattern(_track_tile());pattern.set_extend(cairo.EXTEND_REPEAT);pattern.set_filter(cairo.FILTER_NEAREST)
    pattern.set_matrix(cairo.Matrix(x0=-x,y0=-y))
    p.cr.save();p.cr.set_source(pattern);p.cr.rectangle(x,y,width,height);p.cr.fill();p.cr.restore()


def draw_scrollbar_face(p,x,y,width,height):
    """Native scrollbar bevel has a FACE outer band, unlike a push button."""
    from win95lx.shell.widgets import FACE,LIGHT,SHADOW,BLACK
    p.fill(x,y,width,height,FACE)
    p.fill(x+width-1,y,1,height,BLACK);p.fill(x,y+height-1,width,1,BLACK)
    p.fill(x+1,y+1,width-3,1,LIGHT);p.fill(x+1,y+1,1,height-3,LIGHT)
    p.fill(x+width-2,y+1,1,height-2,SHADOW);p.fill(x+1,y+height-2,width-2,1,SHADOW)


@dataclass(frozen=True)
class VerticalScrollbar:
    height: int
    maximum: int
    arrow: int = 16
    thumb: int = 21

    @classmethod
    def for_page(cls,height,maximum,page,arrow=16,minimum=8):
        if page<=0:raise ValueError('Scrollbar page must be positive')
        track=max(0,height-2*arrow)
        thumb=min(track,max(minimum,round(track*page/max(page,maximum+page))))
        return cls(height,max(0,maximum),arrow,thumb)

    @property
    def track_height(self):
        return self.height - 2*self.arrow

    @property
    def travel(self):
        return max(0, self.track_height-self.thumb)

    def thumb_top(self, value):
        value = max(0, min(value, self.maximum))
        return self.arrow + round(self.travel*value/max(1, self.maximum))

    def value_at(self, thumb_top):
        fraction = (thumb_top-self.arrow)/max(1, self.travel)
        return round(max(0, min(1, fraction))*self.maximum)

    def draw(self, p, x, y, value, artwork=None, *, track="classic"):
        from win95lx.shell.widgets import BLACK, LIGHT

        draw_track(p,x,y+self.arrow,self.arrow,self.track_height,track)
        bottom = self.height-self.arrow
        top = self.thumb_top(value)
        for offset, height, part in ((0,self.arrow,'up'), (top,self.thumb,'thumb'),
                                      (bottom,self.arrow,'down')):
            if artwork:
                artwork(p, x, y+offset, part)
            else:
                draw_scrollbar_face(p,x,y+offset,self.arrow,height)
                if part != 'thumb':
                    widths = (1, 3, 5, 7) if part == 'up' else (7, 5, 3, 1)
                    for row, width in enumerate(widths):
                        p.fill(x+(self.arrow-width)//2, y+offset+6+row, width, 1, BLACK)
