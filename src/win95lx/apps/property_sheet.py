"""Shared native-pixel property sheet, pending edits and accessible controls."""
from pathlib import Path
import cairo
import subprocess
from gi.repository import Gtk,Gdk,GLib,GdkPixbuf
from win95lx.shell.widgets import Painter,FACE,BLACK,LIGHT,NAVY,SHADOW
from win95lx.shell.command_button import draw_command_button,parse_label,resolve_default

class PropertySheet(Gtk.Window):
    size=(404,448)
    title='Properties'
    tabs=()
    tab_rects=()
    asset_prefix=''
    buttons=((158,415,75,23),(239,415,75,23),(320,415,75,23))

    def __init__(self,shell):
        super().__init__(title=self.title)
        self.shell=shell;self.assets=self.dialog_assets=shell.assets
        self.set_transient_for(shell);self.set_decorated(False);self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)
        self.frames=[cairo.ImageSurface.create_from_png(str(self.assets/f'{self.asset_prefix}-{tab}-frame.png')) for tab in self.tabs]
        icon=self.assets/f'cpl-{self.asset_prefix}-32.png'
        if icon.exists():self.set_icon(GdkPixbuf.Pixbuf.new_from_file(str(icon)))
        self.tab=0;self.hits=[];self.disabled=[];self.button_specs=[];self.command_mnemonics={};self.command_actions={('ok',),('cancel',)};self.focus_action=None;self.pressed=None;self.press_inside=True;self.dragging=None;self.caption_drag=None;self.caption_active=True
        self.area=Gtk.DrawingArea();self.area.set_size_request(*self.size);self.add(self.area)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK|Gdk.EventMask.SCROLL_MASK)
        for signal,handler in (('draw',self.draw),('button-press-event',self.press),('button-release-event',self.release),('motion-notify-event',self.motion)):
            self.area.connect(signal,handler)
        self.connect('key-press-event',self.key)
        self.connect('focus-in-event',lambda *_:self.caption_focus(True));self.connect('focus-out-event',lambda *_:self.caption_focus(False))
        self.connect('realize',lambda *_:self.get_window().set_cursor(shell.cursor_for('arrow')))
        self.connect('map-event',self.mapped)
        from win95lx.control_panel.display_preferences import install_palette_filter
        install_palette_filter(self,lambda:shell.display_preferences.palette)

    def mapped(self,*_):
        from win95lx.shell.window_bounds import fit_bounds
        screen=self.get_screen();x,y=self.get_position();w,h=self.size
        x,y,w,h=fit_bounds((x,y,w,h),(screen.get_width(),screen.get_height()))
        self.move(x,y)
        self.get_window().focus(Gdk.CURRENT_TIME);return False
    def caption_focus(self,active):self.caption_active=active;self.area.queue_draw();return False
    def hit(self,rect,action,*,command=False):
        self.hits.append((rect,action))
        if command:self.command_actions.add(action)
    @staticmethod
    def contains(rect,x,y):a,b,w,h=rect;return a<=x<a+w and b<=y<b+h
    def sprite(self,p,rect,x,y):
        sx,sy,w,h=rect;p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip();p.image(self.frames[self.tab],x-sx,y-sy);p.cr.restore()

    def button(self,p,label,rect,action,enabled=True,reason=None):
        # Defer painting until every command is registered: native sheets have
        # one default button, and moving focus transfers its black border.
        self.button_specs.append((label,rect,action,bool(enabled)))
        if enabled:self.hit(rect,action,command=True)
        elif reason:self.disabled.append((rect,reason))

    def draw(self,_area,cr):
        self.hits=[];self.disabled=[];self.button_specs=[];self.command_mnemonics={};self.command_actions=set();p=Painter(cr,self.shell.font);p.image(self.frames[self.tab],0,0)
        w,h=self.size
        if not self.caption_active:
            p.fill(3,3,w-6,17,SHADOW);p.text(self.title,5,4,LIGHT,bold=True)
            self.sprite(p,(w-39,4,16,15),w-39,4);self.sprite(p,(w-21,4,16,15),w-21,4)
        self.hit((3,3,w-45,20),('caption',));self.hit((w-21,4,16,15),('cancel',));self.hit((w-39,4,16,15),('help',))
        for index,rect in enumerate(self.tab_rects):self.hit(rect,('tab',index))
        self.draw_content(p)
        changed=not hasattr(self,'controller') or self.controller.pending!=self.controller.applied or getattr(self.controller,'edited',None) is not None
        for rect,label,name in zip(self.buttons,('OK','Cancel','&Apply'),('ok','cancel','apply')):
            self.button(p,label,rect,(name,),name!='apply' or changed)
        enabled={action:active for _,_,action,active in self.button_specs}
        default=resolve_default(('ok',),self.focus_action,enabled)
        for label,rect,action,active in self.button_specs:
            draw_command_button(p,label,rect,enabled=active,default=action==default,
                                focused=bool(self.caption_active and action==self.focus_action),
                                pressed=action==self.pressed and self.press_inside)
            text,index=parse_label(label)
            if active and index is not None:self.command_mnemonics[text[index].casefold()]=action
        return False

    def draw_content(self,p):pass
    def error(self,error):
        from win95lx.apps.dialogs import message_box
        text=str(error)
        if isinstance(error,subprocess.CalledProcessError):
            detail=(error.stderr or '').casefold()
            text='These settings could not be applied. The previous settings have been kept.'
            if 'authentication' in detail or 'permission' in detail or 'access denied' in detail:text='Access to the requested setting was denied. The previous settings have been kept.'
        message_box(self,self.title,text,Gtk.MessageType.ERROR)
    def help(self):
        from win95lx.apps.dialogs import message_box
        reasons=list(dict.fromkeys(reason for rect,reason in self.disabled))
        message_box(self,self.title,'Changes take effect when you choose Apply. Cancel discards changes that have not been applied.'+('\n\n'+'\n\n'.join(reasons) if reasons else ''),Gtk.MessageType.INFO)
    def action(self,action):
        kind=action[0]
        if kind=='tab':self.tab=action[1];self.tab_changed()
        elif kind=='cancel':
            if hasattr(self,'controller'):self.controller.cancel()
            self.destroy();return
        elif kind in ('ok','apply'):
            try:
                if hasattr(self,'controller'):self.controller.apply()
            except (OSError,ValueError,RuntimeError,GLib.Error,subprocess.SubprocessError) as error:self.error(error);return
            if kind=='ok':self.destroy();return
        elif kind=='help':self.help()
        self.area.queue_draw()

    def press(self,_area,event):
        if event.button!=1:return False
        for rect,action in reversed(self.hits):
            if self.contains(rect,event.x,event.y):
                if action[0]=='caption':self.caption_drag=(event.x,event.y);return True
                self.focus_action=self.pressed=action;self.press_inside=True
                if action[0]=='slider':self.dragging=action;self.slider_at(action,event.x)
                if action[0]=='entry':self.entry_click(action,event)
                self.area.queue_draw();return True
        return False
    def entry_click(self,action,event):pass
    def release(self,_area,event):
        action=self.pressed;self.pressed=None;self.dragging=None;self.caption_drag=None
        if action and any(a==action and self.contains(rect,event.x,event.y) for rect,a in self.hits):self.action(action)
        self.area.queue_draw();return True
    def motion(self,_area,event):
        if self.pressed in self.command_actions:
            inside=any(action==self.pressed and self.contains(rect,event.x,event.y) for rect,action in self.hits)
            if inside!=self.press_inside:self.press_inside=inside;self.area.queue_draw()
        self.area.set_tooltip_text(next((reason for rect,reason in self.disabled if self.contains(rect,event.x,event.y)),None))
        if self.caption_drag:
            screen=self.get_screen();w,h=self.size
            self.move(max(0,min(int(event.x_root-self.caption_drag[0]),max(0,screen.get_width()-w))),max(0,min(int(event.y_root-self.caption_drag[1]),max(0,screen.get_height()-h-28))));return True
        if self.dragging:self.slider_at(self.dragging,event.x)
        return False
    def slider_at(self,action,x):pass
    def tab_changed(self):self.focus_action=None
    def focus_order(self):
        return list(dict.fromkeys(action for _,action in self.hits if action[0] not in ('caption','help','tab','choices','year-step','time-step','scroll')))
    def focus_changed(self):pass
    def key(self,_window,event):
        name=Gdk.keyval_name(event.keyval);ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK);shift=bool(event.state&Gdk.ModifierType.SHIFT_MASK);alt=bool(event.state&Gdk.ModifierType.MOD1_MASK)
        if ctrl and name=='Escape':
            # Start must not discard the user's pending property-sheet edits.
            self.shell.key(self.shell,event);return True
        if alt and name and name.casefold() in self.command_mnemonics:
            action=self.command_mnemonics[name.casefold()];self.focus_action=action;self.action(action);return True
        if name=='Escape' or alt and name=='F4':self.action(('cancel',));return True
        if name=='F1':self.help();return True
        if ctrl and name in ('Tab','ISO_Left_Tab'):self.action(('tab',(self.tab+(-1 if shift else 1))%len(self.tabs)));return True
        if name in ('Tab','ISO_Left_Tab'):
            order=self.focus_order()
            if order:
                index=order.index(self.focus_action) if self.focus_action in order else (-1 if not shift else 0)
                self.focus_action=order[(index+(-1 if shift else 1))%len(order)];self.area.queue_draw()
                self.focus_changed()
            return True
        if name in ('Return','KP_Enter'):self.action(self.focus_action if self.focus_action and self.focus_action in self.command_actions else ('ok',));return True
        if name=='space' and self.focus_action:self.action(self.focus_action);return True
        return False
