"""UI state independent of GTK. Prototype geometry remains unmeasured."""
from dataclasses import dataclass,field
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
    folder: int | str | Path | None = None
    browser: object | None = None
    toolbar: bool = True
    address_bar: bool = True
    web_view: bool = True
    focus_item: str | None = None
    namespace_view: str = "large"
    namespace_scroll: tuple = (0,0)
    namespace_auto: bool = True
    namespace_positions: tuple = ()
    namespace_layout: object | None = None
    namespace_viewport: tuple = (0,0,0,0)
    info_scroll: int = 0
    info_scroll_max: int = 0
    back_history: list = field(default_factory=list)
    forward_history: list = field(default_factory=list)
class DesktopState:
    def __init__(self):
        self.windows=[];self.start_open=False;self.menu_index=0;self.selection=None;self.dialog=None
    def open(self,kind,folder=None):
        titles={'printers':'Printers','computer':'My Computer','control':'Control Panel','display':'Display Properties','system':'System Properties','notepad':'Untitled - Notepad','drive':'(C:)','recycle':'Recycle Bin','start-folder':'Start Menu'}
        existing=next((w for w in self.windows if w.kind==kind and w.folder==folder),None)
        if existing:self.windows.remove(existing);existing.minimized=False;self.windows.append(existing)
        else:
            window = Window(kind, titles[kind], 100+len(self.windows)*20, 65+len(self.windows)*18,
                            folder=folder)
            if kind == 'computer':
                window.width, window.height = 512, 461
            self.windows.append(window)
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
