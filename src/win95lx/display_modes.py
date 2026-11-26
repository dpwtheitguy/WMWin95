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
LEGACY_MODES = ((640,480),(800,600),(1024,768),(1152,864),(1280,960),(1600,1200))
EXTRA_MODES = ((1280,768),(1280,960),(1400,1050),(1440,960),(1600,1000),
               (1920,1440),(2048,1536),(2160,1440),(2304,1440),(2560,1920),
               (2736,1824),(3000,2000),(3200,1800),(3200,2000),(3840,1600),
               (3840,2400),(4096,2160),(5120,2160),(5120,2880),(6016,3384),
               (7680,2160),(7680,4320))
DISPLAY_MODES = tuple(sorted(set(LEGACY_MODES+MODERN_MODES+EXTRA_MODES),key=lambda m:(m[0]*m[1],*m)))


def connected_outputs(listing):
    return list(re.finditer(r'^(\S+) connected\b([^\n]*)\n((?:[ \t].*\n)*)',listing,re.M))

def mode_size(name):
    match=re.fullmatch(r'(?:Win95LX-)?(\d+)x(\d+)(?:[ip]|_.*)?',name)
    return tuple(map(int,match.groups())) if match else None


def available_modes(listing):
    """Native advertised sizes plus common fallbacks within this server's limit.

    Advertising a fallback does not establish that a physical monitor accepts
    it. Apply must still check the real driver and retain its rollback path.
    """
    limit=re.search(r'maximum (\d+) x (\d+)',listing)
    maximum=tuple(map(int,limit.groups())) if limit else (16384,16384)
    native=set()
    for output in connected_outputs(listing):
        for name in re.findall(r'^\s+(\S+)',output[3],re.M):
            size=mode_size(name)
            if size:native.add(size)
    return tuple(sorted({m for m in set(DISPLAY_MODES)|native
                         if 320<=m[0]<=maximum[0] and 200<=m[1]<=maximum[1]},
                        key=lambda m:(m[0]*m[1],*m)))


def discover_modes():
    try:return available_modes(_run('xrandr','--query'))
    except (OSError,subprocess.SubprocessError):return DISPLAY_MODES


def _run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=8).stdout


def set_resolution(width, height):
    if type(width) is not int or type(height) is not int or width<320 or height<200:
        raise ValueError('Invalid display resolution')
    listing = _run('xrandr', '--query')
    outputs = connected_outputs(listing)
    if not outputs:
        raise ValueError("No connected X11 display")
    selected = next((output for output in outputs if ' primary ' in output[2]), outputs[0])
    connector = selected[1]
    mode_rows = [line.split() for line in selected[3].splitlines() if line.strip()]
    modes = {row[0] for row in mode_rows}
    size = f'{width}x{height}'
    if any(mode_size(row[0])==(width,height) and any('*' in rate for rate in row[1:])
           for row in mode_rows):
        return
    mode = size
    if mode not in modes:
        equivalent=next((row[0] for row in mode_rows if mode_size(row[0])==(width,height)),None)
        if equivalent:mode=equivalent
    if mode not in modes:
        if (width, height) not in available_modes(listing):
            raise ValueError('This resolution exceeds the display limits or is not supported.')
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
