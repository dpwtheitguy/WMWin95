#!/bin/sh
# Install the distro Python CUPS binding in the development guest only.
# Does not create queues, alter printer defaults or grant administration rights.
set -eu
/usr/lib/win95lx/require-guest
test "$(id -u)" = 0
export DEBIAN_FRONTEND=noninteractive
apt-get install -y --no-install-recommends python3-cups
/usr/bin/python3 -c 'import cups; print("Guest printing binding available")'
