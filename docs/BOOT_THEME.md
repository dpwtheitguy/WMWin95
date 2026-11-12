# Win95LX boot splash

The Windows 95 OSR 2.5 reference displays a 640×400 VGA raster with a palette-cycling band in the last 11 rows. The theme fits its 4:3 CRT proportions inside the current Plymouth display. Widescreen displays get black side bars. At 1920×1080, for example, the splash is 1440×1080 with 240-pixel side bars.

The original artwork is kept in the ignored `private/` directory. The local reference captures came from a cold boot of a disposable clone of the Windows 95 VM's `desktop-reference-800` disk snapshot. The 20 unique animation frames repeat at approximately nine frames per second.

From the repository root, stage the existing local captures using Bash.

```sh
python3 tools/stage_boot_theme.py private/run/boot-theme-reference/frame-0{24..47}.ppm
```

With a fresh capture, pass its matching 640×400 P6 frames in chronological order. The stager uses `private/plymouth/win95lx` by default and requires a fresh output directory. One capture produces a static splash.

To install in the Win95LX development VM, transfer the staged `win95lx` directory to `/home/developer/win95lx-preview/private/plymouth/win95lx` in the guest. From the repository root on the host, run:

```sh
python3 dev/guest_admin.py dev/guest_install_boot_theme.sh
```

The installer checks the QEMU guest identity, selects the theme through Ubuntu's Plymouth alternative, and updates the current kernel's initramfs. A failed initramfs update restores the previous theme selection and files. Reboot the guest separately when ready. Plymouth uses the `splash` kernel argument.

Inside the guest, verify the configured theme and initramfs contents before reboot.

```sh
readlink -f /usr/share/plymouth/themes/default.plymouth
lsinitramfs "/boot/initrd.img-$(uname -r)" | grep 'plymouth/themes/win95lx/'
```
