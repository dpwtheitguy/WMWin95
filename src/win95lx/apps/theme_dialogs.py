"""Measured Plus! theme dialogs, sharing ordinary file navigation and controls."""
import math
from pathlib import Path
import cairo
from gi.repository import Gtk,Gdk,GdkPixbuf
from win95lx.apps.dialogs import FileDialog,NamespaceDropDialog,run_dialog,fixed_canvas,artwork_button,install_style,NATIVE_STYLE
from win95lx.shell.widgets import Painter,FACE,BLACK,LIGHT,NAVY
from win95lx.shell.command_button import draw_command_button,resolve_default
from win95lx.shell.window_bounds import fit_bounds

THEME_FILTERS=(('Theme Files',('*.theme',),'.theme'),)

class ThemeFileDialog(FileDialog):
    """The native426×264 Plus profile of the shared common file dialog.

    Filesystem operations remain the shared implementation. Save confirmation
    belongs to ThemeStore, which rechecks an identity token after the prompt.
    """
    def __init__(self,parent,folder,*,saving=True,store=None):
        self.theme_parent=parent;self.store=store
        super().__init__(parent,Path(folder),THEME_FILTERS,saving,'Untitled' if saving else '*.Theme')
        self.set_title('Save Theme' if saving else 'Open Theme')
        self.set_position(Gtk.WindowPosition.NONE)
        self.connect('map-event',self.place_native)

    def place_native(self,*_):
        owner=self.theme_parent;left,top=owner.get_position()
        offset=getattr(owner,'body_offset',0)
        screen=self.get_screen();x,y,_,_=fit_bounds((left+3,top+20+offset,426,264),(screen.get_width(),screen.get_height()),resizable=False)
        self.move(x,y);self.get_window().focus(Gdk.CURRENT_TIME)
        self.filename.grab_focus();self.filename.select_region(0,-1);return False

    def build_native(self,path,name):
        assets=self.theme_parent.assets
        image=cairo.ImageSurface.create_from_png(str(assets/('theme-file-save-frame.png' if self.saving else 'theme-file-open-frame.png')))
        self.native_art=(assets,image,self.theme_parent.shell.font)
        super().build_native(path,name)
        self.fixed.set_size_request(426,264);self.canvas.set_size_request(426,264);self.set_default_size(426,264)
        self.fixed.move(self.filename,86,203)
        for child in self.fixed.get_children():
            if isinstance(child,Gtk.ScrolledWindow):child.set_size_request(404,134)
        revised=[]
        for button,rect in self.buttons:
            label=button.get_accessible().get_name()
            rect={'Folder':(78,27,207,22),'Save':(336,201,75,23),'Open':(336,201,75,23),'Cancel':(336,230,75,23),'File type':(84,227,233,21)}.get(label,rect)
            self.fixed.move(button,rect[0],rect[1]);button.set_size_request(*rect[2:]);revised.append((button,rect))
        self.buttons=revised
        icon=assets/'cpl-themes-16.png'
        if icon.is_file():self.file_icons[False]=GdkPixbuf.Pixbuf.new_from_file(str(icon))
        self.change_folder(path)

    def change_folder(self,folder,wildcard=None):
        super().change_folder(folder,wildcard)
        if not self.native_art or self.folder is None or self.store is None:return
        if self.folder==self.store.default_directory.resolve():
            present={row[0].casefold()for row in self.files}
            from win95lx.control_panel.theme_store import ThemeStore
            for name in ThemeStore(self.store.default_directory,self.store.builtins).catalog():
                filename=name+'.theme'
                if filename.casefold()not in present:
                    self.files.append((filename,str(self.folder/filename),False,self.file_icons.get(False),''))
            self.files.set_sort_column_id(0,Gtk.SortType.ASCENDING)

    def draw_native(self,widget,context):
        _,frame,font=self.native_art;p=Painter(context,font);p.image(frame,0,0)
        p.fill(80,29,187,18,LIGHT);folder=(self.folder.name or 'Local Disk (C:)')if self.folder else''
        if self.store is not None and self.folder==self.store.default_directory.resolve():folder='Themes'
        if self.file_icons.get(True):Gdk.cairo_set_source_pixbuf(context,self.file_icons[True],81,29);context.paint()
        p.text(folder,103,31);p.fill(86,229,213,17,LIGHT);p.text('Theme Files',88,231)
        commands={}
        for button,rect in self.buttons:
            label=button.get_accessible().get_name()
            if label in('Save','Open','Cancel'):commands[label]=button
        focused=next((name for name,button in commands.items()if button.has_focus()),None)
        default=focused or('Save'if self.saving else'Open')
        for button,rect in self.buttons:
            label=button.get_accessible().get_name()
            if label in commands:
                p.fill(rect[0]-1,rect[1]-1,rect[2]+2,rect[3]+2,FACE)
                draw_command_button(p,{'Save':'&Save','Open':'&Open','Cancel':'Cancel'}[label],rect,default=label==default,focused=button.has_focus(),pressed=bool(button.get_state_flags()&Gtk.StateFlags.ACTIVE))
        return False

    def accept(self):
        if not self.saving:
            candidate=self.folder/ self.filename.get_text().strip() if self.folder is not None else None
            if candidate is not None and self.store is not None and self.folder==self.store.default_directory.resolve() and candidate.stem in self.store.builtins and not candidate.exists():
                self.path=candidate;self.response(Gtk.ResponseType.OK);return
            return super().accept()
        name=self.filename.get_text().strip()
        if not name or self.folder is None:return
        candidate=self.folder/Path(name).expanduser()
        if candidate.is_dir():self.change_folder(candidate);return
        if not candidate.suffix:candidate=candidate.with_suffix('.theme')
        if not candidate.parent.is_dir():self.feedback.set_text('Choose an existing folder and a theme name.');return
        self.path=candidate;self.response(Gtk.ResponseType.OK)

    def handle_key(self,dialog,event):
        name=Gdk.keyval_name(event.keyval)or''
        if event.state&Gdk.ModifierType.MOD1_MASK:
            if name.casefold()=='n':self.filename.grab_focus();self.filename.select_region(0,-1);return True
            if name.casefold()in(('s',)if self.saving else('o',)):self.accept();return True
        return super().handle_key(dialog,event)


def choose_theme_file(parent,folder,*,saving=True,store=None):
    dialog=ThemeFileDialog(parent,folder,saving=saving,store=store)
    try:return dialog.path if run_dialog(dialog)==Gtk.ResponseType.OK else None
    finally:dialog.destroy()


class ThemeQuestion(NamespaceDropDialog):
    """Native MB_YESNO geometry; Escape/Close do not invent a Cancel response."""
    def __init__(self,parent,text,*,title='Desktop Themes',default=Gtk.ResponseType.YES):
        super().__init__(title=title,transient_for=parent,modal=True)
        self.set_decorated(False);self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.assets=parent.assets;self.dialog_assets=self.assets;self.font=parent.shell.font
        width=max(260,min(600,self.font.width(text)+75));text_width=width-75
        self.lines=[]
        for paragraph in text.splitlines():
            line=''
            words=[]
            for word in paragraph.split():
                piece=''
                for char in word:
                    if piece and self.font.width(piece+char)>text_width:words.append(piece);piece=''
                    piece+=char
                if piece:words.append(piece)
            for word in words:
                value=(line+' '+word).strip()
                if line and self.font.width(value)>text_width:self.lines.append(line);line=word
                else:line=value
            self.lines.append(line)
        body=max(32,len(self.lines)*13+2);height=33+body+17+23+14
        self.size=(width,height);self.text=text;self.body=body;self.selected=default
        self.frame=cairo.ImageSurface.create_from_png(str(self.assets/'theme-delete-frame.png'))
        self.controls=[];self.button_y=height-37
        # Native message box uses the dialog's6px horizontal font base.
        du=math.ceil((width-6)/1.5);left=3+math.floor(((du-104)/2)*1.5+.5)
        fixed,self.canvas=fixed_canvas(self,width,height,self.draw)
        install_style(self,NATIVE_STYLE)
        for label,response,x in (('&Yes',Gtk.ResponseType.YES,left),('&No',Gtk.ResponseType.NO,left+81)):
            button=artwork_button(fixed,self.canvas,label.replace('&',''),(x,self.button_y,75,23),lambda _b,r=response:self.response(r))
            button.connect('notify::has-focus',lambda b,_pspec,r=response:self.focused(b,r));self.controls.append((label,response,button,x))
        self.connect('key-press-event',self.key);self.get_content_area().show_all()
        self.connect('map-event',lambda *_:self.focus_default())
        for _,response,button,_ in self.controls:
            if response==default:button.grab_focus()

    def focus_default(self):
        for _,response,button,_ in self.controls:
            if response==self.selected:button.grab_focus()
        return False

    def focused(self,button,response):
        if button.has_focus():self.selected=response;self.canvas.queue_draw()

    def draw(self,_area,cr):
        width,height=self.size;p=Painter(cr,self.font);p.window_frame(0,0,width,height);p.fill(0,height-1,1,1,BLACK)
        p.fill(3,3,width-6,18,NAVY)
        if self.get_title()=='Desktop Themes':
            cr.save();cr.rectangle(3,3,150,17);cr.clip();p.image(self.frame,0,0);cr.restore()
        else:p.text(self.get_title(),5,4,LIGHT,bold=True)
        cr.save();cr.rectangle(width-35,0,35,22);cr.clip();p.image(self.frame,width-self.frame.get_width(),0);cr.restore()
        cr.save();cr.rectangle(14,33,32,32);cr.clip();p.image(self.frame,0,0);cr.restore()
        top=33+math.ceil((self.body-(len(self.lines)*13+2))/2)
        for index,line in enumerate(self.lines):p.text(line,62,top+index*13)
        for label,response,button,x in self.controls:
            draw_command_button(p,label,(x,self.button_y,75,23),default=response==self.selected,focused=button.has_focus(),pressed=bool(button.get_state_flags()&Gtk.StateFlags.ACTIVE))
        return False

    def key(self,_dialog,event):
        name=Gdk.keyval_name(event.keyval)or''
        if name=='Escape'or name=='F4'and event.state&Gdk.ModifierType.MOD1_MASK:return True
        if name in('Return','KP_Enter'):self.response(self.selected);return True
        if name.casefold()in('y','n'):self.response(Gtk.ResponseType.YES if name.casefold()=='y'else Gtk.ResponseType.NO);return True
        return False


def confirm_theme_delete(parent,name):
    dialog=ThemeQuestion(parent,"Are you sure you want to delete the '"+name+"' theme?")
    try:return run_dialog(dialog)==Gtk.ResponseType.YES
    finally:dialog.destroy()
