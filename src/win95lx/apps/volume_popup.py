"""Live tray volume popup; layout based on SNDVOL32 dialog resource 106.

Native original screenshot acceptance is pending. No saved recording levels
are replayed when the user changes output volume or mute here.
"""
import weakref
from gi.repository import Gtk,Gdk,GLib
from win95lx.apps.popup_events import dismiss_and_replay,local_point
from win95lx.shell.widgets import Painter,FACE,LIGHT,SHADOW,BLACK
from win95lx.control_panel.audio_preferences import PulseAudio
from win95lx.control_panel.audio_updates import PlaybackUpdates

def report_closed_update(shell_ref,result):
    """A failed final write belongs to the live shell, not a destroyed popup."""
    shell=shell_ref()
    if shell is None or not shell.get_realized():return
    if result.endpoint is not None:shell.audio_muted=result.endpoint.muted;shell.area.queue_draw()
    from win95lx.apps.dialogs import message_box
    message_box(shell,'Volume Control','The sound device could not be changed. Reopen Multimedia Properties and check the available playback device.',Gtk.MessageType.ERROR)

class VolumePopup(Gtk.Window):
    width=79;height=134
    def __init__(self,shell,left,backend=None):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.shell=shell;self.assets=self.dialog_assets=shell.assets;self.backend=backend or PulseAudio();self.dragging=False;self.finished=False
        self.set_transient_for(shell);self.set_decorated(False)
        screen=shell.get_screen();self.move(max(0,min(left,screen.get_width()-self.width)),max(0,screen.get_height()-28-self.height))
        prefs=getattr(shell,'audio_preferences',None)
        self.volume=getattr(prefs,'playback_volume',100);self.muted=bool(getattr(shell,'audio_muted',False));self.ready=False
        self.field_sequence={'volume':0,'muted':0};self.updates=None
        self.area=Gtk.DrawingArea();self.area.set_size_request(self.width,self.height);self.add(self.area)
        self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK)
        for signal,handler in (('draw',self.draw),('button-press-event',self.press),('button-release-event',self.release),('motion-notify-event',self.motion)):
            self.area.connect(signal,handler)
        self.connect('realize',lambda *_:self.get_window().set_cursor(shell.cursor_for('arrow')))
        from win95lx.control_panel.display_preferences import install_palette_filter
        install_palette_filter(self,lambda:shell.display_preferences.palette)
        # GTK redirects outside grabbed events to the Window, not its area.
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK|Gdk.EventMask.BUTTON_RELEASE_MASK|Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('button-press-event',self.press);self.connect('button-release-event',self.release);self.connect('motion-notify-event',self.motion)
        self.connect('key-press-event',self.key)
        self.connect('focus-out-event',lambda *_:self.finish(restore_focus=False))
        self.connect('grab-broken-event',lambda *_:self.finish(restore_focus=False))
        self.parent_destroy=shell.connect('destroy',lambda *_:self.finish(restore_focus=False))
        self.connect('destroy',self.destroyed)
        previous=getattr(shell,'_volume_updates',None)
        if previous:previous.close()
        self.updates=PlaybackUpdates(self.backend,GLib.idle_add,self.updated,previous=previous,error_callback=lambda result,owner=weakref.ref(shell):report_closed_update(owner,result))
        shell._volume_updates=self.updates
        self.show_all();self.grab_add();self.present();self.get_window().focus(Gdk.CURRENT_TIME)
    def destroyed(self,*_):
        self.finished=True;self.dragging=False
        if self.has_grab():self.grab_remove()
        handler=getattr(self,'parent_destroy',None)
        if handler and self.shell.handler_is_connected(handler):self.shell.disconnect(handler)
        self.parent_destroy=None
        if self.updates:self.updates.close()
    def updated(self,result):
        if self.finished:return
        if result.endpoint is not None:
            self.ready=True
            if result.error or result.sequence>=self.field_sequence['volume']:self.volume=result.endpoint.percent
            if result.error or result.sequence>=self.field_sequence['muted']:self.muted=result.endpoint.muted
            self.shell.audio_muted=self.muted;self.shell.area.queue_draw()
        self.area.queue_draw()
        if result.error:self.show_error(result.error)

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
        p.text('Mute',25,116,BLACK if self.ready else SHADOW)
        return False
    def finish(self,*,restore_focus=True):
        if self.finished:return False
        self.destroyed();self.destroy()
        if restore_focus and self.shell.get_visible():self.shell.present()
        return False
    def outside(self,event):
        return dismiss_and_replay(event,lambda:self.finish(restore_focus=False))
    def local(self,event):return local_point(self,event)
    def change(self,value):
        if self.finished:return
        value=max(0,min(100,round(value)))
        try:self.field_sequence['volume']=self.updates.submit(volume=value)
        except (RuntimeError,ValueError) as error:self.show_error(error);return
        self.volume=value;self.area.queue_draw()
    def toggle_mute(self):
        # The first read determines the actual mute state; never toggle a guess.
        if self.finished or not self.ready:return
        muted=not self.muted
        try:self.field_sequence['muted']=self.updates.submit(muted=muted)
        except (RuntimeError,ValueError) as error:self.show_error(error);return
        self.muted=muted;self.shell.audio_muted=muted;self.shell.area.queue_draw();self.area.queue_draw()
    def show_error(self,error):
        from win95lx.apps.dialogs import message_box
        self.finish();message_box(self.shell,'Volume Control','The sound device could not be changed. Reopen Multimedia Properties and check the available playback device.',Gtk.MessageType.ERROR)
    def press(self,area,event):
        if self.finished:return True
        x,y=self.local(event)
        if not 0<=x<self.width or not 0<=y<self.height:return self.outside(event)
        if event.button!=1:return self.finish()
        if 26<=x<56 and 24<=y<110:self.dragging=True;self.change(100*(1-(y-34)/69))
        elif 5<=x<72 and 112<=y<132:self.toggle_mute()
        return True
    def release(self,area,event):self.dragging=False;return True
    def motion(self,area,event):
        if self.finished:return True
        if self.dragging:
            x,y=self.local(event);self.change(100*(1-(y-34)/69));return True
        return False
    def key(self,window,event):
        if self.finished:return True
        name=Gdk.keyval_name(event.keyval)
        if name=='Escape'and getattr(event,'state',0)&Gdk.ModifierType.CONTROL_MASK:
            self.finish(restore_focus=False);self.shell.key(self.shell,event);return True
        if name in ('Escape','Return','KP_Enter'):return self.finish()
        if name in ('m','M','space'):self.toggle_mute();return True
        if name in ('Up','Down','Home','End','Page_Up','Page_Down'):
            self.change(100 if name=='Home' else 0 if name=='End' else self.volume+{'Up':2,'Down':-2,'Page_Up':10,'Page_Down':-10}[name]);return True
        return False
