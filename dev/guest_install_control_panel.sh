#!/bin/sh
# Install narrowly scoped OS-settings support only in the development guest.
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
if test -x /usr/lib/win95lx/require-guest; then
    /usr/lib/win95lx/require-guest
else
    test "$(hostname)" = win95lx-dev
fi
test "$(id -u)" = 0
test -d /home/developer/win95lx-preview/src/win95lx/control_panel
install -d /etc/polkit-1/rules.d
cat > /etc/polkit-1/rules.d/49-win95lx-clock.rules <<'EOF'
polkit.addRule(function(action, subject) {
    if (subject.user == "win95" && subject.local && subject.active &&
        (action.id == "org.freedesktop.timedate1.set-time" ||
         action.id == "org.freedesktop.timedate1.set-timezone" ||
         action.id == "org.freedesktop.timedate1.set-ntp")) {
        return polkit.Result.YES;
    }
});
EOF
chmod 644 /etc/polkit-1/rules.d/49-win95lx-clock.rules
PYTHONPATH=/home/developer/win95lx-preview/src python3 - <<'EOF'
from pathlib import Path
from win95lx.control_panel.datetime_settings import fixed_tzif,fixed_zone_name
root=Path('/usr/share/zoneinfo')
for minutes in range(-720,841,15):
    path=root/fixed_zone_name(minutes);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(fixed_tzif(minutes));path.chmod(0o644)
EOF
printf '%s\n' 'Date/time policy and fixed-offset DST zones installed in the guest.'
