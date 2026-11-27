#!/bin/sh
# Dedicated guest only. Root helper accepts only peer UID win95 and create-only
# printer RPC. This does not add win95 to lpadmin or allow broad CUPS changes.
set -eu
/usr/lib/win95lx/require-guest
test "$(id -u)" = 0
test "$(hostname)" = win95lx-dev
root=/opt/win95lx/current
# Root-owned immutable release is required: do not run a writable user checkout.
test "$(stat -c %U "$root/src/win95lx/control_panel/printer_installation.py")" = root
test "$(stat -c %U "$root/src/win95lx/control_panel/printer_service.py")" = root
install -d -m 700 /var/lib/win95lx/printer-installations
uid=$(id -u win95)
cat > /etc/systemd/system/win95lx-printers.service <<EOF
[Unit]
Description=Win95LX create-only printer service
After=cups.service
Requires=cups.service
[Service]
Type=simple
Environment=PYTHONPATH=/opt/win95lx/current/src
ExecStart=/usr/bin/python3 -m win95lx.control_panel.printer_service --peer-uid $uid
RuntimeDirectory=win95lx-printers
RuntimeDirectoryMode=0755
ExecStartPre=/usr/bin/rm -f /run/win95lx-printers/control.sock
NoNewPrivileges=yes
PrivateTmp=yes
ProtectHome=yes
ProtectSystem=strict
ReadWritePaths=/run/win95lx-printers /var/lib/win95lx/printer-installations
RestrictAddressFamilies=AF_UNIX
Restart=on-failure
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable win95lx-printers.service
systemctl restart win95lx-printers.service
systemctl is-active win95lx-printers.service
