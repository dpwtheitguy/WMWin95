#!/bin/sh
# Install the staged private boot theme only in the Win95LX QEMU development guest.
set -eu
test "$(id -u)" = 0
test "$(cat /sys/class/dmi/id/sys_vendor)" = QEMU
test "$(hostname)" = win95lx-dev

source=/home/developer/win95lx-preview/private/plymouth/win95lx
themes=/usr/share/plymouth/themes
theme=$themes/win95lx
alternative=$theme/win95lx.plymouth
plugin_path=$(plymouth --get-splash-plugin-path)
test -f "$plugin_path/script.so"
test -f "/boot/initrd.img-$(uname -r)"
test ! -L "$theme"
test ! -e "$theme" || test -d "$theme"

previous=$(update-alternatives --query default.plymouth)
previous_theme=$(printf '%s\n' "$previous" | sed -n 's/^Value: //p')
previous_mode=$(printf '%s\n' "$previous" | sed -n 's/^Status: //p')
test -f "$previous_theme"
registered=false
if printf '%s\n' "$previous" | grep -Fxq "Alternative: $alternative"; then
    registered=true
fi

work=$(mktemp -d "$themes/.win95lx.XXXXXXXX")
replacement=false
selection_changed=false
cleanup() {
    status=$?
    trap - 0
    if [ "$status" -ne 0 ]; then
        if [ "$replacement" = true ]; then
            rm -rf "$theme"
        fi
        if [ -d "$work/previous" ]; then
            mv -T "$work/previous" "$theme" || status=1
        fi
        if [ "$selection_changed" = true ]; then
            if [ "$registered" = false ]; then
                update-alternatives --remove default.plymouth "$alternative" || status=1
            fi
            if [ "$previous_mode" = auto ]; then
                update-alternatives --auto default.plymouth || status=1
            else
                update-alternatives --set default.plymouth "$previous_theme" || status=1
            fi
        fi
        if [ -d "$work/previous" ]; then
            printf 'Original theme remains available at %s\n' "$work/previous" >&2
            exit "$status"
        fi
    fi
    rm -rf "$work"
    exit "$status"
}
trap cleanup 0
trap 'exit 1' HUP INT TERM

install -d -m 755 "$work/new"
for file in win95lx.plymouth win95lx.script background.png; do
    test -f "$source/$file"
    test ! -L "$source/$file"
    install -m 644 "$source/$file" "$work/new/$file"
done
count=0
while [ -f "$source/ribbon-$count.png" ]; do
    test "$count" -lt 20
    test ! -L "$source/ribbon-$count.png"
    install -m 644 "$source/ribbon-$count.png" "$work/new/ribbon-$count.png"
    count=$((count + 1))
done
test "$count" -gt 0
if [ -d "$theme" ]; then
    mv -T "$theme" "$work/previous"
fi
replacement=true
mv -T "$work/new" "$theme"
selection_changed=true
if [ "$registered" = false ]; then
    update-alternatives --install "$themes/default.plymouth" default.plymouth "$alternative" 50
fi
update-alternatives --set default.plymouth "$alternative"
update-initramfs -u -k "$(uname -r)"
printf 'Win95LX Plymouth theme installed for kernel %s.\n' "$(uname -r)"
