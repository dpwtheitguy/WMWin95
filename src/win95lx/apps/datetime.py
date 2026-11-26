"""Native Date/Time sheet, calendar, clock, civil-time editing and DST policy."""
import calendar,math
from datetime import datetime,timedelta
from dataclasses import replace
from pathlib import Path
from gi.repository import Gdk,GLib
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.datetime_settings import DateTimeController,TimedateBackend,ZONES,native_zone_catalog
from win95lx.shell.widgets import FACE,BLACK,LIGHT,NAVY,SHADOW,TEAL

class DateTimeWindow(PropertySheet):
    title='Date/Time Properties';asset_prefix='datetime';size=(404,341)
    tabs=('datetime','timezone');tab_rects=((10,29,73,22),(83,29,61,22))
    buttons=((158,308,75,23),(239,308,75,23),(320,308,75,23))
    def __init__(self,shell,backend=None):
        super().__init__(shell);self.controller=DateTimeController(Path.home()/'.config/win95lx/datetime.json',backend or TimedateBackend())
        self.zones=native_zone_catalog(self.assets)
        if self.controller.pending.zone not in {zone for label,zone,offset in self.zones}:
            prefs=self.controller.pending;offset=prefs.offset
            label='(GMT'+('+' if offset>=0 else '-')+f'{abs(offset)//60:02}:{abs(offset)%60:02}) '+prefs.zone.rsplit('/',1)[-1].replace('_',' ')
            self.zones+=((label,prefs.zone,offset),)
        self.segment=0;self.digits='';self.digit_time=0;self.timer=GLib.timeout_add_seconds(1,self.tick);self.connect('destroy',self.cleanup)
        self.focus_action=('month',)
    def cleanup(self,*_):
        if self.timer:GLib.source_remove(self.timer);self.timer=None
    def tick(self):self.area.queue_draw();return True
    def value(self):return self.controller.edited or datetime.now(self.controller.pending.tzinfo).replace(tzinfo=None,microsecond=0)
    def edit(self,**values):
        current=self.value();year=values.get('year',current.year);month=values.get('month',current.month)
        if not 1601<=year<=9999:self.error('Enter a year from 1601 through 9999.');return
        day=min(values.get('day',current.day),calendar.monthrange(year,month)[1])
        try:self.controller.edited=current.replace(**{**values,'day':day})
        except ValueError as error:self.error(error)
        self.area.queue_draw()
    def draw_content(self,p):
        value=self.value();prefs=self.controller.pending
        if self.tab==0:
            # Dynamic fields retain the original control borders and arrows.
            p.fill(33,82,51,16,NAVY if self.focus_action==('month',) else LIGHT);p.text(calendar.month_name[value.month],34,83,LIGHT if self.focus_action==('month',) else BLACK)
            p.fill(117,82,58,16,LIGHT);p.text(str(value.year),118,83)
            self.hit((30,79,74,21),('month',));self.hit((114,79,63,21),('year',))
            self.hit((178,80,16,10),('year-step',1));self.hit((178,90,16,10),('year-step',-1))
            p.fill(32,132,156,107,LIGHT)
            for row,week in enumerate(calendar.Calendar(firstweekday=6).monthdayscalendar(value.year,value.month)):
                for column,day in enumerate(week):
                    if not day:continue
                    label=str(day);x=40+round(column*22.5);y=135+row*18
                    if day==value.day:p.fill(x-1,y-1,p.font.width(label)+2,13,NAVY)
                    p.text(label,x,y,LIGHT if day==value.day else BLACK);self.hit((32+round(column*22.5),133+row*18,22,18),('day',day))
            # Original dial markings stay untouched. The old hands lie wholly
            # inside this circle, so they are erased before drawing live hands.
            p.cr.set_source_rgb(*(c/255 for c in FACE));p.cr.arc(295,145,57,0,math.tau);p.cr.fill()
            for angle,length,width,color in (((value.hour%12+value.minute/60)*math.tau/12,34,5,TEAL),((value.minute+value.second/60)*math.tau/60,48,3,TEAL),(value.second*math.tau/60,50,1,SHADOW)):
                dx,dy=math.sin(angle),-math.cos(angle);px,py=-dy,dx
                points=((295+dx*length,145+dy*length),(295+px*width,145+py*width),(295-dx*9,145-dy*9),(295-px*width,145-py*width))
                p.cr.set_source_rgb(*(c/255 for c in color));p.cr.move_to(*points[0])
                for point in points[1:]:p.cr.line_to(*point)
                p.cr.close_path();p.cr.fill()
            text=value.strftime('%I:%M:%S %p').lstrip('0');p.fill(259,224,72,16,LIGHT);p.text(text,261,225)
            self.hit((257,222,76,21),('time',));self.hit((334,222,16,10),('time-step',1));self.hit((334,232,16,10),('time-step',-1))
            hour=str(value.hour%12 or 12);parts=(hour,f'{value.minute:02}',f'{value.second:02}',value.strftime('%p'))
            offsets=(0,p.font.width(hour+':'),p.font.width(hour+':00:'),p.font.width(hour+':00:00 '))
            for index,(part,offset) in enumerate(zip(parts,offsets)):
                self.hit((261+offset,224,p.font.width(part),16),('time',index))
                if self.focus_action and self.focus_action[0]=='time' and self.segment==index:
                    p.fill(261+offset,224,p.font.width(part),14,NAVY);p.text(part,261+offset,225,LIGHT)
            label='Current time zone: '+(value.replace(tzinfo=prefs.tzinfo).tzname() or prefs.zone)
            p.fill(18,271,367,17,FACE);p.text(label,19,272)
        else:
            index=next(index for index,(_,zone,_) in enumerate(self.zones) if zone==prefs.zone)
            p.fill(25,62,338,13,NAVY if self.focus_action==('zone',) else LIGHT)
            p.cr.save();p.cr.rectangle(25,62,338,13);p.cr.clip();p.text(self.zones[index][0],25,62,LIGHT if self.focus_action==('zone',) else BLACK);p.cr.restore()
            self.hit((22,59,360,21),('zone',));self.hit((21,278,360,16),('daylight',))
            if not prefs.daylight:p.fill(24,281,8,8,LIGHT)
    def step_time(self,amount):
        current=self.value();delta=(timedelta(hours=amount),timedelta(minutes=amount),timedelta(seconds=amount),timedelta(hours=12*amount))[self.segment]
        updated=current+delta
        if 1601<=updated.year<=9999:self.controller.edited=updated
        self.area.queue_draw()
    def action(self,action):
        kind=action[0]
        if kind in ('month','zone'):
            from win95lx.apps.choice_dialog import ChoicePopup
            if kind=='month':ChoicePopup(self,(30,79,74,21),tuple(calendar.month_name[1:]),self.value().month-1,lambda index:self.edit(month=index+1))
            else:
                index=next(index for index,(_,zone,_) in enumerate(self.zones) if zone==self.controller.pending.zone)
                ChoicePopup(self,(22,59,360,21),tuple(label for label,zone,offset in self.zones),index,self.select_zone)
        elif kind=='daylight':self.controller.pending=replace(self.controller.pending,daylight=not self.controller.pending.daylight)
        elif kind=='year-step':self.edit(year=self.value().year+action[1])
        elif kind=='day':self.edit(day=action[1])
        elif kind=='time-step':self.step_time(action[1])
        elif kind=='time':
            if len(action)>1:self.segment=action[1]
        elif kind=='year':pass
        else:return super().action(action)
        self.area.queue_draw()
    def select_zone(self,index):self.controller.pending=replace(self.controller.pending,zone=self.zones[index][1]);self.area.queue_draw()
    def focus_order(self):
        order=[('month',),('year',),('day',self.value().day),('time',self.segment)] if self.tab==0 else [('zone',),('daylight',)]
        order+=[('ok',),('cancel',)]
        if self.controller.pending!=self.controller.applied or self.controller.edited is not None:order+=[('apply',)]
        return order
    def tab_changed(self):self.focus_action=('month',) if self.tab==0 else ('zone',)
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval);action=self.focus_action;value=self.value()
        if action and action[0] in ('month','year','day','time','zone'):
            kind=action[0]
            if kind in ('month','zone') and (name=='F4' or name=='Down' and event.state&Gdk.ModifierType.MOD1_MASK):self.action(action);return True
            if kind=='time' and name in ('Left','Right'):self.segment=max(0,min(3,self.segment+(1 if name=='Right' else -1)));return True
            if name in ('Up','Down','Left','Right'):
                delta=1 if name in ('Up','Right') else -1
                if kind=='month':self.edit(month=(value.month-1+delta)%12+1)
                elif kind=='year':self.edit(year=value.year+delta)
                elif kind=='time':self.step_time(delta)
                elif kind=='zone':
                    index=next(index for index,(_,zone,_) in enumerate(self.zones) if zone==self.controller.pending.zone);self.select_zone(max(0,min(len(self.zones)-1,index+delta)))
                else:self.controller.edited=value+timedelta(days=delta if name in ('Left','Right') else -7 if name=='Up' else 7)
                self.area.queue_draw();return True
            if name and name.isdigit() and kind in ('year','time'):
                now=GLib.get_monotonic_time();self.digits=(self.digits if now-self.digit_time<1500000 else '')+name;self.digit_time=now
                self.digits=self.digits[-(4 if kind=='year' else 2):];number=int(self.digits)
                if kind=='year' and len(self.digits)==4:self.edit(year=number)
                elif kind=='time':
                    if self.segment==0 and 1<=number<=12:self.edit(hour=number%12+(12 if value.hour>=12 else 0))
                    elif self.segment in (1,2) and number<60:self.edit(**{('minute' if self.segment==1 else 'second'):number})
                return True
            if kind=='time' and name and name.lower() in ('a','p'):self.edit(hour=value.hour%12+(12 if name.lower()=='p' else 0));return True
        return super().key(window,event)
