#!/bin/sh
# Install the user-authorized non-admin automatic-login session in the QEMU guest.
# Preserves developer authentication and does not modify global shortcuts.
set -eu
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test "$(hostname)" = win95lx-dev
test "$(id -u)" = 0
test -f /home/developer/win95lx-preview/src/win95lx/shell/app.py
install -d /opt/win95lx /opt/win95lx/bin /opt/win95lx/releases
version=$(python3 - <<'EOF'
import hashlib
from pathlib import Path
root=Path('/home/developer/win95lx-preview');digest=hashlib.sha256()
for folder in ('src','private/shell-assets'):
    for p in sorted((root/folder).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts:
            digest.update(str(p.relative_to(root)).encode());digest.update(p.read_bytes())
print(digest.hexdigest()[:16])
EOF
)
release="/opt/win95lx/releases/$version"
install -d "$release/assets"
cp -a /home/developer/win95lx-preview/src "$release/"
cp -a /home/developer/win95lx-preview/private/shell-assets/. "$release/assets/"
PYTHONPATH="$release/src" python3 -c 'from win95lx.shell.app import Shell; from win95lx.explorer.presentation import DriveView'
chown -R root:root "$release"
chmod -R go-w "$release"
ln -sfn "$release" /opt/win95lx/current.new
mv -Tf /opt/win95lx/current.new /opt/win95lx/current
install -d /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/70-win95lx-cursor.conf <<'EOF'
Section "OutputClass"
    Identifier "Win95LX VirtIO cursor"
    MatchDriver "virtio_gpu"
    Driver "modesetting"
    Option "SWcursor" "true"
EndSection
EOF
cat > /opt/win95lx/bin/session <<'EOF'
#!/bin/sh
export XDG_SESSION_TYPE=x11
export WIN95LX_STARTUP_SOUND=1
release=$(readlink -f /opt/win95lx/current)
export PYTHONPATH="$release/src"
resolution=800x600
if [ -r "$HOME/.config/win95lx/resolution" ]; then
    read -r resolution < "$HOME/.config/win95lx/resolution"
fi
python3 -m win95lx.display_modes "$resolution" ||
    python3 -m win95lx.display_modes 800x600
# Independent desktop with an allowlisted set of built-in GTK accessories.
exec python3 -m win95lx.shell.app --assets "$release/assets" > "$HOME/.win95lx-shell.log" 2>&1
EOF
chmod 755 /opt/win95lx/bin/session
cat > /usr/share/xsessions/win95lx.desktop <<'EOF'
[Desktop Entry]
Name=Win95LX Development
Comment=Original-asset desktop prototype
Exec=/opt/win95lx/bin/session
Type=Application
DesktopNames=Win95LX
EOF
printf '%s\n' 'Selectable Win95LX session installed.'
# Explicitly authorized by the user: automatic login for a non-admin guest user.
if ! id win95 >/dev/null 2>&1; then
    useradd --create-home --shell /bin/bash --comment 'Win95LX Desktop' win95
    passwd -l win95
fi
case " $(id -Gn win95) " in *' sudo '*|*' adm '*) echo 'Desktop account has unexpected admin groups' >&2; exit 1;; esac
install -d /etc/lightdm/lightdm.conf.d /var/lib/win95lx
if [ ! -e /var/lib/win95lx/login-baseline.tar ]; then
    tar -cf /var/lib/win95lx/login-baseline.tar /etc/lightdm/lightdm.conf.d 2>/dev/null
fi
cat > /etc/lightdm/lightdm.conf.d/70-win95lx.conf <<'EOF'
[Seat:*]
autologin-user=win95
autologin-session=win95lx
EOF
printf '%s\n' 'User-authorized non-admin guest autologin configured; developer maintenance auth preserved.'
