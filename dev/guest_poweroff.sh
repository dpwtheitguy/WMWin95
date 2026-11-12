#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test "$(hostname)" = win95lx-dev
systemctl poweroff
