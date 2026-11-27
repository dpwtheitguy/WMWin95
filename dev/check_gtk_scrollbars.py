#!/usr/bin/env python3
"""Isolated GTK scrollbar track pixels, states and native app profiles."""
import argparse,collections,json,os,sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_version('Gtk','3.0');gi.require_foreign('cairo');import cairo
    from gi.repository import Gtk,Gdk
    from win95lx.shell.accessories import SCROLLBAR_STYLE
    from check_menu_seams import flush_draws
    from pixels import read
    display=Gdk.Display.get_default();assert display and 'X11'in type(display).__name__ and display.get_name()==os.environ.get('DISPLAY')
    provider=Gtk.CssProvider();provider.load_from_data(SCROLLBAR_STYLE);Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(),provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION+5)
    assert (ROOT/'src/win95lx/shell/resources/scrollbar-track.png').is_file(),'Missing generated GTK track resource'
    assert (ROOT/'src/win95lx/shell/resources/scrollbar-track@2.png').is_file(),'Missing generated2xGTK track resource'
    scale=int(os.environ.get('GDK_SCALE','1'));comparisons=[];checks=[];references=[]
    native=ROOT/'private/screenshots/gtk-scrollbars-20261126'
    for name,rect in [('native-notepad-scrollable',(584,80,12,30)),('native-wordpad-scrollable',(580,160,12,30)),('native-file-open-windows',(240,219,30,12))]:
        path=native/(name+'.png');references.append(path);w,h,px=read(path);x,y,rw,rh=rect;assert all(px[(y+yy)*w+x+xx][:3]==(255,255,255)for yy in range(rh)for xx in range(rw))
    for profile,context,klass,expected in [('generic',None,'win95-app-scrollbar','checker'),('notepad',None,'notepad-scrollbar','white'),('wordpad','win95-wordpad',None,'white'),('file','win95-file',None,'white'),('native-file','win95-native-file',None,'white')]:
        for orientation in(Gtk.Orientation.VERTICAL,Gtk.Orientation.HORIZONTAL):
            window=Gtk.Window();box=Gtk.Box();window.add(box)
            if context:box.get_style_context().add_class(context)
            adjustment=Gtk.Adjustment(value=0,lower=0,upper=10000,step_increment=1,page_increment=100,page_size=100)
            bar=Gtk.Scrollbar(orientation=orientation,adjustment=adjustment)
            if klass:bar.get_style_context().add_class(klass)
            vertical=orientation==Gtk.Orientation.VERTICAL;bar.set_size_request(16 if vertical else 180,180 if vertical else 16);box.pack_start(bar,False,False,0);window.show_all();flush_draws(Gtk)
            try:
                for state,flags in [('normal',Gtk.StateFlags.NORMAL),('hover',Gtk.StateFlags.PRELIGHT),('pressed',Gtk.StateFlags.ACTIVE),('disabled',Gtk.StateFlags.INSENSITIVE)]:
                    bar.set_sensitive(state!='disabled');bar.unset_state_flags(Gtk.StateFlags.PRELIGHT|Gtk.StateFlags.ACTIVE);bar.set_state_flags(flags,False);flush_draws(Gtk)
                    w,h=bar.get_allocated_width(),bar.get_allocated_height();surface=cairo.ImageSurface(cairo.FORMAT_RGB24,w*scale,h*scale);surface.set_device_scale(scale,scale);bar.draw(cairo.Context(surface));path=a.output/f'{profile}-{int(orientation)}-{state}.png';surface.write_to_png(str(path));sw,sh,pixels=read(path)
                    rect=(2,80,12,30)if vertical else(80,2,30,12);x,y,rw,rh=(v*scale for v in rect);sample=[pixels[(y+yy)*sw+x+xx][:3]for yy in range(rh)for xx in range(rw)];counts=collections.Counter(sample)
                    if expected=='white':assert counts=={(255,255,255):rw*rh},(profile,state,counts)
                    else:
                        assert counts=={(255,255,255):rw*rh//2,(192,192,192):rw*rh//2},(profile,state,counts)
                        assert all(sample[yy*rw+xx]!=sample[yy*rw+xx+scale]for yy in range(rh)for xx in range(rw-scale))
                        assert all(sample[yy*rw+xx]!=sample[(yy+scale)*rw+xx]for yy in range(rh-scale)for xx in range(rw))
                    rgba=bar.get_style_context().get_background_color(flags)
                    comparisons.append({'profile':profile,'orientation':'vertical'if vertical else'horizontal','state':state,'track':expected,'rectangle':rect,'colors':{str(color):count for color,count in counts.items()},'root_background_rgba':[rgba.red,rgba.green,rgba.blue,rgba.alpha],'failed':False})
            finally:window.destroy()
    Gtk.StyleContext.remove_provider_for_screen(Gdk.Screen.get_default(),provider)
    # Exercise actual app providers and persistent ScrolledWindow gutters.
    def scrollers(widget):
        if isinstance(widget,Gtk.ScrolledWindow):yield widget
        if isinstance(widget,Gtk.Container):
            for child in widget.get_children():yield from scrollers(child)
    with TemporaryDirectory() as directory,patch('pathlib.Path.home',return_value=Path(directory)):
        from win95lx.apps.notepad import NotepadWindow
        from win95lx.apps.wordpad import build_window
        from win95lx.apps.dialogs import FileDialog
        folder=Path(directory)/'files';folder.mkdir()
        for i in range(40):(folder/f'file-{i:02}.txt').write_text('text')
        notes=NotepadWindow();word=build_window(ROOT/'private/shell-assets');notes.show_all();word.show_all();flush_draws(Gtk)
        parents=[Gtk.Window(),Gtk.Window()];parents[1].dialog_assets=ROOT/'private/shell-assets'
        dialogs=[FileDialog(parent,folder,(('Text Documents',('*.txt',),'.txt'),))for parent in parents]
        try:
            for dialog in dialogs:dialog.show_all()
            flush_draws(Gtk)
            connections=[]
            for name,window in [('notepad',notes),('wordpad',word),('fallback-file',dialogs[0]),('native-file',dialogs[1])]:
                items=list(scrollers(window));assert items,name
                assert all(not item.get_overlay_scrolling()for item in items),name
                for phase in('empty','populated','empty-again'):
                    if name in('notepad','wordpad'):window.buffer.set_text('1\n'*100 if phase=='populated'else'')
                    elif phase=='populated':window.change_folder(folder)
                    else:window.files.clear()
                    flush_draws(Gtk);bar=items[0].get_vscrollbar();adjustment=items[0].get_vadjustment()
                    absent=adjustment.get_upper()-adjustment.get_lower()<=adjustment.get_page_size()+1e-9
                    assert absent==(phase!='populated'),(name,phase,adjustment.get_upper(),adjustment.get_page_size())
                    assert bar.get_style_context().has_class('win95-unscrollable')==absent
                    if not bar.get_mapped():
                        assert name in('wordpad','fallback-file','native-file')and absent
                        comparisons.append({'profile':name,'state':'actual-'+phase,'native_hidden':True,'pixel_scope':'No pixels claimed for an automatically hidden empty-list scrollbar','failed':False});continue
                    w,h=bar.get_allocated_width(),bar.get_allocated_height();assert w>=16 and h>40,(name,w,h)
                    surface=cairo.ImageSurface(cairo.FORMAT_RGB24,w*scale,h*scale);surface.set_device_scale(scale,scale);bar.draw(cairo.Context(surface));path=a.output/(name+'-actual-'+phase+'.png');surface.write_to_png(str(path));sw,sh,pixels=read(path)
                    x,y=2,16+(h-32)*3//4;rw,rh=min(12,w-4),min(10,h-16-y);x,y,rw,rh=(v*scale for v in(x,y,rw,rh));counts=collections.Counter(pixels[(y+yy)*sw+x+xx][:3]for yy in range(rh)for xx in range(rw));assert counts=={(255,255,255):rw*rh},(name,phase,counts)
                    comparisons.append({'profile':name,'state':'actual-'+phase,'track':'white','rectangle':[x,y,rw,rh],'colors':{str(color):count for color,count in counts.items()},'failed':False})
                for item in items:connections.extend(item._win95_scrollbar_connections)
                checks.append(name+': empty/populated/empty track; native thumb absence; persistent non-overlay gutter')
            # Replacing an adjustment must disconnect the old watcher as well.
            old=list(notes.scroller._win95_scrollbar_connections);notes.scroller.set_vadjustment(Gtk.Adjustment());flush_draws(Gtk)
            assert all(not adjustment.handler_is_connected(handler)for adjustment,handler in old)
            connections.extend(notes.scroller._win95_scrollbar_connections)
        finally:
            for window in[*dialogs,*parents,notes,word]:window.destroy()
            assert all(not adjustment.handler_is_connected(handler)for adjustment,handler in connections)
            checks.append('Adjustment replacement and window destroy disconnect all scrollbar watchers')
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),references),'gtk_scale':scale,'scope':'Exposed GTK tracks only: native IE4 app-specific white profiles; generic192/255 single-pixel tile; not full scrollbar/button fidelity','comparisons':comparisons,'checks':checks,'failed':0}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'comparisons':len(comparisons),'checks':checks,'failed':0},indent=2))
if __name__=='__main__':main()
