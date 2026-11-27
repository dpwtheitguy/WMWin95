"""Native Sounds Properties with editable event schemes and real WAV previews."""
from pathlib import Path
import json
from gi.repository import Gtk,Gdk,GLib
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.preferences import PreferenceController
from win95lx.control_panel.sound_preferences import SoundPreferences,SoundBackend,EVENTS,BUILTINS,sound_path,wave_details
from win95lx.sound import SoundPlayer
from win95lx.shell.widgets import FACE,BLACK,LIGHT,NAVY
from win95lx.shell.scrollbar import VerticalScrollbar

class SoundsWindow(PropertySheet):
    title='Sounds Properties';asset_prefix='sounds';size=(366,448)
    tabs=('sounds',);tab_rects=((9,29,51,22),)
    buttons=((121,415,75,23),(202,415,75,23),(283,415,75,23))
    def __init__(self,shell,player=None):
        super().__init__(shell)
        self.controller=PreferenceController(Path.home()/'.config/win95lx/sounds.json',SoundBackend(self.assets),SoundPreferences)
        library=json.loads((self.assets/'sound-library.json').read_text())
        self.factory={**BUILTINS,**library['schemes']}
        self.sound_labels={row['file']:row['original_name'] for row in library['sources']}
        self.sound_choices=tuple((row['profile']+' / '+row['original_name'],row['file']) for row in library['sources'])
        self.player=player or SoundPlayer();self.selection=0;self.scroll=0;self.tree_dirty=False
        self.focus_action=None;self.was_playing=False;self.scroll_drag=None
        self.area.connect('scroll-event',self.wheel)
        self.timer=GLib.timeout_add(100,self.poll_player);self.connect('destroy',self.cleanup)
    def cleanup(self,*_):
        self.player.stop()
        if self.timer:GLib.source_remove(self.timer);self.timer=None
    def poll_player(self):
        playing=self.player.playing
        if playing!=self.was_playing:self.was_playing=playing;self.area.queue_draw()
        return True
    @property
    def event(self):return EVENTS[self.selection][1]
    def value(self):return self.controller.pending.events.get(self.event,'')
    def choose_event(self,index):
        self.selection=max(0,min(len(EVENTS)-1,index));self.scroll=max(0,min(self.scroll,self.selection));self.scroll=min(len(EVENTS)-7,max(self.scroll,self.selection-6));self.tree_dirty=True;self.player.stop();self.area.queue_draw()
    def draw_content(self,p):
        if self.tree_dirty:
            p.fill(26,80,298,118,LIGHT)
            for row,(label,key) in enumerate(EVENTS[self.scroll:self.scroll+7]):
                y=80+row*16;index=self.scroll+row;x=66 if key else 46
                if key is None:self.sprite(p,(26,80,16,16),26,y)
                if index==self.selection:p.fill(x,y,p.font.width(label),16,NAVY)
                p.text(label,x,y+2,LIGHT if index==self.selection else BLACK)
            # Native arrow and thumb sprites; preserve the actual white tree
            # background instead of assuming every scrollbar track is gray.
            bar=VerticalScrollbar(120,len(EVENTS)-7,16,16)
            bar.draw(p,324,80,self.scroll,lambda painter,x,y,part:self.sprite(painter,{'up':(324,80,16,16),'down':(324,184,16,16),'thumb':(324,96,16,16)}[part],x,y),track="window")
        for row in range(min(7,len(EVENTS)-self.scroll)):self.hit((26,80+row*16,298,16),('event',self.scroll+row))
        self.hit((324,80,16,120),('scroll',))
        enabled=self.event is not None
        if enabled:
            p.fill(33,227,180,14,FACE);p.text('Name:',33,228)
            p.bevel(33,244,177,20,True);p.fill(35,246,159,16,LIGHT)
            value=self.value();label=self.sound_labels.get(value,Path(value).name) if value else '(None)'
            p.cr.save();p.cr.rectangle(36,246,157,15);p.cr.clip();p.text(label,36,247);p.cr.restore()
            self.sprite(p,(194,246,14,16),194,246);self.hit((33,244,177,20),('name',))
        self.button(p,'&Browse...',(33,272,86,23),('browse',),enabled,'Select a sound event before choosing a WAV file.')
        value=self.value()
        self.button(p,'&Details...',(124,272,87,23),('details',),bool(enabled and value),'Select an event with an assigned WAV file to view its details.')
        # Keep the original small square playback buttons and their glyphs.
        if enabled and value:
            self.sprite(p,(286,244,22,21),286,244);self.hit((286,244,22,21),('play',),command=True)
            for row,width in enumerate((1,2,3,4,5,4,3,2,1)):p.fill(295,249+row,width,1,BLACK)
        if self.player.playing:
            self.hit((309,244,22,21),('stop',),command=True);p.fill(316,251,7,7,BLACK)
        # Measured native CBS_DROPDOWNLIST HWND: (33,332,300,21).
        # Clear only its client field; never erase the GroupBox padding/bevel.
        p.fill(35,334,280,17,LIGHT)
        p.cr.save();p.cr.rectangle(35,334,280,17);p.cr.clip()
        p.text(self.controller.pending.scheme,37,336);p.cr.restore()
        self.hit((33,332,300,21),('scheme',))
        self.button(p,'&Save As...',(177,358,75,23),('save-scheme',))
        custom=self.controller.pending.scheme in self.controller.pending.schemes
        self.button(p,'D&elete',(258,358,75,23),('delete-scheme',),custom,'Only named custom sound schemes can be deleted.')
    def popup(self,rect,choices,value,callback):
        from win95lx.apps.choice_dialog import ChoicePopup
        self.popup_window=ChoicePopup(self,rect,choices,value,callback)
    def action(self,action):
        kind=action[0]
        if kind=='event':self.focus_action=('events',);self.choose_event(action[1])
        elif kind=='scheme':
            names=tuple(self.factory)+tuple(self.controller.pending.schemes);current=self.controller.pending.scheme
            self.popup((33,332,300,21),names,names.index(current) if current in names else 0,self.select_scheme)
        elif kind=='name' and self.event:
            choices=(('(None)',''),)+self.sound_choices
            if self.value() and self.value() not in [value for label,value in choices]:choices+=((Path(self.value()).name,self.value()),)
            values=tuple(value for label,value in choices)
            self.popup((33,244,177,20),tuple(label for label,value in choices),values.index(self.value()),lambda i:self.assign(values[i]))
        elif kind=='browse' and self.event:
            from win95lx.apps.dialogs import choose_file
            current=sound_path(self.value(),self.assets) if self.value() else None
            path=choose_file(self,current,(('Sounds (*.wav)',('*.wav','*.WAV')),('All Files (*.*)',('*',))))
            if path:
                try:wave_details(path);self.assign(str(path.resolve()))
                except (OSError,ValueError) as error:self.error(error)
        elif kind=='details' and self.value():
            from win95lx.apps.dialogs import message_box
            try:
                info=wave_details(sound_path(self.value(),self.assets))
                message_box(self,'Sound Details',f"{self.sound_labels.get(self.value(),Path(self.value()).name)}\n\n{info['sample_rate']:,} Hz, {info['bits']} bit, {info['channels']} channel(s)\nLength: {info['duration']:.2f} seconds",Gtk.MessageType.INFO)
            except (OSError,ValueError) as error:self.error(error)
        elif kind=='play' and self.value():
            try:self.player.play(sound_path(self.value(),self.assets))
            except (OSError,ValueError,RuntimeError) as error:self.error(error)
        elif kind=='stop':self.player.stop()
        elif kind=='save-scheme':
            from win95lx.apps.dialogs import name_dialog
            name=name_dialog(self,'Save Scheme As',self.controller.pending.scheme)
            if name is not None:
                try:
                    if name.strip() in self.factory:raise ValueError('Choose a different name for your custom sound scheme.')
                    if name.strip() in self.controller.pending.schemes:
                        from win95lx.apps.dialogs import message_box,YES_NO
                        if message_box(self,'Save Scheme As','Replace the existing sound scheme?',Gtk.MessageType.QUESTION,YES_NO,Gtk.ResponseType.NO)!=Gtk.ResponseType.YES:return
                    self.controller.pending=self.controller.pending.save_scheme(name)
                except ValueError as error:self.error(error)
        elif kind=='delete-scheme':
            from win95lx.apps.dialogs import message_box,YES_NO
            name=self.controller.pending.scheme
            if name in self.controller.pending.schemes and message_box(self,'Delete Scheme',f'Delete the sound scheme "{name}"?',Gtk.MessageType.QUESTION,YES_NO,Gtk.ResponseType.NO)==Gtk.ResponseType.YES:
                self.controller.pending=self.controller.pending.delete_scheme(name)
        elif kind=='scroll':return
        else:return super().action(action)
        self.area.queue_draw()
    def select_scheme(self,index):
        names=tuple(self.factory)+tuple(self.controller.pending.schemes)
        self.controller.pending=self.controller.pending.select(names[index],self.factory);self.player.stop();self.area.queue_draw()
    def assign(self,value):
        self.controller.pending=self.controller.pending.assign(self.event,value);self.player.stop();self.area.queue_draw()
    def wheel(self,_area,event):
        if not (24<=event.x<340 and 78<=event.y<200):return False
        self.scroll=max(0,min(len(EVENTS)-7,self.scroll+(1 if event.direction==Gdk.ScrollDirection.DOWN else -1)));self.tree_dirty=True;self.area.queue_draw();return True
    def press(self,area,event):
        if event.button==1 and 324<=event.x<340 and 80<=event.y<200:
            bar=VerticalScrollbar(120,len(EVENTS)-7,16,16);y=event.y-80;top=bar.thumb_top(self.scroll)
            if top<=y<top+16:self.scroll_drag=y-top
            else:self.scroll=max(0,min(len(EVENTS)-7,self.scroll+(-1 if y<16 else 1 if y>=104 else -7 if y<top else 7)))
            self.tree_dirty=True;self.area.queue_draw();return True
        return super().press(area,event)
    def motion(self,area,event):
        if self.scroll_drag is not None:
            self.scroll=VerticalScrollbar(120,len(EVENTS)-7,16,16).value_at(event.y-80-self.scroll_drag);self.tree_dirty=True;self.area.queue_draw();return True
        return super().motion(area,event)
    def release(self,area,event):self.scroll_drag=None;return super().release(area,event)
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval);alt=bool(event.state&Gdk.ModifierType.MOD1_MASK)
        if self.focus_action==('events',) and name in ('Up','Down','Home','End','Page_Up','Page_Down'):
            self.choose_event(0 if name=='Home' else len(EVENTS)-1 if name=='End' else self.selection+{'Up':-1,'Down':1,'Page_Up':-7,'Page_Down':7}[name]);return True
        if self.focus_action in (('name',),('scheme',)) and (name=='F4' or alt and name=='Down'):
            self.action(self.focus_action);return True
        return super().key(window,event)
    def focus_order(self):
        order=[('events',)]
        if self.event:order+=[('name',),('browse',)]
        if self.value():order+=[('details',),('play',)]
        if self.player.playing:order+=[('stop',)]
        order+=[('scheme',),('save-scheme',)]
        if self.controller.pending.scheme in self.controller.pending.schemes:order+=[('delete-scheme',)]
        order+=[('ok',),('cancel',)]
        if self.controller.pending!=self.controller.applied:order+=[('apply',)]
        return order
