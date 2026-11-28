"""Saver selection and idle lifecycle, independent of Wine and GTK.

The desktop supplies measured idle seconds. Preview/configuration sessions never
enter this scheduler, and a failed launch cannot retry on every timer tick.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScreenSaverPreferences:
    saver: str = ''
    wait_minutes: int = 10

    def validate(self):
        if not isinstance(self.saver,str) or len(self.saver)>160 or any(ord(c)<32 for c in self.saver):
            raise ValueError('Choose a screen saver from the installed catalog.')
        if type(self.wait_minutes) is not int or not 1<=self.wait_minutes<=60:
            raise ValueError('The wait must be between 1 and 60 minutes.')
        return self


class ScreenSaverIdle:
    """At most one owned fullscreen process per uninterrupted idle period.

    Run all methods on one serialized worker: runtime cleanup can block. Give
    this scheduler its own runtime instance; configuration and preview have
    separate owners and must never be stopped by desktop activity here.
    """
    def __init__(self, runtime, preferences=None, on_error=lambda error:None):
        self.runtime=runtime
        self.preferences=(preferences or ScreenSaverPreferences()).validate()
        self.on_error=on_error
        self.process=None
        self.attempted=False
        self.closed=False
        self.last_idle=None

    def configure(self,value):
        value.validate()
        self.stop()
        self.preferences=value
        self.attempted=False
        self.last_idle=None

    def stop(self):
        if self.process is not None:
            try:self.runtime.stop()
            finally:self.process=None

    def tick(self,idle_seconds,*,inhibited=False):
        if self.closed:return
        if isinstance(idle_seconds,bool) or not isinstance(idle_seconds,(int,float)) or not 0<=idle_seconds<float('inf'):
            raise ValueError('Invalid measured idle time.')
        activity=self.last_idle is not None and idle_seconds<self.last_idle
        self.last_idle=idle_seconds
        if activity:
            self.stop()
            self.attempted=False
        if self.process is not None and self.process.poll() is not None:
            self.stop()
        if inhibited:
            self.stop()
            return
        if self.process is not None or self.attempted or not self.preferences.saver:return
        if idle_seconds<self.preferences.wait_minutes*60:return
        self.attempted=True
        try:self.process=self.runtime.launch(self.preferences.saver,mode='fullscreen')
        except Exception as error:self.on_error(error)

    def close(self):
        self.closed=True
        self.stop()
