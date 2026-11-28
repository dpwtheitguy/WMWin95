#!/usr/bin/env python3
"""Does the original Lens engine capture a real non-Wine Linux window?"""
import argparse,ctypes,hashlib,json,os,select,subprocess,sys,tempfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--xvfb',type=Path,required=True);a=p.parse_args();assert os.uname().nodename=='win95lx-dev';a.output.mkdir(parents=True,exist_ok=False);sys.path.insert(0,str(a.source))
from win95lx.control_panel.screensaver_runtime import ScreenSaverCatalog,WineScreenSaverRuntime
with tempfile.TemporaryDirectory(prefix='w95uat-lens-linux-')as temporary:
 root=Path(temporary);r,w=os.pipe();server=subprocess.Popen([str(a.xvfb),'-displayfd',str(w),'-screen','0','800x600x24','-nolisten','tcp','-noreset'],pass_fds=(w,),stderr=subprocess.PIPE);os.close(w);runtime=None;window=None
 try:
  assert select.select([r],[],[],10)[0];display=':'+os.read(r,32).decode().strip();os.close(r);assert display!=':0';os.environ.update(DISPLAY=display,GDK_BACKEND='x11');os.environ.pop('WAYLAND_DISPLAY',None)
  import gi;gi.require_version('Gtk','3.0');gi.require_foreign('cairo');from gi.repository import Gtk,Gdk
  owned=Gdk.Display.open(display);assert owned;Gdk.DisplayManager.get().set_default_display(owned)
  window=Gtk.Window();window.set_decorated(False);window.set_default_size(800,600);window.move(0,0);area=Gtk.DrawingArea();window.add(area)
  def draw(_area,cr):
   colors=((1,0,0),(0,1,0),(0,0,1),(1,1,0))
   for y in range(0,600,40):
    for x in range(0,800,40):cr.set_source_rgb(*colors[(x//40+y//40)%4]);cr.rectangle(x,y,40,40);cr.fill()
  area.connect('draw',draw);window.show_all()
  def flush():
   for _ in range(5):
    while Gtk.events_pending():Gtk.main_iteration_do(False)
    time.sleep(.02)
  def capture(name):
   flush();owned.sync();pix=Gdk.pixbuf_get_from_window(Gdk.get_default_root_window(),0,0,800,600);pix.savev(str(a.output/(name+'.png')),'png',[],[]);data=bytes(pix.get_pixels());stride=pix.get_rowstride();c=pix.get_n_channels();colors={data[y*stride+x*c:y*stride+x*c+3]for y in range(600)for x in range(800)};return {'sha256':hashlib.sha256(data).hexdigest(),'unique_colors':len(colors)}
  flush();before=capture('linux-gtk-pattern-before')
  runtime=WineScreenSaverRuntime(ScreenSaverCatalog.load(a.assets/'catalog.json'),root/'state');runtime.prepare('plus95-science');after_prepare=capture('linux-gtk-after-prepare');assert before['unique_colors']==4;assert after_prepare['sha256']==before['sha256'],'Preparation changed the visible Linux background.'
  process=runtime.launch('plus95-science');time.sleep(3);first=capture('lens-over-linux-3s');time.sleep(3);last=capture('lens-over-linux-6s')
  x=ctypes.CDLL('libX11.so.6');t=ctypes.CDLL('libXtst.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p;d=x.XOpenDisplay(display.encode());t.XTestFakeMotionEvent.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_int,ctypes.c_int,ctypes.c_ulong];x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
  t.XTestFakeMotionEvent(d,-1,30,30,0);x.XFlush(d);code=process.wait(timeout=5);runtime.stop();x.XCloseDisplay(d)
  report={'before':before,'after_prepare':after_prepare,'preparation_visible_pixels_unchanged':True,'first':first,'last':last,'temporal_change':first['sha256']!=last['sha256'],'mouse_exit':code,'scope':'Owned LinuxGTK checkerboard under originalLens; inspectactualframes beforeacceptance.'};(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
 finally:
  if runtime:runtime.close()
  if window:window.destroy()
  server.terminate();server.wait(timeout=5)
 (a.output/'cleanup.json').write_text(json.dumps({'owned_xvfb_exit':server.returncode,'temporary_state_removed':True})+'\n')
