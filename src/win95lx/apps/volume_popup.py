"""Live tray volume popup; layout based on SNDVOL32 dialog resource 106.

Native original screenshot acceptance is pending. No saved recording levels
are replayed when the user changes output volume or mute here.
"""
import subprocess
from gi.repository import Gtk,Gdk
from win95lx.shell.widgets import Painter,FACE,LIGHT,SHADOW,BLACK
from win95lx.control_panel.audio_preferences import PulseAudio

class VolumePopup(Gtk.Window):
    width=79;height=134
    def __init__(self,shell,left,backend=None):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.shell=shell;self.assets=self.dialog_assets=shell.assets;self.backend=backend or PulseAudio();self.dragging=False;self.finished=False
        self.set_transient_for(shell);self.set_decorated(False)
        screen=shell.get_screen();self.move(max(0,min(left,screen.get_width()-self.width)),max(0,screen.get_height()-28-self.height))
        self.refresh()
        self.area=Gtk.DrawingArea();self.area.set_size_request(self.width,self.height);self.add(self.area)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK)
        for signal,handler in (('draw',self.draw),('button-press-event',self.press),('button-release-event',self.release),('motion-notify-event',self.motion)):
            self.area.connect(signal,handler)
        self.connect('realize',lambda *_:self.get_window().set_cursor(shell.cursor_for('arrow')))
        from win95lx.control_panel.display_preferences import install_palette_filter
        install_palette_filter(self,lambda:shell.display_preferences.palette)
        self.connect('key-press-event',self.key);self.connect('focus-out-event',lambda *_:self.finish())
        self.show_all();self.grab_add();self.present();self.get_window().focus(Gdk.CURRENT_TIME)
    def refresh(self):
        state=self.backend.snapshot();name=state['playback'];device=next((d for d in state['devices']['sinks'] if d.name==name),None)
        if device is None:raise RuntimeError('No playback device is available.')
        self.volume=device.percent;self.muted=device.muted;self.shell.audio_muted=self.muted;self.shell.area.queue_draw()
    def draw(self,area,cr):
        p=Painter(cr,self.shell.font);p.window_frame(0,0,self.width,self.height)
        p.text('Volume',(self.width-p.font.width('Volume'))//2,8)
        for y in range(33,105,8):p.fill(14,y,5,1,SHADOW)
        p.fill(39,29,3,75,SHADOW);p.fill(42,29,1,75,LIGHT)
        y=29+round(69*(1-min(100,self.volume)/100));p.bevel(30,y,22,11)
        p.bevel(8,116,13,13,True);p.fill(10,118,9,9,LIGHT)
        if self.muted:
            for x in range(3):p.fill(10+x,122+x,1,2,BLACK)
            for x in range(5):p.fill(12+x,124-x,1,2,BLACK)
        p.text('Mute',25,116)
        return False
    def finish(self):
        if self.finished:return False
        self.finished=True;self.grab_remove();self.destroy();self.shell.present();return False
    def change(self,value):
        value=max(0,min(100,round(value)))
        try:self.backend.set_playback_volume(value);self.refresh()
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:self.show_error(error)
        self.area.queue_draw()
    def toggle_mute(self):
        try:self.backend.set_playback_mute(not self.muted);self.refresh()
        except (OSError,RuntimeError,ValueError,subprocess.SubprocessError) as error:self.show_error(error)
        self.area.queue_draw()
    def show_error(self,error):
        from win95lx.apps.dialogs import message_box
        self.finish();message_box(self.shell,'Volume Control','The sound device could not be changed. Reopen Multimedia Properties and check the available playback device.',Gtk.MessageType.ERROR)
    def press(self,area,event):
        if event.button!=1 or not 0<=event.x<self.width or not 0<=event.y<self.height:return self.finish()
        if 26<=event.x<56 and 24<=event.y<110:self.dragging=True;self.change(100*(1-(event.y-34)/69))
        elif 5<=event.x<72 and 112<=event.y<132:self.toggle_mute()
        return True
    def release(self,area,event):self.dragging=False;return True
    def motion(self,area,event):
        if self.dragging:self.change(100*(1-(event.y-34)/69));return True
        return False
    def key(self,window,event):
        name=Gdk.keyval_name(event.keyval)
        if name in ('Escape','Return','KP_Enter'):return self.finish()
        if name in ('m','M','space'):self.toggle_mute();return True
        if name in ('Up','Down','Home','End','Page_Up','Page_Down'):
            self.change(100 if name=='Home' else 0 if name=='End' else self.volume+{'Up':2,'Down':-2,'Page_Up':10,'Page_Down':-10}[name]);return True
        return False
