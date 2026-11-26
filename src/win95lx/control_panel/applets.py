"""Registered prototype applets. Unimplemented Linux settings are never exposed."""
def system(p,win,button):
    x,y,w,h=win.x,win.y,win.width,win.height
    p.text('System',x+18,y+35);p.text('Win95LX',x+130,y+68,bold=True);p.text('Development Edition',x+130,y+90);p.text('Version 0.0.1',x+130,y+112);p.text('Personal desktop environment',x+24,y+170);button(p,'OK',x+w-91,y+h-33,75,23,('close',win))
APPLETS={'system':system}
