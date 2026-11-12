"""Registered prototype applets. Unimplemented Linux settings are never exposed."""
from win95lx.shell.widgets import TEAL

def display(p, win, button, resolution, error=False):
    x, y, w, h = win.x, win.y, win.width, win.height
    p.text('Settings', x+18, y+38)
    p.bevel(x+80, y+65, 280, 145, True)
    p.fill(x+84, y+69, 272, 137, TEAL)
    p.text('Screen area', x+20, y+218)
    button(p, '<', x+20, y+237, 22, 19, ('resolution-step', -1))
    p.text(f'{resolution[0]} by {resolution[1]} pixels', x+51, y+240)
    button(p, '>', x+183, y+237, 22, 19, ('resolution-step', 1))
    if error:
        p.text('This display could not switch to that mode.', x+20, y+263)
    button(p, 'OK', x+w-174, y+h-33, 75, 23, ('resolution-apply', win))
    button(p, 'Cancel', x+w-91, y+h-33, 75, 23, ('close', win))

def system(p,win,button):
    x,y,w,h=win.x,win.y,win.width,win.height
    p.text('System',x+18,y+35);p.text('Win95LX',x+130,y+68,bold=True);p.text('Development Edition',x+130,y+90);p.text('Version 0.0.1',x+130,y+112);p.text('Personal desktop environment',x+24,y+170);button(p,'OK',x+w-91,y+h-33,75,23,('close',win))
APPLETS={'display':display,'system':system}
