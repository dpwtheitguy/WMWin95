"""Responsive namespace layout; no GTK, painting or filesystem access."""
from dataclasses import dataclass
from math import ceil
MODES=('large','small','list','details')
@dataclass(frozen=True)
class Layout:
    positions:tuple
    viewport:tuple
    extent:tuple
    scroll:tuple
    horizontal:bool
    vertical:bool
    cell:tuple
    header:int

def arrange(count,width,height,mode='large',scroll=(0,0),*,auto=True,positions=None,label_width=120):
    if mode not in MODES:raise ValueError('Unknown namespace view')
    if min(count,width,height)<0:raise ValueError('Negative layout size')
    header=17 if mode=='details' else 0
    cw,ch=(75,75) if mode=='large' else (max(140,label_width+22),17)
    def calculate(vw,vh):
        if mode=='details':pts=tuple((0,header+i*ch) for i in range(count));ew=max(vw,420);eh=header+count*ch
        elif mode=='list':
            rows=max(1,(vh-4)//ch);pts=tuple((i//rows*cw+2,i%rows*ch+2) for i in range(count));ew=ceil(count/rows)*cw+4 if count else 0;eh=min(count,rows)*ch+4 if count else 0
        else:
            cols=max(1,(vw-4)//cw);pts=tuple((i%cols*cw+2,i//cols*ch+2) for i in range(count))
            if not auto and positions is not None and len(positions)==count:pts=tuple(positions)
            ew=max((x+cw for x,y in pts),default=0)+2;eh=max((y+ch for x,y in pts),default=0)+2
        return pts,ew,eh
    horizontal=vertical=False
    # Scrollbars affect row/column capacity; solve monotonically to avoid flicker.
    for _ in range(3):
        vw=max(0,width-(16 if vertical else 0));vh=max(0,height-(16 if horizontal else 0))
        pts,ew,eh=calculate(vw,vh);horizontal=horizontal or ew>vw;vertical=vertical or eh>vh
    vw=max(0,width-(16 if vertical else 0));vh=max(0,height-(16 if horizontal else 0));pts,ew,eh=calculate(vw,vh)
    sx=max(0,min(int(scroll[0]),max(0,ew-vw)));sy=max(0,min(int(scroll[1]),max(0,eh-vh)))
    return Layout(pts,(vw,vh),(ew,eh),(sx,sy),horizontal,vertical,(cw,ch),header)

def clipped_hit(rect,viewport):
    x,y,w,h=rect;vx,vy,vw,vh=viewport;x1,y1=max(x,vx),max(y,vy);x2,y2=min(x+w,vx+vw),min(y+h,vy+vh)
    return (x1,y1,x2-x1,y2-y1) if x2>x1 and y2>y1 else None

def reveal(layout,index):
    """Bring an item into view after keyboard selection, retaining other axis."""
    x,y=layout.positions[index];cw,ch=layout.cell;vw,vh=layout.viewport;sx,sy=layout.scroll
    if x<sx:sx=x
    elif x+cw>sx+vw:sx=x+cw-vw
    if y<sy+layout.header:sy=max(0,y-layout.header)
    elif y+ch>sy+vh:sy=y+ch-vh
    return max(0,min(sx,max(0,layout.extent[0]-vw))),max(0,min(sy,max(0,layout.extent[1]-vh)))
