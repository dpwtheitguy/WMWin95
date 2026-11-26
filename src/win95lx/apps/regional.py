"""Five-tab native Regional Settings with live Win95LX formatting effects."""
from dataclasses import replace
from datetime import datetime
from gi.repository import Gdk
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.regional_preferences import RegionalPreferences,RegionalBackend,REGIONS,regional_preset,config_path
from win95lx.control_panel.preferences import PreferenceController
from win95lx.shell.text_entry import TextEntry
from win95lx.shell.widgets import FACE,BLACK,LIGHT,NAVY,SHADOW

# Measured control rectangles, not inferred from a different CPL's dialog units.
FIELDS={
 1:(('decimal',(174,129,119,21)),('digits',(174,157,119,21)),('grouping',(174,185,119,21)),('group_size',(174,213,119,21)),
    ('negative_sign',(174,254,119,21)),('negative_format',(174,282,119,21)),('leading_zero',(174,310,119,21)),('measurement',(174,338,119,21)),('list_separator',(174,366,119,21))),
 2:(('currency',(174,153,119,21)),('currency_position',(174,181,119,21)),('currency_negative',(174,209,119,21)),('currency_decimal',(174,251,119,21)),('currency_digits',(174,279,119,21)),('currency_grouping',(174,324,119,21)),('currency_group_size',(174,352,119,21))),
 3:(('time_style',(111,111,253,21)),('time_separator',(111,140,74,21)),('am',(111,188,74,21)),('pm',(111,216,74,21))),
 4:(('short_date',(125,150,239,21)),('date_separator',(125,179,75,21)),('long_date',(125,271,239,21))),
}
CHOICES={
 'decimal':('.',','),'grouping':(',','.',' '),'group_size':('0','3'),'negative_sign':('-',),
 'negative_format':('(1.1)','-1.1','- 1.1','1.1-','1.1 -'),'leading_zero':('0.7','.7'),'measurement':('Metric','U.S.'),'list_separator':(',',';'),
 'currency':('$','£','€','¥'),'currency_position':('$1.1','1.1$','$ 1.1','1.1 $'),
 'currency_negative':('($1.1)','-$1.1','$-1.1','$1.1-','(1.1$)','-1.1$','1.1-$','1.1$-','-1.1 $','-$ 1.1','1.1 $-','$ 1.1-','$ -1.1','1.1- $','($ 1.1)','(1.1 $)'),
 'currency_decimal':('.',','),'currency_grouping':(',','.',' '),'currency_group_size':('0','3'),
 'time_style':('h:mm:ss tt','hh:mm:ss tt','H:mm:ss','HH:mm:ss'),'time_separator':(':','.'),'am':('AM',''),'pm':('PM',''),
 'short_date':('M/d/yy','M/d/yyyy','MM/dd/yy','MM/dd/yyyy','dd/MM/yyyy','yyyy-MM-dd'),
 'date_separator':('/','-','.'),'long_date':('dddd, MMMM dd, yyyy','MMMM d, yyyy','dddd, d MMMM yyyy','yyyy-MM-dd'),
}
for key in ('digits','currency_digits'):CHOICES[key]=tuple(str(n) for n in range(10))
NUMERIC=('digits','currency_digits','group_size','currency_group_size')
FIXED=('negative_format','currency_position','currency_negative','leading_zero','measurement')

class RegionalWindow(PropertySheet):
    title='Regional Settings Properties';asset_prefix='regional'
    tabs=('regional','number','currency','time','date')
    tab_rects=((10,29,94,22),(104,29,51,22),(155,29,54,22),(209,29,42,22),(251,29,44,22))
    def __init__(self,shell):
        super().__init__(shell);self.controller=PreferenceController(config_path(),RegionalBackend(config_path()),RegionalPreferences)
        self.editing_key=None;self.entry=TextEntry();self.focus_action=('region',)
    def text_value(self,key):
        value=getattr(self.controller.pending,key)
        return ('0.7' if value else '.7') if key=='leading_zero' else str(value)
    def commit_entry(self):
        if self.editing_key is None:return True
        key=self.editing_key
        try:
            value=int(self.entry.text) if key in NUMERIC else self.entry.text
            self.controller.pending=replace(self.controller.pending,**{key:value}).validate()
        except ValueError as error:self.error(error);return False
        self.editing_key=None;return True
    def draw_content(self,p):
        prefs=self.controller.pending;now=datetime.now()
        if self.tab==0:
            self.hit((42,109,318,21),('region',))
            p.fill(45,112,296,15,NAVY if self.focus_action==('region',) else LIGHT);p.text(prefs.region,45,112,LIGHT if self.focus_action==('region',) else BLACK)
        else:
            for key,(x,y,w,h) in FIELDS[self.tab]:
                p.fill(x+2,y+2,w-20,17,LIGHT)
                text=self.entry.text if self.editing_key==key else self.text_value(key)
                p.cr.save();p.cr.rectangle(x+2,y+2,w-20,17);p.cr.clip()
                if self.editing_key==key:
                    a,b=self.entry.selection
                    if a!=b:p.fill(x+3+p.font.width(text[:a]),y+3,p.font.width(text[a:b]),13,NAVY)
                    for index,char in enumerate(text):p.text(char,x+3+p.font.width(text[:index]),y+3,LIGHT if a<=index<b else BLACK)
                    p.fill(x+3+p.font.width(text[:self.entry.cursor]),y+3,1,13,BLACK)
                else:p.text(text,x+3,y+3)
                p.cr.restore();self.hit((x,y,w-17,h),('field',key));self.hit((x+w-17,y,17,h),('choices',key))
            if self.tab in (1,2):
                currency=self.tab==2;rects=((84,83,95,18),(255,83,94,18)) if currency else ((83,84,104,18),(264,84,104,18))
                for sign,(x,y,w,h) in zip((1,-1),rects):
                    p.fill(x,y,w,h,FACE);p.cr.save();p.cr.rectangle(x,y,w,h);p.cr.clip();p.text(prefs.number(sign*123456789,currency),x,y,SHADOW);p.cr.restore()
            elif self.tab==3:
                p.fill(113,85,251,17,FACE);p.text(prefs.time(now),113,85,SHADOW)
            elif self.tab==4:
                for rect,text in (((128,125,235,17),prefs.date(now)),((128,246,235,17),prefs.date(now,prefs.long_date))):
                    x,y,w,h=rect;p.fill(*rect,FACE);p.cr.save();p.cr.rectangle(*rect);p.cr.clip();p.text(text,x,y,SHADOW);p.cr.restore()
                self.disabled.append(((108,69,271,21),'Gregorian Calendar is the supported calendar for this regional-formatting implementation. Additional calendar systems are unfinished.'))
    def choose(self,key):
        from win95lx.apps.choice_dialog import ChoicePopup
        if not self.commit_entry():return
        choices=CHOICES[key];value=self.text_value(key)
        if value not in choices:choices=(value,)+choices
        rect=dict(FIELDS[self.tab])[key]
        ChoicePopup(self,rect,choices,choices.index(value),lambda index:self.selected(key,choices[index]))
    def selected(self,key,value):
        if key in NUMERIC:value=int(value)
        elif key=='leading_zero':value=value=='0.7'
        try:self.controller.pending=replace(self.controller.pending,**{key:value}).validate()
        except ValueError as error:self.error(error)
        self.editing_key=None;self.area.queue_draw()
    def action(self,action):
        kind=action[0]
        if kind=='cancel':self.editing_key=None;return super().action(action)
        if kind in ('tab','apply','ok','region','choices') and not self.commit_entry():return
        if kind=='field':
            if not self.commit_entry():return
            key=action[1]
            if key in FIXED:self.choose(key)
            else:self.editing_key=key;self.entry=TextEntry(self.text_value(key));self.entry.select_all()
        elif kind=='choices':self.choose(action[1])
        elif kind=='region':
            from win95lx.apps.choice_dialog import ChoicePopup
            ChoicePopup(self,(42,109,318,21),REGIONS,REGIONS.index(self.controller.pending.region),self.region_selected)
        else:
            super().action(action)
            if kind in ('apply','ok'):
                for window in self.shell.accessory_windows.values():
                    if hasattr(window,'refresh'):window.refresh()
                    window.queue_draw()
                self.shell.area.queue_draw()
            return
        self.area.queue_draw()
    def region_selected(self,index):self.controller.pending=regional_preset(REGIONS[index]);self.area.queue_draw()
    def focus_changed(self):
        if self.focus_action and self.focus_action[0]=='field' and self.focus_action[1] not in FIXED:
            self.editing_key=self.focus_action[1];self.entry=TextEntry(self.text_value(self.editing_key));self.entry.select_all()
    def tab_changed(self):
        self.focus_action=('region',) if self.tab==0 else ('field',FIELDS[self.tab][0][0]);self.focus_changed()
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval);ctrl=bool(event.state&Gdk.ModifierType.CONTROL_MASK);shift=bool(event.state&Gdk.ModifierType.SHIFT_MASK)
        if self.editing_key and name not in ('Escape','Tab','ISO_Left_Tab','Return','KP_Enter','F1'):
            char=chr(Gdk.keyval_to_unicode(event.keyval)) if Gdk.keyval_to_unicode(event.keyval) else ''
            if name=='F4' or name=='Down' and event.state&Gdk.ModifierType.MOD1_MASK:self.choose(self.editing_key);return True
            if self.entry.key(name,char,ctrl,shift):self.area.queue_draw();return True
        if name in ('Tab','ISO_Left_Tab') and not self.commit_entry():return True
        if self.focus_action and self.focus_action[0] in ('choices','field','region'):
            if name=='F4' or name=='Down' and event.state&Gdk.ModifierType.MOD1_MASK:
                self.action(('region',) if self.focus_action[0]=='region' else ('choices',self.focus_action[1]));return True
        return super().key(window,event)
