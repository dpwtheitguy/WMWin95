"""Play the privately staged Windows startup sound on guest login."""

from pathlib import Path
import shutil
import subprocess


def play_startup(assets):
    sound = assets / 'startup.wav'
    player = shutil.which('aplay')
    if not player or not sound.is_file():
        return False
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    stamp = Path.home() / '.cache' / 'win95lx' / 'startup-boot-id'
    if stamp.is_file() and stamp.read_text().strip() == boot_id:
        return False
    result = subprocess.run([player, '-q', str(sound)], check=False)
    if result.returncode == 0:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.write_text(boot_id + '\n')
    return False
