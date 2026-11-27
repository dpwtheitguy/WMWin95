"""Shared event translation for native-looking GTK popup windows."""
from gi.repository import Gtk,Gdk


def local_point(window,event):
    if hasattr(event,'x_root'):
        x,y=window.get_position()
        return event.x_root-x,event.y_root-y
    return event.x,event.y


def dismiss_and_replay(event,dismiss):
    """Release a popup's grab, then deliver the initiating outside click once."""
    copied=event.copy() if hasattr(event,'copy') else None
    dismiss()
    if copied is not None:
        pointer=Gdk.Display.get_default().get_default_seat().get_pointer()
        window,x,y=pointer.get_window_at_position()
        if window and not window.is_destroyed():
            copied.window=window;copied.x=x;copied.y=y
            Gtk.main_do_event(copied)
    return True
