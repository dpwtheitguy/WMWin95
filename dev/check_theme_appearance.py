#!/usr/bin/env python3
"""Owned X11 caption geometry, real pointer hit and persistence acceptance."""
import argparse,json,os,select,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'dev')]

def child(a):
    import gi
    gi.__path__.append(a.gi_path);gi.require_version('Gtk','3.0');gi.require_foreign('cairo')
    from gi.repository import Gtk,Gdk
    from check_accessibility import owned_display_guard
    assert owned_display_guard(os.environ['DISPLAY'],a.pid)
    from check_menu_seams import flush_draws
    from win95lx.apps.property_sheet import PropertySheet
    from win95lx.assets.bitmap import BitmapFont
    from win95lx.control_panel.theme_appearance import appearance,AppearanceProvider,FontLibrary,DEFAULT_COLORS,DEFAULT_FONTS,DEFAULT_METRICS
    from types import SimpleNamespace
    from copy import deepcopy
    import ctypes
    class Sheet(PropertySheet):
        title='Appearance validation';tabs=('general',);asset_prefix='keyboard'
        def __init__(self,shell):self.clicked=False;super().__init__(shell)
        def draw_content(self,p):
            p.fill(20,80,90,40,'ButtonFace');self.button(p,'&Test',(20,80,75,23),('test',))
        def action(self,action):
            if action==('test',):self.clicked=True;self.area.queue_draw()
            else:super().action(action)
    a.output.mkdir(parents=True,exist_ok=False)
    shell=Gtk.Window();shell.assets=a.assets;shell.font=BitmapFont((a.assets/'ms-sans-serif-8.fnt').read_bytes());shell.display_preferences=SimpleNamespace(palette=3);shell.cursor_for=lambda name:Gdk.Cursor.new_from_name(Gdk.Display.get_default(),'default');shell.show_all()
    window=Sheet(shell);window.show_all();flush_draws(Gtk)
    def capture(name):
        flush_draws(Gtk);Gdk.Display.get_default().sync();x,y=window.get_position();image=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),x,y,*window.physical_size);assert image;image.savev(str(a.output/(name+'.png')),'png',[],[]);return image
    baseline=capture('default')
    appearance.font_resolver=FontLibrary(a.assets/'font-library')
    providers={key:AppearanceProvider(key,a.output/(key+'.json'))for key in ('colors','fonts','metrics')};old={key:p.snapshot()for key,p in providers.items()}
    colors=deepcopy(DEFAULT_COLORS);colors.update(ActiveTitle=[128,0,0],ButtonFace=[192,208,192],ButtonText=[0,96,0]);providers['colors'].apply(colors)
    fonts=deepcopy(DEFAULT_FONTS);fonts['caption'].update(family='Comic Sans MS',height=-16);providers['fonts'].apply(fonts)
    providers['metrics'].apply(dict(DEFAULT_METRICS,caption_height=28))
    capture('custom-caption-and-button')
    assert window.body_offset==10 and window.physical_size==(404,458)
    assert appearance.font('caption',shell.font).face=='Comic Sans MS'
    rect=window.logical_to_physical((20,80,75,23));assert rect==(20,90,75,23)
    x11=ctypes.CDLL('libX11.so.6');xt=ctypes.CDLL('libXtst.so.6');x11.XOpenDisplay.argtypes=[ctypes.c_char_p];x11.XOpenDisplay.restype=ctypes.c_void_p;display=x11.XOpenDisplay(os.environ['DISPLAY'].encode());x11.XFlush.argtypes=[ctypes.c_void_p];x11.XCloseDisplay.argtypes=[ctypes.c_void_p]
    xt.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];xt.XTestFakeButtonEvent.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_int,ctypes.c_ulong]
    wx,wy=window.get_position();xt.XTestFakeMotionEvent(display,-1,wx+50,wy+101,0);xt.XTestFakeButtonEvent(display,1,1,0);xt.XTestFakeButtonEvent(display,1,0,0);x11.XFlush(display);flush_draws(Gtk);assert window.clicked
    capture('custom-clicked')
    from win95lx.control_panel.theme_appearance import Appearance
    reopened=Appearance();reopened.font_resolver=appearance.font_resolver
    for key in providers:AppearanceProvider(key,a.output/(key+'.json'),reopened).load()
    assert reopened.values==appearance.values
    for key,p in providers.items():p.restore(old[key])
    window.focus_action=None;window.area.queue_draw()
    restored=capture('restored-default');assert bytes(baseline.get_pixels())==bytes(restored.get_pixels())
    report={'checks':['actual semantic caption and button color','original Comic Sans TTF raster','caption height adds10px without scaling native body','physical pointer hits translated command','providers reload persisted values','rollback returns byte-identical baseline framebuffer'],'failed':0,'viewport':a.size,'scope':'Owned X11 actual framebuffer/input; not a GDI font equivalence or whole native palette comparison.'};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));window.destroy();shell.destroy();x11.XCloseDisplay(display)

def main():
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--pid',type=int);p.add_argument('--size',default='800x600');p.add_argument('--assets',type=Path,default=ROOT/'private/shell-assets');p.add_argument('--output',type=Path,required=True);p.add_argument('--gi-path',default='/tmp/win95lx-sprint-tools.uouVbC/usr/lib/python3/dist-packages/gi');a=p.parse_args()
    if a.child:return child(a)
    with tempfile.TemporaryDirectory(prefix='w95uat-appearance-')as temporary:
        r,w=os.pipe();server=subprocess.Popen([shutil.which('Xvfb')or'/tmp/win95lx-sprint-tools.uouVbC/usr/bin/Xvfb','-displayfd',str(w),'-screen','0',a.size+'x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);os.close(w)
        try:
            if not select.select([r],[],[],10)[0]:raise RuntimeError('Owned display failed.')
            env=os.environ.copy();env.pop('WAYLAND_DISPLAY',None);env.update(DISPLAY=':'+os.read(r,32).decode().strip(),GDK_BACKEND='x11')
            for name in ('HOME','XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_DATA_HOME'):
                directory=Path(temporary)/name;directory.mkdir();env[name]=str(directory)
            subprocess.run([sys.executable,__file__,'--child','--pid',str(server.pid),'--size',a.size,'--assets',str(a.assets.resolve()),'--output',str(a.output.resolve()),'--gi-path',a.gi_path],env=env,check=True,timeout=30)
        finally:os.close(r);server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
