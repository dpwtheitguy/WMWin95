"""One registry for Control Panel routing, icons, shortcuts and acceptance scope."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Applet:
    key:str
    label:str
    native_command:str
    backend:str
    implemented:bool=False

CATALOG=(
    Applet('accessibility','Accessibility Options','control access.cpl','XKB AccessX and session accessibility'),
    Applet('hardware','Add New Hardware','control sysdm.cpl add new hardware','udev device discovery and driver inventory'),
    Applet('addremove','Add/Remove Programs','control appwiz.cpl','dpkg/APT package management'),
    Applet('datetime','Date/Time','control timedate.cpl','system clock and zoneinfo',True),
    Applet('themes','Desktop Themes','control themes.cpl','original Plus themes and session preferences'),
    Applet('display','Display','control desk.cpl','RandR and session appearance',True),
    Applet('fonts','Fonts','control fonts','Fontconfig and per-user font files'),
    Applet('internet','Internet','control inetcpl.cpl','browser preferences, proxy and certificate store'),
    Applet('keyboard','Keyboard','control keyboard','X11 repeat, XKB layouts and GTK caret',True),
    Applet('modems','Modems','control modem.cpl','ModemManager; requires a modem'),
    Applet('mouse','Mouse','control mouse','X11 pointer and original cursor library',True),
    Applet('multimedia','Multimedia','control mmsys.cpl','PulseAudio/PipeWire and ALSA'),
    Applet('network','Network','control netcpl.cpl','NetworkManager'),
    Applet('passwords','Passwords','control password.cpl','PAM and account password tools'),
    Applet('power','Power','control power','DPMS, UPower and logind'),
    Applet('printers','Printers','control printers','CUPS'),
    Applet('regional','Regional Settings','control intl.cpl','per-user formatting and locale',True),
    Applet('sounds','Sounds','control mmsys.cpl @1','sound event mappings and audio playback'),
    Applet('system','System','control sysdm.cpl','procfs, sysfs and system diagnostics',True),
    Applet('users','Users','control user profiles','local accounts and session profiles'),
)
BY_KEY={applet.key:applet for applet in CATALOG}
BY_LABEL={applet.label:applet for applet in CATALOG}

def implemented():return tuple(applet for applet in CATALOG if applet.implemented)
def labels():return tuple(applet.label for applet in implemented())
def targets():return {applet.label:applet.key for applet in implemented()}
def entries():
    return tuple((applet.key if applet.key in ('display','mouse') else 'cpl-'+applet.key,applet.label,applet.key) for applet in implemented())
