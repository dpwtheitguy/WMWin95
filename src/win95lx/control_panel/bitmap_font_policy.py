"""Per-file Fontconfig acceptance for personally installed legacy bitmap fonts."""
import os,tempfile
from pathlib import Path
from xml.sax.saxutils import escape
BITMAP_EXTENSIONS=frozenset(('.fon','.fnt','.bdf','.pcf'))

def policy_xml(paths):
    patterns=''.join('<pattern><patelt name="file"><string>'+escape(str(path))+'</string></patelt></pattern>' for path in sorted(paths,key=str))
    return ('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">\n'
            '<!-- Managed by Win95LX Fonts; only owned personal font files. -->\n'
            '<fontconfig><selectfont><acceptfont>'+patterns+'</acceptfont></selectfont></fontconfig>\n').encode()

class BitmapFontPolicy:
    def __init__(self,home,root):self.home=Path(home);self.root=Path(root);self.path=self.home/'.config/fontconfig/conf.d/70-win95lx-bitmap-fonts.conf'
    def paths(self,ledger):return tuple(self.root/name for name in ledger if Path(name).suffix.casefold() in BITMAP_EXTENSIONS)
    def check(self):
        if self.path.is_symlink() or not self.path.resolve().is_relative_to(self.home):raise PermissionError('The bitmap font configuration must remain inside your user folder.')
    def write(self,data):
        self.check();self.path.parent.mkdir(parents=True,exist_ok=True);fd,temp=tempfile.mkstemp(prefix='.win95lx-fonts-',dir=self.path.parent)
        try:
            with os.fdopen(fd,'wb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            os.replace(temp,self.path)
        finally:Path(temp).unlink(missing_ok=True)
    def update(self,previous,updated):
        old_paths,new_paths=self.paths(previous),self.paths(updated)
        if old_paths==new_paths:return None
        self.check();before=self.path.read_bytes() if self.path.exists() else None
        if before is not None and before!=policy_xml(old_paths):raise PermissionError('The bitmap font configuration changed outside Fonts. No settings were replaced.')
        after=policy_xml(new_paths);self.write(after)
        return before,after
    def restore(self,state):
        if state is None:return
        before,after=state;self.check()
        if not self.path.exists() or self.path.read_bytes()!=after:raise RuntimeError('The font configuration changed during the operation and was not overwritten.')
        if before is None:self.path.unlink()
        else:self.write(before)
