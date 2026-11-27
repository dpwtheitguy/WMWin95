"""Nonblocking event playback using applied per-user Windows sound schemes."""
from pathlib import Path
import json,shutil,subprocess
from win95lx.control_panel.sound_preferences import SoundPreferences,sound_path,wave_details

class SoundPlayer:
    def __init__(self):self.process=None
    @property
    def playing(self):return self.process is not None and self.process.poll() is None
    def stop(self):
        if self.playing:
            self.process.terminate()
            try:self.process.wait(timeout=.2)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.process=None
    def play(self,path):
        wave_details(path)
        command=next(([binary,str(path)] if name!='aplay' else [binary,'-q',str(path)] for name in ('pw-play','paplay','aplay') if (binary:=shutil.which(name))),None)
        if command is None:raise RuntimeError('No audio playback service is available.')
        self.stop();self.process=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        return self.process

_player=SoundPlayer()
def preferences():
    try:return SoundPreferences(**json.loads((Path.home()/'.config/win95lx/sounds.json').read_text())).validate()
    except (OSError,ValueError,TypeError):return SoundPreferences()

def play_event(assets,event):
    filename=preferences().events.get(event,'')
    if not filename:return False
    try:_player.play(sound_path(filename,assets));return True
    except (OSError,ValueError,RuntimeError):return False

def play_startup(assets):
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    stamp=Path.home()/'.cache/win95lx/startup-boot-id'
    if stamp.is_file() and stamp.read_text().strip()==boot_id:return False
    if not play_event(assets,'SystemStart'):return False
    # Wait only in the dedicated startup worker. Failed playback retries later.
    process=_player.process
    if process is None:return False
    result=process.wait()
    if result==0:
        stamp.parent.mkdir(parents=True,exist_ok=True);stamp.write_text(boot_id+'\n');return True
    return False


def notify(owner,event):
    """Route semantic events from the shell or a transient native dialog."""
    visited=set()
    while owner is not None and id(owner) not in visited:
        visited.add(id(owner))
        assets=getattr(owner,'dialog_assets',None) or getattr(owner,'assets',None)
        if assets is not None:return play_event(Path(assets),event)
        if hasattr(owner,'get_attach_widget') and owner.get_attach_widget() is not None:owner=owner.get_attach_widget()
        elif hasattr(owner,'get_transient_for'):owner=owner.get_transient_for()
        elif hasattr(owner,'get_toplevel') and owner.get_toplevel() is not owner:owner=owner.get_toplevel()
        else:owner=None
    return False
