"""Unregistered native Add/Remove prototype; curated/read-only by default."""
import json,weakref,cairo
from pathlib import Path
from threading import Thread,Event
from gi.repository import Gtk,Gdk,GLib
from win95lx.apps.property_sheet import PropertySheet
from win95lx.shell.widgets import Painter,FACE,LIGHT,SHADOW,BLACK,NAVY
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.explorer.webview_details import wrapped
from win95lx.control_panel.addremove_preferences import (Catalogue,SetupBackend,SetupController,SetupError,SetupCancelled,load_catalogue,GROUP_LABELS)

INSTALL_REASON='Installing or removing software is unavailable until the component installer service is installed.'
DISK_REASON='Startup disk creation is unavailable until the startup-media service is installed and validated.'

def default_backend():
 path=Path(__file__).resolve().parents[3]/'config/functional-profiles.json'
 return SetupBackend(load_catalogue(str(path)))

def row_state(controller,members):
 values=[controller.pending.feature(c.id) for c in members]
 if not values or any(v is None for v in values):return None
 if all(values):return True
 if any(values):return 'partial'
 return False

class ComponentList:
 def draw_list(self,p,rect,rows,selection,scroll,*,components=False):
  x,y,w,h=rect;visible=max(1,(h-4)//(18 if components else 13));row_height=18 if components else 13
  maximum=max(0,len(rows)-visible);scroll=max(0,min(scroll,maximum));self.list_max=maximum;self.list_visible=visible
  gutter=16 if maximum else 0;client=(x+2,y+2,w-4-gutter,h-4)
  p.fill(x+2,y+2,w-4,h-4,LIGHT);p.cr.save();p.cr.rectangle(*client);p.cr.clip()
  for offset,row in enumerate(rows[scroll:scroll+visible+1]):
   ident,label,state,enabled,reason=row;yy=y+2+offset*row_height;selected=scroll+offset==selection
   if selected:p.fill(x+2,yy,w-4-gutter,row_height,NAVY)
   color=LIGHT if selected else BLACK
   tx=x+3
   clipped_height=max(0,min(row_height,y+h-2-yy))
   if components:
    tx=x+36;key='partial' if state=='partial' else 'checked' if state is True else 'unchecked'
    p.image(self.checks[key],x+4,yy+3)
    if not enabled and state is None:p.fill(x+5,yy+4,9,9,FACE)
    icon=self.shell.small_images.get(4)
    if icon:p.image(icon,x+18,yy+1)
    if clipped_height and enabled:self.hit((x+2,yy,16,clipped_height),('toggle',ident))
    elif clipped_height and reason:self.disabled.append(((x+2,yy,16,clipped_height),reason))
   p.text(label,tx,yy+(2 if components else 0),color)
   clipped_height=max(0,min(row_height,y+h-2-yy))
   if clipped_height:self.hit((x+18 if components else x+2,yy,w-20-gutter if components else w-4-gutter,clipped_height),('select',scroll+offset))
  p.cr.restore()
  if maximum:
   thumb=max(16,round(max(0,h-4-32)*visible/max(1,len(rows))))
   bar=VerticalScrollbar(h-4,maximum,thumb=thumb);bx,by=x+w-18,y+2;bar.draw(p,bx,by,scroll,track='window')
   self.hit((bx,by,16,16),('scroll',-1));self.hit((bx,by+bar.height-16,16,16),('scroll',1))
   top=bar.thumb_top(scroll);self.hit((bx,by+top,16,thumb),('list-thumb',))
   if top>16:self.hit((bx,by+16,16,top-16),('scroll',-visible))
   if top+thumb<bar.height-16:self.hit((bx,by+top+thumb,16,bar.height-16-top-thumb),('scroll',visible))
   self.scroll_geometry=(by,bar)
  return scroll
 def press(self,area,event):
  if event.button==1:
   for rect,action in reversed(self.hits):
    if action[0]=='list-thumb' and self.contains(rect,event.x,event.y):
     self.list_drag=event.y-rect[1];return True
  return super().press(area,event)
 def motion(self,area,event):
  if getattr(self,'list_drag',None) is not None:
   by,bar=self.scroll_geometry;self.scroll=bar.value_at(event.y-by-self.list_drag);self.area.queue_draw();return True
  return super().motion(area,event)
 def release(self,area,event):
  if getattr(self,'list_drag',None) is not None:self.list_drag=None;self.area.queue_draw();return True
  return super().release(area,event)
 def focus_order(self):
  order=[]
  for action in super().focus_order():
   if action[0] in ('toggle','list-thumb'):continue
   if action[0]=='select':
    action=('select',self.selection)
   if action not in order:order.append(action)
  return order
 def text_block(self,p,text,rect,color=BLACK):
  x,y,w,h=rect;p.fill(x,y,w,h,FACE);p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip()
  for n,line in enumerate(wrapped(text,p.font,w)):p.text(line,x,y+n*13,color)
  p.cr.restore()
 def load_art(self):
  self.layouts=json.loads((self.assets/'addremove-native-layout.json').read_text())
  self.checks={s:cairo.ImageSurface.create_from_png(str(self.assets/f'addremove-check-{s}.png')) for s in ('checked','unchecked','partial')}
 def wheel(self,area,event):
  self.action(('scroll',1 if event.direction==Gdk.ScrollDirection.DOWN else -1));return True
 def key_list(self,event):
  name=Gdk.keyval_name(event.keyval)
  if self.focus_action and self.focus_action[0]=='select' and name in ('Up','Down','Home','End','space'):
   if name=='space':
    rows=self.rows()
    if rows and rows[self.selection][3]:self.action(('toggle',rows[self.selection][0]))
   else:
    count=len(self.rows());target=0 if name=='Home' else count-1 if name=='End' else self.selection+(-1 if name=='Up' else 1)
    self.action(('select',max(0,min(max(0,count-1),target))))
   return True
  return False

class AddRemoveWindow(ComponentList,PropertySheet):
 title='Add/Remove Programs Properties';asset_prefix='addremove';size=(367,443)
 tabs=('install','windows-setup','startup-disk');tab_rects=((9,29,86,23),(95,29,87,23),(182,29,70,23))
 buttons=((121,410,75,23),(202,410,75,23),(283,410,75,23))
 def __init__(self,shell,backend=None):
  self.controller=SetupController(SetupBackend(Catalogue(())));self.loading=True;self.busy=False;self.alive=True;self.generation=0;self.load_error='';self.children=[];self.selection=0;self.scroll=0;self.cancel_event=Event();self.list_max=0;self.list_visible=1
  super().__init__(shell);self.load_art();self.area.connect('scroll-event',self.wheel);self.connect('destroy',self.closed)
  owner=weakref.ref(self);generation=self.generation
  def worker():
   controller=None;error=None
   try:controller=SetupController(backend or default_backend());controller.load()
   except Exception as caught:error=caught
   def done():
    window=owner()
    if window is None or not window.alive or window.generation!=generation:return False
    window.loading=False;window.load_error=str(error) if error else ''
    if controller is not None:window.controller=controller
    window.area.queue_draw();return False
   GLib.idle_add(done)
  Thread(target=worker,daemon=True).start()
 def closed(self,*_):
  self.alive=False;self.generation+=1;self.cancel_event.set()
  for child in tuple(self.children):child.destroy()
 def rows(self):
  if self.loading or self.controller.pending is None:return ()
  if self.tab==0:return tuple((p.id,p.label,None,False,'') for p in self.controller.pending.programmes if p.installed)
  catalogue=self.controller.backend.catalogue
  return tuple((g,GROUP_LABELS.get(g,g.replace('_',' ').title()),row_state(self.controller,catalogue.members(g)),False,'Choose Details to inspect available and unavailable settings.') for g in catalogue.groups)
 def button(self,p,label,rect,action,enabled=True,reason=None):
  return super().button(p,label,rect,action,enabled and (not self.busy or action==('cancel',)),reason)
 def draw_content(self,p):
  rows=self.rows();self.selection=min(self.selection,max(0,len(rows)-1))
  if self.tab==0:
   self.button(p,'&Install...',(246,110,96,23),('install',),False,INSTALL_REASON)
   self.scroll=self.draw_list(p,(24,222,318,121),rows,self.selection,self.scroll)
   builtin=bool(rows and rows[self.selection][0]=='desktop-enhancements')
   removable=bool(rows and self.controller.backend.writable and not builtin)
   self.button(p,'Add/&Remove...',(246,366,96,23),('programme',),builtin or removable,INSTALL_REASON)
   if self.loading or self.load_error:self.text_block(p,'Reading installed programs...' if self.loading else 'Installed software information is unavailable.',(28,226,302,40))
  elif self.tab==1:
   self.scroll=self.draw_list(p,(24,123,320,94),rows,self.selection,self.scroll,components=True)
   self.text_block(p,'Not available',(230,227,85,13))
   free=self.controller.pending.free_bytes if self.controller.pending else 0;self.text_block(p,f'{free/1048576:.1f} MB' if free else 'Not available',(230,243,85,13))
   description='Choose a component and click Details.'
   if rows:description=GROUP_LABELS.get(rows[self.selection][0],rows[self.selection][1])+'. Compatibility settings remain unavailable until their runtime bindings are validated.'
   if self.loading:description='Reading component information...'
   if self.load_error:description='Component information is unavailable. Reopen this window to try again.'
   self.text_block(p,description,(33,277,300,49));self.text_block(p,f'{len(self.controller.backend.catalogue.members(rows[self.selection][0])) if rows else 0} components listed',(33,334,204,15))
   self.button(p,'&Details...',(253,327,80,23),('details',),bool(rows))
   self.button(p,'&Have Disk...',(261,366,80,23),('have-disk',),False,'Installing unregistered components from disks is unavailable; only registered components are supported.')
  else:self.button(p,'&Create Disk...',(237,149,105,23),('create-disk',),False,DISK_REASON)
 def tab_changed(self):self.selection=self.scroll=0;self.focus_action=('select',0) if self.tab!=2 else ('ok',)
 def action(self,action):
  kind=action[0]
  if self.busy:
   if kind=='cancel':self.cancel_event.set()
   return
  if kind=='select':
   self.selection=action[1];self.focus_action=('select',self.selection);self.scroll=max(0,min(self.scroll,self.selection));self.scroll=max(self.scroll,self.selection-self.list_visible+1)
  elif kind=='scroll':self.scroll=max(0,min(self.list_max,self.scroll+action[1]))
  elif kind=='programme':
   rows=self.rows()
   if rows and rows[self.selection][0]=='desktop-enhancements':self.tab=1;self.tab_changed()
   elif rows:
    try:self.controller.set_programme(rows[self.selection][0],False)
    except (SetupError,ValueError) as error:self.error(error)
  elif kind=='details':
   rows=self.rows()
   if rows:
    child=ComponentDetails(self,rows[self.selection][0]);self.children.append(child);child.connect('destroy',lambda w:self.children.remove(w) if w in self.children else None);child.show_all()
  elif kind in ('ok','apply'):
   if self.loading or self.controller.pending==self.controller.applied:
    if kind=='ok':self.destroy()
    return
   self.busy=True;self.cancel_event.clear();owner=weakref.ref(self);controller=self.controller
   def worker():
    error=None
    try:controller.apply(self.cancel_event)
    except Exception as caught:error=caught
    def done():
     window=owner()
     if window is None or not window.alive:return False
     window.busy=False
     if error:window.error(error)
     elif kind=='ok':window.destroy();return False
     window.area.queue_draw();return False
    GLib.idle_add(done)
   Thread(target=worker,daemon=True).start()
  else:return super().action(action)
  self.area.queue_draw()
 def key(self,window,event):
  if self.key_list(event):return True
  return super().key(window,event)

class ComponentDetails(ComponentList,PropertySheet):
 asset_prefix='addremove';tabs=('details',);size=(347,379);buttons=((177,342,75,23),(258,342,75,23));tab_rects=()
 def __init__(self,parent,group):
  self.parent=parent;self.group=group;self.title=GROUP_LABELS.get(group,group.title());self.selection=0;self.scroll=0;self.list_max=0;self.list_visible=1
  self.controller=SetupController(parent.controller.backend);self.controller.applied=self.controller.pending=parent.controller.pending
  super().__init__(parent.shell);self.set_transient_for(parent);self.set_modal(True);self.load_art();self.area.connect('scroll-event',self.wheel);self.focus_action=('select',0)
 def rows(self):
  return tuple((c.id,c.label,self.controller.pending.feature(c.id),c.available and self.controller.backend.writable,c.reason or INSTALL_REASON) for c in self.controller.backend.catalogue.members(self.group))
 def draw(self,area,cr):
  result=super().draw(area,cr);self.hits=[(r,a) for r,a in self.hits if a[0] not in ('help','caption')];self.hits.insert(0,((3,3,self.size[0]-24,20),('caption',)))
  p=Painter(cr,self.shell.font);p.fill(3,3,self.size[0]-24,17,NAVY if self.caption_active else SHADOW);p.cr.save();p.cr.rectangle(4,3,self.size[0]-26,17);p.cr.clip();p.text(self.title,5,4,LIGHT,bold=True);p.cr.restore();return result
 def draw_content(self,p):
  rows=self.rows();self.selection=min(self.selection,max(0,len(rows)-1));self.scroll=self.draw_list(p,(14,92,318,94),rows,self.selection,self.scroll,components=True)
  self.text_block(p,'Not available',(221,196,84,13));free=self.controller.pending.free_bytes;self.text_block(p,f'{free/1048576:.1f} MB' if free else 'Not available',(221,212,84,13))
  text='No registered components.'
  if rows:
   c=self.controller.backend.catalogue.members(self.group)[self.selection];state=self.controller.pending.feature(c.id);text=c.description+' '+(c.reason if not c.available else INSTALL_REASON if not self.controller.backend.writable else '')
   if state is None:text+=' Current global setting is not exposed; no selection is being simulated.'
  self.text_block(p,text,(23,251,299,42));self.text_block(p,f'{len(rows)} components listed',(23,303,206,15))
  self.button(p,'&Details...',(246,298,75,23),('more',),False,'No further component level is implemented.')
 def action(self,action):
  kind=action[0]
  if kind=='select':self.selection=action[1];self.focus_action=('select',self.selection);self.scroll=max(0,min(self.scroll,self.selection));self.scroll=max(self.scroll,self.selection-self.list_visible+1)
  elif kind=='scroll':self.scroll=max(0,min(self.list_max,self.scroll+action[1]))
  elif kind=='toggle':
   try:self.controller.set_feature(action[1],not bool(self.controller.pending.feature(action[1])))
   except (SetupError,ValueError) as error:self.error(error)
  elif kind=='ok':self.parent.controller.pending=self.controller.pending;self.parent.area.queue_draw();self.destroy();return
  else:return super().action(action)
  self.area.queue_draw()
 def key(self,window,event):
  if self.key_list(event):return True
  return super().key(window,event)
