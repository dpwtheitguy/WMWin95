#!/usr/bin/env python3
"""Compare full native desktop shortcut cells, not resource identities alone."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
CASES={'classic':[('drive',9,2,'W95UAT Drive'),('folder',4,77,'W95UAT Folder'),('control',36,152,'W95UAT Control Panel'),('file',152,227,'W95UAT File')],
       'ie4':[('drive',9,227,'W95UAT Drive'),('folder',4,377,'W95UAT Folder'),('control',36,152,'W95UAT Control Panel'),('file',152,302,'W95UAT File')]}
LONG_TEXT='W95UAT This deliberately long shortcut name needs more than three lines and must not be guessed'
def reference(profile,name,selected):
    path=('shortcut-classic-selected-'+name if selected else'shortcut-classic-refresh')if profile=='classic'else('shortcut-ie4-'+name+'-selected'if selected else'shortcut-ie4-neutral')
    return ROOT/'private/screenshots'/(path+'-20261127.png')
def inactive_reference(profile):return ROOT/'private/screenshots'/('shortcut-'+profile+'-file-inactive-20261127.png')
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--shell',action='store_true');parser.add_argument('--profile',choices=('classic','ie4'),default='ie4');args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    import cairo
    from win95lx.assets.bitmap import BitmapFont
    from win95lx.shell.widgets import Painter
    from win95lx.shell.icon_labels import draw_icon_label
    from pixels import read,write
    font=BitmapFont((ROOT/'private/shell-assets/ms-sans-serif-8.fnt').read_bytes());comparisons=[];references=[inactive_reference(args.profile)]
    if args.profile=='ie4':references.append(ROOT/'private/screenshots/shortcut-ie4-active-wallpaper-20261127.png')
    for name,ident,y,text in CASES[args.profile]:
        dy=-1 if name=='folder'and args.profile=='ie4'else 0;phase=1 if dy else 0
        base=cairo.ImageSurface.create_from_png(str(ROOT/'private/shell-assets'/('explorer-folder-32.png'if dy else f'shell32-group-{ident}.png')));overlay=cairo.ImageSurface.create_from_png(str(ROOT/'private/shell-assets/shell32-group-30.png'))
        for selected in(False,True):
            ref=reference(args.profile,name,selected);references.append(ref)
            nw,nh,native=read(ref);expected=[native[(y+yy)*nw+75+xx]for yy in range(75)for xx in range(75)]
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,75,75);p=Painter(cairo.Context(surface),font);p.fill(0,0,75,75,(0,128,128))
            if selected:p.selected_image(base,21,dy,phase=phase)
            else:p.image(base,21,dy)
            p.image(overlay,21,0);metrics=draw_icon_label(p,text,37,36,desktop=True,selected=selected,focused=selected,profile=args.profile)
            filename=name+('-selected'if selected else'-normal');surface.write_to_png(str(args.output/(filename+'.png')));_,_,actual=read(args.output/(filename+'.png'));difference=sum(a!=b for a,b in zip(actual,expected));write(args.output/(filename+'-native.png'),75,75,expected);assert difference==0,(filename,difference)
            comparisons.append({'name':filename,'differing_pixels':difference,'native_rect':[75,y,75,75],'label_metrics':metrics})
            # A checker that only checks the group30 identity misses both the
            # former single-line baseline defect and dithered overlay regressions.
            old=cairo.ImageSurface(cairo.FORMAT_RGB24,75,75);oldp=Painter(cairo.Context(old),font);oldp.fill(0,0,75,75,(0,128,128));oldp.selected_image(base,21,0)if selected else oldp.image(base,21,0);oldp.image(overlay,21,0)
            from win95lx.shell.taskbar import title_that_fits
            label=title_that_fits(font,text,72,False)
            left=37-font.width(label)//2
            if selected:oldp.fill(left-1,35,font.width(label)+2,15,(0,0,128))
            oldp.text(label,left,35,(255,255,255));old.write_to_png(str(args.output/(filename+'-old.png')));_,_,oldpx=read(args.output/(filename+'-old.png'));legacy=sum(oldpx[yy*75+xx]!=expected[yy*75+xx]for yy in range(35,75)for xx in range(75));assert legacy>0
            comparisons[-1]['legacy_cell_differing_pixels']=legacy
    # Losing desktop focus hides both icon selection and the label highlight.
    file_y=next(y for name,ident,y,text in CASES[args.profile]if name=='file');nw,nh,native=read(inactive_reference(args.profile));normal=read(args.output/'file-normal.png')[2];expected=[native[(file_y+yy)*nw+75+xx]for yy in range(75)for xx in range(75)];assert normal==expected;comparisons.append({'name':'file-inactive','differing_pixels':0})
    if args.profile=='ie4':
        base=cairo.ImageSurface.create_from_png(str(ROOT/'private/shell-assets/shell32-group-152.png'));overlay=cairo.ImageSurface.create_from_png(str(ROOT/'private/shell-assets/shell32-group-30.png'))
        for mode,selected,active,filename in [('normal',False,True,'shortcut-ie4-neutral'),('selected',True,True,'shortcut-ie4-long-selected'),('inactive',True,False,'shortcut-ie4-long-inactive')]:
            ref=ROOT/'private/screenshots'/(filename+'-20261127.png');references.append(ref);nw,nh,native=read(ref);expected=[native[(2+yy)*nw+150+xx]for yy in range(150)for xx in range(75)]
            surface=cairo.ImageSurface(cairo.FORMAT_RGB24,75,150);p=Painter(cairo.Context(surface),font);p.fill(0,0,75,150,(0,128,128))
            if selected and active:p.selected_image(base,21,0)
            else:p.image(base,21,0)
            p.image(overlay,21,0);metrics=draw_icon_label(p,LONG_TEXT,37,36,desktop=True,selected=selected,focused=selected,active=active)
            path=args.output/('long-'+mode+'.png');surface.write_to_png(str(path));_,_,actual=read(path);difference=sum(a!=b for a,b in zip(actual,expected));assert difference==0,('long',mode,difference);comparisons.append({'name':'long-'+mode,'differing_pixels':difference,'lines':len(metrics['lines'])})
    if args.shell:comparisons.extend(check_shell(args.output,args.profile))
    from hashlib import sha256
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),list(set(references))),'profile':args.profile+' Windows95 OSR2.5, standard256-color teal desktop','comparisons':comparisons,'references':{str(path.relative_to(ROOT)):sha256(path.read_bytes()).hexdigest()for path in set(references)},'failed':sum(row.get('differing_pixels',0)>0 for row in comparisons),'scope':'Native32px desktop shortcuts and full75x75cells; no16px/Plus or arbitrarywallpaper-focus-color acceptance.'};(args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if report['failed']:raise SystemExit(1)
def check_shell(output,profile):
    if profile!='ie4':raise ValueError('Actual shell is the IE4 baseline; Classic component comparisons do not add a product preset.')
    import os,tempfile
    from unittest.mock import patch
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    from win95lx.shell.widgets import Painter
    from win95lx.explorer.namespace import Shortcut,write_shortcut
    from check_menu_seams import flush_draws
    from pixels import read
    d=Gdk.Display.get_default();assert os.environ.get('GDK_BACKEND')=='x11' and not os.environ.get('WAYLAND_DISPLAY') and 'X11'in type(d).__name__ and d.get_name()==os.environ['DISPLAY'] and d.get_name().split('.')[0]not in(':0',':1')
    comparisons=[]
    with tempfile.TemporaryDirectory(prefix='w95uat-shortcut-cells-')as directory,patch('pathlib.Path.home',return_value=Path(directory)):
        home=Path(directory);folder=home/'Folder';folder.mkdir();document=home/'sample.txt';document.write_text('Owned visual fixture')
        shell=Shell(ROOT/'private/shell-assets');shell.disconnect_by_func(Gtk.main_quit);shell.show_all();flush_draws(Gtk);shell.desktop_focus=True;shell.get_window().focus(Gdk.CURRENT_TIME);flush_draws(Gtk)
        links={'drive':Shortcut('namespace','drive'),'folder':Shortcut('path',str(folder)),'control':Shortcut('namespace','control'),'file':Shortcut('path',str(document))};data=[(name,y,text,links[name])for name,ident,y,text in CASES[profile]]
        try:
            shell.desktop_folder.mkdir(parents=True,exist_ok=True)
            for name,y,text,link in data:
                dest=write_shortcut(shell.desktop_folder,text,link);dest.rename(shell.desktop_folder/(text+'.desktop'));shell.desktop_icons.positions['file:'+text+'.desktop']=(75,y)
            shell.refresh_desktop_files()
            for selected in(False,True):
                for name,y,text,link in data:
                    shell.state.selection='file:'+text+'.desktop'if selected else None;shell.desktop_focus=True
                    image=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw_desktop(Painter(cairo.Context(image),shell.font),shell.width,shell.height);path=output/('actual-shell-'+name+('-selected'if selected else'-normal')+'.png');image.write_to_png(str(path))
                    w,h,p=read(path);ref=reference(profile,name,selected);nw,nh,n=read(ref)
                    diff=sum(p[(y+yy)*w+75+xx]!=n[(y+yy)*nw+75+xx]for yy in range(75)for xx in range(75));
                    comparisons.append({'name':'actual-shell-'+name+('-selected'if selected else'-normal'),'differing_pixels':diff})
            # Full source renderer, not just its helper, must expand and shrink.
            dest=write_shortcut(shell.desktop_folder,LONG_TEXT,Shortcut('path',str(document)));dest.rename(shell.desktop_folder/(LONG_TEXT+'.desktop'));shell.desktop_icons.positions['file:'+LONG_TEXT+'.desktop']=(150,2);shell.refresh_desktop_files()
            for mode,selected,active,filename in [('normal',False,True,'shortcut-ie4-neutral'),('selected',True,True,'shortcut-ie4-long-selected'),('inactive',True,False,'shortcut-ie4-long-inactive')]:
                shell.desktop_focus=active;shell.state.selection='file:'+LONG_TEXT+'.desktop'if selected else None
                image=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw_desktop(Painter(cairo.Context(image),shell.font),shell.width,shell.height);path=output/('actual-shell-long-'+mode+'.png');image.write_to_png(str(path));w,h,p=read(path);nw,nh,n=read(ROOT/'private/screenshots'/(filename+'-20261127.png'));diff=sum(p[(2+yy)*w+150+xx]!=n[(2+yy)*nw+150+xx]for yy in range(150)for xx in range(75));comparisons.append({'name':'actual-shell-long-'+mode,'differing_pixels':diff})
            shell.desktop_focus=True;shell.state.selection=None;shell.wallpaper.name='Clouds';shell.wallpaper.mode='center'
            image=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw_desktop(Painter(cairo.Context(image),shell.font),shell.width,shell.height);path=output/'actual-shell-wallpaper.png';image.write_to_png(str(path));w,h,p=read(path);nw,nh,n=read(ROOT/'private/screenshots/shortcut-ie4-active-wallpaper-20261127.png')
            for name,y,text,link in data:
                # Compare the whole opaque text union; bitmap palette/rendering
                # outside the label is a separate wallpaper acceptance scope.
                from win95lx.shell.icon_labels import icon_label_metrics
                metrics=icon_label_metrics(text,shell.font,112,y+36);xx,yy,rw,rh=metrics['rect'];diff=sum(p[(yy+j)*w+xx+i]!=n[(yy+j)*nw+xx+i]for j in range(rh)for i in range(rw));comparisons.append({'name':'actual-shell-wallpaper-label-'+name,'differing_pixels':diff,'rect':metrics['rect']})
            shell.wallpaper.name='(None)'
            shell.desktop_focus=False;shell.state.selection='file:W95UAT File.desktop';image=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw_desktop(Painter(cairo.Context(image),shell.font),shell.width,shell.height);path=output/'actual-shell-inactive.png';image.write_to_png(str(path));w,h,p=read(path);nw,nh,n=read(inactive_reference(profile));file_y=next(y for name,y,text,link in data if name=='file');diff=sum(p[(file_y+yy)*w+75+xx]!=n[(file_y+yy)*nw+75+xx]for yy in range(75)for xx in range(75));assert diff==0,('actual-shell-inactive',diff);comparisons.append({'name':'actual-shell-inactive','differing_pixels':diff})
        finally:shell.destroy()
    return comparisons

if __name__=='__main__':main()
