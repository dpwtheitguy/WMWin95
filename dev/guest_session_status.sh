#!/bin/sh
set -eu
test "$(hostname)" = win95lx-dev
loginctl list-sessions --no-legend
id win95
cat /home/win95/.win95lx-shell.log
journalctl -b -u lightdm --no-pager -n 25
