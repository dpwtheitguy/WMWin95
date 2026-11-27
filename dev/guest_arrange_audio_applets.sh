#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
export DISPLAY=:0 XAUTHORITY=/run/lightdm/root/:0
python3 - <<'PY'
import ctypes as C,ctypes.util
x=C.CDLL(ctypes.util.find_library('X11'));D=C.c_void_p;W=C.c_ulong
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=D
x.XDefaultRootWindow.argtypes=[D];x.XDefaultRootWindow.restype=W
x.XQueryTree.argtypes=[D,W,C.POINTER(W),C.POINTER(W),C.POINTER(C.POINTER(W)),C.POINTER(C.c_uint)]
x.XFetchName.argtypes=[D,W,C.POINTER(D)];x.XFree.argtypes=[D]
x.XMoveWindow.argtypes=[D,W,C.c_int,C.c_int];x.XSync.argtypes=[D,C.c_int];x.XCloseDisplay.argtypes=[D]
d=x.XOpenDisplay(None)
if not d:raise RuntimeError('Guest display unavailable')
root=x.XDefaultRootWindow(d);r=W();parent=W();children=C.POINTER(W)();count=C.c_uint()
try:
    x.XQueryTree(d,root,C.byref(r),C.byref(parent),C.byref(children),C.byref(count))
    moved=[]
    for i in range(count.value):
        name=D();x.XFetchName(d,children[i],C.byref(name))
        if not name:continue
        title=C.string_at(name).decode(errors='replace');x.XFree(name)
        if title in ('Sounds Properties','Multimedia Properties'):
            left=414 if title=='Sounds Properties' else 18
            x.XMoveWindow(d,children[i],left,60);moved.append(title)
    x.XSync(d,False)
    print('Arranged:',', '.join(moved))
finally:
    if children:x.XFree(children)
    x.XCloseDisplay(d)
PY
