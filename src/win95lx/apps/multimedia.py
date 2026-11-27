"""Native Multimedia sheet backed by actual PulseAudio/PipeWire endpoints."""
from dataclasses import replace
from pathlib import Path
import json,subprocess
from gi.repository import Gtk,Gdk
from win95lx.apps.property_sheet import PropertySheet
from win95lx.control_panel.audio_preferences import AudioPreferences,PulseAudio,merge_untouched_audio
from win95lx.control_panel.preferences import PreferenceController
from win95lx.shell.widgets import FACE,BLACK,LIGHT,SHADOW,NAVY

QUALITY_REASON='Recording quality is selected by the recording application. A shared recording/export settings integration is not implemented yet.'
VIDEO_REASON='Default video window sizing is not connected to a media player yet. This control is unfinished.'
MIDI_REASON='MIDI output configuration is not implemented yet. Windows MIDI driver installation is unavailable; a Linux MIDI backend must be connected.'
CD_REASON='Analog CD drive and headphone mixer configuration is not implemented in this applet. Digital CD playback uses the normal playback device.'
PREFERRED_REASON='Application-specific audio routing is not implemented yet. Preferred playback and recording devices set the session defaults.'

class UnavailableAudio:
    def preferences(self):return AudioPreferences()
    def snapshot(self):return None
    def restore(self,state):pass
    def apply(self,value):
        value.validate()
        if value.playback or value.recording:raise RuntimeError('The audio service is unavailable. Start the session audio service and reopen Multimedia Properties.')
    def inventory(self):return {'sinks':(),'sources':()}

class AudioController(PreferenceController):
    def apply(self):
        self.pending=merge_untouched_audio(self.pending,self.applied,self.backend.preferences())
        super().apply()

class MultimediaWindow(PropertySheet):
    title='Multimedia Properties';asset_prefix='multimedia';size=(366,448)
    tabs=('audio','video','midi','cd-music','advanced')
    tab_rects=((10,29,64,20),(74,29,62,20),(136,29,60,20),(196,29,69,20),(265,29,74,20))
    buttons=((121,415,75,23),(202,415,75,23),(283,415,75,23))
    def __init__(self,shell,backend=None):
        super().__init__(shell);self.backend=backend or PulseAudio();self.service_error=None
        try:self.inventory=self.backend.inventory();actual=self.backend.preferences()
        except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
            self.service_error='The session audio service is unavailable. Start it and reopen Multimedia Properties.';self.backend=UnavailableAudio();self.inventory=self.backend.inventory();actual=self.backend.preferences()
        self.controller=AudioController(Path.home()/'.config/win95lx/multimedia.json',self.backend,AudioPreferences,self.apply_session)
        # Use the service's current defaults/levels rather than replaying stale
        # persisted settings changed by another application since last opening.
        self.controller.applied=self.controller.pending=replace(actual,tray=self.controller.applied.tray)
        self.device_selection=0
        self.focus_action=('slider','playback') if self.choices('sinks') else ('ok',)
    def apply_session(self,prefs):self.shell.audio_preferences=prefs;self.shell.area.queue_draw()
    def choices(self,kind):return tuple(d for d in self.inventory[kind] if kind=='sinks' or not d.monitor)
    def update(self,**kwargs):self.controller.pending=replace(self.controller.pending,**kwargs).validate();self.area.queue_draw()
    def combo(self,p,rect,label,action,enabled):
        x,y,w,h=rect;p.fill(x,y,w,h,FACE)
        # Preserve the native two-pixel inset and seventeen-pixel arrow gutter.
        for source,dx,dy in (((85,137,w,2),x,y),((85,155,w,2),x,y+h-2),((85,139,2,16),x,y+2),((326,139,2,16),x+w-2,y+2)):
            sx,sy,sw,sh=source;p.cr.save();p.cr.rectangle(dx,dy,sw,sh);p.cr.clip();p.image(self.frames[0],dx-sx,dy-sy);p.cr.restore()
        p.fill(x+2,y+2,w-4,h-4,LIGHT if enabled else FACE)
        focused=enabled and self.focus_action==action
        if focused:p.fill(x+3,y+3,w-21,h-6,NAVY)
        p.cr.save();p.cr.rectangle(x+3,y+2,w-20,h-4);p.cr.clip();p.text(label,x+3,y+3,LIGHT if focused else BLACK if enabled else SHADOW);p.cr.restore()
        sx,sy,frame=(318,279,self.frames[1]) if enabled else (311,139,self.frames[0])
        p.cr.save();p.cr.rectangle(x+w-17,y+2,16,16);p.cr.clip();p.image(frame,x+w-17-sx,y+2-sy);p.cr.restore()
        if enabled:self.hit(rect,action)
    def draw_content(self,p):
        prefs=self.controller.pending
        if self.tab==0:
            for kind,field,y,cy in (('sinks','playback',87,137),('sources','recording',233,285)):
                devices=self.choices(kind);enabled=bool(devices);name=getattr(prefs,field)
                device=next((d for d in devices if d.name==name),None)
                if enabled:
                    for text,x,yy in (('Volume:',85,y+1),('Low',130,y+1),('High',302,y+1),('Preferred device:',85,cy-16)):
                        p.fill(x,yy,p.font.width(text)+2,14,FACE);p.text(text,x,yy)
                    p.fill(167,y,126,25,FACE)
                    for dy,color in ((9,SHADOW),(10,BLACK),(11,FACE),(12,LIGHT)):p.fill(172,y+dy,114,1,color)
                    center=172+round(min(100,getattr(prefs,field+'_volume'))*114/100)
                    self.sprite(p,(167,y+2,11,22),center-5,y+2)
                    self.hit((159,y,137,33),('slider',field))
                    if self.focus_action==('slider',field):
                        for xx in range(159,296,2):p.fill(xx,y,1,1,BLACK);p.fill(xx,y+32,1,1,BLACK)
                        for yy in range(y,y+33,2):p.fill(159,yy,1,1,BLACK);p.fill(295,yy,1,1,BLACK)
                else:self.disabled.append(((85,y,243,70),self.service_error or ('No recording input is available. A playback monitor is not a microphone.' if kind=='sources' else 'No playback device is available.')))
                self.combo(p,(85,cy,243,20),device.description if device else 'No Playback Devices' if kind=='sinks' else 'No Recording Devices',('device',kind),enabled)
            p.fill(85,171,243,17,FACE);p.bevel(85,172,13,13,True);p.fill(87,174,9,9,LIGHT)
            if prefs.tray:
                for offset in range(3):p.fill(88+offset,177+offset,1,2,BLACK)
                for offset in range(5):p.fill(90+offset,179-offset,1,2,BLACK)
            enabled=bool(self.choices('sinks'))
            p.text('Show volume control on the taskbar',103,172,BLACK if enabled else SHADOW)
            if enabled:self.hit((85,171,244,17),('tray',))
            else:self.disabled.append(((85,171,244,17),self.service_error or 'A playback device is required for the volume control.'))
            self.disabled.extend([((85,330,243,23),QUALITY_REASON),((24,375,250,20),PREFERRED_REASON)])
        elif self.tab==1:
            self.disabled.extend([((24,263,318,73),VIDEO_REASON)])
            # An available-looking native control is disabled explicitly while
            # player integration is unfinished; keyboard Help gives the reason.
            self.combo(p,(108,277,227,20),'Original size',('video',),False)
            for label,y in (('Window',280),('Full screen',308)):
                p.fill(47,y,60,14,FACE);p.text(label,47,y,SHADOW)
        elif self.tab==2:
            self.disabled.append(((24,62,317,265),MIDI_REASON))
        elif self.tab==3:
            self.combo(p,(115,97,45,20),'',('cd-device',),False)
            for label,x,y in (('CD-ROM drive:',33,100),('Headphone:',33,137),('Low',115,137),('High',289,137)):
                p.fill(x,y,p.font.width(label)+2,14,FACE);p.text(label,x,y,SHADOW)
            self.disabled.append(((24,62,317,119),CD_REASON))
        else:
            rows=self.device_rows();p.fill(26,80,313,277,LIGHT)
            for index,(label,detail) in enumerate(rows[:16]):
                y=82+index*16;selected=index==self.device_selection
                if selected:p.fill(30,y,305,16,NAVY)
                p.text(label[:52],31,y+1,LIGHT if selected else BLACK);self.hit((28,y,308,16),('row',index))
            self.button(p,'Properties',(247,370,94,23),('properties',),bool(rows))
    def device_rows(self):
        return [(('Playback: ' if kind=='sinks' else 'Recording: ')+d.description,f'{d.description}\n\nDevice: {d.name}\nChannels: {len(d.channels)}\nMaster volume: {d.percent}%\nMuted: '+('Yes' if d.muted else 'No')+('\nPlayback monitor; not a microphone.' if d.monitor else '')) for kind in ('sinks','sources') for d in self.inventory[kind]]
    def action(self,action):
        kind=action[0]
        if kind=='tray':self.update(tray=not self.controller.pending.tray)
        elif kind=='device':
            from win95lx.apps.choice_dialog import ChoicePopup
            devices=self.choices(action[1]);field='playback' if action[1]=='sinks' else 'recording'
            current=next((i for i,d in enumerate(devices) if d.name==getattr(self.controller.pending,field)),0)
            self.popup_window=ChoicePopup(self,(85,137 if field=='playback' else 285,243,20),[d.description for d in devices],current,lambda i:self.choose_device(field,devices[i]))
        elif kind=='row':self.device_selection=action[1]
        elif kind=='properties':
            from win95lx.apps.dialogs import message_box
            try:self.inventory=self.backend.inventory()
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:self.error(error);return
            rows=self.device_rows();self.device_selection=min(self.device_selection,max(0,len(rows)-1))
            if rows:message_box(self,'Multimedia Device Properties',rows[self.device_selection][1],Gtk.MessageType.INFO)
        elif kind in ('slider',):pass
        else:return super().action(action)
        self.area.queue_draw()
    def choose_device(self,field,device):self.update(**{field:device.name,field+'_volume':device.percent})
    def slider_at(self,action,x):self.update(**{action[1]+'_volume':round(max(0,min(1,(x-172)/114))*100)})
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        if self.tab==0 and self.focus_action and self.focus_action[0]=='slider' and name in ('Left','Right','Home','End','Page_Up','Page_Down'):
            field=self.focus_action[1]+'_volume';value=getattr(self.controller.pending,field)
            self.update(**{field:0 if name=='Home' else 100 if name=='End' else max(0,min(100,value+{'Left':-1,'Right':1,'Page_Up':10,'Page_Down':-10}[name]))});return True
        if self.tab==0 and self.focus_action and self.focus_action[0]=='device' and name in ('F4','Down'):
            self.action(self.focus_action);return True
        if self.tab==4 and name in ('Up','Down','Home','End'):
            last=max(0,len(self.device_rows())-1);self.device_selection=0 if name=='Home' else last if name=='End' else max(0,min(last,self.device_selection+(1 if name=='Down' else -1)));self.area.queue_draw();return True
        return super().key(window,event)
    def tab_changed(self):
        self.focus_action=None
        if self.tab==4:
            try:self.inventory=self.backend.inventory()
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:self.error(error)
            self.device_selection=min(self.device_selection,max(0,len(self.device_rows())-1))
    def focus_order(self):
        order=[]
        if self.tab==0:
            for kind,field in (('sinks','playback'),('sources','recording')):
                if self.choices(kind):order.extend([('slider',field),('device',kind)])
            if self.choices('sinks'):order.append(('tray',))
        elif self.tab==4 and self.device_rows():order.extend([('row',self.device_selection),('properties',)])
        order.extend([('ok',),('cancel',)])
        if self.controller.pending!=self.controller.applied:order.append(('apply',))
        return order
