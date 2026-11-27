"""Interactive IE4 My Computer toolbar, address band and Web View."""
import cairo
from win95lx.control_panel.catalog import entries as control_entries
from win95lx.shell.widgets import BLACK, FACE, LIGHT, SHADOW

BUTTONS=(('back',8,75),('forward',75,144),('up',144,204),
         ('cut',204,262),('copy',262,316),('paste',316,374),
         ('undo',374,435),('delete',435,493),
         ('properties',493,553),('views',553,630))


def surface(shell,name):
    key='explorer-'+name
    if key not in shell.images:
        path=shell.assets/(key+'.png')
        if path.is_file():shell.images[key]=cairo.ImageSurface.create_from_png(str(path))
    return shell.images.get(key)


def geometry(win):
    if win.restored_bounds is not None:
        return win.x-4,win.y-4,win.width+8,win.height+8
    return win.x,win.y,win.width,win.height


def draw(shell,p,win):
    x,y,w,h=geometry(win)
    left=x+4; width=w-8
    if 'mouse' not in shell.images and (shell.assets/'mouse-icon.png').exists():shell.images['mouse']=cairo.ImageSurface.create_from_png(str(shell.assets/'mouse-icon.png'))
    computer=win.kind=='computer'
    entries=((9,'(C:)','drive'),(36,'Control Panel','control')) if computer else control_entries()
    small_icon='computer' if computer else 36
    if shell.popup and isinstance(shell.popup[2],tuple) and shell.popup[2]==(win,'File'):
        p.bevel(left+11,y+26,32,19,True)
        p.menu_text('File',left+20,y+30,BLACK,'f')
    top=y+46
    if win.toolbar:
        p.fill(left,top,width,46,FACE)
        p.fill(left,top+1,width,1,SHADOW)
        p.fill(left,top+45,width,1,BLACK)
        p.cr.save();p.cr.rectangle(left,top,width,46);p.cr.clip()
        grip=surface(shell,'toolbar-grip')
        if grip:p.image(grip,left,top)
        for command,start,end in BUTTONS:
            image=surface(shell,('control-toolbar-' if (command=='up' and not computer or command=='back' and win.back_history) else 'toolbar-')+command)
            if image:p.image(image,left+start,top)
            if start<width:shell.hit(left+start,top+2,min(end,width)-start,42,('explorer-tool',win,command))
        ending=surface(shell,'toolbar-end')
        if ending and width>630:
            p.cr.set_source_surface(ending,left+630,top)
            p.cr.get_source().set_extend(cairo.EXTEND_REPEAT)
            p.cr.rectangle(left+630,top,width-630,46);p.cr.fill()
        for name,dx,dy in (('toolbar-right',width-2,0),('toolbar-top-right',width-42,0),('toolbar-bottom-right',width-7,45)):
            edge=surface(shell,name)
            if edge:p.image(edge,left+dx,top+dy)
        p.fill(left+width-41,top+1,1,1,LIGHT)
        p.cr.restore()
        top+=46
    if win.address_bar:
        # Three independently staged control edges; address text remains live.
        for name,dx in (('address-left',0),('address-right',width-24)):
            image=surface(shell,name)
            if image:p.image(image,left+dx,top)
        middle=surface(shell,'address-middle')
        if middle and width>100:
            p.cr.save();p.cr.set_source_surface(middle,left+76,top)
            p.cr.get_source().set_extend(cairo.EXTEND_REPEAT)
            p.cr.rectangle(left+76,top,width-100,26);p.cr.fill();p.cr.restore()
        if not computer:
            p.fill(left+56,top+1,20,17,LIGHT)
            icon=shell.small_images.get(small_icon)
            if icon:p.image(icon,left+57,top+2)
        label=shell.address_text if shell.address_window is win else win.title
        p.cr.save();p.cr.rectangle(left+76,top+1,width-100,17);p.cr.clip()
        if shell.address_window is win:
            a,b=shell.address_entry.selection
            from win95lx.shell.widgets import NAVY
            if a!=b:p.fill(left+76+p.font.width(label[:a]),top+2,p.font.width(label[a:b]),15,NAVY)
            p.text(label[:a],left+76,top+4)
            p.text(label[a:b],left+76+p.font.width(label[:a]),top+4,LIGHT if a!=b else BLACK)
            p.text(label[b:],left+76+p.font.width(label[:b]),top+4)
            p.fill(left+76+p.font.width(label[:shell.address_entry.cursor]),top+3,1,14,BLACK)
        else:p.text(label,left+76,top+4)
        p.cr.restore()
        shell.hit(left+55,top+1,width-76,18,('explorer-address',win))
        shell.hit(left+width-22,top+1,18,18,('explorer-locations',win))
        top+=26
    bottom=y+h-24
    p.bevel(left,top,width,bottom-top,True)
    p.fill(left+1,top+1,width-3,1,BLACK)
    p.fill(left+1,top+1,1,bottom-top-2,BLACK)
    p.fill(left+2,top+2,width-4,bottom-top-4,LIGHT)
    origin=left+2,top+2
    p.cr.save();p.cr.rectangle(origin[0],origin[1],max(0,width-4),max(0,bottom-top-4));p.cr.clip()
    if win.web_view:
        compact=bottom-top<200
        panel_visible=width-4>=400
        if compact:
            image=surface(shell,'web-heading' if computer else 'control-web-heading')
            if image:
                p.cr.save();p.cr.rectangle(origin[0]+14,origin[1]+4,image.get_width(),23);p.cr.clip()
                p.image(image,origin[0]+14,origin[1]+4);p.cr.restore()
        else:
            for name,dx,dy in (('web-computer',2,2),('web-heading',108,20)):
                image=surface(shell,name if computer else 'control-'+name)
                if image:p.image(image,origin[0]+dx,origin[1]+dy)
            p.fill(origin[0]+84,origin[1]+44,width-88,1,BLACK)
        from win95lx.shell.webview_panel import draw as draw_panel
        if panel_visible:
            if not draw_panel(shell,p,win,left,top,width,bottom-top,panel_top=32 if compact else 88):
                description=surface(shell,'web-description')
                if description:p.image(description,left+20,top+104)
        icon_left=origin[0]+(round((width-4)*.3)+6 if panel_visible else 6)
        icon_top=origin[1]+(34 if compact else 58)
        step=75
    else:
        icon_left=origin[0]+10;icon_top=origin[1]+10;step=102
    if not computer:
        from win95lx.shell.namespace_view import draw as draw_namespace
        draw_namespace(shell,p,win,entries,icon_left,icon_top,
                       max(0,left+width-2-icon_left),max(0,bottom-2-icon_top))
    for index,(ident,label,target) in enumerate(entries if computer else ()):
        # Namespace contents reflect the Linux machine; no fictitious A: or Windows CD.
        if win.web_view:
            dx,dy=((step,0),(0,75))[index] if computer else (index*step,0)
        else:dx,dy=index*step,0
        shell.icon(p,ident,label,icon_left+dx,icon_top+dy,
                   ('item',win,target,label,(dx,dy)),shell.item_selection in ((win,label),(win,None)) and shell.state.active is win and shell.popup is None,
                   image_offset=-1 if win.web_view else 0,label_offset=1 if win.web_view and index==0 else 0)
    p.cr.restore()
    sy=y+h-23
    if shell.popup and isinstance(shell.popup[2],tuple) and shell.popup[2]==(win,'File'):
        hints={'shortcut':'Creates shortcuts to the selected items.',
               'close':'Closes this window.', 'computer':'Opens My Computer.',
               'offline':'Works offline without connecting to the Internet.',
               'properties':'Displays the properties of the selected item.'}
        hint=hints.get(shell.drive_menu_highlight,'Contains commands for working with the selected items.')
        p.fill(left,sy-2,width,23,FACE)
        p.fill(left,sy-2,width,1,LIGHT)
        p.text(hint,left+3,sy+3)
        return
    first=max(120,round(width*.30));last=max(first+60,width-215)
    for a,b in ((0,first),(first+2,last),(last+2,width)):
        p.bevel(left+a,sy,b-a,18,True)
    count=len(entries) if shell.item_selection==(win,None) else 1 if shell.item_selection and shell.item_selection[0] is win else 0
    p.text(f'{count} object(s) selected' if count else f'{len(entries)} object(s)',left+3,sy+2)
    icon=shell.small_images.get(small_icon)
    if icon:p.image(icon,left+last+5,sy+1)
    p.text(win.title,left+last+24,sy+2)
