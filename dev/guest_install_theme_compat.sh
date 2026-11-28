#!/bin/sh
# Optional original Plus95 screensaver compatibility research, guest only.
set -eu
/usr/lib/win95lx/require-guest
test "$(id -u)" = 0
test "$(hostname)" = win95lx-dev
# No host packages, prefix or screen-saver/locking policy is changed.
dpkg --add-architecture i386
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends wine wine64 wine32:i386
