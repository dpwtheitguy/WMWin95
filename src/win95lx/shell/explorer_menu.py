"""IE4 My Computer File menu, measured in the original OSR2.5 guest."""
from win95lx.explorer.commands import Command as Entry, file_commands, namespace_context


def computer_file_rows(offline=False,selection=None):
    return file_commands(namespace_context(selection,offline))


WIDTH = 122
HEIGHT = 144


def draw(p, x, y, rows, highlight, check, hit, win):
    from win95lx.shell.widgets import BLACK, FACE, LIGHT, NAVY, SHADOW
    height=HEIGHT if len(rows)==9 else 5+sum(9 if row is None else 17 for row in rows)
    p.window_frame(x,y+1,WIDTH,height-1)
    p.fill(x+WIDTH-1,y+1,1,1,BLACK)
    p.fill(x,y+height-1,1,1,BLACK)
    p.fill(x,y,32,1,LIGHT)
    hit(x,y,WIDTH,height,('dismiss',))
    targets=[]
    top=y+4
    for row in rows:
        if row is None:
            p.fill(x+3,top+3,WIDTH-6,1,SHADOW)
            p.fill(x+3,top+4,WIDTH-6,1,LIGHT)
            top+=9
            continue
        selected=row.enabled and row.command==highlight
        if selected:p.fill(x+2,top-1,WIDTH-4,17,NAVY)
        color=LIGHT if selected else BLACK if row.enabled else SHADOW
        if not row.enabled:p.menu_text(row.label,x+25,top+2,LIGHT,row.mnemonic)
        if row.default:
            p.text(row.label,x+24,top+1,color,bold=True)
            p.fill(x+24,top+13,p.font.width(row.label[0],True),1,color)
        else:p.menu_text(row.label,x+24,top+1,color,row.mnemonic)
        if row.checked:
            if check is not None:
                p.cr.save();p.cr.set_source_rgb(*(v/255 for v in color));p.cr.mask_surface(check,x+9,top+5);p.cr.restore()
            else:
                for dx,dy in ((0,2),(1,3),(2,4),(3,3),(4,2),(5,1),(6,0)):
                    p.fill(x+7+dx,top+4+dy,1,2,color)
        if row.enabled:
            action=('close',win) if row.command=='close' else ('computer-menu',win,row.command)
            hit(x+2,top-1,WIDTH-4,17,action)
            targets.append((x+2,top-1,row.command,action))
        top+=17
    return targets
