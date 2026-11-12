#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test "$(hostname)" = win95lx-dev
test -f /etc/lightdm/lightdm.conf.d/70-win95lx.conf
systemctl restart lightdm
