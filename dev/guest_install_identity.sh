#!/bin/sh
# Install a stable identity guard; computer-name changes must not break the OS.
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test "$(id -u)" = 0
if test -f /etc/win95lx/guest-id; then
    test "$(cat /etc/win95lx/guest-id)" = "$(cat /etc/machine-id)"
else
    test "$(hostname)" = win95lx-dev
fi
install -d -m 755 /etc/win95lx /usr/lib/win95lx
install -m 644 /etc/machine-id /etc/win95lx/guest-id
cat > /usr/lib/win95lx/require-guest <<'EOF'
#!/bin/sh
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test -f /etc/win95lx/guest-id
test ! -L /etc/win95lx/guest-id
identity=$(cat /etc/machine-id)
test "${#identity}" = 32
case "$identity" in *[!0-9a-f]*) exit 1;; esac
mode=$(stat -c %a /etc/win95lx/guest-id)
test "$((0$mode & 022))" = 0
test "$(stat -c %u /etc/win95lx/guest-id)" = 0
test "$(cat /etc/win95lx/guest-id)" = "$(cat /etc/machine-id)"
EOF
chmod 755 /usr/lib/win95lx/require-guest
chown root:root /etc/win95lx/guest-id /usr/lib/win95lx/require-guest
/usr/lib/win95lx/require-guest
printf '%s\n' 'Stable guest identity installed; no privilege grant added.'
