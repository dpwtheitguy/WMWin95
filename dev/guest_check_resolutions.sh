#!/bin/sh
# Exercise actual guest RandR modes, then restore the original resolution.
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
export DISPLAY=:0 XAUTHORITY=/run/lightdm/root/:0
release=$(readlink -f /opt/win95lx/current)
export PYTHONPATH="$release/src"
python3 - <<'PY'
import json,re,subprocess,time
from pathlib import Path
from win95lx.display_modes import available_modes,set_resolution
listing=subprocess.check_output(['xrandr','--query'],text=True)
m=re.search(r'current (\d+) x (\d+)',listing);original=tuple(map(int,m.groups()))
modes=available_modes(listing);results=[]
try:
    for width,height in modes:
        start=time.monotonic()
        try:
            set_resolution(width,height);time.sleep(.15)
            actual=subprocess.check_output(['xrandr','--query'],text=True)
            current=tuple(map(int,re.search(r'current (\d+) x (\d+)',actual).groups()))
            if current!=(width,height):raise RuntimeError(f'Driver returned {current}')
            results.append({'mode':[width,height],'driver_applied':True,'elapsed_seconds':round(time.monotonic()-start,3)})
        except Exception as error:results.append({'mode':[width,height],'driver_applied':False,'error':str(error)})
        print(json.dumps(results[-1]),flush=True)
finally:
    set_resolution(*original)
    Path('/home/developer/resolution-driver-report.json').write_text(json.dumps({'original_mode':original,'results':results,'restored':True,'scope':'Actual RandR timing application/readback. Does not establish host viewer/pointer or every control state.'},indent=2)+'\n')
PY
