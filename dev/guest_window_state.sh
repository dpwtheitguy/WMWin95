#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
export DISPLAY=:0 XAUTHORITY=/run/lightdm/root/:0
xwininfo -root -tree | awk '/Win95LX|Notepad|WordPad|Save As|Edit Pattern|Display Properties/'
