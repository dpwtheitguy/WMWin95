"""Windows 95 Fonts folder: real inventory, preview and personal installation."""
from pathlib import Path
import math,subprocess,time,urllib.parse,ctypes as C,ctypes.util
import cairo
import gi
gi.require_version('Gtk','3.0');gi.require_version('PangoCairo','1.0')
from gi.repository import Gtk,Gdk,GLib,GdkPixbuf,Pango,PangoCairo
from win95lx.control_panel.font_catalog import FontCatalog,FontFace,font_metadata,fontconfig,EXTENSIONS
from win95lx.shell.widgets import Painter,FACE,BLACK,LIGHT,NAVY,SHADOW
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.apps.popup_events import dismiss_and_replay,local_point
from win95lx.shell.icon_labels import wrap_label
from win95lx.shell.system_menu import options,WindowOperation,ARROWS
from win95lx.shell.window_bounds import fit_bounds

PRINT_REASON='Native print setup and printer integration are not implemented yet.'
LINK_REASON='Font shortcuts and renaming are not implemented in this folder. Installed font files keep their original names.'

class FontMenu(Gtk.Window):
    def __init__(self,parent,rows,x,width,top=42):
        super().__init__(type=Gtk.WindowType.POPUP);self.parent=parent;parent.menu_popup=self;self.shell=parent.shell;self.rows=rows;self.width=width;self.value=next((i for i,row in enumerate(rows) if row and row[2]),-1);self.hits=[];self.closed=False
        height=5+sum(9 if row is None else 17 for row in rows);self.height=height;px,py=parent.get_position();self.move(px+x,py+top);self.set_transient_for(parent)
        self.area=Gtk.DrawingArea();self.area.set_size_request(width,height);self.add(self.area);self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.POINTER_MOTION_MASK);self.area.connect('draw',self.draw);self.area.connect('button-press-event',self.press);self.area.connect('motion-notify-event',self.motion);self.connect('key-press-event',self.key);self.connect('focus-out-event',lambda *_:self.finish(restore_focus=False));self.connect('button-press-event',self.press);self.connect('grab-broken-event',lambda *_:self.finish(restore_focus=False));self.connect('destroy',self.cleanup);self.parent_destroy=parent.connect('destroy',lambda *_:self.finish(restore_focus=False));self.show_all();self.grab_add();self.get_window().focus(Gdk.CURRENT_TIME)
    def draw(self,area,cr):
        p=Painter(cr,self.shell.font);p.bevel(0,0,self.width,area.get_allocated_height());self.hits=[];y=3
        for index,row in enumerate(self.rows):
            if row is None:p.fill(2,y+3,self.width-4,1,SHADOW);p.fill(2,y+4,self.width-4,1,LIGHT);y+=9;continue
            label,command,enabled,reason,*accelerator=row;selected=index==self.value
            if selected:p.fill(2,y,self.width-4,17,NAVY)
            color=LIGHT if selected else BLACK
            if not enabled:
                if not selected:p.text(label,25,y+3,LIGHT)
                color=SHADOW
            p.text(label,24,y+2,color)
            if accelerator:p.text(accelerator[0],self.width-14-p.font.width(accelerator[0]),y+2,color)
            self.hits.append((y,index));y+=17
    def cleanup(self,*_):
        self.closed=True
        if self.has_grab():self.grab_remove()
        handler=getattr(self,'parent_destroy',None)
        if handler and self.parent.handler_is_connected(handler):self.parent.disconnect(handler)
        self.parent_destroy=None
        if self.parent.menu_popup is self:self.parent.menu_popup=None
        if self.parent.get_visible():self.parent.area.queue_draw()
    def finish(self,index=None,*,restore_focus=True):
        if self.closed:return True
        self.cleanup();self.destroy()
        if restore_focus and self.parent.get_window():self.parent.get_window().focus(Gdk.CURRENT_TIME)
        if index is not None and self.parent.get_visible() and self.rows[index] and self.rows[index][2]:
            parent,command=self.parent,self.rows[index][1]
            def invoke():
                if parent.get_visible():parent.command(command)
                return False
            GLib.idle_add(invoke)
        self.parent.area.queue_draw();return True
    def press(self,area,e):
        if self.closed:return True
        x,y=local_point(self,e)
        if not 0<=x<self.width or not 0<=y<self.height:return dismiss_and_replay(e,lambda:self.finish(restore_focus=False))
        index=next((i for top,i in self.hits if top<=y<top+17),None)
        if index is not None and not self.rows[index][2]:self.area.set_tooltip_text(self.rows[index][3]);return True
        return self.finish(index if e.button==1 else None)
    def motion(self,area,e):
        if self.closed:return True
        x,y=local_point(self,e)
        self.value=next((i for top,i in self.hits if 0<=x<self.width and top<=y<top+17),-1);self.area.queue_draw();return True
    def key(self,window,e):
        if self.closed:return True
        name=Gdk.keyval_name(e.keyval);enabled=[i for i,row in enumerate(self.rows) if row and row[2]]
        if name=='Escape':return self.finish()
        if name in ('Return','KP_Enter','space'):return self.finish(self.value if self.value>=0 else None)
        if name in ('Up','Down') and enabled:
            current=enabled.index(self.value) if self.value in enabled else -1;self.value=enabled[(current+(-1 if name=='Up' else 1))%len(enabled)];self.area.queue_draw();return True
        if name and len(name)==1:
            index=next((i for i,row in enumerate(self.rows) if row and row[2] and row[0][0].casefold()==name.casefold()),None)
            if index is not None:return self.finish(index)
        return False

class FontWindow(Gtk.Window):
    def __init__(self,shell,title,size,frame_name):
        super().__init__(title=title);self.shell=shell;self.assets=self.dialog_assets=shell.assets;self.native_size=size;self.title=title;self.frame=cairo.ImageSurface.create_from_png(str(self.assets/frame_name));self.caption_active=True;self.drag=None;self.sizing=None;self.restored=None;self.operation=None;self.menu_popup=None;self.hits=[]
        self.set_transient_for(shell);self.set_decorated(False);self.set_resizable(True);self.set_default_size(*size);self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.area=Gtk.DrawingArea();self.area.set_size_request(320,180);self.add(self.area);self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.SCROLL_MASK)
        self.area.connect('draw',self.draw);self.area.connect('button-press-event',self.press);self.area.connect('button-release-event',self.release);self.area.connect('motion-notify-event',self.motion);self.area.connect('scroll-event',self.wheel);self.connect('key-press-event',self.key);self.connect('map-event',self.mapped)
        self.connect('focus-in-event',lambda *_:self.caption_focus(True));self.connect('focus-out-event',lambda *_:self.caption_focus(False));self.connect('realize',lambda *_:self.get_window().set_cursor(shell.cursor_for('arrow')))
        from win95lx.control_panel.display_preferences import install_palette_filter
        install_palette_filter(self,lambda:shell.display_preferences.palette)
        icon=self.assets/'fonts-folder-32.png'
        if icon.exists():self.set_icon(GdkPixbuf.Pixbuf.new_from_file(str(icon)))
    def mapped(self,*_):
        x,y=self.get_position();w,h=self.get_size();screen=self.get_screen();x,y,w,h=fit_bounds((x,y,w,h),(screen.get_width(),screen.get_height()),resizable=True);self.move(x,y);self.resize(w,h);self.get_window().focus(Gdk.CURRENT_TIME);return False
    def caption_focus(self,active):
        if not active and self.menu_popup is not None:return False
        self.caption_active=active;self.area.queue_draw();return False
    def sprite(self,p,rect,x,y):
        sx,sy,w,h=rect;p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip();p.image(self.frame,x-sx,y-sy);p.cr.restore()
    def chrome(self,p,w,h):
        if (w,h)==self.native_size:p.image(self.frame,0,0)
        else:
            p.window_frame(0,0,w,h);p.fill(4,4,w-8,18,NAVY)
            self.sprite(p,(4,4,20,18),4,4);p.text(self.title,24,6,LIGHT,bold=True)
            for symbol,x in (('minimize',w-56),('restore' if self.restored else 'maximize',w-40),('close',w-22)):p.caption_button(symbol,x,6)
        if not self.caption_active:
            p.fill(24,4,w-80,18,SHADOW);p.text(self.title,24,6,LIGHT,bold=True)
        self.hits=[((w-56,6,16,14),'minimize'),((w-40,6,16,14),'maximize'),((w-22,6,16,14),'close'),((4,4,19,18),'system')]
    def hit(self,rect,action):self.hits.append((rect,action))
    def maximize(self):
        if self.restored is None:self.restored=(*self.get_position(),*self.get_size());self.move(0,0);screen=self.get_screen();self.resize(screen.get_width(),screen.get_height()-28)
        else:
            x,y,w,h=self.restored;self.restored=None;self.move(x,y);self.resize(w,h)
    def system_menu(self):
        rows=[(label,('system',command),enabled,'','Alt+F4' if command=='close' else '') for command,label,mnemonic,enabled in options(resizable=True,minimizable=True,maximized=self.restored is not None)]
        rows.insert(len(rows)-1,None)
        self.menu_popup=FontMenu(self,rows,4,126,top=22)
    def command(self,command):
        if command=='close':self.destroy()
        elif command=='minimize':self.hide();self.shell.get_window().focus(Gdk.CURRENT_TIME)
        elif command=='maximize':self.maximize()
        elif command=='system':self.system_menu()
        elif isinstance(command,tuple) and command[0]=='system':
            action=command[1]
            if action in ('restore','maximize'):self.maximize()
            elif action in ('close','minimize'):self.command(action)
            else:
                pointer=self.get_display().get_default_seat().get_pointer().get_position();self.operation=WindowOperation.begin(action,(*self.get_position(),*self.get_size()),(pointer.x,pointer.y))
        self.area.queue_draw();return False
    def error(self,error):
        from win95lx.apps.dialogs import message_box
        text='The font operation could not be completed. The previous files have been kept.' if isinstance(error,subprocess.SubprocessError) else str(error)
        message_box(self,self.title,text,Gtk.MessageType.ERROR)
    def press(self,area,e):
        if e.button!=1:return False
        self.get_window().focus(getattr(e,'time',Gdk.CURRENT_TIME));w,h=self.get_size()
        if e.x>=w-12 and e.y>=h-12:self.sizing=(e.x_root,e.y_root,w,h);return True
        for rect,command in reversed(self.hits):
            x,y,rw,rh=rect
            if x<=e.x<x+rw and y<=e.y<y+rh:self.command(command);return True
        if e.y<23:
            if getattr(e,'type',None)==Gdk.EventType._2BUTTON_PRESS:self.maximize()
            else:self.drag=(e.x,e.y)
            return True
        return False
    def release(self,area,e):self.drag=None;self.sizing=None;self.operation=None;return False
    def motion(self,area,e):
        screen=self.get_screen()
        if self.drag:
            x,y,_,_=fit_bounds((int(e.x_root-self.drag[0]),int(e.y_root-self.drag[1]),*self.get_size()),(screen.get_width(),screen.get_height()));self.move(x,y);return True
        if self.sizing:
            x,y,w,h=self.sizing;self.resize(max(320,int(w+e.x_root-x)),max(180,int(h+e.y_root-y)));return True
        if self.operation:
            x,y,w,h=self.operation.motion(e.x_root,e.y_root,(screen.get_width(),screen.get_height()));self.move(x,y);self.resize(w,h);return True
        return False
    def key(self,window,e):
        name=Gdk.keyval_name(e.keyval);alt=bool(e.state&Gdk.ModifierType.MOD1_MASK)
        if self.operation:
            if name=='Escape':
                x,y,w,h=self.operation.original;self.move(x,y);self.resize(w,h);self.operation=None;return True
            if name in ('Return','KP_Enter'):self.operation=None;return True
            if name in ARROWS:
                screen=self.get_screen();x,y,w,h=self.operation.step(*ARROWS[name],(screen.get_width(),screen.get_height()));self.move(x,y);self.resize(w,h);return True
        if alt and name=='space':self.system_menu();return True
        if alt and name=='F4':self.destroy();return True
        return False
    def wheel(self,area,e):return False

class FontsWindow(FontWindow):
    def __init__(self,shell,catalog=None):
        super().__init__(shell,'Fonts',(600,411),'fonts-folder-frame.png');self.catalog=catalog or FontCatalog();self.faces=[];self.selection=set();self.cursor=0;self.anchor=0;self.scroll=0;self.status=True;self.view='large';self.hide_variations=False;self.search='';self.search_time=0;self.previews=[];self.scroll_drag=None
        self.images={name:cairo.ImageSurface.create_from_png(str(self.assets/f'fonts-{name}-32.png')) for name in ('truetype','bitmap','opentype')};self.refresh()
        self.connect('destroy',lambda *_:[preview.destroy() for preview in tuple(self.previews)])
        self.drag_dest_set(Gtk.DestDefaults.ALL,[Gtk.TargetEntry.new('text/uri-list',0,0)],Gdk.DragAction.COPY);self.connect('drag-data-received',self.drop_received)
    def refresh(self):
        selected={self.faces[i].key for i in self.selection if i<len(self.faces)};faces=self.catalog.inventory();seen=set();self.faces=[]
        for face in faces:
            key=str(face.path) if face.format=='Windows FNT' else face.key
            if key in seen:continue
            seen.add(key)
            if self.hide_variations and any(word in face.style.casefold() for word in ('bold','italic','oblique')):continue
            self.faces.append(face)
        self.selection={i for i,face in enumerate(self.faces) if face.key in selected};self.cursor=min(self.cursor,max(0,len(self.faces)-1));self.scroll=0;self.area.queue_draw()
    def metrics(self,w=None,h=None):
        if w is None:w,h=self.get_size()
        height=max(1,h-(69 if self.status else 50));columns=max(1,(w-28)//75) if self.view=='large' else 1
        step=75 if self.view=='large' else 20;visible=max(1,height//step);maximum=max(0,math.ceil(len(self.faces)/columns)-visible)
        return columns,step,visible,maximum,height
    def draw(self,area,cr):
        w,h=area.get_allocated_width(),area.get_allocated_height();p=Painter(cr,self.shell.font);self.chrome(p,w,h)
        if (w,h)!=(600,411):
            for label,x in (('File',9),('Edit',37),('View',68),('Help',104)):p.text(label,x,27)
            p.fill(4,42,w-8,1,SHADOW);p.fill(5,43,w-10,1,BLACK)
        for label,x,width in (('File',6,26),('Edit',32,28),('View',60,36),('Help',96,37)):self.hit((x,24,width,18),('menu',label))
        columns,step,visible,maximum,height=self.metrics(w,h);self.scroll=min(self.scroll,maximum)
        p.fill(6,44,w-12,height,LIGHT);cr.save();cr.rectangle(6,44,w-12-(16 if maximum else 0),height);cr.clip()
        first=self.scroll*columns;last=min(len(self.faces),first+(visible+1)*columns)
        for index in range(first,last):
            row,col=divmod(index-first,columns);face=self.faces[index];selected=index in self.selection
            if self.view=='large':
                x,y=27+75*col,46+step*row;image=self.images['bitmap' if face.format in ('Windows FNT','BDF','PCF') else 'opentype' if face.path.suffix.casefold()=='.otf' else 'truetype']
                if selected:p.selected_image(image,x,y)
                else:p.image(image,x,y)
                labels=wrap_label(face.label,p.font,70,3)
                for line,label in enumerate(labels):
                    tx=43+75*col-p.font.width(label)//2;ty=y+36+13*line
                    if selected:p.fill(tx-1,ty+1,p.font.width(label)+2,13,NAVY)
                    p.text(label,tx,ty,LIGHT if selected else BLACK)
                    if index==self.cursor and line==0:
                        color=(255,255,0) if selected else BLACK
                        p.fill(tx-2,ty,p.font.width(label)+4,1,color);p.fill(tx-2,ty+14,p.font.width(label)+4,1,color)
                        p.fill(tx-2,ty,1,15,color);p.fill(tx+p.font.width(label)+1,ty,1,15,color)
                self.hit((6+75*col,44+step*row,75,75),('select',index))
            else:
                y=45+step*row
                if selected:p.fill(7,y,w-30,20,NAVY)
                p.text(face.label,28,y+3,LIGHT if selected else BLACK)
                if self.view=='details':p.text(face.format,w-180,y+3,LIGHT if selected else BLACK)
                self.hit((6,y,w-28,20),('select',index))
        cr.restore()
        if maximum:
            VerticalScrollbar(height,maximum).draw(p,w-22,44,self.scroll);self.hit((w-22,44,16,height),('scroll',))
        if self.status:
            if (w,h)!=(600,411):p.bevel(4,h-22,w-8,18,True)
            p.fill(6,h-18,w-28,13,FACE);p.text(f'{len(self.selection)} font(s) selected' if self.selection else f'{len(self.faces)} font(s)',6,h-18)
        return False
    def selected(self):return tuple(self.faces[i] for i in sorted(self.selection) if i<len(self.faces))
    def select(self,index,state=0):
        if not 0<=index<len(self.faces):return
        if state&Gdk.ModifierType.SHIFT_MASK:self.selection=set(range(min(self.anchor,index),max(self.anchor,index)+1))
        elif state&Gdk.ModifierType.CONTROL_MASK:self.selection.symmetric_difference_update((index,));self.anchor=index
        else:self.selection={index};self.anchor=index
        self.cursor=index;columns,step,visible,maximum,height=self.metrics();row=index//columns;self.scroll=max(0,min(self.scroll,row));self.scroll=min(maximum,max(self.scroll,row-visible+1));self.area.queue_draw()
    def menu_rows(self,name):
        selected=bool(self.selected());reason=next((self.catalog.removal_reason(face.path) for face in self.selected() if self.catalog.removal_reason(face.path)),None)
        if name=='File':return [('Open','preview',selected,''),('Print','print',False,PRINT_REASON),('Install New Font...','install',True,''),None,('Create Shortcut','shortcut',False,LINK_REASON),('Delete','delete',selected and reason is None,reason or ''),('Rename','rename',False,LINK_REASON),('Properties','properties',selected,''),None,('Close','close',True,'')]
        if name=='Edit':return [('Undo','undo',False,'Undo for font installation/removal is not implemented yet.','Ctrl+Z'),None,('Cut','cut',False,'Moving installed fonts through the clipboard is not implemented.','Ctrl+X'),('Copy','copy',selected,'','Ctrl+C'),('Paste','paste',True,'','Ctrl+V'),None,('Select All','all',bool(self.faces),'','Ctrl+A'),('Invert Selection','invert',bool(self.faces),'')]
        if name=='View':return [('Toolbar','toolbar',False,'The Fonts toolbar has not been implemented.'),('Status Bar','status',True,''),None,('Large Icons','large',True,''),('List','list',True,''),('List Fonts By Similarity','similarity',False,'Font-similarity classification is not implemented.'),('Details','details',True,''),None,('Hide Variations (Bold, Italic, etc.)','variations',True,''),None,('Refresh','refresh',True,''),('Options...','options',False,'Font options are not implemented yet.')]
        return [('Help Topics','help',True,''),None,('About Fonts','about',True,'')]
    def command(self,command):
        if isinstance(command,tuple) and command[0]=='menu':
            label=command[1];self.menu_popup=FontMenu(self,self.menu_rows(label),{'File':4,'Edit':32,'View':64,'Help':99}[label],{'File':132,'Edit':154,'View':199,'Help':130}[label]);return False
        if isinstance(command,tuple) and command[0]=='select':self.select(command[1]);return False
        if command in ('preview','properties'):
            if self.selected():
                try:preview=FontPreview(self,self.selected()[0]);self.previews.append(preview);preview.show_all();preview.present()
                except (OSError,ValueError,RuntimeError) as error:self.error(error)
        elif command=='install':
            from win95lx.apps.dialogs import choose_file
            path=choose_file(self,None,(('Fonts',tuple('*'+value for ext in sorted(EXTENSIONS) for value in (ext,ext.upper()))),('All Files (*.*)',('*',))))
            if path:self.install_files((path,))
        elif command=='delete':self.delete_selected()
        elif command=='refresh':self.refresh()
        elif command=='all':self.selection=set(range(len(self.faces)));self.area.queue_draw()
        elif command=='invert':self.selection=set(range(len(self.faces)))-self.selection;self.area.queue_draw()
        elif command in ('large','list','details'):self.view=command;self.scroll=0;self.area.queue_draw()
        elif command=='status':self.status=not self.status;self.area.queue_draw()
        elif command=='variations':self.hide_variations=not self.hide_variations;self.selection.clear();self.refresh()
        elif command=='copy':Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text('\n'.join(face.path.resolve().as_uri() for face in self.selected()),-1)
        elif command=='paste':self.install_uris(Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).wait_for_text() or '')
        elif command in ('help','about'):
            from win95lx.apps.dialogs import message_box
            reasons=list(dict.fromkeys(row[3] for name in ('File','Edit','View') for row in self.menu_rows(name) if row and not row[2] and row[3]))
            message_box(self,'Fonts','Open a font to view its sample. Install New Font copies it into your personal Fonts folder. System fonts remain read-only.\n\n'+'\n\n'.join(reasons),Gtk.MessageType.INFO)
        else:return super().command(command)
        return False
    def install_files(self,paths):
        installed=[]
        for path in paths:
            try:installed.extend(self.catalog.install(path))
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:self.error(error)
        self.refresh();keys={face.key for face in installed};self.selection={i for i,face in enumerate(self.faces) if face.key in keys};self.area.queue_draw();return installed
    def install_uris(self,text):
        paths=[]
        for value in text.splitlines():
            parsed=urllib.parse.urlparse(value)
            if parsed.scheme=='file' and parsed.netloc in ('','localhost'):paths.append(Path(urllib.parse.unquote(parsed.path)))
        if not paths:self.error(ValueError('The clipboard does not contain a local font file.'));return ()
        return self.install_files(paths)
    def drop_received(self,window,context,x,y,data,info,event_time):
        installed=self.install_uris('\n'.join(data.get_uris() or ()));Gtk.drag_finish(context,bool(installed),False,event_time)
    def delete_selected(self):
        from win95lx.apps.dialogs import message_box,YES_NO
        faces=self.selected();paths=tuple(dict.fromkeys(face.path for face in faces))
        if not paths:return
        reason=next((self.catalog.removal_reason(path) for path in paths if self.catalog.removal_reason(path)),None)
        if reason:self.error(PermissionError(reason));return
        if message_box(self,'Delete Font',f'Are you sure you want to delete {len(paths)} font file(s)? All faces in a font collection will be removed.',Gtk.MessageType.QUESTION,YES_NO,Gtk.ResponseType.NO)!=Gtk.ResponseType.YES:return
        for path in paths:
            try:self.catalog.remove(path)
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:self.error(error)
        self.selection.clear();self.refresh()
    def press(self,area,e):
        for rect,command in reversed(self.hits):
            x,y,w,h=rect
            if x<=e.x<x+w and y<=e.y<y+h and isinstance(command,tuple) and command[0]=='select':
                self.select(command[1],e.state)
                if getattr(e,'type',None)==Gdk.EventType._2BUTTON_PRESS:self.command('preview')
                return True
            if x<=e.x<x+w and y<=e.y<y+h and command==('scroll',):
                _,_,_,maximum,height=self.metrics();bar=VerticalScrollbar(height,maximum);top=bar.thumb_top(self.scroll);local=e.y-44
                if top<=local<top+bar.thumb:self.scroll_drag=local-top
                else:self.scroll=max(0,min(maximum,self.scroll+(-1 if local<16 else 1 if local>=height-16 else -4 if local<top else 4)))
                self.area.queue_draw();return True
        if e.button==1 and 44<=e.y<self.get_size()[1]-25:self.selection.clear();self.area.queue_draw()
        return super().press(area,e)
    def motion(self,area,e):
        if self.scroll_drag is not None:
            _,_,_,maximum,height=self.metrics();self.scroll=VerticalScrollbar(height,maximum).value_at(e.y-44-self.scroll_drag);self.area.queue_draw();return True
        return super().motion(area,e)
    def release(self,area,e):self.scroll_drag=None;return super().release(area,e)
    def wheel(self,area,e):
        maximum=self.metrics()[3];self.scroll=max(0,min(maximum,self.scroll+(1 if e.direction==Gdk.ScrollDirection.DOWN else -1)));self.area.queue_draw();return True
    def key(self,window,e):
        if self.operation is not None:return super().key(window,e)
        name=Gdk.keyval_name(e.keyval);ctrl=bool(e.state&Gdk.ModifierType.CONTROL_MASK);alt=bool(e.state&Gdk.ModifierType.MOD1_MASK)
        if alt and name and name.casefold() in ('f','e','v','h'):self.command(('menu',{'f':'File','e':'Edit','v':'View','h':'Help'}[name.casefold()]));return True
        if ctrl and name and name.casefold() in ('a','c','v'):self.command({'a':'all','c':'copy','v':'paste'}[name.casefold()]);return True
        if name in ('Return','KP_Enter'):self.command('preview');return True
        if name=='Delete':self.command('delete');return True
        if name=='F5':self.refresh();return True
        if name=='F1':self.command('help');return True
        if name in ('Left','Right','Up','Down','Home','End','Page_Up','Page_Down') and self.faces:
            columns,step,visible,maximum,height=self.metrics();index=0 if name=='Home' else len(self.faces)-1 if name=='End' else max(0,min(len(self.faces)-1,self.cursor+{'Left':-1,'Right':1,'Up':-columns,'Down':columns,'Page_Up':-columns*visible,'Page_Down':columns*visible}[name]));self.select(index,e.state);return True
        if name=='space' and not alt and self.faces:self.select(self.cursor,e.state);return True
        if not ctrl and not alt:
            char=Gdk.keyval_to_unicode(e.keyval)
            if char and chr(char).isprintable():
                now=time.monotonic();self.search=(self.search if now-self.search_time<1 else '')+chr(char).casefold();self.search_time=now
                index=next((i for i,face in enumerate(self.faces) if face.label.casefold().startswith(self.search)),None)
                if index is not None:self.select(index,e.state)
                return True
        return super().key(window,e)

class FontPreview(FontWindow):
    def __init__(self,parent,face):
        title=face.label+' ('+face.format+')';super().__init__(parent.shell,title,(371,414),'fonts-preview-frame.png');self.set_transient_for(parent);self.connect('destroy',lambda *_:parent.get_window().focus(Gdk.CURRENT_TIME) if parent.get_window() else None);self.face=face;self.scroll=0;self.content_height=1000;self.scroll_drag=None
        self.metadata=font_metadata(face.path,face.index);self.size_bytes=face.path.stat().st_size
        serif=self.assets/'fonts-preview-serif.ttf';paths=[face.path]+([serif] if serif.exists() else [])
        scanner=fontconfig();config=scanner.preview_config(paths)
        try:
            self.font_map=PangoCairo.FontMap.new()
            pointer=C.pythonapi.PyCapsule_GetPointer;pointer.argtypes=[C.py_object,C.c_char_p];pointer.restype=C.c_void_p
            library=ctypes.util.find_library('pangoft2-1.0')
            if not library:raise RuntimeError('The font preview renderer is unavailable.')
            pango=C.CDLL(library);pango.pango_fc_font_map_set_config.argtypes=[C.c_void_p,C.c_void_p];pango.pango_fc_font_map_set_config.restype=None
            pango.pango_fc_font_map_set_config(pointer(self.font_map.__gpointer__,None),config)
        finally:scanner.destroy_config(config)
        self.preview_context=self.font_map.create_context();PangoCairo.context_set_resolution(self.preview_context,96)
        def closed(*_):
            if self in parent.previews:parent.previews.remove(self)
            self.preview_context=None;self.font_map=None
        self.connect('destroy',closed)
        self.set_icon(GdkPixbuf.Pixbuf.new_from_file(str(self.assets/'fonts-truetype-16.png')))
    def text(self,cr,text,x,y,pixels,family=None,width=None):
        description=Pango.FontDescription();description.set_family(family or self.face.family);description.set_absolute_size(round(pixels*Pango.SCALE))
        if family is None:
            style=self.face.style.casefold()
            if 'bold' in style:description.set_weight(Pango.Weight.BOLD)
            if 'italic' in style or 'oblique' in style:description.set_style(Pango.Style.ITALIC)
        PangoCairo.update_context(cr,self.preview_context);layout=Pango.Layout.new(self.preview_context);layout.set_font_description(description);layout.set_text(text,-1)
        if family is None:
            attributes=Pango.AttrList();attributes.insert(Pango.attr_fallback_new(False));layout.set_attributes(attributes)
        if width is not None:layout.set_width(round(width*Pango.SCALE));layout.set_wrap(Pango.WrapMode.WORD_CHAR)
        PangoCairo.update_layout(cr,layout);cr.move_to(x,y);PangoCairo.show_layout(cr,layout);return layout.get_pixel_size()[1]
    def draw(self,area,cr):
        w,h=area.get_allocated_width(),area.get_allocated_height();p=Painter(cr,self.shell.font);self.chrome(p,w,h)
        p.fill(24,4,w-80,18,NAVY if self.caption_active else SHADOW);p.cr.save();p.cr.rectangle(24,4,w-82,18);p.cr.clip();p.text(self.title,24,6,LIGHT,bold=True);p.cr.restore()
        self.hit((12,30,76,25),'close')
        p.button('Print',w-88,32,75,23);p.fill(w-85,35,69,17,FACE);label='Print';tx=w-88+(75-p.font.width(label))//2;p.text(label,tx+1,38,LIGHT);p.text(label,tx,37,SHADOW)
        viewport=max(1,h-70);width=max(1,w-29);p.fill(6,63,width,viewport,LIGHT);cr.save();cr.rectangle(6,63,width,viewport);cr.clip()
        options=cairo.FontOptions();options.set_antialias(cairo.ANTIALIAS_NONE);options.set_hint_style(cairo.HINT_STYLE_FULL);options.set_hint_metrics(cairo.HINT_METRICS_ON);cr.set_font_options(options);cr.set_source_rgb(0,0,0);y=63-self.scroll
        y+=self.text(cr,self.title,6,y,32,'Times New Roman')+4;p.fill(6,y,width,1,BLACK);y+=5
        info=[f'Typeface name: {self.face.family}',f'File size: {max(1,self.size_bytes//1024)} KB','Version: '+self.metadata.get('version',f'{self.face.version/65536:.2f}' if self.face.version else 'Not specified')]
        if self.metadata.get('copyright'):info.append(self.metadata['copyright'])
        for label in info:y+=max(19,self.text(cr,label,6,y,13,'Times New Roman',width-4))
        p.fill(6,y,width,1,BLACK);y+=5
        for label in ('abcdefghijklmnopqrstuvwxyz','ABCDEFGHIJKLMNOPQRSTUVWXYZ','1234567890.:,;\'"(!?)'):
            y+=max(24,self.text(cr,label,6,y,20))
        p.fill(6,y,width,1,BLACK);y+=10
        for points in (12,18,24,36,48,60,72):
            self.text(cr,str(points),6,y+3,11,'Times New Roman');y+=max(20,self.text(cr,'The quick brown fox jumps over the lazy dog. 1234567890',30,y,points*4/3))+13
        self.content_height=round(y+self.scroll-63);cr.restore();maximum=max(0,self.content_height-viewport);self.scroll=min(self.scroll,maximum)
        VerticalScrollbar(viewport,maximum,thumb=max(21,round(viewport*viewport/max(viewport,self.content_height)))).draw(p,w-22,63,self.scroll);self.hit((w-22,63,16,viewport),('preview-scroll',))
        return False
    def wheel(self,area,e):self.scroll=max(0,min(max(0,self.content_height-self.get_size()[1]+70),self.scroll+(39 if e.direction==Gdk.ScrollDirection.DOWN else -39)));self.area.queue_draw();return True
    def press(self,area,e):
        w,h=self.get_size()
        if w-22<=e.x<w-6 and 63<=e.y<h-7:
            viewport=h-70;maximum=max(0,self.content_height-viewport);bar=VerticalScrollbar(viewport,maximum,thumb=max(21,round(viewport*viewport/max(viewport,self.content_height))));local=e.y-63;top=bar.thumb_top(self.scroll)
            if top<=local<top+bar.thumb:self.scroll_drag=local-top
            else:self.scroll=max(0,min(maximum,self.scroll+(-26 if local<16 else 26 if local>=viewport-16 else -viewport if local<top else viewport)))
            self.area.queue_draw();return True
        return super().press(area,e)
    def motion(self,area,e):
        w,h=self.get_size();self.area.set_tooltip_text(PRINT_REASON if w-88<=e.x<w-13 and 32<=e.y<55 else None)
        if self.scroll_drag is not None:
            viewport=h-70;maximum=max(0,self.content_height-viewport);self.scroll=VerticalScrollbar(viewport,maximum,thumb=max(21,round(viewport*viewport/max(viewport,self.content_height)))).value_at(e.y-63-self.scroll_drag);self.area.queue_draw();return True
        return super().motion(area,e)
    def release(self,area,e):self.scroll_drag=None;return super().release(area,e)
    def key(self,window,e):
        if self.operation is not None:return super().key(window,e)
        name=Gdk.keyval_name(e.keyval);maximum=max(0,self.content_height-self.get_size()[1]+70)
        if name in ('Escape','Return','KP_Enter'):self.destroy();return True
        if name in ('Down','Up','Page_Down','Page_Up','Home','End'):
            self.scroll=0 if name=='Home' else maximum if name=='End' else max(0,min(maximum,self.scroll+{'Down':26,'Up':-26,'Page_Down':self.get_size()[1]-70,'Page_Up':70-self.get_size()[1]}[name]));self.area.queue_draw();return True
        if name=='F1':
            from win95lx.apps.dialogs import message_box
            message_box(self,'Font Preview',PRINT_REASON,Gtk.MessageType.INFO);return True
        return super().key(window,e)
