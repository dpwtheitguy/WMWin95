"""Real X11 keyboard repeat/layout and session caret preferences."""
from dataclasses import dataclass
import re
import subprocess
import ctypes
from pathlib import Path

LAYOUTS=(('English (United States)','us'),('English (United Kingdom)','gb'),
         ('French (France)','fr'),('German (Germany)','de'),('Spanish (Spain)','es'),
         ('Italian (Italy)','it'),('Portuguese (Brazil)','br'),('Swedish','se'),
         ('Norwegian','no'),('Danish','dk'),('Finnish','fi'),('Dutch','nl'),
         ('Polish','pl'),('Czech','cz'),('Turkish','tr'),('Japanese','jp'))
LAYOUT_NAMES=dict((code,label) for label,code in LAYOUTS)
LAYOUT_DESCRIPTIONS={'us':'United States 101','gb':'United Kingdom','fr':'French','de':'German','es':'Spanish','it':'Italian','br':'Brazilian','se':'Swedish','no':'Norwegian','dk':'Danish','fi':'Finnish','nl':'Dutch','pl':'Polish','cz':'Czech','tr':'Turkish','jp':'Japanese'}

def available_layouts(path=Path('/usr/share/X11/xkb/rules/base.lst')):
    rows=list(LAYOUTS);seen=set(LAYOUT_NAMES);section=''
    try:lines=path.read_text().splitlines()
    except OSError:return tuple(rows)
    for line in lines:
        if line.startswith('!'):section=line[1:].strip();continue
        if section!='layout' or not line.strip():continue
        parts=line.split(None,1)
        if len(parts)==2 and re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',parts[0]) and parts[0] not in seen:
            rows.append((parts[1],parts[0]));seen.add(parts[0])
    return tuple(sorted(rows,key=lambda row:row[0].casefold()))

def apply_session(settings,prefs):
    settings.set_property('gtk-cursor-blink',prefs.blink_ms!=0)
    if prefs.blink_ms:settings.set_property('gtk-cursor-blink-time',prefs.blink_ms*2)

@dataclass(frozen=True)
class KeyboardPreferences:
    delay_ms:int=250
    rate:int=16
    blink_ms:int=530
    layouts:tuple=('us',)
    switch:str='none'
    variants:tuple=('',)
    options:str=''
    model:str='pc105'
    rules:str='evdev'
    indicator:bool=False

    def __post_init__(self):
        if isinstance(self.layouts,list):object.__setattr__(self,'layouts',tuple(self.layouts))
        if isinstance(self.variants,list):object.__setattr__(self,'variants',tuple(self.variants))

    def validate(self):
        for field,low,high in (('delay_ms',1,10000),('rate',1,1000),('blink_ms',0,1200)):
            value=getattr(self,field)
            if type(value) is not int or not low<=value<=high:raise ValueError('Invalid keyboard '+field)
        if not isinstance(self.layouts,(tuple,list)) or not 1<=len(self.layouts)<=4 or len(set(self.layouts))!=len(self.layouts):raise ValueError('Choose one to four different keyboard layouts.')
        if any(not isinstance(code,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,40}',code) for code in self.layouts):raise ValueError('Invalid keyboard layout.')
        if self.switch not in ('none','alt_shift','ctrl_shift'):raise ValueError('Unknown language shortcut.')
        if type(self.indicator) is not bool:raise ValueError('Invalid language indicator preference.')
        if not isinstance(self.variants,(tuple,list)) or len(self.variants)!=len(self.layouts):raise ValueError('Invalid layout variants.')
        for item in (*self.variants,self.options,self.model,self.rules):
            if not isinstance(item,str) or not re.fullmatch(r'[a-zA-Z0-9_:+,.-]{0,256}',item):raise ValueError('Invalid keyboard configuration.')
        return self

    @classmethod
    def from_mapping(cls,value):
        return cls(**{**value,'layouts':tuple(value['layouts']),'variants':tuple(value['variants'])}).validate()

    def position(self,field):
        if field=='delay_ms':return max(0,min(3,round((1000-self.delay_ms)/250))),3
        if field=='rate':return max(0,min(31,self.rate-1)),31
        return (10 if self.blink_ms==0 else round((1200-self.blink_ms)/100)),10

    def slider(self,field,index):
        from dataclasses import replace
        maximum=self.position(field)[1];index=max(0,min(maximum,index))
        value={'delay_ms':1000-index*250,'rate':index+1,'blink_ms':1200-index*100}[field]
        return replace(self,**{field:value}).validate()

class X11Keyboard:
    def __init__(self,runner=None):self.run=runner or self._run
    @staticmethod
    def _run(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=8).stdout

    def snapshot(self):
        state=self.run('xset','q')
        repeat=re.search(r'auto repeat delay:\s*(\d+)\s+repeat rate:\s*(\d+)',state)
        if not repeat:raise RuntimeError('The X server did not report keyboard repeat settings.')
        layout=self.run('setxkbmap','-query')
        settings={key:value.strip() for key,value in re.findall(r'^(\w+):\s*(.*)$',layout,re.M)}
        enabled=re.search(r'auto repeat:\s*(on|off)',state)
        settings['_repeat_enabled']=enabled[1] if enabled else 'on'
        return (int(repeat[1]),int(repeat[2]),settings)

    def preferences(self):
        delay,rate,state=self.snapshot();layouts=tuple(state.get('layout','us').split(','));variants=tuple(state.get('variant','').split(','))
        variants=(variants+('',)*len(layouts))[:len(layouts)]
        options=state.get('options','');switch='alt_shift' if 'grp:alt_shift_toggle' in options else 'ctrl_shift' if 'grp:ctrl_shift_toggle' in options else 'none'
        # Retain server-specific options and models; an unrelated blink edit
        # must not silently reset them or enable globally disabled repeat.
        return KeyboardPreferences(delay,rate,530,layouts,switch,variants,options,state.get('model','pc105'),state.get('rules','evdev')).validate()

    def restore(self,state):
        delay,rate,settings=state
        self.run('xset','r','rate',str(delay),str(rate))
        self._layout(settings)
        if settings.get('_repeat_enabled')=='off':self.run('xset','-r')

    def _layout(self,settings):
        args=['setxkbmap','-rules',settings.get('rules','evdev'),'-model',settings.get('model','pc105'),'-layout',settings.get('layout','us'),'-variant',settings.get('variant',''),'-option','']
        if settings.get('options'):args+=['-option',settings['options']]
        self.run(*args)

    def apply(self,prefs):
        prefs.validate();old=self.snapshot()
        if old[:2]!=(prefs.delay_ms,prefs.rate):self.run('xset','r','rate',str(prefs.delay_ms),str(prefs.rate))
        if old[2].get('_repeat_enabled')=='off':self.run('xset','-r')
        options=[part for part in prefs.options.split(',') if part and part not in ('grp:alt_shift_toggle','grp:ctrl_shift_toggle')]
        if prefs.switch!='none':options.append('grp:'+prefs.switch+'_toggle')
        settings={'rules':prefs.rules,'model':prefs.model,'layout':','.join(prefs.layouts),'variant':','.join(prefs.variants),'options':','.join(options)}
        current={key:old[2].get(key,'') for key in settings}
        if current!=settings:self._layout(settings)
        actual=self.snapshot()
        if actual[:2]!=(prefs.delay_ms,prefs.rate):raise RuntimeError('The X server did not accept the repeat settings.')
        if actual[2].get('layout','us')!=settings['layout']:raise RuntimeError('The X server did not accept the keyboard layouts.')

class KeyboardGroups:
    """Read and switch the actual XKB group for the language tray indicator."""
    class State(ctypes.Structure):
        _fields_=[('group',ctypes.c_ubyte),('locked_group',ctypes.c_ubyte),('base_group',ctypes.c_ushort),('latched_group',ctypes.c_ushort),
                  *[(name,ctypes.c_ubyte) for name in ('mods','base_mods','latched_mods','locked_mods','compat_state','grab_mods','compat_grab_mods','lookup_mods','compat_lookup_mods')],('ptr_buttons',ctypes.c_ushort)]
    def __init__(self):
        self.lib=ctypes.CDLL('libX11.so.6');self.lib.XOpenDisplay.argtypes=[ctypes.c_char_p];self.lib.XOpenDisplay.restype=ctypes.c_void_p
        self.display=self.lib.XOpenDisplay(None)
        if not self.display:raise RuntimeError('Language switching requires an X11 session.')
        self.lib.XkbGetState.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.POINTER(self.State)]
        self.lib.XkbLockGroup.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint]
        self.lib.XSync.argtypes=[ctypes.c_void_p,ctypes.c_int];self.lib.XCloseDisplay.argtypes=[ctypes.c_void_p]
    def current(self):
        state=self.State()
        if self.lib.XkbGetState(self.display,0x100,ctypes.byref(state))!=0:raise RuntimeError('The X server did not report the active keyboard language.')
        return state.group
    def select(self,index):
        if type(index) is not int or not 0<=index<4:raise ValueError('Invalid keyboard group.')
        if not self.lib.XkbLockGroup(self.display,0x100,index):raise RuntimeError('The X server did not accept the keyboard language.')
        self.lib.XSync(self.display,0)
        if self.current()!=index:raise RuntimeError('The keyboard language did not change.')
    def close(self):
        if self.display:self.lib.XCloseDisplay(self.display);self.display=None
