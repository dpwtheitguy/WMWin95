"""Mouse settings and transactional X11 application, independent of the UI."""
from dataclasses import dataclass,asdict,field
import ctypes,json
from pathlib import Path

SCHEMES=('(None)','3D Pointers','Windows Standard (large)','Windows Standard (extra large)','Animated Hourglasses','Windows Standard')
ROLES=(('arrow','Normal Select'),('help','Help Select'),('busy','Working In Background'),
       ('wait','Busy'),('cross','Precision Select'),('beam','Text Select'),('pen','Handwriting'),
       ('no','Unavailable'),('size4','Vertical Resize'),('size3','Horizontal Resize'),
       ('size2','Diagonal Resize 1'),('size1','Diagonal Resize 2'),('move','Move'),('up','Alternate Select'))

@dataclass(frozen=True)
class MousePreferences:
    left_handed:bool=False
    double_click_ms:int=500
    speed:int=5
    scheme:str=SCHEMES[0]
    overrides:dict=field(default_factory=dict)

    def validate(self):
        if type(self.left_handed) is not bool:raise ValueError('Invalid button configuration.')
        if type(self.double_click_ms) is not int or not 100<=self.double_click_ms<=900:raise ValueError('Invalid double-click speed.')
        if type(self.speed) is not int or not 1<=self.speed<=10:raise ValueError('Invalid pointer speed.')
        if not isinstance(self.scheme,str) or not (self.scheme in SCHEMES or self.scheme.startswith('Plus! / ') and len(self.scheme)<100):raise ValueError('Unknown pointer scheme.')
        if not isinstance(self.overrides,dict) or any(role not in dict(ROLES) or not isinstance(path,str) for role,path in self.overrides.items()):raise ValueError('Invalid pointer customization.')
        return self

    @classmethod
    def load(cls,path):
        try:return cls(**json.loads(path.read_text())).validate()
        except (OSError,ValueError,TypeError):return cls()

    def save(self,path):
        self.validate();path.parent.mkdir(parents=True,exist_ok=True)
        temp=path.with_suffix('.tmp');temp.write_text(json.dumps(asdict(self),indent=2)+'\n');temp.replace(path)

    def pointer(self,assets,role):
        if role in self.overrides:return Path(self.overrides[role])
        from win95lx.assets.cursors import PointerLibrary
        return assets/PointerLibrary(assets).frame(self.scheme,role)['file']

class X11Mouse:
    """Use the connected X server; input settings need no root privileges."""
    def __init__(self):
        self.lib=ctypes.CDLL('libX11.so.6')
        self.lib.XOpenDisplay.argtypes=[ctypes.c_char_p];self.lib.XOpenDisplay.restype=ctypes.c_void_p
        self.display=self.lib.XOpenDisplay(None)
        if not self.display:raise RuntimeError('Mouse settings require an X11 session.')
        p=ctypes.c_void_p;i=ctypes.c_int;u=ctypes.c_ubyte
        self.lib.XGetPointerMapping.argtypes=[p,ctypes.POINTER(u),i]
        self.lib.XSetPointerMapping.argtypes=[p,ctypes.POINTER(u),i]
        self.lib.XGetPointerControl.argtypes=[p,ctypes.POINTER(i),ctypes.POINTER(i),ctypes.POINTER(i)]
        self.lib.XChangePointerControl.argtypes=[p,i,i,i,i,i]
        self.lib.XSync.argtypes=[p,i];self.lib.XCloseDisplay.argtypes=[p]
    def snapshot(self):
        data=(ctypes.c_ubyte*256)();count=self.lib.XGetPointerMapping(self.display,data,256)
        n,d,t=ctypes.c_int(),ctypes.c_int(),ctypes.c_int()
        self.lib.XGetPointerControl(self.display,ctypes.byref(n),ctypes.byref(d),ctypes.byref(t))
        return tuple(data[:count]),n.value,d.value,t.value
    def restore(self,state):
        buttons,n,d,t=state;data=(ctypes.c_ubyte*len(buttons))(*buttons)
        status=self.lib.XSetPointerMapping(self.display,data,len(buttons))
        if status:raise RuntimeError('Release all mouse buttons and try again.')
        self.lib.XChangePointerControl(self.display,1,1,n,d,t);self.lib.XSync(self.display,0)
    def apply(self,prefs):
        prefs.validate();buttons,n,d,t=self.snapshot();buttons=list(buttons)
        # Change logical buttons 1 and 3 without moving wheel/side buttons.
        if 1 not in buttons or 3 not in buttons:raise RuntimeError('This pointer has no left/right button mapping.')
        a,b=buttons.index(1),buttons.index(3)
        if (a>b)!=prefs.left_handed:buttons[a],buttons[b]=buttons[b],buttons[a]
        self.restore((buttons,prefs.speed,5,t))
        actual=self.snapshot()
        if actual[0]!=tuple(buttons) or actual[1]*5!=prefs.speed*actual[2]:raise RuntimeError('The X server did not accept the requested mouse settings.')
    def preferences(self):
        buttons,n,d,t=self.snapshot()
        return MousePreferences(left_handed=buttons.index(1)>buttons.index(3),speed=max(1,min(10,round(n/max(1,d)*5))))
    def close(self):
        if self.display:self.lib.XCloseDisplay(self.display);self.display=None

class MouseController:
    def __init__(self,path,backend,apply_session):
        self.path,self.backend,self.apply_session=path,backend,apply_session
        self.applied=backend.preferences() if isinstance(backend,X11Mouse) and not path.exists() else MousePreferences.load(path);self.pending=self.applied
    def cancel(self):self.pending=self.applied
    def apply(self):
        self.pending.validate();previous=self.backend.snapshot()
        try:
            self.backend.apply(self.pending);self.apply_session(self.pending);self.pending.save(self.path)
        except Exception:
            self.backend.restore(previous);self.apply_session(self.applied);raise
        self.applied=self.pending
