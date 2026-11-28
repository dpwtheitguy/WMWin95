#!/bin/sh
# Reviewed development-guest-only OpenGL dependencies for original32-bit savers.
set -eu
/usr/lib/win95lx/require-guest
test "$(id -u)" = 0
test "$(hostname)" = win95lx-dev
test "$(dpkg --print-architecture)" = amd64
. /etc/os-release
test "$ID" = ubuntu
test "$VERSION_ID" = 24.04
# No host, display/locking policy or Wine prefix changes. No package removals.
dpkg --add-architecture i386
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get --simulate --no-install-recommends --no-remove install libgl1:i386 libglx-mesa0:i386 libgl1-mesa-dri:i386 libosmesa6:i386
apt-get install -y --no-install-recommends --no-remove libgl1:i386 libglx-mesa0:i386 libgl1-mesa-dri:i386 libosmesa6:i386
dpkg-query -W -f='${binary:Package} ${Version} ${Status}\n' libgl1:i386 libglx-mesa0:i386 libgl1-mesa-dri:i386 libosmesa6:i386
test -e /usr/lib/i386-linux-gnu/libGL.so.1
test -d /usr/lib/i386-linux-gnu/dri
ldd /usr/lib/i386-linux-gnu/libGL.so.1
test -e /usr/lib/i386-linux-gnu/libOSMesa.so.8
ldd /usr/lib/i386-linux-gnu/libOSMesa.so.8
