"""Recognize the installed development guest independently of its computer name."""
import os,re,stat
from pathlib import Path
MARKER=Path('/etc/win95lx/guest-id')
MACHINE_ID=Path('/etc/machine-id')
VENDOR=Path('/sys/class/dmi/id/sys_vendor')

def is_development_guest():
    try:
        if VENDOR.read_text().strip()!='QEMU':return False
        if MARKER.is_symlink():return False
        if MARKER.exists():
            info=MARKER.stat();identity=MACHINE_ID.read_text().strip()
            return (stat.S_ISREG(info.st_mode) and info.st_uid==0 and not info.st_mode&0o022
                    and bool(re.fullmatch(r'[0-9a-f]{32}',identity))
                    and MARKER.read_text().strip()==identity)
        # Bootstrap compatibility for an existing guest before marker install.
        return os.uname().nodename=='win95lx-dev'
    except (OSError,UnicodeError):return False
