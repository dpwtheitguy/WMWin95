"""Select X11 display modes while keeping the shell's artwork at native pixels."""
import argparse
import re
import shlex
import subprocess
from pathlib import Path

# Common desktop and laptop sizes plus ultrawide and high-resolution panels.
MODERN_MODES = (
    (1280, 720), (1280, 800), (1280, 1024), (1360, 768), (1366, 768),
    (1440, 900), (1536, 864), (1600, 900), (1680, 1050), (1920, 1080),
    (1920, 1200), (2048, 1152), (2256, 1504), (2560, 1080), (2560, 1440),
    (2560, 1600), (2880, 1800), (3440, 1440), (3840, 2160), (5120, 1440),
)
REFERENCE_MODE = (800, 600)
DISPLAY_MODES = (REFERENCE_MODE,) + tuple(sorted(MODERN_MODES, key=lambda mode: mode[0]*mode[1]))


def _run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=8).stdout


def set_resolution(width, height):
    if (width, height) not in DISPLAY_MODES:
        raise ValueError("Unknown display resolution")
    listing = _run('xrandr', '--query')
    outputs = list(re.finditer(r'^(\S+) connected\b([^\n]*)\n((?:[ \t].*\n)*)', listing, re.M))
    if not outputs:
        raise ValueError("No connected X11 display")
    selected = next((output for output in outputs if ' primary ' in output[2]), outputs[0])
    connector = selected[1]
    modes = {line.split()[0] for line in selected[3].splitlines() if line.strip()}
    size = f'{width}x{height}'
    mode = size
    if mode not in modes:
        mode = f'Win95LX-{size}'
        if mode not in modes:
            modeline = next(line for line in _run('cvt', '-r', str(width), str(height), '60').splitlines()
                            if line.startswith('Modeline '))
            timings = shlex.split(modeline)[2:]
            # CVT rounds the active width to eight pixels. Preserve the exact
            # requested width and keep the generated blanking intervals.
            padding = width - int(timings[1])
            if padding:
                timings[0] = f'{float(timings[0]) * (int(timings[4]) + padding) / int(timings[4]):.3f}'
                for index in range(1, 5):
                    timings[index] = str(int(timings[index]) + padding)
            try:
                _run('xrandr', '--newmode', mode, *timings)
            except subprocess.CalledProcessError as error:
                if 'BadName' not in error.stderr:
                    raise
            _run('xrandr', '--addmode', connector, mode)
    _run('xrandr', '--output', connector, '--mode', mode)


def remember_resolution(width, height):
    path = Path.home() / '.config' / 'win95lx' / 'resolution'
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(f'{width}x{height}\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('resolution', metavar='WIDTHxHEIGHT')
    args = parser.parse_args()
    try:
        set_resolution(*map(int, args.resolution.lower().split('x')))
    except (OSError, subprocess.SubprocessError, ValueError, TypeError, StopIteration) as error:
        parser.exit(1, f'Display mode {args.resolution} could not be set: {error}\n')


if __name__ == '__main__':
    main()
