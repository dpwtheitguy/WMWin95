#!/usr/bin/env python3
"""Fonts inventory, native regions, keyboard/pointer and isolated installation."""
import argparse,json,os,subprocess,sys,time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--require-x11',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    import gi;gi.require_foreign('cairo');import cairo
    from win95lx.shell.app import Shell,Gtk,Gdk
    display=Gdk.Display.get_default()
    if a.require_x11 and ('X11' not in type(display).__name__ or display.get_name()!=os.environ.get('DISPLAY')):raise RuntimeError('The isolated test requires the requested X11 display; refusing to create a window on another backend.')
    from win95lx.apps.fonts import FontsWindow,FontPreview
    from win95lx.apps.dialogs import FileDialog
    from win95lx.control_panel.font_catalog import FontCatalog,fontconfig,FontFace
    from check_menu_seams import flush_draws
    from check_reference_ui import compare_region
    from pixels import read
    checks=[];comparisons=[]
    with TemporaryDirectory() as temporary:
        home=Path(temporary);root=home/'share/fonts/Win95LX';config=home/'fontconfig.xml';config.write_text(f'<?xml version="1.0"?><!DOCTYPE fontconfig SYSTEM "fonts.dtd"><fontconfig><dir>/usr/share/fonts</dir><dir>{root}</dir><cachedir>{home}/cache</cachedir></fontconfig>')
        with patch('pathlib.Path.home',return_value=home),patch.dict(os.environ,{'HOME':str(home),'XDG_DATA_HOME':str(home/'share'),'FONTCONFIG_FILE':str(config)}):
            scanner=fontconfig();scanner.refresh();catalog=FontCatalog(root=root,manifest=home/'config/fonts.json',home=home,scanner=scanner)
            shell=Shell(ROOT/'private/shell-assets');shell.show_all();flush_draws(Gtk)
            source=ROOT/'private/shell-assets/fonts-source-arial.ttf';bold=ROOT/'private/shell-assets/fonts-source-arial-bold.ttf'
            face=scanner.query(source)[0]
            class Fixture:
                def inventory(self):return (face,)
                def removal_reason(self,path):return 'System font read-only'
            window=FontsWindow(shell,Fixture());window.show_all();flush_draws(Gtk)
            def capture(win,name,size=None):
                if size:win.resize(*size);flush_draws(Gtk)
                w,h=win.area.get_allocated_width(),win.area.get_allocated_height();surface=cairo.ImageSurface(cairo.FORMAT_RGB24,w,h);win.caption_active=True;win.draw(win.area,cairo.Context(surface));path=a.output/(name+'.png');surface.write_to_png(str(path));return read(path)
            try:
                actual=capture(window,'fonts-native-frame');reference=read(ROOT/'private/screenshots/fonts-20261126/classic-fonts-default.png')
                for name,rect in (('caption-menu',(0,0,600,44)),('first-true-type-icon',(27,46,32,32)),('first-font-cell',(6,44,75,75)),('left-pane-inset',(0,44,6,342))):
                    x,y,w,h=rect;diff=compare_region(actual,reference,(66+x,66+y,w,h),(x,y));comparisons.append({'region':name,'differing_pixels':diff});assert diff==0,(name,diff)
                event=lambda x,y:SimpleNamespace(x=x,y=y,x_root=x+50,y_root=y+50,state=0,button=1,type=Gdk.EventType.BUTTON_PRESS,time=Gdk.CURRENT_TIME)
                window.press(window.area,event(30,65));assert window.selection=={0}
                selected=capture(window,'fonts-first-selected');selected_reference=read(ROOT/'private/screenshots/fonts-20261126/classic-fonts-first-selected-attempt.png')
                difference=compare_region(selected,selected_reference,(72,110,75,75),(6,44));comparisons.append({'region':'selected-first-font-cell','differing_pixels':difference});assert difference==0,('selected-cell',difference)
                window.key(window,SimpleNamespace(keyval=Gdk.KEY_Return,state=0));flush_draws(Gtk);assert window.previews;preview=window.previews[-1]
                capture(preview,'font-preview-real-arial');assert preview.face.family=='Arial';assert preview.content_height>preview.get_size()[1]-70
                preview.key(preview,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert preview.scroll>0;capture(preview,'font-preview-end');preview.key(preview,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));assert preview.scroll==0;preview.command('close');flush_draws(Gtk);window.get_window().focus(Gdk.CURRENT_TIME);flush_draws(Gtk)
                window.command(('menu','File'));flush_draws(Gtk);assert window.caption_active;capture(window,'fonts-file-menu-owner')
                delete=next(row for row in window.menu_popup.rows if row and row[1]=='delete');assert not delete[2]
                window.menu_popup.key(window.menu_popup,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0));assert window.menu_popup is None
                window.key(window,SimpleNamespace(keyval=Gdk.KEY_space,state=Gdk.ModifierType.MOD1_MASK));flush_draws(Gtk);assert window.menu_popup
                window.menu_popup.finish();window.command(('system','move'));before=(*window.get_position(),*window.get_size());window.key(window,SimpleNamespace(keyval=Gdk.KEY_Right,state=0));window.key(window,SimpleNamespace(keyval=Gdk.KEY_Escape,state=0));assert (*window.get_position(),*window.get_size())==before
                window.destroy();window=None
                checks.append('Native folder frame/menu/inset and first TrueType icon; full-cell pointer selection; real Arial preview and scrolling; File disabled state, owner focus, Alt+Space and canceled keyboard Move')
                window=FontsWindow(shell,catalog);window.show_all();flush_draws(Gtk);assert window.faces
                started=time.perf_counter();catalog.install(source);discovery_ms=(time.perf_counter()-started)*1000
                seen=subprocess.check_output(['fc-list','--format','%{file}\n'],text=True);assert str(root/source.name) in seen
                window.refresh();index=next(i for i,f in enumerate(window.faces) if f.path==root/source.name);window.select(index);capture(window,'fonts-installed-selected')
                assert next(row for row in window.menu_rows('File') if row and row[1]=='delete')[2]
                with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.NO):window.command('delete')
                assert (root/source.name).exists()
                dialog=FileDialog(window,bold.parent,(('Fonts',('*.ttf','*.TTF')),));dialog.show_all();flush_draws(Gtk);assert dialog.folder==bold.parent;dialog.destroy()
                with patch('win95lx.apps.dialogs.choose_file',return_value=bold):window.command('install')
                assert (root/bold.name).exists();window.refresh();index=next(i for i,f in enumerate(window.faces) if f.path==root/source.name);window.select(index)
                with patch('win95lx.apps.dialogs.message_box',return_value=Gtk.ResponseType.YES):window.command('delete')
                assert not (root/source.name).exists();seen=subprocess.check_output(['fc-list','--format','%{file}\n'],text=True);assert str(root/source.name) not in seen
                window.key(window,SimpleNamespace(keyval=Gdk.KEY_End,state=0));assert window.cursor==len(window.faces)-1;assert window.scroll>0
                capture(window,'fonts-scrolled-end');window.key(window,SimpleNamespace(keyval=Gdk.KEY_Home,state=0));assert window.cursor==0
                window.command('all');assert len(window.selection)==len(window.faces);window.command('invert');assert not window.selection
                window.command('details');capture(window,'fonts-details');window.command('large');window.command('status');assert not window.status;window.command('status')
                capture(window,'fonts-resized',(700,500));assert window.area.get_allocated_width()==700
                window.command('maximize');flush_draws(Gtk);assert window.restored;window.command('maximize');flush_draws(Gtk);assert window.restored is None
                with patch.object(window,'error') as error:window.install_uris('https://example.com/font.ttf');error.assert_called_once()
                checks.append('Real per-user font copy, native cache refresh and independent fc-list discovery/removal; deletion No/Yes, native file-chooser install route, selection endpoints, scrolling, Select All/Invert, Details, status toggle, resize/maximize/restore, nonlocal clipboard URL rejection')
                # Catalog operations are immediate; no Apply/reset of existing
                # system fonts or non-managed user font files is performed.
                for path in list(root.glob('*')):
                    if catalog.removal_reason(path) is None:catalog.remove(path)
            finally:
                if window:window.destroy()
                shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
    from evidence import identity
    report={**identity(ROOT,Path(__file__).resolve(),[ROOT/'private/screenshots/fonts-20261126/classic-fonts-default.png']),'checks':checks,'comparisons':comparisons,'font_install_cache_ms':round(discovery_ms,3),'display_backend':type(display).__name__,'display_name':display.get_name(),'font_cache_method':'Fontconfig FcDirCacheRescan with refresh and visibility verification','display':[Gdk.Screen.get_default().get_width(),Gdk.Screen.get_default().get_height()],'failed':0,'pixel_scope':'Named native folder regions and unselected/selected first font cells only; preview glyph rasterization, resized states, menus and install dialog are not pixel accepted.'}
    (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
