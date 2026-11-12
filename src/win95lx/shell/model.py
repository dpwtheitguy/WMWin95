"""UI state independent of GTK. Prototype geometry remains unmeasured."""
from dataclasses import dataclass
from pathlib import Path
@dataclass
class Window:
    kind:str
    title:str
    x:int=120
    y:int=80
    width:int=450
    height:int=310
    minimized:bool=False
    restored_bounds: tuple[int, int, int, int] | None = None
class DesktopState:
    def __init__(self):
        self.windows=[];self.start_open=False;self.menu_index=0;self.selection=None;self.dialog=None
    def open(self,kind):
        titles={'computer':'My Computer','control':'Control Panel','display':'Display Properties','system':'System Properties','notepad':'Untitled - Notepad','drive':'(C:)','recycle':'Recycle Bin'}
        existing=next((w for w in self.windows if w.kind==kind),None)
        if existing:self.windows.remove(existing);existing.minimized=False;self.windows.append(existing)
        else:self.windows.append(Window(kind,titles[kind],100+len(self.windows)*20,65+len(self.windows)*18))
        self.start_open=False
    @property
    def active(self):return next((w for w in reversed(self.windows) if not w.minimized),None)
    def close(self):
        if self.dialog:self.dialog=None
        elif self.active:self.windows.remove(self.active)
    def escape(self):self.start_open=False;self.dialog=None
    def cycle(self):
        if self.windows:
            current=self.active
            index=self.windows.index(current) if current else 0
            target=self.windows[(index-1)%len(self.windows)]
            self.windows.remove(target);target.minimized=False;self.windows.append(target)
# Compatibility import for the initial scaffold.
from win95lx.explorer.presentation import DriveView
