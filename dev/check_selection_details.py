#!/usr/bin/env python3
"""Native Web View selection, contextual File verbs and real shortcut workflows."""
import argparse,hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools'),str(ROOT/'dev')]
from pixels import read
from check_reference_ui import compare_region

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'private/screenshots'/datetime.now(timezone.utc).strftime('selection-%Y%m%dT%H%M%S%fZ'));a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 import gi;gi.require_foreign('cairo');import cairo
 from gi.repository import GLib
 from win95lx.shell.app import Shell,Gtk,Gdk
 from win95lx.explorer.drive_browser import DriveBrowser
 from win95lx.explorer.namespace import resolve_shortcut
 from check_menu_seams import flush_draws
 comparisons=[];checks=[]
 with TemporaryDirectory() as home,patch('pathlib.Path.home',return_value=Path(home)):
  root=Path(home);(root/'Desktop').mkdir();(root/'Documents').mkdir();(root/'Documents/report.txt').write_text('shortcut target')
  shell=Shell(ROOT/'private/shell-assets');shell._drive=DriveBrowser(root);shell.desktop_folder=root/'Desktop';shell.refresh_desktop_files();shell.show_all();flush_draws(Gtk)
  shell.open('computer');win=shell.state.active;win.x=win.y=0;win.width=shell.width;win.height=shell.height-28;win.restored_bounds=(100,65,512,461)
  def render(name):
   im=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height);shell.draw(shell.area,cairo.Context(im));path=a.output/(name+'.png');im.write_to_png(str(path));return read(path)
  def click_item(label,modifiers=0):
   hit=next((x,y,w,h,action) for x,y,w,h,action in shell.hits if action[0]=='item' and action[1] is win and action[3]==label)
   x,y,w,h,action=hit;shell.press(shell.area,SimpleNamespace(x=x+32,y=y+15,button=1,type=Gdk.EventType.BUTTON_PRESS,state=modifiers,time=Gdk.CURRENT_TIME))
  def exact(name,actual,rect):
   reference=ROOT/'private/screenshots/start-development-20261110/native-controlpanel-selected-user.png'
   origin=(rect[0]+round((shell.width-4)*.3)-239,rect[1]) if 'image' in name else rect[:2]
   count=compare_region(actual,read(reference),rect,origin);comparisons.append({'name':name,'rect':rect,'differing_pixels':count,'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest()});assert not count,(name,count)
  render('empty');click_item('Control Panel');actual=render('control-panel-selected')
  exact('Control Panel title and type',actual,(20,218,150,30))
  exact('selected Control Panel image and label',actual,(245,245,70,60))
  if shell.width==800:exact('complete Control Panel info block',actual,(20,218,212,170))
  checks.append('pointer selection updates original Verdana information block')
  count=len(shell.state.windows);bounds=(win.x,win.y,win.width,win.height)
  shell.navigate_namespace(win,'control');render('control-panel-in-place')
  assert shell.state.active is win and len(shell.state.windows)==count and win.kind=='control'
  assert (win.x,win.y,win.width,win.height)==bounds
  shell.action(('explorer-tool',win,'back'));assert win.kind=='computer'
  shell.action(('explorer-tool',win,'forward'));assert win.kind=='control'
  shell.action(('explorer-tool',win,'up'));assert win.kind=='computer'
  shell.navigate_namespace(win,'control',new_window=True);assert len(shell.state.windows)==count+1
  shell.action(('close',shell.state.active));assert shell.state.active is win
  checks.append('same-window namespace navigation Back Forward Up and explicit separate windows')
  shell.item_selection=(win,'Control Panel');render('control-panel-reselected')

  click_item('(C:)',Gdk.ModifierType.CONTROL_MASK);render('multiple-selected');assert shell.item_selection==(win,None);checks.append('Ctrl click selects multiple namespace items')
  click_item('(C:)');render('drive-selected');shell.action(('window-menu',win,'File',24));render('drive-file-menu')
  assert {'open','explore','find','format','shortcut','properties'}<={row[2] for row in shell.drive_menu_rows};checks.append('selected drive adds native verbs')
  shell.popup=None;click_item('Control Panel');render('panel-selected-before-shortcut')
  def question(answer,name):
   observed=[]
   def inspect():
    dialogs=[w for w in Gtk.Window.list_toplevels() if isinstance(w,Gtk.Dialog) and w.get_visible()]
    if not dialogs:return GLib.SOURCE_CONTINUE
    dialog=dialogs[0]
    try:
     assert dialog.get_title()=='Shortcut';assert tuple(dialog.get_size())==(374,119)
     flush_draws(Gtk);Gdk.pixbuf_get_from_window(dialog.get_window(),0,0,*dialog.get_size()).savev(str(a.output/(name+'.png')),'png',[],[])
     observed.append(True)
    finally:dialog.response(answer)
    return GLib.SOURCE_REMOVE
   GLib.timeout_add(100,inspect);shell.action(('computer-menu',win,'shortcut'));assert observed
  question(Gtk.ResponseType.NO,'shortcut-no');assert not list(shell.desktop_folder.glob('*.desktop'))
  question(Gtk.ResponseType.YES,'shortcut-yes');links=list(shell.desktop_folder.glob('*.desktop'));assert len(links)==1
  assert resolve_shortcut(links[0]).target=='control';shell.open_drive_file(links[0].relative_to(root));assert shell.state.active.kind=='control';shell.action(('close',shell.state.active))
  question(Gtk.ResponseType.YES,'shortcut-duplicate');assert len(list(shell.desktop_folder.glob('*.desktop')))==2;checks.append('native question No Yes duplicate and namespace reopen')
  from win95lx.explorer.namespace import create_shortcut,create_file_shortcut
  create_shortcut(shell.desktop_folder,'(C:)')
  create_file_shortcut(shell.desktop_folder,root/'Documents')
  create_file_shortcut(shell.desktop_folder,root/'Documents/report.txt')
  for window in shell.state.windows:window.minimized=True
  shell.item_selection=None;shell.state.selection=None;shell.refresh_desktop_files()
  icons=render('shortcut-target-icons-desktop')
  # Compare rendered targets/overlays with independent original resource images.
  for path in shell.desktop_folder.glob('*.desktop'):
   target=resolve_shortcut(path)
   resource=36 if target.target=='control' else 9 if target.target=='drive' else 4 if Path(target.target).is_dir() else 152
   _,_,base=read(ROOT/'private/shell-assets'/('explorer-folder-32.png' if resource==4 else f'shell32-group-{resource}.png'))
   _,_,arrow=read(ROOT/'private/shell-assets/shell32-group-30.png')
   x,y=shell.desktop_file_defaults['file:'+path.name]
   for yy in range(32):
    for xx in range(32):
     b,overlay=base[yy*32+xx],arrow[yy*32+xx]
     expected=overlay[:3] if overlay[3] else b[:3] if b[3] else (0,128,128)
     assert icons[2][(y+yy)*icons[0]+x+21+xx][:3]==expected,(path.name,xx,yy)
  checks.append('namespace drive folder document target icons and original arrow overlay')
  for window in shell.state.windows:window.minimized=False

  shell.open('drive','Documents');folder=shell.state.active;folder.browser.selection={'report.txt'}
  shell.drive_edit(folder,'shortcut');link=next((root/'Documents').glob('*.desktop'));assert resolve_shortcut(link).target==str(root/'Documents/report.txt')
  # Follow the link through the normal Open path, rather than testing only its serialized URL.
  shell.open_drive_file(link.relative_to(root));assert 'notepad' in shell.accessory_windows
  shell.accessory_windows['notepad'].destroy();shell.accessory_windows.pop('notepad',None)
  shell.drive_edit(folder,'copy');shell.drive_edit(folder,'paste-shortcut');assert len(list((root/'Documents').glob('*.desktop')))==2
  shell.refresh_file_views();folder.browser.selection={link.name};shell.action(('window-menu',folder,'File',24));render('file-shortcut-menu')
  assert 'shortcut' in {row[2] for row in shell.drive_menu_rows};shell.popup=None
  from win95lx.explorer.trash import TrashStore
  shell.trash=TrashStore(root/'Trash');record=shell.trash.put(link);shell.trash.restore(record);assert resolve_shortcut(link).target==str(root/'Documents/report.txt')
  checks.append('file link Create Open Copy Paste Shortcut Trash Restore')
  # Exercise every implemented Edit option against disposable real files.
  shell.state.windows.remove(folder);shell.open('drive','Documents');folder=shell.state.active
  browser=shell.browser_for(folder);browser.selection.clear();render('edit-empty-selection')
  shell.action(('window-menu',folder,'Edit',68));render('edit-empty-menu')
  enabled={row[2] for row in shell.drive_menu_rows};assert 'cut' not in enabled and 'copy' not in enabled and 'undo' not in enabled
  from win95lx.shell.widgets import Painter
  canvas=cairo.ImageSurface(cairo.FORMAT_RGB24,shell.width,shell.height)
  shell.file_clipboard=__import__('win95lx.explorer.file_operations',fromlist=['FileClipboard']).FileClipboard()
  shell.drive_menu(Painter(cairo.Context(canvas),shell.font),48,46,folder,'Edit')
  canvas.write_to_png(str(a.output/'edit-native-geometry.png'))
  reference=ROOT/'private/screenshots/start-development-20261110/native-edit-cdrive-empty.png'
  difference=compare_region(read(a.output/'edit-native-geometry.png'),read(reference),(50,82,150,110),(50,82))
  comparisons.append({'name':'Edit Cut Copy Paste Paste Shortcut Select All Invert rows','differing_pixels':difference,'rect':[50,82,150,110],'reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest()})
  assert not difference,difference
  shell.drive_edit(folder,'select-all');assert browser.selection=={name for name,_ in browser.entries}
  shell.drive_edit(folder,'invert');assert not browser.selection
  browser.selection={'report.txt'};shell.action(('window-menu',folder,'Edit',68));render('edit-selected-menu')
  assert {'cut','copy','select-all','invert'}<={row[2] for row in shell.drive_menu_rows}
  shell.drive_edit(folder,'copy');shell.drive_edit(folder,'paste')
  assert (root/'Documents/Copy of report.txt').read_text()=='shortcut target'
  assert (root/'Documents/report.txt').read_text()=='shortcut target'
  (root/'Destination').mkdir();browser.selection={'report.txt'};shell.drive_edit(folder,'cut')
  assert (root/'Documents/report.txt').exists()
  shell.open('drive','Destination');destination=shell.state.active;shell.drive_edit(destination,'paste')
  assert not (root/'Documents/report.txt').exists() and (root/'Destination/report.txt').exists()
  assert not shell.file_clipboard.sources
  shell.action(('window-menu',destination,'Edit',68));render('edit-after-cut-paste')
  assert 'paste' not in {row[2] for row in shell.drive_menu_rows}
  checks.append('Edit empty selected Cut Copy Paste same-folder Select All Invert and clipboard consumption')

  for window in tuple(shell.accessory_windows.values()):window.destroy()
  shell.disconnect_by_func(Gtk.main_quit);shell.destroy()
 digest=hashlib.sha256()
 for path in sorted((ROOT/'src').rglob('*.py')):digest.update(str(path.relative_to(ROOT)).encode());digest.update(path.read_bytes())
 report={'source_sha256':digest.hexdigest(),'viewport':[shell.width,shell.height],'checks':checks,'comparisons':comparisons,'failed':0}
 (a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
