"""Native drawn dropdown popup and small reusable property-sheet selectors."""
import cairo
from gi.repository import Gtk,Gdk
from win95lx.shell.widgets import Painter,BLACK,LIGHT,NAVY,FACE,SHADOW
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.shell.command_button import draw_command_button
from win95lx.apps.popup_events import dismiss_and_replay,local_point

class ChoicePopup(Gtk.Window):
    def __init__(self,parent,rect,choices,value,callback):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_transient_for(parent);self.set_decorated(False);self.parent=parent;self.shell=parent.shell
        self.choices=tuple(choices);self.value=value;self.callback=callback;self.visible=min(12,len(choices));self.scroll=max(0,min(value,len(choices)-self.visible))
        self.width=rect[2];self.height=self.visible*13+2;self.drag=None;self.finished=False
        x,y=parent.get_position();screen=parent.get_screen();left=min(x+rect[0],screen.get_width()-self.width)
        top=y+rect[1]+rect[3]
        if top+self.height>screen.get_height()-28:top=max(0,y+rect[1]-self.height)
        self.move(max(0,left),max(0,top));self.area=Gtk.DrawingArea();self.area.set_size_request(self.width,self.height);self.add(self.area)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.SCROLL_MASK)
        self.area.connect('draw',self.draw);self.area.connect('button-press-event',self.press);self.area.connect('motion-notify-event',self.motion);self.area.connect('scroll-event',self.wheel)
        self.connect('realize',lambda *_:self.get_window().set_cursor(self.shell.cursor_for('arrow')))
        # GTK redirects an outside click to the grabbed Window, not its child
        # DrawingArea. Listening only on the area leaves the popup trapped.
        self.connect('button-press-event',self.press)
        self.connect('key-press-event',self.key)
        self.connect('focus-out-event',lambda *_:self.finish(None,restore_focus=False))
        self.connect('grab-broken-event',lambda *_:self.finish(None,restore_focus=False))
        self.connect('destroy',self.cleanup)
        self.parent_destroy=self.parent.connect('destroy',lambda *_:self.finish(None,restore_focus=False))
        self.show_all();self.grab_add();self.present();self.get_window().focus(Gdk.CURRENT_TIME)
    def draw(self,_area,cr):
        p=Painter(cr,self.shell.font);p.fill(0,0,self.width,self.height,BLACK);p.fill(1,1,self.width-2,self.height-2,LIGHT)
        gutter=16 if len(self.choices)>self.visible else 0
        for row,label in enumerate(self.choices[self.scroll:self.scroll+self.visible]):
            y=1+row*13;selected=self.scroll+row==self.value
            if selected:p.fill(1,y,self.width-2-gutter,13,NAVY)
            p.text(label,3,y,LIGHT if selected else BLACK)
        if gutter:VerticalScrollbar(self.height-2,len(self.choices)-self.visible).draw(p,self.width-17,1,self.scroll)
        return False
    def cleanup(self,*_):
        self.finished=True
        if self.has_grab():self.grab_remove()
        handler=getattr(self,'parent_destroy',None)
        if handler and self.parent is not None and self.parent.handler_is_connected(handler):self.parent.disconnect(handler)
        self.parent_destroy=None;self.callback=None;self.parent=None
    def finish(self,value,*,restore_focus=True):
        if self.finished:return False
        parent,callback=self.parent,self.callback
        self.finished=True;self.cleanup();self.destroy()
        if restore_focus and parent.get_visible():parent.present()
        if value is not None and parent.get_visible():callback(value)
        return False
    def outside(self,event):
        # Preserve the initiating click: after removing the GTK grab, dispatch
        # it to the actual window under the pointer, then its normal release.
        return dismiss_and_replay(event,lambda:self.finish(None,restore_focus=False))
    def press(self,_area,event):
        if self.finished:return True
        local_x,local_y=local_point(self,event)
        if not 0<=local_x<self.width or not 0<=local_y<self.height:return self.outside(event)
        if event.button!=1:return self.finish(None)
        if len(self.choices)>self.visible and local_x>=self.width-17:
            delta=-1 if local_y<17 else 1 if local_y>=self.height-17 else self.visible*(-1 if local_y<self.height/2 else 1)
            self.scroll=max(0,min(len(self.choices)-self.visible,self.scroll+delta));self.area.queue_draw();return True
        index=self.scroll+int((local_y-1)//13)
        if 0<=index<len(self.choices):self.finish(index)
        return True
    def motion(self,_area,event):
        if self.finished:return True
        gutter=16 if len(self.choices)>self.visible else 0
        if 1<=event.y<self.height-1 and 1<=event.x<self.width-1-gutter:
            self.value=self.scroll+int((event.y-1)//13);self.area.queue_draw()
    def wheel(self,_area,event):
        if self.finished:return True
        self.scroll=max(0,min(len(self.choices)-self.visible,self.scroll+(1 if event.direction==Gdk.ScrollDirection.DOWN else -1)));self.area.queue_draw();return True
    def key(self,_window,event):
        if self.finished:return True
        name=Gdk.keyval_name(event.keyval)
        if name in ('Tab','ISO_Left_Tab'):
            parent=self.parent;self.finish(self.value);parent.key(parent,event);return True
        if name=='Escape' and getattr(event,'state',0)&Gdk.ModifierType.CONTROL_MASK or name=='F4' and getattr(event,'state',0)&Gdk.ModifierType.MOD1_MASK:
            parent=self.parent;self.finish(None,restore_focus=False);parent.key(parent,event);return True
        if name in ('Escape','F4'):return self.finish(None)
        if name in ('Return','KP_Enter','space'):return self.finish(self.value)
        if name in ('Up','Down','Home','End','Page_Up','Page_Down'):
            self.value=0 if name=='Home' else len(self.choices)-1 if name=='End' else max(0,min(len(self.choices)-1,self.value+{'Up':-1,'Down':1,'Page_Up':-self.visible,'Page_Down':self.visible}[name]))
            self.scroll=max(0,min(self.scroll,self.value));self.scroll=min(len(self.choices)-self.visible,max(self.scroll,self.value-self.visible+1));self.area.queue_draw();return True
        return False

class LanguageDialog(Gtk.Dialog):
    def __init__(self,parent,layouts,value=0,properties=False):
        super().__init__(title='Language Properties' if properties else 'Add Language',transient_for=parent,modal=True)
        self.shell=parent.shell;self.dialog_assets=parent.assets;self.assets=parent.assets
        self.layouts=tuple(layouts);self.value=value;self.properties=properties;self.focus=1
        self.set_decorated(False);self.set_resizable(False);self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.frame=cairo.ImageSurface.create_from_png(str(self.assets/('keyboard-language-properties.png' if properties else 'keyboard-add-language.png')))
        self.rect=(14,75 if properties else 51,318,21)
        self.size=(347,171);self.buttons=((177,133,75,23),(257,133,75,23))
        self.area=Gtk.DrawingArea();self.area.set_size_request(*self.size);self.get_content_area().pack_start(self.area,True,True,0)
        self.get_content_area().set_spacing(0)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK);self.area.connect('draw',self.draw);self.area.connect('button-press-event',self.press);self.connect('key-press-event',self.key)
        self.show_all()
    def draw(self,_area,cr):
        p=Painter(cr,self.shell.font);p.image(self.frame,0,0);x,y,w,h=self.rect
        p.fill(x+2,y+2,w-20,17,NAVY if self.focus==0 else LIGHT);p.text(self.layouts[self.value][0],x+3,y+3,LIGHT if self.focus==0 else BLACK)
        if self.properties:
            p.fill(86,33,235,18,FACE);p.text(self.layouts[self.value][0],87,34)
        for index,(label,rect) in enumerate(zip(('OK','Cancel'),self.buttons),1):
            draw_command_button(p,label,rect,default=self.focus==index or self.focus==0 and index==1,focused=self.focus==index)
        return False
    def choose(self):ChoicePopup(self,self.rect,[label for label,code in self.layouts],self.value,self.selected)
    def selected(self,index):self.value=index;self.area.queue_draw()
    def press(self,_area,event):
        x,y,w,h=self.rect
        if x<=event.x<x+w and y<=event.y<y+h:self.focus=0;self.choose()
        elif 177<=event.x<252 and 133<=event.y<156:self.response(Gtk.ResponseType.OK)
        elif 257<=event.x<332 and 133<=event.y<156 or 325<=event.x<341 and 6<=event.y<21:self.response(Gtk.ResponseType.CANCEL)
        return True
    def key(self,_window,event):
        name=Gdk.keyval_name(event.keyval)
        if name=='Escape' and getattr(event,'state',0)&Gdk.ModifierType.CONTROL_MASK:
            self.shell.key(self.shell,event);return True
        if name=='Escape':self.response(Gtk.ResponseType.CANCEL);return True
        if name in ('Return','KP_Enter'):self.response(Gtk.ResponseType.CANCEL if self.focus==2 else Gtk.ResponseType.OK);return True
        if name in ('Tab','ISO_Left_Tab'):self.focus=(self.focus+(-1 if event.state&Gdk.ModifierType.SHIFT_MASK else 1))%3;self.area.queue_draw();return True
        if name=='F4' or name=='Down' and event.state&Gdk.ModifierType.MOD1_MASK:self.choose();return True
        if self.focus==0 and name in ('Up','Down','Home','End'):
            self.value=0 if name=='Home' else len(self.layouts)-1 if name=='End' else max(0,min(len(self.layouts)-1,self.value+(1 if name=='Down' else -1)));self.area.queue_draw();return True
        if name=='space' and self.focus:self.response(Gtk.ResponseType.OK if self.focus==1 else Gtk.ResponseType.CANCEL);return True
        return False

def choose_language(parent,choices,value=0,properties=False):
    if not choices:return None
    dialog=LanguageDialog(parent,choices,value,properties)
    try:return choices[dialog.value][1] if dialog.run()==Gtk.ResponseType.OK else None
    finally:dialog.destroy()
