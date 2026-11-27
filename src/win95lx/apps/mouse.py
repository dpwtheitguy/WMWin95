"""Measured Mouse Properties sheet with real X11 settings and pending edits."""
from dataclasses import replace
from pathlib import Path
import json
import cairo
from gi.repository import Gtk,Gdk,GdkPixbuf,GLib
from win95lx.control_panel.mouse_preferences import MouseController,MousePreferences,X11Mouse,SCHEMES,ROLES
from win95lx.shell.widgets import Painter,FACE,BLACK,LIGHT,NAVY,SHADOW
from win95lx.shell.combo_box import ComboBox

class MouseWindow(Gtk.Window):
    def __init__(self,shell,backend=None):
        super().__init__(title='Mouse Properties');self.shell=shell;self.assets=shell.assets;self.dialog_assets=self.assets
        self.set_transient_for(shell);self.set_decorated(False);self.set_resizable(False);self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.frames={name:cairo.ImageSurface.create_from_png(str(self.assets/f'mouse-{name}-frame.png')) for name in ('buttons','pointers','motion','general')}
        self.controller=MouseController(Path.home()/'.config/win95lx/mouse.json',backend or X11Mouse(),self.apply_session)
        self.tab=0;self.role=0;self.scroll=0;self.hits=[];self.focus=0;self.focus_action=('hand',False);self.pressed=None;self.dragging=None;self.caption_active=True;self.caption_drag=None;self.test_open=False;self.last_test_click=None;self.animation_frame=None;self.animation_timer=None
        self.animation=[cairo.ImageSurface.create_from_png(str(self.assets/f'mouse-test-{index:02}.png')) for index in range(32)]
        self.scheme_choices=shell.pointer_library.names;self.scheme_scroll=0;self.scheme_drag=None
        if self.controller.pending.scheme not in self.scheme_choices:self.controller.pending=replace(self.controller.pending,scheme='(None)')
        self.combo=ComboBox(self.scheme_choices,self.scheme_choices.index(self.controller.pending.scheme));self.preview_cache={}
        self.area=Gtk.DrawingArea();self.area.set_size_request(404,448);self.add(self.area)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.SCROLL_MASK)
        self.area.connect('draw',self.draw);self.area.connect('button-press-event',self.press);self.area.connect('button-release-event',self.release);self.area.connect('motion-notify-event',self.motion);self.area.connect('scroll-event',self.wheel)
        self.connect('key-press-event',self.key);self.connect('destroy',self.cleanup)
        from win95lx.control_panel.display_preferences import install_palette_filter
        install_palette_filter(self,lambda:shell.display_preferences.palette)
        self.set_icon(GdkPixbuf.Pixbuf.new_from_file(str(self.assets/'mouse-icon.png')))
        self.connect('realize',lambda *_:self.get_window().set_cursor(shell.cursor_for('arrow')))
        self.connect('map-event',self.mapped)
        self.connect('focus-in-event',lambda *_:self.caption_focus(True))
        self.connect('focus-out-event',lambda *_:self.caption_focus(False))
        self.preview_signature=None;self.preview_epoch=GLib.get_monotonic_time()
        self.preview_timer=GLib.timeout_add(16,self.animate_previews)
    def mapped(self,*_):
        from win95lx.shell.window_bounds import fit_bounds
        screen=self.get_screen();x,y=self.get_position()
        x,y,_,_=fit_bounds((x,y,404,448),(screen.get_width(),screen.get_height()))
        self.move(x,y);self.get_window().focus(Gdk.CURRENT_TIME);return False
    def apply_session(self,prefs):self.shell.apply_mouse_preferences(prefs)
    def update(self,**kwargs):
        if 'scheme' in kwargs:self.preview_epoch=GLib.get_monotonic_time()
        self.controller.pending=replace(self.controller.pending,**kwargs);self.area.queue_draw()
    def hit(self,rect,action):self.hits.append((rect,action))
    def button(self,p,label,rect,action,enabled=True):
        if enabled:self.hit(rect,action)
        p.button(label,*rect,pressed=self.pressed==action)
        if not enabled:
            x,y,w,h=rect;p.fill(x+3,y+3,w-6,h-6,FACE);p.text(label,x+(w-p.font.width(label))//2+1,y+6,LIGHT);p.text(label,x+(w-p.font.width(label))//2,y+5,SHADOW)
    def sprite(self,p,frame,source,x,y):
        sx,sy,w,h=source;p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip();p.image(frame,x-sx,y-sy);p.cr.restore()
    def slider(self,p,frame,rect,value,default,thumb,maximum=10):
        x,y,w,h=rect
        if value!=default:
            p.fill(x,y,w,h,FACE)
            p.fill(x,y+8,w,1,SHADOW);p.fill(x,y+9,w,1,LIGHT)
            cx=x+round((w-11)*value/maximum)
            self.sprite(p,frame,thumb,cx,y)
    def pointer_image(self,role,background=LIGHT):
        prefs=self.controller.pending
        frame=self.shell.pointer_library.frame(prefs.scheme,role,(GLib.get_monotonic_time()-self.preview_epoch)/1000)
        path=Path(prefs.overrides[role]) if role in prefs.overrides else self.assets/frame['file']
        key=(path,background)
        if key not in self.preview_cache:
            try:pix=GdkPixbuf.Pixbuf.new_from_file(str(path))
            except GLib.Error:pix=GdkPixbuf.Pixbuf.new_from_file(str(replace(self.controller.pending,overrides={}).pointer(self.assets,role)))
            im=cairo.ImageSurface(cairo.FORMAT_ARGB32,pix.get_width(),pix.get_height());cr=cairo.Context(im);Gdk.cairo_set_source_pixbuf(cr,pix,0,0);cr.paint()
            if role not in prefs.overrides:
                color={FACE:SHADOW,NAVY:(255,255,0),LIGHT:BLACK,BLACK:LIGHT}.get(background,tuple(255-c for c in background))
                cr.set_source_rgb(*(c/255 for c in color))
                for x,y in frame.get('invert',[]):cr.rectangle(x,y,1,1)
                cr.fill()
            self.preview_cache[key]=im
        return self.preview_cache[key]
    def draw(self,_widget,cr):
        self.hits=[];p=Painter(cr,self.shell.font);prefs=self.controller.pending;frame=self.frames[('buttons','pointers','motion','general')[self.tab]];p.image(frame,0,0)
        if not self.caption_active:
            p.fill(3,3,398,17,SHADOW);p.text('Mouse Properties',5,4,LIGHT,bold=True)
            self.sprite(p,frame,(365,4,16,15),365,4);self.sprite(p,frame,(383,4,16,15),383,4)
        for index,(x,w) in enumerate(((10,49),(59,52),(111,43),(154,48))):self.hit((x,29,w,22),('tab',index))
        self.hit((383,4,16,15),('cancel',));self.hit((365,4,16,15),('help',));self.hit((3,3,359,20),('caption',))
        self.hit((158,415,75,23),('ok',));self.hit((239,415,75,23),('cancel',))
        if prefs!=self.controller.applied:self.button(p,'Apply',(320,415,75,23),('apply',))
        if self.tab==0:
            for left,xx in ((False,34),(True,134)):
                self.hit((xx,85,99,20),('hand',left))
                if prefs.left_handed:
                    self.sprite(p,frame,(34 if left else 134,88,13,13),xx,88)
            if prefs.left_handed:
                for xx,lines in ((32,('Left Button:',' · Context Menu',' · Special Drag')),(268,('Right Button:',' · Normal Select',' · Normal Drag'))):
                    p.fill(xx,120,112,44,FACE)
                    for row,line in enumerate(lines):p.text(line,xx,120+13*row)
            self.hit((72,285,137,25),('double',));self.slider(p,frame,(72,287,137,21),900-prefs.double_click_ms,400,(135,287,11,21),800)
            self.hit((269,286,79,84),('test',))
            if self.animation_frame is not None:p.image(self.animation[self.animation_frame],284,296)
        elif self.tab==1:
            p.fill(35,88,227,15,NAVY);p.text(prefs.scheme,37,89,LIGHT)
            self.hit((34,85,246,21),('scheme',))
            p.fill(301,70,77,75,FACE)
            image=self.pointer_image(ROLES[self.role][0],FACE);p.image(image,324,92)
            p.fill(26,157,336,204,LIGHT)
            for visible,(role,label) in enumerate(ROLES[self.scroll:self.scroll+6]):
                index=self.scroll+visible;y=157+visible*34;selected=index==self.role
                if selected:p.fill(26,y,336,34,NAVY)
                p.text(label,31,y+10,LIGHT if selected else BLACK)
                image=self.pointer_image(role,NAVY if selected else LIGHT);p.cr.save();p.cr.rectangle(321,y+1,39,32);p.cr.clip();p.image(image,325,y+1);p.cr.restore()
                self.hit((26,y,336,34),('role',index))
            from win95lx.shell.scrollbar import VerticalScrollbar
            bar=VerticalScrollbar(205,len(ROLES)-6,thumb=74)
            def artwork(painter,x,y,part):self.sprite(painter,frame,{'up':(362,157,16,16),'down':(362,346,16,16),'thumb':(362,173,16,74)}[part],x,y)
            bar.draw(p,362,157,self.scroll,artwork)
            thumb_top=157+bar.thumb_top(self.scroll)
            self.hit((362,173,16,max(0,thumb_top-173)),('scroll',-6))
            self.hit((362,thumb_top+74,16,max(0,346-thumb_top-74)),('scroll',6))
            self.hit((362,thumb_top,16,74),('pointer-thumb',))
            self.hit((362,157,16,16),('scroll',-1));self.hit((362,346,16,16),('scroll',1))
            self.button(p,'Browse...',(304,370,75,23),('browse',))
            self.button(p,'Use Default',(223,370,75,23),('default',),ROLES[self.role][0] in prefs.overrides)
            # Custom scheme management is not yet accepted; retain disabled controls.
            self.button(p,'Save As...',(124,114,75,23),('save-scheme',),False)
            self.button(p,'Delete',(205,114,75,23),('delete-scheme',),False)
            if self.combo.expanded:
                from win95lx.shell.scrollbar import VerticalScrollbar
                visible=ComboBox(self.scheme_choices[self.scheme_scroll:self.scheme_scroll+12],self.combo.value-self.scheme_scroll)
                visible.draw_list(p,34,85,230)
                VerticalScrollbar(158,max(0,len(self.scheme_choices)-12),thumb=47).draw(p,264,106,self.scheme_scroll)
        elif self.tab==2:
            self.hit((134,94,184,27),('speed',));self.slider(p,frame,(134,94,184,23),prefs.speed-1,4,(221,94,11,23),9)
            # X11 has no core pointer-trails equivalent; do not fake a global setting.
            p.fill(97,180,13,13,FACE);p.bevel(97,180,13,13,True);p.text('Show pointer trails',119,180,SHADOW)
        else:
            p.fill(26,134,269,19,FACE);p.text('System pointing device',28,135)
            self.button(p,'Change...',(304,132,75,23),('driver',),False)
        if self.focus_action!=('hand',False):
            if self.tab==0:
                for rect in ((50,88,69,1),(50,101,69,1),(50,88,1,14),(118,88,1,14)):p.fill(*rect,FACE)
            for (x,y,w,h),action in self.hits:
                if action==self.focus_action and action[0]!='caption':
                    for xx in range(x+3,x+w-3,2):p.fill(xx,y+3,1,1,BLACK);p.fill(xx,y+h-4,1,1,BLACK)
                    for yy in range(y+3,y+h-3,2):p.fill(x+3,yy,1,1,BLACK);p.fill(x+w-4,yy,1,1,BLACK)
        return False
    def action(self,action):
        kind=action[0]
        if kind=='tab':
            self.tab=action[1];self.combo.expanded=False;self.focus_action=(('hand',False),('scheme',),('speed',),('ok',))[self.tab]
        elif kind=='cancel':self.controller.cancel();self.destroy();return
        elif kind in ('apply','ok'):
            try:self.controller.apply()
            except (OSError,ValueError,RuntimeError,GLib.Error) as error:
                from win95lx.apps.dialogs import message_box
                message_box(self,'Mouse Properties',str(error),Gtk.MessageType.ERROR);return
            if kind=='ok':self.destroy();return
        elif kind=='hand':self.update(left_handed=action[1])
        elif kind=='scheme':self.open_schemes()
        elif kind=='role':self.role=action[1]
        elif kind=='scroll':self.scroll=max(0,min(len(ROLES)-6,self.scroll+action[1]))
        elif kind=='default':
            overrides=dict(self.controller.pending.overrides);overrides.pop(ROLES[self.role][0],None);self.update(overrides=overrides)
        elif kind=='browse':
            from win95lx.apps.dialogs import choose_file,message_box
            path=choose_file(self,Path.home()/'pointer.cur',(('Mouse pointers',('*.cur',)),))
            if path:
                try:
                    data=Path(path).read_bytes()
                    if data[:4]!=b'\x00\x00\x02\x00':raise ValueError('Select a Windows cursor (.cur) file.')
                    GdkPixbuf.Pixbuf.new_from_file(str(path))
                    overrides=dict(self.controller.pending.overrides);overrides[ROLES[self.role][0]]=str(Path(path).absolute());self.update(overrides=overrides)
                except (OSError,ValueError,GLib.Error) as error:message_box(self,'Mouse Properties',str(error),Gtk.MessageType.ERROR)
        elif kind=='help':
            from win95lx.apps.dialogs import message_box
            message_box(self,'Mouse Properties','Choose button configuration, double-click speed, pointer artwork, or pointer speed. Changes take effect when you choose Apply. Pointer trails, named scheme saving, and driver replacement are not available.',Gtk.MessageType.INFO)
        self.area.queue_draw()
    def slider_at(self,action,x):
        if action[0]=='double':self.update(double_click_ms=900-round(max(0,min(1,(x-72)/136))*800))
        elif action[0]=='speed':self.update(speed=1+round(max(0,min(1,(x-134)/183))*9))
    def press(self,_area,e):
        if e.button!=1:return False
        if self.combo.expanded:
            if 264<=e.x<280 and 106<=e.y<264:
                from win95lx.shell.scrollbar import VerticalScrollbar
                bar=VerticalScrollbar(158,len(self.scheme_choices)-12,thumb=47);top=106+bar.thumb_top(self.scheme_scroll)
                if e.y<122:self.scheme_scroll=max(0,self.scheme_scroll-1)
                elif e.y>=248:self.scheme_scroll=min(len(self.scheme_choices)-12,self.scheme_scroll+1)
                elif top<=e.y<top+47:self.scheme_drag=e.y-top
                else:self.scheme_scroll=max(0,min(len(self.scheme_choices)-12,self.scheme_scroll+(-12 if e.y<top else 12)))
                self.area.queue_draw();return True
            index=self.combo.row_at(e.x-34,e.y-85,230)
            self.combo.expanded=False
            if index is not None and index<12:
                self.combo.value=self.scheme_scroll+index;self.update(scheme=self.scheme_choices[self.combo.value],overrides={})
            self.area.queue_draw();return True
        for (x,y,w,h),action in reversed(self.hits):
            if x<=e.x<x+w and y<=e.y<y+h:
                if action[0]=='caption':
                    x,y=self.get_position();self.caption_drag=(e.x_root-x,e.y_root-y);return True
                self.focus_action=action;self.pressed=action
                if action[0]=='pointer-thumb':
                    from win95lx.shell.scrollbar import VerticalScrollbar
                    self.dragging=('pointer-thumb',e.y-157-VerticalScrollbar(205,len(ROLES)-6,thumb=74).thumb_top(self.scroll))
                if action[0] in ('double','speed'):self.dragging=action;self.slider_at(action,e.x)
                if action[0]=='test' and e.type==Gdk.EventType.BUTTON_PRESS:
                    now=getattr(e,'time',0)
                    if self.last_test_click is not None and 0<=now-self.last_test_click<=self.controller.pending.double_click_ms:self.animate();self.last_test_click=None
                    else:self.last_test_click=now
                self.area.queue_draw();return True
    def release(self,_area,e):
        if self.scheme_drag is not None:self.scheme_drag=None;return True
        self.caption_drag=None
        action=self.pressed;self.pressed=None;self.dragging=None
        if action and any(a==action and x<=e.x<x+w and y<=e.y<y+h for (x,y,w,h),a in self.hits):self.action(action)
        self.area.queue_draw();return True
    def motion(self,_area,e):
        if self.scheme_drag is not None:
            from win95lx.shell.scrollbar import VerticalScrollbar
            self.scheme_scroll=VerticalScrollbar(158,len(self.scheme_choices)-12,thumb=47).value_at(e.y-106-self.scheme_drag);self.area.queue_draw();return
        if self.caption_drag:
            from win95lx.shell.window_bounds import fit_bounds
            screen=self.get_screen();x,y,_,_=fit_bounds((int(e.x_root-self.caption_drag[0]),int(e.y_root-self.caption_drag[1]),404,448),(screen.get_width(),screen.get_height()))
            self.move(x,y);return
        if self.dragging:
            if self.dragging[0]=='pointer-thumb':
                from win95lx.shell.scrollbar import VerticalScrollbar
                self.scroll=VerticalScrollbar(205,len(ROLES)-6,thumb=74).value_at(e.y-157-self.dragging[1]);self.area.queue_draw()
            else:self.slider_at(self.dragging,e.x)
    def wheel(self,_area,e):
        if self.combo.expanded:
            self.scheme_scroll=max(0,min(len(self.scheme_choices)-12,self.scheme_scroll+(1 if e.direction==Gdk.ScrollDirection.DOWN else -1)));self.area.queue_draw();return
        if self.tab==1:self.action(('scroll',1 if e.direction==Gdk.ScrollDirection.DOWN else -1))
    def animate(self):
        if self.animation_timer:GLib.source_remove(self.animation_timer)
        self.animation_frame=0
        def tick():
            self.animation_frame+=1
            if self.animation_frame==len(self.animation):self.animation_frame=None;self.animation_timer=None;self.area.queue_draw();return False
            self.area.queue_draw();return True
        self.animation_timer=GLib.timeout_add(67,tick);self.area.queue_draw()
    def animate_previews(self):
        if self.tab==1 and self.shell.pointer_library.animated(self.controller.pending.scheme):
            roles=[role for role,label in ROLES[self.scroll:self.scroll+6]]+[ROLES[self.role][0]]
            signature=tuple(self.shell.pointer_library.frame(self.controller.pending.scheme,role,(GLib.get_monotonic_time()-self.preview_epoch)/1000)['file'] for role in roles)
            if signature!=self.preview_signature:self.preview_signature=signature;self.area.queue_draw()
        return True
    def cleanup(self,*_):
        if self.preview_timer:GLib.source_remove(self.preview_timer);self.preview_timer=None
        if self.animation_timer:GLib.source_remove(self.animation_timer);self.animation_timer=None
        self.controller.backend.close()
    def open_schemes(self):
        self.combo.open();self.scheme_scroll=max(0,min(self.combo.value,len(self.scheme_choices)-12));self.area.queue_draw()
    def caption_focus(self,active):
        self.caption_active=active;self.area.queue_draw();return False
    def key(self,_window,e):
        if e.state&Gdk.ModifierType.CONTROL_MASK and e.keyval==Gdk.KEY_Escape:
            self.shell.key(self.shell,e);return True
        if e.state&Gdk.ModifierType.MOD1_MASK and e.keyval==Gdk.KEY_F4:self.action(('cancel',));return True
        if e.keyval==Gdk.KEY_Escape:
            if self.combo.expanded:self.combo.expanded=False;self.combo.value=self.scheme_choices.index(self.controller.pending.scheme);self.area.queue_draw()
            else:self.action(('cancel',))
            return True
        if e.state&Gdk.ModifierType.CONTROL_MASK and e.keyval in (Gdk.KEY_Tab,Gdk.KEY_ISO_Left_Tab):
            self.action(('tab',(self.tab+(-1 if e.state&Gdk.ModifierType.SHIFT_MASK else 1))%4));return True
        if e.keyval in (Gdk.KEY_Tab,Gdk.KEY_ISO_Left_Tab):
            actions=[]
            for rect,action in self.hits:
                if action[0] not in ('caption','tab','help','scroll','pointer-thumb') and (action[0]!='role' or action[1]==self.role) and action not in actions:actions.append(action)
            index=actions.index(self.focus_action) if self.focus_action in actions else -1
            self.focus_action=actions[(index+(-1 if e.state&Gdk.ModifierType.SHIFT_MASK else 1))%len(actions)];self.area.queue_draw();return True
        if self.tab==1 and (e.keyval==Gdk.KEY_F4 or e.state&Gdk.ModifierType.MOD1_MASK and e.keyval==Gdk.KEY_Down):self.open_schemes();self.area.queue_draw();return True
        if self.tab==1 and self.focus_action[0]=='scheme' and e.keyval in (Gdk.KEY_Up,Gdk.KEY_Down):
            self.combo.step(-1 if e.keyval==Gdk.KEY_Up else 1)
            self.scheme_scroll=max(0,min(self.scheme_scroll,self.combo.value));self.scheme_scroll=max(self.scheme_scroll,self.combo.value-11)
            if not self.combo.expanded:self.update(scheme=self.scheme_choices[self.combo.value],overrides={})
            self.area.queue_draw();return True
        if self.tab==1 and self.focus_action[0]=='role' and e.keyval in (Gdk.KEY_Up,Gdk.KEY_Down):
            self.role=max(0,min(len(ROLES)-1,self.role+(-1 if e.keyval==Gdk.KEY_Up else 1)));self.focus_action=('role',self.role)
            self.scroll=max(0,min(self.scroll,self.role));self.scroll=max(self.scroll,self.role-5);self.area.queue_draw();return True
        if e.keyval in (Gdk.KEY_Left,Gdk.KEY_Right):
            delta=-1 if e.keyval==Gdk.KEY_Left else 1
            if self.focus_action[0]=='hand':self.focus_action=('hand',not self.controller.pending.left_handed);self.action(self.focus_action)
            elif self.focus_action[0]=='double':self.update(double_click_ms=max(100,min(900,self.controller.pending.double_click_ms-100*delta)))
            elif self.focus_action[0]=='speed':self.update(speed=max(1,min(10,self.controller.pending.speed+delta)))
            return True
        if e.keyval==Gdk.KEY_space:
            if self.focus_action[0]=='test':self.animate()
            else:self.action(self.focus_action)
            return True
        if e.keyval in (Gdk.KEY_Return,Gdk.KEY_KP_Enter):
            if self.combo.expanded:self.combo.expanded=False;self.update(scheme=self.scheme_choices[self.combo.value],overrides={})
            else:self.action(('ok',))
            return True
        return False
