#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test "$(hostname)" = win95lx-dev
export DISPLAY=:0 XAUTHORITY=/run/lightdm/root/:0
xwininfo -root -tree | awk '/Win95LX|Notepad|WordPad|Save As|Edit Pattern|Display Properties/'
