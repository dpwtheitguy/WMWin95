#!/bin/sh
set -eu
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
loginctl list-sessions --no-legend
id win95
cat /home/win95/.win95lx-shell.log
journalctl -b -u lightdm --no-pager -n 25
