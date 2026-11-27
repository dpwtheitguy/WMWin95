#!/bin/sh
# Explicitly run only when reverting the guest customization; preserves user data.
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
rm -f /etc/lightdm/lightdm.conf.d/70-win95lx.conf
rm -f /usr/share/xsessions/win95lx.desktop
rm -f /etc/X11/xorg.conf.d/70-win95lx-cursor.conf
printf '%s\n' 'Custom session and automatic login removed. User files and accounts preserved.'
