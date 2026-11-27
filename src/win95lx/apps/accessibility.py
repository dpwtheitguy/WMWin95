"""Measured Accessibility Properties with real session keyboard accessibility."""
from dataclasses import replace
from pathlib import Path
import json,cairo
from gi.repository import Gtk,Gdk
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.access_preferences import AccessPreferences,AccessController,XKBAccess
from win95lx.shell.widgets import FACE,BLACK,LIGHT,SHADOW,NAVY
from win95lx.shell.command_button import parse_label
from win95lx.shell.icon_labels import wrap_label

SHORTCUT='Independent Windows feature shortcuts are unfinished. XKB currently groups StickyKeys and SlowKeys shortcuts; this control cannot independently configure just this feature.'
FEEDBACK='Audible accessibility feedback routing has not been validated. No working sound output is claimed for this option yet.'
STATUS='Accessibility status indicators have not been integrated into the taskbar.'
PREVIEW='Testing pending FilterKeys settings inside this edit box is unfinished. Apply enables the actual keyboard filtering.'
REPEAT_REASON='RepeatKeys override controls are unfinished. Ordinary keyboard repeat remains managed by Keyboard Properties.'

class AccessControls:
    def load_native(self,key):
        self.layouts=json.loads((self.assets/'accessibility-native-layout.json').read_text());self.layout_key=key;self.timings=json.loads((self.assets/'accessibility-native-timings.json').read_text())
        self.check_images={state:cairo.ImageSurface.create_from_png(str(self.assets/f'accessibility-check-{state}.png')) for state in ('checked','unchecked')}
        self.radio_images={state:cairo.ImageSurface.create_from_png(str(self.assets/f'accessibility-radio-{state}.png')) for state in ('checked','unchecked')}
    def remember(self,child):
        self.children.append(child);child.connect('destroy',lambda obj:self.children.remove(obj) if obj in self.children else None);child.show_all();return child
    def control(self,ident):return next(c for c in self.layouts[self.layout_key]['controls'] if c['id']==ident and c['visible'])
    def check(self,p,ident,field,value,enabled=True,reason=None):
        c=self.control(ident);x,y,w,h=c['rect'];label,mnemonic=parse_label(c['text']);p.fill(x,y,w,h,FACE)
        p.image(self.check_images['checked' if value else 'unchecked'],x,y+1)
        if not enabled:
            # Native disabled colors remain a separate pixel acceptance target.
            p.fill(x+2,y+4,9,9,FACE)
            if value:
                for dx,dy in ((3,7),(4,8),(5,9),(6,8),(7,7),(8,6),(9,5)):p.fill(x+dx,y+dy,1,2,SHADOW)
            p.menu_text(label,x+19,y+2,LIGHT,mnemonic);p.menu_text(label,x+18,y+1,SHADOW,mnemonic)
            self.disabled.append(((x,y,w,h),reason or 'This integration is unfinished.'));return
        p.menu_text(label,x+18,y+1,BLACK,mnemonic)
        action=('check',field);self.hit((x,y,w,h),action)
        if mnemonic is not None:self.command_mnemonics[label[mnemonic].casefold()]=action
        if self.focus_action==action:
            width=p.font.width(label)
            p.fill(x+17,y,width+2,1,BLACK);p.fill(x+17,y+15,width+2,1,BLACK);p.fill(x+17,y,1,16,BLACK);p.fill(x+18+width,y,1,16,BLACK)
    def native_button(self,p,ident,action,enabled=True,reason=None):
        c=self.control(ident);self.button(p,c['text'],tuple(c['rect']),action,enabled,reason)
    def unavailable_edit(self,p,ident,reason):
        x,y,w,h=self.control(ident)['rect'];p.fill(x+2,y+2,w-4,h-4,FACE);self.disabled.append(((x,y,w,h),reason))
    def disabled_slider(self,p,ident,reason):
        c=self.control(ident);x,y,w,h=c['rect'];p.fill(x,y,w,h,FACE);p.fill(x+8,y+10,w-17,1,SHADOW);p.fill(x+8,y+11,w-17,1,LIGHT)
        maximum=max(1,c['range_max']-c['range_min']);left=x+8+round((w-27)*(c['position']-c['range_min'])/maximum)
        p.fill(left,y+2,11,21,SHADOW);p.fill(left+1,y+3,9,19,FACE);self.disabled.append(((x,y,w,h),reason))
    def radio(self,p,ident,action,checked,enabled=True,reason=None):
        c=self.control(ident);x,y,w,h=c['rect'];label,mnemonic=parse_label(c['text']);p.fill(x,y,w,h,FACE)
        if enabled:p.image(self.radio_images['checked' if checked else 'unchecked'],x,y+1)
        else:
            p.cr.set_source_rgb(.5,.5,.5);p.cr.arc(x+6,y+7,5,0,6.283);p.cr.stroke();p.cr.set_source_rgb(1,1,1);p.cr.arc(x+6,y+7,4,0,6.283);p.cr.fill()
            if checked:p.cr.set_source_rgb(.5,.5,.5);p.cr.arc(x+6,y+7,2,0,6.283);p.cr.fill()
        lines=wrap_label(label,p.font,w-18,max(1,h//13)) if h>25 else [label];offset=0
        for n,line in enumerate(lines):
            index=mnemonic-offset if mnemonic is not None and offset<=mnemonic<offset+len(line) else None
            p.menu_text(line,x+18,y+1+n*13,BLACK if enabled else SHADOW,index)
            offset+=len(line)+1
        if enabled:self.hit((x,y,w,h),action)
        else:self.disabled.append(((x,y,w,h),reason))

class AccessibilityWindow(AccessControls,PropertySheet):
    title='Accessibility Properties';asset_prefix='accessibility';size=(367,443)
    tabs=('keyboard','sound','display','mouse','general')
    tab_rects=((10,29,59,22),(69,29,42,22),(111,29,46,22),(157,29,44,22),(201,29,48,22))
    buttons=((121,410,75,23),(202,410,75,23),(283,410,75,23))
    def __init__(self,shell,backend=None,path=None):
        super().__init__(shell);self.load_native('access-0');self.controller=AccessController(path or Path.home()/'.config/win95lx/accessibility.json',backend or XKBAccess());self.filter_mode='slow' if self.controller.pending.slow else 'bounce';self.children=[];self.popup_window=None;self.focus_action=('check','sticky')
        self.connect('destroy',lambda *_:[w.destroy() for w in tuple(self.children)])
    def draw_content(self,p):
        self.layout_key=f'access-{self.tab}';prefs=self.controller.pending
        if self.tab==0:
            self.check(p,1031,'sticky',prefs.sticky);self.native_button(p,1032,('settings','sticky'))
            self.check(p,1055,'filter',prefs.slow or prefs.bounce);self.native_button(p,1050,('settings','filter'))
            self.check(p,1042,'toggle_feedback',prefs.toggle_feedback,False,FEEDBACK);self.native_button(p,1033,('settings','toggle'),False,'ToggleKeys shortcut and audible feedback integration is unfinished.')
            self.check(p,1000,'extra_help',False,False,'Extra keyboard-help hints have not been integrated into the shared applications.')
        elif self.tab==1:
            self.check(p,1077,'sound_sentry',False,False,'SoundSentry visual warnings are unfinished; the central sound event bus is not connected to visual warnings.')
            self.native_button(p,1078,('sound-settings',),False,'SoundSentry visual warning settings are unfinished.')
            self.check(p,1079,'show_sounds',False,False,'ShowSounds caption notification support is unfinished; supported applications must opt into that notification.')
        elif self.tab==2:
            self.check(p,1034,'contrast',False,False,'High Contrast requires shared custom-control palette and theme integration, which is unfinished.')
            self.native_button(p,1035,('contrast-settings',),False,'High Contrast palette/theme integration is unfinished.')
        elif self.tab==3:
            self.check(p,1081,'mouse',prefs.mouse);self.native_button(p,1003,('settings','amouse'),False,'MouseKeys option mapping and status/shortcut integration is unfinished; enabling MouseKeys itself works.')
        else:
            self.check(p,1037,'automatic_reset',prefs.automatic_reset)
            x,y,w,h=self.control(1038)['rect'];p.fill(x+2,y+2,w-20,h-4,NAVY if prefs.automatic_reset and self.focus_action==('minutes',) else LIGHT if prefs.automatic_reset else FACE);p.text(str(prefs.reset_seconds//60),x+3,y+3,LIGHT if prefs.automatic_reset and self.focus_action==('minutes',) else BLACK if prefs.automatic_reset else SHADOW)
            if prefs.automatic_reset:self.hit((x,y,w,h),('minutes',))
            self.check(p,1039,'warning',False,False,'The native feature-on warning dialog is not integrated with keyboard shortcuts.')
            self.check(p,1040,'feature_feedback',prefs.feature_feedback,False,FEEDBACK)
            self.check(p,1010,'serial',False,False,'SerialKeys device selection and serial-to-input service integration are unfinished. Hardware availability has not been assumed.')
            self.native_button(p,1041,('serial-settings',),False,'SerialKeys device/service integration is unfinished.')
    def tab_changed(self):
        self.layout_key=f'access-{self.tab}';self.focus_action=None
    def update(self,**values):self.controller.pending=replace(self.controller.pending,**values).validate();self.area.queue_draw()
    def action(self,action):
        kind=action[0]
        if kind=='check':
            field=action[1]
            if field=='filter':
                on=not(self.controller.pending.slow or self.controller.pending.bounce);self.update(slow=on and self.filter_mode=='slow',bounce=on and self.filter_mode=='bounce')
            else:self.update(**{field:not getattr(self.controller.pending,field)})
        elif kind=='settings':
            self.remember(AccessSettings(self,action[1]))
        elif kind=='minutes':
            from win95lx.apps.choice_dialog import ChoicePopup
            values=(5,10,15,20,25,30);current=min(range(len(values)),key=lambda i:abs(values[i]*60-self.controller.pending.reset_seconds));self.popup_window=ChoicePopup(self,tuple(self.control(1038)['rect']),tuple(map(str,values)),current,lambda i:self.update(reset_seconds=values[i]*60))
        else:return super().action(action)
        self.area.queue_draw()

class AccessSettings(AccessControls,PropertySheet):
    tabs=('settings',);tab_rects=()
    def __init__(self,parent,kind):
        self.parent=parent;self.kind=kind;data=parent.layouts[kind+'-0'];self.title=data['title'];self.asset_prefix='accessibility-'+kind;self.size=tuple(data['size']);self.buttons=tuple(tuple(next(c['rect'] for c in data['controls'] if c['id']==i and c['visible'])) for i in (1,2))
        super().__init__(parent.shell);self.set_transient_for(parent);self.set_modal(True);self.load_native(kind+'-0');self.pending=parent.pending if isinstance(parent,AccessSettings) else parent.controller.pending;self.filter_mode=parent.filter_mode;self.focus_action=None;self.children=[]
        self.connect('destroy',lambda *_:[w.destroy() for w in tuple(self.children)])
    def draw_content(self,p):
        v=self.pending;k=self.kind
        if k=='sticky':
            self.check(p,1043,'keyboard_shortcuts',v.keyboard_shortcuts,False,SHORTCUT)
            self.check(p,1044,'sticky_lock',v.sticky_lock);self.check(p,1045,'two_keys_disable',v.two_keys_disable)
            self.check(p,1007,'sticky_feedback',v.sticky_feedback,False,FEEDBACK);self.check(p,1011,'status',False,False,STATUS)
        elif k=='toggle':self.check(p,1076,'keyboard_shortcuts',False,False,'The five-second Num Lock shortcut has not been integrated.')
        elif k=='filter':
            self.check(p,1046,'keyboard_shortcuts',v.keyboard_shortcuts,False,SHORTCUT)
            self.radio(p,1047,('mode','bounce'),self.filter_mode=='bounce');self.radio(p,1048,('mode','slow'),self.filter_mode=='slow')
            self.native_button(p,1059,('advanced','abounce'),self.filter_mode=='bounce','Select Ignore repeated keystrokes to edit the bounce delay.')
            self.native_button(p,1066,('advanced','aslow'),self.filter_mode=='slow','Select Ignore quick keystrokes to edit the hold delay.')
            self.unavailable_edit(p,1049,PREVIEW);self.check(p,1069,'feedback',False,False,FEEDBACK);self.check(p,1070,'status',False,False,STATUS)
        elif k=='amouse':
            self.check(p,1001,'keyboard_shortcuts',False,False,'The MouseKeys Left Alt+Left Shift+Num Lock shortcut has not been integrated.')
            self.check(p,1002,'mouse_modifiers',False,False,'Ctrl/Shift speed routing depends on the keymap and is not yet integrated.')
            self.check(p,1004,'status',False,False,STATUS)
            for ident in (603,604):self.disabled_slider(p,ident,'Native pointer speed/acceleration mapping is unfinished; current backend values are preserved.')
            for ident in (1018,1019):self.radio(p,ident,('numlock',ident),False,False,'Num Lock routing depends on the keymap and is not yet integrated.')
        elif k in ('abounce','aslow'):
            if k=='aslow':
                for ident in (1060,1061):self.radio(p,ident,('repeat',ident),False,False,REPEAT_REASON)
                for ident in (1065,1067):self.unavailable_edit(p,ident,REPEAT_REASON)
                for ident in (1062,1063):self.disabled_slider(p,ident,REPEAT_REASON)
            field,ident,edit,values=('bounce_ms',1057,1056,tuple(self.timings['bounce_ms'])) if k=='abounce' else ('slow_ms',1064,1068,tuple(self.timings['slow_ms']))
            self.timing_slider(p,field,ident,edit,values)
            self.unavailable_edit(p,1058 if k=='abounce' else 1021,PREVIEW)
    def timing_slider(self,p,field,ident,edit,values):
        c=self.control(ident);x,y,w,h=c['rect'];value=getattr(self.pending,field);index=min(range(len(values)),key=lambda i:abs(values[i]-value));self.slider_spec=(field,tuple(c['rect']),values)
        if field=='slow_ms':self.disabled.append(((x,y,24,h),'Zero-delay SlowKeys combined with RepeatKeys filtering is not implemented; choose a nonzero hold delay.'))
        # Copy the measured native thumb; redraw the native track/ticks only.
        source_index=c['position']-1;left=x+13;span=w-27;steps=len(values)-1
        position=lambda n:left+(span*n+steps//2)//steps
        original=position(source_index);thumb_y=y+2
        p.fill(x,y,w,h,FACE)
        p.fill(x+8,y+9,w-17,1,SHADOW);p.fill(x+8,y+10,w-18,1,BLACK);p.fill(x+8,y+11,w-17,1,FACE);p.fill(x+8,y+12,w-16,1,LIGHT);p.fill(x+w-9,y+9,1,4,LIGHT);p.fill(x+8,y+9,1,3,SHADOW)
        for n in range(len(values)):p.fill(position(n),y+24,1,4 if n in (0,steps) else 3,BLACK)
        self.sprite(p,(original-5,thumb_y,11,21),position(index)-5,thumb_y)
        self.hit((x,y,w,h),('slider',field));ex,ey,ew,eh=self.control(edit)['rect'];p.fill(ex+2,ey+2,ew-4,eh-4,FACE);p.text(f'{value/1000:.2f}',ex+3,ey+4)
    def slider_at(self,action,x):
        field,rect,values=self.slider_spec;left,y,w,h=rect;index=max(0,min(len(values)-1,round((x-left-13)*(len(values)-1)/(w-27))));value=values[index]
        # XKB SlowKeys delay zero is represented by disabling its filter.
        if field=='slow_ms' and value==0:
            self.error(ValueError('Zero-delay SlowKeys together with RepeatKeys filtering is not implemented. Choose a nonzero hold delay.'));return
        else:self.pending=replace(self.pending,**{field:value})
        self.area.queue_draw()
    def action(self,action):
        kind=action[0]
        if kind=='check':self.pending=replace(self.pending,**{action[1]:not getattr(self.pending,action[1])})
        elif kind=='mode':
            self.filter_mode=action[1]
            if self.pending.slow or self.pending.bounce:self.pending=replace(self.pending,slow=self.filter_mode=='slow',bounce=self.filter_mode=='bounce')
        elif kind=='advanced':
            self.remember(AccessSettings(self,action[1]))
        elif kind=='ok':
            self.pending.validate();self.parent.filter_mode=self.filter_mode
            if isinstance(self.parent,AccessSettings):self.parent.pending=self.pending
            else:self.parent.controller.pending=self.pending
            self.parent.area.queue_draw();self.destroy();return
        else:return super().action(action)
        self.area.queue_draw()
    def help(self):
        from win95lx.apps.dialogs import message_box
        reasons=list(dict.fromkeys(reason for rect,reason in self.disabled));message_box(self,self.title,'OK keeps these edits pending in Accessibility Properties. Apply there activates them. Cancel discards edits in this dialog.'+('\n\n'+'\n\n'.join(reasons) if reasons else ''),Gtk.MessageType.INFO)
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        if self.focus_action and self.focus_action[0]=='slider' and name in ('Left','Right','Up','Down','Home','End'):
            field,rect,values=self.slider_spec;current=min(range(len(values)),key=lambda i:abs(values[i]-getattr(self.pending,field)));index=0 if name=='Home' else len(values)-1 if name=='End' else max(0,min(len(values)-1,current+(-1 if name in ('Left','Down') else 1)));self.slider_at(self.focus_action,rect[0]+13+(rect[2]-27)*index/(len(values)-1));return True
        return super().key(window,event)
