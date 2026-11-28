"""Reversible session saver coordination; never writes lock or Xfconf settings.

All methods performing bus I/O belong on the host's serialized worker. A private
bus connection owns cookies, so process death restores the existing daemon.
"""
from dataclasses import dataclass
from pathlib import Path
import os
import threading
import uuid

SERVICE='org.xfce.ScreenSaver'
PATH='/org/xfce/ScreenSaver'


def same_display(pid,display):
    try:
        values=dict(item.split(b'=',1)for item in (Path('/proc')/str(pid)/'environ').read_bytes().split(b'\0')if b'='in item)
        actual=values.get(b'DISPLAY',b'').decode(errors='replace')
        return actual.split('.')[0]==display.split('.')[0]
    except OSError:raise RuntimeError('The current screen saver service could not be identified.') from None


def same_display_daemon(display):
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:
            if process.stat().st_uid!=os.getuid():continue
            if(process/'comm').read_text().strip()!='xfce4-screensav':continue
            if(process/'exe').resolve().name!='xfce4-screensaver':continue
            try:
                if same_display(process.name,display):return True
            except RuntimeError:return True
        except OSError:continue
    return False


class SessionBus:
    def __init__(self,address):
        from gi.repository import Gio,GLib
        self.Gio,self.GLib=Gio,GLib
        self.connection=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT|Gio.DBusConnectionFlags.MESSAGE_BUS_CONNECTION,None,None)
        self.connection.set_exit_on_close(False)
    def call(self,destination,path,interface,method,signature=None,values=()):
        parameters=self.GLib.Variant(signature,values)if signature else None
        return self.connection.call_sync(destination,path,interface,method,parameters,None,self.Gio.DBusCallFlags.NO_AUTO_START,1500,None).unpack()
    def owner(self):
        present=self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','NameHasOwner','(s)',(SERVICE,))[0]
        if not present:return None
        unique=self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetNameOwner','(s)',(SERVICE,))[0]
        pid=self.call('org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','GetConnectionUnixProcessID','(s)',(unique,))[0]
        return unique,pid
    def lock_policy(self):
        values=[]
        for name in ('/lock/enabled','/lock/saver-activation/enabled'):
            try:value=self.call('org.xfce.Xfconf','/org/xfce/Xfconf','org.xfce.Xfconf','GetProperty','(ss)',('xfce4-screensaver',name))[0]
            except Exception as error:
                # Documented4.18 defaults are TRUE. Unknown/read-only policy is
                # conservative: never acquire an idle inhibitor in that case.
                if 'PropertyNotFound'in str(error) or 'does not exist'in str(error):value=True
                else:raise
            if type(value)is not bool:raise ValueError('Invalid screen locking policy.')
            values.append(value)
        return all(values)
    def active(self,owner):return bool(self.call(owner,PATH,SERVICE,'GetActive')[0])
    def inhibitors(self,owner):return list(self.call(owner,PATH,SERVICE,'GetInhibitors')[0])
    def acquire(self,owner,mode,reason):
        value=self.call(owner,PATH,SERVICE,mode,'(ss)',('Win95LX',reason))[0]
        if type(value)is not int or not 0<value<2**32:raise ValueError('Invalid screen saver ownership cookie.')
        return value
    def release(self,owner,mode,cookie):self.call(owner,PATH,SERVICE,'Un'+mode,'(u)',(cookie,))
    def close(self):self.connection.close_sync(None)


@dataclass(frozen=True)
class OwnershipState:
    ready:bool=False
    active:bool=False
    external_inhibited:bool=False
    mode:str=''
    error:str=''


class SaverOwnership:
    """Inhibit visuals without idle locking; throttle with lock policy intact.

    In lock-preserving mode the daemon's activation/lock schedule wins: Wine is
    stopped whenever the daemon is active. Manual/suspend Lock always bypasses
    our Inhibit cookie. Configuration is neither changed nor restored over edits.
    """
    def __init__(self,*,address=None,display=None,bus_factory=SessionBus,display_check=same_display,daemon_check=same_display_daemon):
        self.address=os.environ.get('DBUS_SESSION_BUS_ADDRESS')if address is None else address
        self.display=os.environ.get('DISPLAY','')if display is None else display
        self.bus_factory=bus_factory;self.display_check=display_check;self.daemon_check=daemon_check
        self.bus=None;self.owner=None;self.cookie=None;self.mode='';self.closed=False;self.lock=threading.RLock()
        self.reason='Win95LX desktop visuals '+uuid.uuid4().hex
        self.state=OwnershipState()
    def _release(self):
        if self.bus and self.cookie is not None:
            try:self.bus.release(self.owner,self.mode,self.cookie)
            finally:self.cookie=None;self.mode='';self.owner=None
    def refresh(self):
        with self.lock:
            if self.closed:return self.state
            try:
                if not self.address:
                    if self.daemon_check(self.display):raise RuntimeError('The screen saver session bus is unavailable.')
                    self.state=OwnershipState(ready=True);return self.state
                if self.bus is None:self.bus=self.bus_factory(self.address)
                owner=self.bus.owner()
                if owner is None or not self.display_check(owner[1],self.display):
                    self._release();self.state=OwnershipState(ready=True);return self.state
                unique=owner[0]
                if self.owner and unique!=self.owner:
                    # Release only against the exact previous unique owner;
                    # never send its cookie to a newly started daemon.
                    try:self._release()
                    except Exception:self.cookie=None;self.mode='';self.owner=None
                try:locking=self.bus.lock_policy()
                except Exception:locking=True  # Unknown policy must never inhibit automatic locking.
                desired='Throttle'if locking else'Inhibit'
                if self.cookie is None or desired!=self.mode:
                    # Returning automatic locking takes precedence over visuals.
                    if self.mode=='Inhibit'and desired=='Throttle':self._release()
                    old=(self.owner,self.mode,self.cookie)
                    cookie=self.bus.acquire(unique,desired,self.reason)
                    self.owner,self.mode,self.cookie=unique,desired,cookie
                    if old[2]is not None:self.bus.release(old[0],old[1],old[2])
                active=self.bus.active(unique)
                external=any(('Reason="'+self.reason+'";')not in row for row in self.bus.inhibitors(unique))
                self.state=OwnershipState(True,active,external,self.mode)
            except Exception:
                # Closing our unique connection also releases a partial acquire
                # even if the explicit release failed. Keep the daemon intact.
                try:
                    if self.bus:self.bus.close()
                except Exception:pass
                self.bus=None;self.cookie=None;self.owner=None;self.mode=''
                self.state=OwnershipState(error='The current screen saver service is unavailable. Automatic screen saving has been paused.')
            return self.state
    def close(self):
        with self.lock:
            if self.closed:return
            self.closed=True
            try:self._release()
            finally:
                if self.bus:self.bus.close()
                self.bus=None;self.state=OwnershipState()
