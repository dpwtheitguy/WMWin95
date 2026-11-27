"""Control Panel namespace item views using shared classic controls."""
from win95lx.explorer.namespace_layout import arrange,clipped_hit
from win95lx.shell.widgets import FACE,LIGHT,BLACK,NAVY
from win95lx.shell.scrollbar import VerticalScrollbar

def bar(shell,p,win,x,y,length,maximum,value,axis,page):
    if length<32:return
    b=VerticalScrollbar(length,maximum)
    p.cr.save()
    if axis==0:p.cr.translate(x,y+16);p.cr.rotate(-1.5707963267948966);bx,by=0,0
    else:bx,by=x,y
    b.draw(p,bx,by,value)
    p.cr.restore()
    def hit(offset,size,delta):
        rect=(x+offset,y,size,16) if axis==0 else (x,y+offset,16,size)
        shell.hit(*rect,('namespace-scroll',win,axis,delta))
    hit(0,16,-17);hit(length-16,16,17)
    thumb=b.thumb_top(value)
    rect=(x+thumb,y,b.thumb,16) if axis==0 else (x,y+thumb,16,b.thumb)
    shell.hit(*rect,('namespace-thumb',win,axis,x,y,length,maximum,thumb))
    if thumb>16:hit(16,thumb-16,-page)
    end=thumb+b.thumb
    if end<length-16:hit(end,length-16-end,page)

def draw(shell,p,win,entries,x,y,width,height,*,defaults=None):
    labels=[label for _,label,_ in entries];longest=max((p.font.width(t) for t in labels),default=0)
    key=('namespace:'+win.kind,win.namespace_view)
    if getattr(win,'namespace_key',None)!=key:
        win.namespace_key=key;win.namespace_positions=()
        saved=shell.shortcut_icons.position(key[0],'$auto',(0 if win.kind=='computer' else int(win.namespace_auto),0))
        win.namespace_auto=bool(saved[0])
    positions=win.namespace_positions
    if not win.namespace_auto and win.namespace_view in ('large','small'):
        seed=positions or defaults or arrange(len(entries),max(0,width),max(0,height),win.namespace_view,label_width=longest).positions
        positions=tuple(shell.shortcut_icons.position(key[0]+':'+key[1],label,point) for label,point in zip(labels,seed))
    if defaults is not None and win.namespace_view=='large' and (win.namespace_auto or not positions):positions=defaults
    layout=arrange(len(entries),max(0,width),max(0,height),win.namespace_view,win.namespace_scroll,
                   auto=win.namespace_auto and defaults is None,positions=positions,label_width=longest)
    win.namespace_layout=layout;win.namespace_positions=layout.positions;win.namespace_scroll=layout.scroll
    vw,vh=layout.viewport;sx,sy=layout.scroll;win.namespace_viewport=(x,y,vw,vh)
    p.cr.save();p.cr.rectangle(x,y,vw,vh);p.cr.clip()
    for i,(ident,label,target) in enumerate(entries):
        dx,dy=layout.positions[i]
        drag=getattr(shell,'namespace_item_drag',None)
        if drag and drag[0] is win and drag[1]==label and getattr(shell,'namespace_item_point',None) is not None:dx,dy=shell.namespace_item_point
        xx,yy=x+dx-sx,y+dy-sy
        selected=shell.item_selection in ((win,label),(win,None)) and shell.state.active is win and shell.popup is None
        action=('item',win,target,label,(dx,dy))
        if win.namespace_view=='large':
            count=len(shell.hits);shell.icon(p,ident,label,xx,yy,action,selected,image_offset=-1 if win.kind=='computer' and win.web_view else 0,label_offset=1 if win.kind=='computer' and win.web_view and i==0 else 0)
            new=shell.hits[count:];del shell.hits[count:]
            for hx,hy,hw,hh,act in new:
                clipped=clipped_hit((hx,hy,hw,hh),(x,y,vw,vh))
                if clipped:shell.hit(*clipped,act)
        else:
            image=shell.small_images.get(ident)
            if image:p.image(image,xx,yy)
            elif ident in shell.images:
                p.cr.save();p.cr.translate(xx,yy);p.cr.scale(.5,.5);p.image(shell.images[ident],0,0);p.cr.restore()
            if selected:p.fill(xx+17,yy,min(p.font.width(label)+2,layout.cell[0]-18),16,NAVY)
            p.cr.save();p.cr.rectangle(xx+17,yy,max(0,(190 if win.namespace_view=='details' else layout.cell[0])-18),17);p.cr.clip()
            p.text(label,xx+18,yy+1,LIGHT if selected else BLACK);p.cr.restore()
            if win.namespace_view=='details':
                if not hasattr(shell,'cpl_descriptions'):
                    import json
                    path=shell.assets/'cpl-descriptions.json';shell.cpl_descriptions=json.loads(path.read_text()) if path.exists() else {}
                p.text(shell.cpl_descriptions.get(label,''),x+192-sx,yy+1)
            clipped=clipped_hit((xx,yy,layout.cell[0],17),(x,y+layout.header,vw,max(0,vh-layout.header)))
            if clipped:shell.hit(*clipped,action)
    if layout.header:
        p.bevel(x-sx,y,190,17);p.text('Name',x+4-sx,y+2);p.bevel(x+190-sx,y,max(vw-190,230),17);p.text('Description',x+194-sx,y+2)
    p.cr.restore()
    if layout.vertical:bar(shell,p,win,x+vw,y,vh,max(0,layout.extent[1]-vh),sy,1,vh)
    if layout.horizontal:bar(shell,p,win,x,y+vh,vw,max(0,layout.extent[0]-vw),sx,0,vw)
    if layout.horizontal and layout.vertical:p.fill(x+vw,y+vh,16,16,FACE)
