#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
test -f /etc/lightdm/lightdm.conf.d/70-win95lx.conf
systemctl restart lightdm
