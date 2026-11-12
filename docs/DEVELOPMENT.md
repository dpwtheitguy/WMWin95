# Development and recovery

## Current environment

Host: Pop!_OS 24.04, QEMU 8.2.2, KVM API 12. QEMU was installed by the user. KVM and device visibility require broader host execution than the default Codex sandbox; an initial sandbox-only check incorrectly appeared to show no KVM device. Both Linux and Windows-reference guests have subsequently booted under KVM.

The Linux guest is now persistently installed, with root on `/dev/vda2` (ext4) in a project-local 32 GiB qcow2. The official Xubuntu/Subiquity installer installed the downloaded, checksum-matched minimal ISO. It used an explicit `/dev/vda` storage match after verifying QEMU identity, a blank disk and the expected disk size. The original media remains unchanged.

Hardware: pinned `pc-i440fx-8.2`, 4 GiB RAM, two host-model CPUs, virtio disk/network/tablet, standard VGA, X11 at 800x600. No physical disks, host folders or privileged devices are passed through. Linux networking is user-mode NAT for updates, with SSH bound only to host `127.0.0.1:22295`. QMP uses a local socket in a mode-0700 directory. Windows reference networking is disabled entirely.

## Accounts and maintenance

`win95` is the non-admin normal desktop user and belongs only to its own group. Its password is locked; the user explicitly authorized automatic login into the Win95LX development session. The authenticated `developer` account retains normal sudo policy and its XFCE maintenance environment. The prototype session runs no XFCE panel, shortcut daemon, file manager or terminal.

Generated guest-only developer credentials are in `private/run/development-credentials.json` with mode 0600. The SSH key and separate live/installed guest known-host files also remain private. Do not print or copy these into reports or commits. Password authentication over SSH is disabled; maintenance login and sudo still authenticate normally.

“Close Desktop” ends the prototype session and returns to the greeter. Select the developer account and XFCE session for graphical maintenance. SSH remains a separate maintenance route using the private key. This is not a production greeter/theme implementation; normal login/maintenance styling remains unfinished.

`dev/guest_admin.py SCRIPT` transfers a reviewed script and executes it via authenticated sudo **inside the designated guest**. Guest-changing scripts verify QEMU identity and hostname. It never runs host sudo. The installation script's automatic-login scope was initially rejected by automatic review; the user subsequently explicitly authorized it. No global shortcut overrides were applied: the dedicated shell session instead omits the conflicting XFCE components.

## Source, deployment and runtime

`dev/deploy_preview.py` runs the unit tests, then transfers source and private shell assets to the developer account. It only launches a developer preview when `--launch` is explicitly selected and that same account has an active graphical session.

`dev/guest_install_session.sh` prepares a content-addressed release under `/opt/win95lx/releases/`, imports the application with the guest GTK runtime before promotion, makes release files root-owned and removes group/other write permissions, then atomically updates `/opt/win95lx/current`. The normal desktop user can read the code/assets but cannot edit the release. A selectable `/usr/share/xsessions/win95lx.desktop` launches it.

A reboot test caught an incomplete module refactor and a malformed source file. Both were fixed. The deployment now validates the runtime import before updating the current release. Unit tests cover the bitmap decoder, drive boundary, window state and comparison workflow; real QMP screenshots/input cover the integrated GTK guest.

## VM operation

```sh
python3 dev/start_xubuntu.py
python3 tools/qmp.py status
python3 tools/qmp.py key ctrl-esc
python3 tools/qmp.py click 44 27 --double
python3 tools/qmp.py capture private/screenshots/development/new-capture.ppm
python3 tools/ppm_to_png.py private/screenshots/development/new-capture.ppm private/screenshots/development/new-capture.png
python3 dev/capture_shell.py --output private/screenshots/implementation/new-run
```

Do not reuse output names or start a second instance. The launcher refuses an existing QMP socket; inspect the actual process before treating runtime files as stale. QMP typing assumes a US layout. Source capture runs record input sequences, source hashes and configuration, but are not reference comparisons.

Normal shutdown for an offline checkpoint:

```sh
python3 dev/guest_admin.py dev/guest_poweroff.sh
# Wait until QEMU exits, then:
python3 dev/checkpoint.py new-name
python3 dev/start_xubuntu.py
```

`checkpoint.py` refuses an active VM. `desktop-milestone-002` is the validated development milestone. `initial-shell` contains the earlier incomplete deployment and is retained only for diagnosis. Snapshot application is intentionally not automated; a revert discards later guest changes and needs explicit review. `dev/guest_remove_session.sh` removes the custom session and automatic-login configuration while preserving accounts and user data; it is prepared but has not been executed.

The temporary loopback HTTP provisioning server was stopped after guest SSH setup. Current scripts use key-only SSH instead.

## Remaining work

Finish the original Windows installation, confirm installed edition/shell state, capture immutable original references, measure each implementation screen, and validate interaction behavior. Complete real window/application integration, original sound mappings, editable Control Panel settings, persistent application data, native file operations, packaging and a complete authenticated maintenance/greeter flow. No current image is certified pixel-equal. No XFCE component has been forked.

## Latest evidence

Current root-owned release: `30207fbbfbf6ee7e`. The `desktop-milestone-002` offline snapshot contains that release and has been reboot-tested. The final implementation capture set is `private/screenshots/implementation/run-004/`; `private/screenshots/development/milestone-final.png` shows the running shell after the final reboot. Fifteen tests pass. The first user-supplied OEM number has now been accepted and the reference installation is proceeding; Linux work remains independently available.
