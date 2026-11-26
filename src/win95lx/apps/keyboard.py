"""Windows 95 Keyboard Properties with real X11 repeat and layout changes."""
from dataclasses import replace
from pathlib import Path
from gi.repository import Gtk,Gdk,GLib
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.keyboard_preferences import KeyboardPreferences,X11Keyboard,LAYOUTS,LAYOUT_NAMES,LAYOUT_DESCRIPTIONS,available_layouts
from win95lx.control_panel.preferences import PreferenceController
from win95lx.shell.text_entry import TextEntry
from win95lx.shell.widgets import FACE,BLACK,LIGHT,NAVY,SHADOW

DRIVER_REASON='Change keyboard driver: Windows .DRV drivers cannot run in this session. Keyboard devices are managed by the running system; repeat speed and installed layouts work here.'

class KeyboardWindow(PropertySheet):
    title='Keyboard Properties';asset_prefix='keyboard'
    tabs=('speed','language','general')
    tab_rects=((10,29,44,22),(54,29,60,22),(114,29,49,22))

    def __init__(self,shell,backend=None):
        super().__init__(shell)
        self.controller=PreferenceController(Path.home()/'.config/win95lx/keyboard.json',backend or X11Keyboard(),KeyboardPreferences,self.apply_session)
        settings=Gtk.Settings.get_default()
        if not self.controller.path.exists():
            self.controller.applied=replace(self.controller.applied,blink_ms=min(1200,settings.get_property('gtk-cursor-blink-time')//2) if settings.get_property('gtk-cursor-blink') else 0)
            self.controller.pending=self.controller.applied
        self.test_entry=TextEntry();self.language_selection=0
        self.layouts_available=available_layouts();self.layout_names=dict((code,label) for label,code in self.layouts_available)
        self.focus_action=('slider','delay_ms')
        self.caret=True;self.caret_timer=GLib.timeout_add(100,self.blink);self.last_blink=GLib.get_monotonic_time()
        self.connect('destroy',self.cleanup)

    def cleanup(self,*_):
        if self.caret_timer:GLib.source_remove(self.caret_timer);self.caret_timer=None
    def apply_session(self,prefs):
        from win95lx.control_panel.keyboard_preferences import apply_session
        apply_session(Gtk.Settings.get_default(),prefs)
        self.shell.keyboard_preferences=prefs
    def update(self,**values):self.controller.pending=replace(self.controller.pending,**values).validate();self.area.queue_draw()
    def blink(self):
        delay=self.controller.pending.blink_ms
        if self.focus_action==('entry','test'):
            now=GLib.get_monotonic_time()
            if delay and now-self.last_blink>=delay*1000:self.caret=not self.caret;self.last_blink=now;self.area.queue_draw()
        return True

    def draw_content(self,p):
        prefs=self.controller.pending
        if self.tab==0:
            for field,y,original in (('delay_ms',113,250),('rate',188,16),('blink_ms',337,530)):
                rect=(128,y,200,30);self.hit(rect,('slider',field))
                if getattr(prefs,field)!=original:
                    # Erase only the old thumb, retain independent native ticks.
                    p.fill(134,y,184,24,FACE)
                    for row,color in enumerate((SHADOW,BLACK,FACE,LIGHT),9):p.fill(134,y+row,184,1,color)
                    index,maximum=prefs.position(field);center=139+round(174*index/maximum)
                    source_x={'delay_ms':308,'rate':218,'blink_ms':256}[field]
                    self.sprite(p,(source_x,y+1,11,22),center-5,y+1)
            # Trackbar focus belongs to the control, not the full hit box.
            for x,y,w,h in ((126,113,201,1),(126,141,201,1),(126,113,1,29),(326,113,1,29)):p.fill(x,y,w,h,FACE)
            if self.focus_action and self.focus_action[0]=='slider':
                y={'delay_ms':113,'rate':188,'blink_ms':337}[self.focus_action[1]]
                for x in range(127,327,2):p.fill(x,y,1,1,SHADOW);p.fill(x,y+28,1,1,SHADOW)
                for yy in range(y+1,y+28,2):p.fill(126,yy,1,1,SHADOW);p.fill(326,yy,1,1,SHADOW)
            self.hit((45,255,314,22),('entry','test'))
            if self.test_entry.text or self.focus_action==('entry','test'):
                p.fill(47,257,309,18,LIGHT)
                # Horizontal scrolling keeps the insertion point visible.
                left=max(0,p.font.width(self.test_entry.text[:self.test_entry.cursor])-302)
                p.cr.save();p.cr.rectangle(47,257,309,18);p.cr.clip()
                a,b=self.test_entry.selection
                if a!=b:p.fill(48+p.font.width(self.test_entry.text[:a])-left,258,p.font.width(self.test_entry.text[a:b]),13,NAVY)
                for index,char in enumerate(self.test_entry.text):p.text(char,48+p.font.width(self.test_entry.text[:index])-left,258,LIGHT if a<=index<b else BLACK)
                if self.focus_action==('entry','test') and self.caret:
                    p.fill(48+p.font.width(self.test_entry.text[:self.test_entry.cursor])-left,258,1,13,BLACK)
                p.cr.restore()
        elif self.tab==1:
            layouts=tuple(prefs.layouts);self.language_selection=min(self.language_selection,len(layouts)-1)
            if layouts!=('us',) or self.language_selection:
                p.fill(36,101,331,80,LIGHT)
                for index,code in enumerate(layouts):
                    y=102+index*17;selected=index==self.language_selection
                    if selected:p.fill(36,y,331,17,NAVY)
                    p.text(self.layout_names.get(code,code),57,y+2,LIGHT if selected else BLACK)
                    p.fill(36,y,18,17,LIGHT);p.text({'us':'En','gb':'En'}.get(code,code.title()[:2]),39,y+2,BLACK)
                    description=LAYOUT_DESCRIPTIONS.get(code,code)
                    p.text(description,367-p.font.width(description),y+2,LIGHT if selected else BLACK)
                p.fill(124,239,135,17,FACE);p.text(self.layout_names.get(layouts[0],layouts[0]),125,241)
            for index in range(len(layouts)):self.hit((34,100+index*17,334,17),('language',index))
            if len(layouts)<4:self.hit((33,203,108,23),('add',))
            else:self.button(p,'Add...',(33,203,108,23),('add',),False,'This keyboard backend supports four layouts. Remove a language before adding another.')
            self.hit((147,203,108,23),('properties',))
            reason='At least one keyboard language must remain installed.'
            if len(layouts)>1:self.button(p,'Remove',(261,203,108,23),('remove',))
            else:self.disabled.append(((261,203,108,23),reason))
            if self.language_selection>0:self.button(p,'Set as Default',(261,237,108,23),('default',))
            else:self.disabled.append(((261,237,108,23),'The selected language is already the default.'))
            # A shortcut is relevant only when more than one layout is installed.
            for value,x,label in (('alt_shift',34,'Left Alt+Shift'),('ctrl_shift',130,'Ctrl+Shift'),('none',209,'None')):
                if len(layouts)>1:
                    p.fill(x,302,90 if value=='alt_shift' else 72,15,FACE)
                    p.cr.set_source_rgb(0,0,0);p.cr.arc(x+6,309,5,0,6.283);p.cr.stroke();p.cr.set_source_rgb(1,1,1);p.cr.arc(x+6,309,4,0,6.283);p.cr.fill()
                    if prefs.switch==value:p.cr.set_source_rgb(0,0,0);p.cr.arc(x+6,309,2,0,6.283);p.cr.fill()
                    p.text(label,x+15,303);self.hit((x,300,91,18),('switch',value))
            if len(layouts)>1:
                p.text('Enable indicator on taskbar',43,342)
                if prefs.indicator:
                    for offset in range(3):p.fill(28+offset,346+offset,1,2,BLACK)
                    for offset in range(5):p.fill(30+offset,348-offset,1,2,BLACK)
                self.hit((24,339,216,19),('indicator',))
            else:self.disabled.append(((24,339,216,19),'Install a second keyboard language to enable the taskbar language indicator.'))
        else:
            p.fill(26,134,269,19,FACE);p.text('System keyboard',28,135)
            self.button(p,'Change...',(304,132,75,23),('driver',),False,DRIVER_REASON)

    def action(self,action):
        kind=action[0];prefs=self.controller.pending
        if kind=='language':self.language_selection=action[1]
        elif kind=='remove':
            if len(prefs.layouts)>1:
                layouts=list(prefs.layouts);variants=list(prefs.variants);layouts.pop(self.language_selection);variants.pop(self.language_selection)
                self.update(layouts=tuple(layouts),variants=tuple(variants));self.language_selection=max(0,self.language_selection-1)
        elif kind=='default' and self.language_selection>0:
            layouts=list(prefs.layouts);variants=list(prefs.variants);layouts.insert(0,layouts.pop(self.language_selection));variants.insert(0,variants.pop(self.language_selection));self.language_selection=0;self.update(layouts=tuple(layouts),variants=tuple(variants))
        elif kind=='switch':self.update(switch=action[1])
        elif kind=='indicator':self.update(indicator=not prefs.indicator)
        elif kind=='add':
            from win95lx.apps.choice_dialog import choose_language
            if len(prefs.layouts)>=4:self.error('This keyboard backend supports at most four installed layouts. Remove a language before adding another.');return
            code=choose_language(self,tuple((label,code) for label,code in self.layouts_available if code not in prefs.layouts))
            if code:
                if code not in prefs.layouts:
                    try:self.update(layouts=tuple(prefs.layouts)+(code,),variants=tuple(prefs.variants)+('',))
                    except ValueError as error:self.error(error)
        elif kind=='properties':
            from win95lx.apps.choice_dialog import choose_language
            code=prefs.layouts[self.language_selection];choices=tuple((label,key) for label,key in self.layouts_available if key==code or key not in prefs.layouts)
            selected=next((index for index,(_,key) in enumerate(choices) if key==code),0)
            replacement=choose_language(self,choices,selected,True)
            if replacement and replacement!=code:
                layouts=list(prefs.layouts);variants=list(prefs.variants);layouts[self.language_selection]=replacement;variants[self.language_selection]='';self.update(layouts=tuple(layouts),variants=tuple(variants))
        elif kind in ('slider','entry'):pass
        else:return super().action(action)
        self.area.queue_draw()

    def slider_at(self,action,x):
        field=action[1];maximum=self.controller.pending.position(field)[1]
        self.controller.pending=self.controller.pending.slider(field,round(max(0,min(1,(x-139)/174))*maximum));self.area.queue_draw()
    def entry_click(self,action,event):self.test_entry.cursor=self.test_entry.anchor=len(self.test_entry.text);self.caret=True
    def focus_order(self):
        if self.tab==0:order=[('slider','delay_ms'),('slider','rate'),('entry','test'),('slider','blink_ms')]
        elif self.tab==1:
            order=[('language',self.language_selection)]
            if len(self.controller.pending.layouts)<4:order+=[('add',)]
            order+=[('properties',)]
            if len(self.controller.pending.layouts)>1:order+=[('remove',)]
            if self.language_selection>0:order+=[('default',)]
            if len(self.controller.pending.layouts)>1:order+=[('switch',self.controller.pending.switch),('indicator',)]
        else:order=[]
        order+=[('ok',),('cancel',)]
        if self.controller.pending!=self.controller.applied:order+=[('apply',)]
        return order
    def tab_changed(self):
        self.focus_action=(('slider','delay_ms'),('language',self.language_selection),('ok',))[self.tab]
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval);ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK)
        if self.tab==1 and self.focus_action and self.focus_action[0]=='language' and name in ('Up','Down','Home','End'):
            count=len(self.controller.pending.layouts);self.language_selection=0 if name=='Home' else count-1 if name=='End' else max(0,min(count-1,self.language_selection+(1 if name=='Down' else -1)));self.focus_action=('language',self.language_selection);self.area.queue_draw();return True
        if self.tab==1 and self.focus_action and self.focus_action[0]=='switch' and name in ('Left','Right','Up','Down'):
            options=('alt_shift','ctrl_shift','none');index=options.index(self.controller.pending.switch);value=options[(index+(1 if name in ('Down','Right') else -1))%3];self.update(switch=value);self.focus_action=('switch',value);return True
        if self.focus_action and self.focus_action[0]=='slider' and name in ('Left','Right','Up','Down','Home','End'):
            field=self.focus_action[1];index,maximum=self.controller.pending.position(field)
            index=0 if name=='Home' else maximum if name=='End' else index+(1 if name in ('Right','Up') else -1)
            self.controller.pending=self.controller.pending.slider(field,index);self.area.queue_draw();return True
        if self.focus_action==('entry','test') and name not in ('Escape','Tab','ISO_Left_Tab','Return','KP_Enter','F1'):
            char=chr(Gdk.keyval_to_unicode(event.keyval)) if Gdk.keyval_to_unicode(event.keyval) else ''
            if self.test_entry.key(name,char,ctrl,bool(event.state&Gdk.ModifierType.SHIFT_MASK)):self.caret=True;self.area.queue_draw();return True
        return super().key(window,event)
