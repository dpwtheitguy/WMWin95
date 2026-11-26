"""Native-size desktop pattern chooser and 8x8 editor."""

from pathlib import Path
import cairo
from gi.repository import Gdk, Gtk
from win95lx.apps.dialogs import artwork_button, dialog_art, fixed_canvas, install_style, NATIVE_STYLE, run_dialog
from win95lx.control_panel.wallpaper import paint_pattern
from win95lx.shell.scrollbar import VerticalScrollbar
from win95lx.shell.widgets import BLACK, FACE, LIGHT, NAVY, TEAL, Painter


class PatternDialog(Gtk.Dialog):
    def __init__(self,parent,patterns,name,rows):
        super().__init__(title='Pattern',transient_for=parent,modal=True)
        self.set_decorated(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        assets,_,self.font = dialog_art(parent,'close')
        art = assets/'desktop-pattern-dialog.png'
        self.frame = cairo.ImageSurface.create_from_png(str(art)) if art.is_file() else None
        self.patterns = {'(None)':(0,)*8, **{name:tuple(rows) for name,rows in patterns.items()}}
        if name not in self.patterns:
            self.patterns[name] = tuple(rows)
        self.names = tuple(self.patterns)
        self.selected = self.names.index(name) if name in self.names else 0
        self.scroll = max(0,self.selected-5)
        self.result = None
        self.get_style_context().add_class('win95-native-file')
        install_style(self,NATIVE_STYLE)
        fixed,self.canvas = fixed_canvas(self,318,206,self.draw)
        self.canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.SCROLL_MASK)
        self.canvas.connect('button-press-event',self.click)
        self.canvas.connect('scroll-event',self.wheel)
        for label,rect,callback in (
            ('OK',(230,34,75,23),self.accept),
            ('Cancel',(230,64,75,23),lambda *_:self.response(Gtk.ResponseType.CANCEL)),
            ('Edit Pattern...',(230,93,75,23),self.edit),
            ('Close',(297,4,16,16),lambda *_:self.response(Gtk.ResponseType.CANCEL)),
        ):
            artwork_button(fixed,self.canvas,label,rect,callback)
        self.connect('key-press-event',self.key)
        self.get_content_area().show_all()

    def draw(self,_widget,context):
        p=Painter(context,self.font)
        if self.frame:
            p.image(self.frame,0,0)
        else:
            p.window_frame(0,0,318,206)
            p.fill(3,3,312,18,NAVY)
            p.text('Pattern',5,5,LIGHT,bold=True)
        p.fill(16,114,99,76,LIGHT)
        for index,name in enumerate(self.names[self.scroll:self.scroll+6]):
            y=114+index*13
            if self.scroll+index == self.selected:
                p.fill(16,y,99,13,NAVY)
            p.cr.save()
            p.cr.rectangle(16,114,99,76)
            p.cr.clip()
            p.text(name,17,y,LIGHT if self.scroll+index==self.selected else BLACK)
            p.cr.restore()
        bar=VerticalScrollbar(78,max(0,len(self.names)-6),16,14)
        bar.draw(p,116,113,self.scroll)
        p.fill(145,113,73,78,TEAL)
        paint_pattern(p,self.patterns[self.names[self.selected]],145,113,73,78)
        if self.names[self.selected] != '(None)':
            p.button('Edit Pattern...',230,93,75,23)
        return False

    def select(self,index):
        self.selected=max(0,min(len(self.names)-1,index))
        self.scroll=max(min(self.scroll,self.selected),self.selected-5)
        self.canvas.queue_draw()

    def click(self,_widget,event):
        if event.button != 1:
            return False
        if 16<=event.x<115 and 114<=event.y<190:
            self.select(self.scroll+int((event.y-114)//13))
        elif 116<=event.x<132 and 113<=event.y<191:
            direction=-1 if event.y<152 else 1
            self.scroll=max(0,min(len(self.names)-6,self.scroll+direction))
            self.canvas.queue_draw()
        return True

    def wheel(self,_widget,event):
        direction=-1 if event.direction==Gdk.ScrollDirection.UP else 1
        self.scroll=max(0,min(max(0,len(self.names)-6),self.scroll+direction))
        self.canvas.queue_draw()
        return True

    def key(self,_widget,event):
        if event.keyval in (Gdk.KEY_Up,Gdk.KEY_Down):
            self.select(self.selected+(-1 if event.keyval==Gdk.KEY_Up else 1))
        elif event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter):
            self.accept()
        elif event.keyval==Gdk.KEY_Escape:
            self.response(Gtk.ResponseType.CANCEL)
        else:
            return False
        return True

    def accept(self,*_):
        name=self.names[self.selected]
        self.result=name,self.patterns[name]
        self.response(Gtk.ResponseType.OK)

    def edit(self,*_):
        if self.names[self.selected]=='(None)':
            return
        rows=list(self.patterns[self.names[self.selected]])
        dialog=Gtk.Dialog(title='Edit Pattern',transient_for=self,modal=True)
        dialog.set_decorated(False)
        dialog.get_style_context().add_class('win95-native-file')
        install_style(dialog,NATIVE_STYLE)
        def draw(_widget,context):
            p=Painter(context,self.font)
            p.window_frame(0,0,286,228)
            p.fill(3,3,280,18,NAVY)
            p.text('Edit Pattern',5,5,LIGHT,bold=True)
            p.text('Pattern',16,32)
            p.text('Preview',174,32)
            for y,value in enumerate(rows):
                for x in range(8):
                    p.fill(16+x*16,50+y*16,15,15,BLACK if value&(128>>x) else LIGHT)
            p.fill(174,50,96,96,TEAL)
            paint_pattern(p,rows,174,50,96,96)
            p.button('OK',113,192,75,23)
            p.button('Cancel',194,192,75,23)
        fixed,canvas=fixed_canvas(dialog,286,228,draw)
        canvas.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        def click(_widget,event):
            if 16<=event.x<144 and 50<=event.y<178:
                x,y=int((event.x-16)//16),int((event.y-50)//16)
                rows[y] ^= 128>>x
                canvas.queue_draw()
                return True
            return False
        canvas.connect('button-press-event',click)
        artwork_button(fixed,canvas,'OK',(113,192,75,23),lambda *_:dialog.response(Gtk.ResponseType.OK))
        artwork_button(fixed,canvas,'Cancel',(194,192,75,23),lambda *_:dialog.response(Gtk.ResponseType.CANCEL))
        def key(_widget,event):
            if event.keyval==Gdk.KEY_Escape:
                dialog.response(Gtk.ResponseType.CANCEL)
                return True
            if event.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter):
                dialog.response(Gtk.ResponseType.OK)
                return True
            return False
        dialog.connect('key-press-event',key)
        dialog.pattern_canvas=canvas
        dialog.get_content_area().show_all()
        if run_dialog(dialog)==Gtk.ResponseType.OK:
            self.patterns['Custom']=tuple(rows)
            self.names=tuple(self.patterns)
            self.select(self.names.index('Custom'))
        dialog.destroy()


def choose_pattern(parent,patterns,name,rows):
    dialog=PatternDialog(parent,patterns,name,rows)
    try:
        return dialog.result if run_dialog(dialog)==Gtk.ResponseType.OK else None
    finally:
        dialog.destroy()
