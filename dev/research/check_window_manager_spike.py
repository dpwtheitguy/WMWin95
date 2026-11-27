#!/usr/bin/env python3
"""Isolated X11 spike: never run on :0. Own HOME and nested X server required.
Run on copied sources/assets; writes only --output. No production settings.
"""
import argparse,ctypes,json,os,subprocess,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--assets',type=Path,required=True);a=p.parse_args()
if os.environ.get('DISPLAY') in (None,':0',':0.0'):raise SystemExit('Refusing primary display')
if not os.environ.get('WIN95LX_WM_SPIKE'):raise SystemExit('Explicit isolated-spike environment required')
import gi
gi.require_version('Gtk','3.0');from gi.repository import Gtk,Gdk,GLib
from win95lx.shell.app import Shell
# No audio execution and no changes through applet Apply/OK handlers.
import win95lx.shell.app as shell_module
shell_module.play_event=lambda *_:None
shell=Shell(a.assets);shell.show_all();a.output.mkdir(parents=True,exist_ok=True)
X=ctypes.CDLL('libX11.so.6');X.XOpenDisplay.restype=ctypes.c_void_p;d=X.XOpenDisplay(None)
X.XDefaultRootWindow.argtypes=[ctypes.c_void_p];X.XDefaultRootWindow.restype=ctypes.c_ulong;root=X.XDefaultRootWindow(d)
X.XGetInputFocus.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_int)]
X.XQueryTree.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.c_ulong),ctypes.POINTER(ctypes.POINTER(ctypes.c_ulong)),ctypes.POINTER(ctypes.c_uint)]
X.XFree.argtypes=[ctypes.c_void_p]
results=[]
def xid(w):return w.get_window().get_xid() if w.get_window() else None
def top_ancestor(wid):
 current=wid
 while current and current!=root:
  rr=ctypes.c_ulong();parent=ctypes.c_ulong();children=ctypes.POINTER(ctypes.c_ulong)();n=ctypes.c_uint()
  X.XQueryTree(d,current,ctypes.byref(rr),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(n));X.XFree(children)
  if parent.value==root:return current
  current=parent.value
 return current
def snapshot(name):
 focus=ctypes.c_ulong();revert=ctypes.c_int();X.XGetInputFocus(d,ctypes.byref(focus),ctypes.byref(revert))
 rr=ctypes.c_ulong();parent=ctypes.c_ulong();children=ctypes.POINTER(ctypes.c_ulong)();n=ctypes.c_uint();X.XQueryTree(d,root,ctypes.byref(rr),ctypes.byref(parent),ctypes.byref(children),ctypes.byref(n));stack=[children[i] for i in range(n.value)];X.XFree(children)
 windows={'shell':shell,**shell.accessory_windows};states={key:{'xid':xid(w),'root_ancestor':top_ancestor(xid(w)),'visible':w.get_visible(),'mapped':w.get_mapped(),'active':w.is_active(),'decorated':w.get_decorated()} for key,w in windows.items()}
 for v in states.values():v['stack_index']=stack.index(v['root_ancestor']) if v['root_ancestor'] in stack else None
 r=Gdk.get_default_root_window();pix=Gdk.pixbuf_get_from_window(r,0,0,800,600);pix.savev(str(a.output/(name+'.png')),'png',[],[])
 results.append({'state':name,'focus':focus.value,'root_children_bottom_to_top':stack,'windows':states,'shell_start_open':shell.state.start_open,'shell_dialog':str(shell.state.dialog)})
 subprocess.run(['xprop','-root','_NET_ACTIVE_WINDOW','_NET_CLIENT_LIST_STACKING'],stdout=(a.output/(name+'-properties.txt')).open('w'))
 print(name,flush=True)
def open_apps():
 shell.open('computer');shell.launch_accessory('keyboard');shell.launch_accessory('mouse');shell.launch_accessory('notepad')
 for i,w in enumerate(shell.accessory_windows.values()):w.move(70+i*130,80+i*55)
def focus_shell():shell.get_window().focus(Gdk.CURRENT_TIME)
def start():shell.state.start_open=True;shell.area.queue_draw();focus_shell()
def run():shell.state.start_open=False;shell.state.dialog='run';shell.area.queue_draw();focus_shell()
def minimize():shell.accessory_windows['notepad'].hide();focus_shell()
def restore():w=shell.accessory_windows['notepad'];w.show_all();w.present()
def popup_probe():
 popup=Gtk.Window(type=Gtk.WindowType.POPUP);popup.set_transient_for(shell);popup.set_decorated(False);popup.move(5,150);popup.set_default_size(300,220);popup.add(Gtk.Label(label="ISOLATED NATIVE POPUP PROBE\nAbove normal windows?"));popup.show_all();shell._spike_popup=popup
def alt_space():
 shell.accessory_windows["mouse"].present();subprocess.Popen(["sh","-c","sleep 0.2; xdotool key alt+space"])
def ctrl_escape():
 w=shell.accessory_windows['keyboard'];w.present()
 subprocess.Popen(['sh','-c','sleep 0.2; xdotool key ctrl+Escape'])
actions=[('baseline',lambda:None),('mixed_windows',open_apps),('shell_focus',focus_shell),('start_overlay',start),('run_overlay',run),('notepad_minimized',minimize),('notepad_restored',restore),('ctrl_escape_applet',ctrl_escape),('native_popup_probe',popup_probe),('alt_space_applet',alt_space)]
index=0
def step():
 global index
 if index:
  snapshot(actions[index-1][0])
 if index==len(actions):
  (a.output/'results.json').write_text(json.dumps(results,indent=2)+'\n');Gtk.main_quit();return False
 actions[index][1]();index+=1;return True
GLib.timeout_add(900,step);Gtk.main()
