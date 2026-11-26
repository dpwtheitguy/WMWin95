"""Pixel geometry and rendering for a classic vertical scrollbar."""

from dataclasses import dataclass

@dataclass(frozen=True)
class VerticalScrollbar:
    height: int
    maximum: int
    arrow: int = 16
    thumb: int = 21

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

    def draw(self, p, x, y, value, artwork=None):
        from win95lx.shell.widgets import BLACK, LIGHT

        p.fill(x, y+self.arrow, self.arrow, self.track_height, LIGHT)
        bottom = self.height-self.arrow
        top = self.thumb_top(value)
        for offset, height, part in ((0,self.arrow,'up'), (top,self.thumb,'thumb'),
                                      (bottom,self.arrow,'down')):
            if artwork:
                artwork(p, x, y+offset, part)
            else:
                p.bevel(x, y+offset, self.arrow, height)
                if part != 'thumb':
                    widths = (1, 3, 5, 7) if part == 'up' else (7, 5, 3, 1)
                    for row, width in enumerate(widths):
                        p.fill(x+(self.arrow-width)//2, y+offset+6+row, width, 1, BLACK)
