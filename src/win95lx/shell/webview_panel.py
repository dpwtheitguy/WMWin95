"""Render the IE4 selection panel using original mono Verdana, not menu glyphs."""
import json,math
from win95lx.assets.raster_font import RasterFont
from win95lx.explorer.webview_details import describe,wrapped,size_text
from win95lx.shell.widgets import Painter,BLACK,FACE,LIGHT,SHADOW
from win95lx.control_panel.catalog import labels as control_labels


def draw(shell,p,win,left,top,width,height,*,panel_top=88):
    catalog=shell.assets/'webview-strings.json'
    if not catalog.is_file():return False
    if not hasattr(shell,'webview_strings'):
        shell.webview_strings=json.loads(catalog.read_text())
        shell.webview_fonts=[RasterFont(shell.assets/f'webview-verdana-{weight}.json') for weight in ('regular','bold')]
    selected=None
    if shell.item_selection and shell.item_selection[0] is win:
        selected=[shell.item_selection[1]] if shell.item_selection[1] is not None else (list(control_labels()) if win.kind=='control' else ['(C:)','Control Panel'])
    if win.kind=='control':
        from win95lx.explorer.webview_details import Details
        if selected and selected[0]=='Display':details=Details('Display','Changes settings for your display.')
        elif selected and selected[0]=='Mouse':details=Details('Mouse','Changes settings for your mouse.')
        elif selected and len(selected)==1 and selected[0] in control_labels():
            if not hasattr(shell,'cpl_descriptions'):
                path=shell.assets/'cpl-descriptions.json';shell.cpl_descriptions=json.loads(path.read_text()) if path.exists() else {}
            details=Details(selected[0],shell.cpl_descriptions.get(selected[0],''))
        elif selected:details=Details(title=f'{len(selected)} objects selected.',names=tuple(selected))
        else:details=describe(None,shell.webview_strings,shell._drive.view.root)
    else:details=describe(selected,shell.webview_strings,shell._drive.view.root)
    regular,bold=shell.webview_fonts
    rp,bp=Painter(p.cr,regular),Painter(p.cr,bold)
    p.cr.save();p.cr.rectangle(left+2,top+panel_top,max(0,width*.3-4),max(0,height-panel_top));p.cr.clip()
    p.cr.translate(0,-win.info_scroll)
    x,y=left+22,top+panel_top+17
    available=max(1,round((width-4)*.3)-44)
    if details.title:
        for line in wrapped(details.title,bold,available):bp.text(line,x,y);y+=13
    if details.type_name:rp.text(details.type_name,x,y);y+=13
    if details.description:
        if details.title:y+=13
        for line in wrapped(details.description,regular,available):rp.text(line,x,y);y+=13
    for name in details.names:
        y+=13
        for line in wrapped(name,regular,available):rp.text(line,x,y);y+=13
    if details.disk:
        total,used,free=details.disk;y+=26
        rp.text('Capacity: '+size_text(total),x,y);y+=26
        for caption,value,color in (('Used: ',used,FACE),('Free: ',free,LIGHT)):
            p.fill(x,y,12,12,BLACK);p.fill(x+1,y+1,10,10,color)
            rp.text(caption+size_text(value),x+18,y-1);y+=26
        # Native-sized 100x50 disk chart; values come from the real filesystem.
        cy=y+25
        p.cr.save();p.cr.translate(x+50,cy);p.cr.scale(50,20)
        p.cr.arc(0,.4,1,0,math.tau);p.cr.set_source_rgb(.75,.75,.75);p.cr.fill_preserve();p.cr.set_source_rgb(0,0,0);p.cr.set_line_width(.025);p.cr.stroke()
        p.cr.arc(0,0,1,0,math.tau);p.cr.set_source_rgb(1,1,1);p.cr.fill_preserve();p.cr.set_source_rgb(0,0,0);p.cr.stroke()
        p.cr.move_to(0,0);p.cr.arc(0,0,1,math.pi,math.pi+math.tau*(used/total if total else 0));p.cr.close_path();p.cr.set_source_rgb(.75,.75,.75);p.cr.fill_preserve();p.cr.set_source_rgb(0,0,0);p.cr.stroke();p.cr.restore()
        y=cy+30
    win.info_scroll_max=max(0,int(y+5-(top+height)))
    win.info_scroll=max(0,min(win.info_scroll,win.info_scroll_max))
    p.cr.restore()
    if win.info_scroll_max:
        from win95lx.shell.scrollbar import VerticalScrollbar
        sx,sy=left+round((width-4)*.3)-14,top+panel_top
        bar=VerticalScrollbar(int(height-panel_top),win.info_scroll_max)
        bar.draw(p,sx,sy,win.info_scroll)
        shell.hit(sx,sy,16,16,('info-scroll',win,-13))
        shell.hit(sx,sy+bar.height-16,16,16,('info-scroll',win,13))
    return True
