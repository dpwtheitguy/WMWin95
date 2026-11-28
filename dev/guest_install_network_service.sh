#!/bin/sh
# Reviewed policy must already exist. No broad NetworkManager authorization.
# This installer does not create profiles, choose adapters or edit networking.
set -eu
/usr/lib/win95lx/require-guest
test "$(id -u)" = 0
test -f /etc/win95lx/guest-id
root=/opt/win95lx/current
for module in network_service.py network_preferences.py; do
    test "$(stat -c %U "$root/src/win95lx/control_panel/$module")" = root
    test "$(stat -c %a "$root/src/win95lx/control_panel/$module")" = 644
done
PYTHONPATH="$root/src" /usr/bin/python3 -c 'from win95lx.control_panel.network_service import load_policy; load_policy()'
install -d -m 700 /var/lib/win95lx/network
cat > /etc/systemd/system/win95lx-network.service <<'UNIT'
[Unit]
Description=Win95LX scoped existing network profile service
After=NetworkManager.service systemd-logind.service
Requires=NetworkManager.service systemd-logind.service
[Service]
Type=simple
Environment=PYTHONPATH=/opt/win95lx/current/src
ExecStart=/usr/bin/python3 -m win95lx.control_panel.network_service
RuntimeDirectory=win95lx-network
RuntimeDirectoryMode=0755
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/run/win95lx-network /var/lib/win95lx/network
RestrictAddressFamilies=AF_UNIX
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable win95lx-network.service
systemctl start win95lx-network.service
systemctl is-active win95lx-network.service
