# Current status update — 2026-11-05

The first OEM number supplied by the user was accepted. The reference is no longer blocked on a key. Installation is incomplete: its OEM path attempted a write to the read-only emulated A: disk, then left incomplete hard-disk boot/setup metadata. Checkpoints `boot-floppy-writeprotect` and `reference-boot-config` preserve progress. An inactive FAT32 primary partition was corrected with a backed-up, verified one-byte active-flag change. Standard DOS boot paths and the original memory/CD drivers were supplied without patching Microsoft binaries. The latest Windows launch reported an incomplete registry/SYSTEM.INI; the reference process subsequently exited for an unconfirmed reason.

Original media remains unchanged. See the private checkpoints and `reports/reference-active-partition.json`, `reports/reference-boot-paths.json`, and `reports/reference-boot-workaround.json`. `dev/prepare_reference_boot.py` prints a plan by default and requires explicit `--apply` at the designated guest's DOS prompt.

CAB extraction is already sufficient for asset work. Linux development is independent of this reference installation; a completed original-shell VM is for the requested geometry, behavior, registry and screenshot validation. Historical bring-up notes below retain earlier states and are superseded by this update.

# Current reference bring-up status

The installed Linux prototype has passed a full reboot into its non-admin Win95LX X11 session. QEMU 8.2.2/KVM is working for both guests. The original installer accepted the first OEM number supplied by the user and is now copying Windows 95 files. The installed original shell and final edition confirmation are still pending.

New ISO evidence: an El Torito boot descriptor at sector 17 points to catalog sector 20 and a 1.44 MiB floppy-emulation image at sector 1112. The catalog validation checksum passed. `private/boot-media/boot.json` records image SHA-256 and offsets; originals are preserved. DOS reports Windows 95 version 4.00.1111. This does not establish the final installed OSR label or independently authenticate the media.

The first apparent boot stall was reproduced under KVM and TCG. It was the embedded boot selector handing control to the empty virtual hard disk, not a confirmed CPU-virtualization incompatibility. Explicitly select CD boot (choice 2 in the first selector); the Windows 95 startup/setup menu follows. KVM then reached the original setup successfully. Retain the initial diagnostic report as history, not evidence that KVM is unsupported.

Setup created the private 2 GiB reference disk's partition and large-disk support. Its subsequent formatter-media prompt did not find the boot disk automatically. DOS inspection located the boot image at A: and the CD at D:, with the installer under D:\WIN95. The formatter on A: is used only on the new reference virtual C: drive. Record all such bring-up choices before sealing a reference. No host physical disk is attached and no networking is enabled.

The remaining sections preserve initial acquisition/preflight observations; later runtime findings above supersede their missing-QEMU/driver assumptions.

# Reference media and virtual machines

## Windows media observed on 2026-11-04

- Source: `/home/dwilson/Downloads/Windows 95C.iso`, opened read-only; no mount.
- SHA-256: `c13b6bad0dcbd4f13c3d840d2b7efe939c6d4e40b1c63f086a5f92edfb1e9b77`.
- ISO volume: `WINDOWS95C`; publisher field: `MICROSOFT CORPORATION`. These fields are labels, not proof of authenticity.
- Layout: root setup launcher, `win95/`, `plus/`, `drivers/`, `admin/`, `other/`, `help/`, `sampler/`, `datalink/` and demos.
- Evidence: `win95/setup.exe` version resource contains 4.00.1111; root launcher contains 4.00.1068. Bundled IE4 setup reports 4.72.2106.1. Setup/version resources include US English language evidence (0409); textual setup materials inspected are English.
- Identification: consistent with English OSR2-family media labelled 95C; **OSR 2.5 installation state is not yet confirmed**. Bundled IE4 and the filename alone do not prove installed edition. Record installed System Properties, registry product/version and shell binary versions before accepting the reference. Do not confuse OS component build numbers with OSR marketing labels.

The complete ISO/CAB inventory is `private/reference/inventory.json`. Extraction produced 7,210 files; 54 CAB-level failures are recorded. libarchive 3.7.2 does not support the multipart sets encountered. Their presence is not evidence that the ISO is corrupt. Use `cabextract` with all cabinet siblings available in the isolated development environment; preserve logs and provenance. Do not execute EXE installers to obtain resources on the host.

`private/resources/inventory.json` contains 9,617 resource/file records: 8,256 raw resources extracted, 1,271 loose original assets copied, 70 unsupported/failed executable inspections, 20 executables with no resources. PE and NE raw resources preserve type, identifier, language where available, dimensions where decoded, source path and hashes. Dialog/menu/string/font payloads are raw metadata; group icon reconstruction, cursor packaging/hotspots, full font decoding, semantic dialog parsing, legacy executable formats, SZDD-compressed files and multipart CABs remain incomplete. Never report raw payloads as ready-to-install icons or fonts.

All original asset bytes, extraction inventories and screenshots stay in Git-ignored `private/`. The tools do not grant redistribution rights. Compare the ISO hash before and after extraction; the recorded check passed.

## Current runtime update

The user subsequently installed QEMU 8.2.2. Broader host checks confirm working KVM API 12. A separate Xubuntu live guest is running with KVM enabled; keyboard input and framebuffer capture are verified. The Windows reference VM itself has not yet been installed or booted. Original preflight observations below are historical.

The core Windows cabinet chain has since been extracted using private cabextract 1.11: 2,519 files in `private/cabsets/windows95` and 17,522 raw resource records in `private/resources-core`. Extraction completed with a differing-Set-ID warning preserved in the log; the original libarchive failure record remains intact. Other cabinet sets and final edition authentication remain pending.

## Primary reference VM: QEMU/KVM

User preference: use KVM. The current execution environment cannot see `/dev/kvm` or a system `qemu-system-i386`/`qemu-system-x86_64`. This may reflect environment isolation rather than the physical host. Do not change kernel modules, device permissions, groups or packages without approval.

Generate a reviewable command:

```sh
python3 tools/reference_vm.py --iso "$HOME/Downloads/Windows 95C.iso"
# If KVM cannot run this historical guest, explicitly select software emulation:
python3 tools/reference_vm.py --iso "$HOME/Downloads/Windows 95C.iso" --accel tcg
```

The script prints commands only. Create the private 2 GiB qcow2 disk once, only if absent. Proposed hardware: legacy PC/i440fx family, one Pentium CPU, 64 MiB RAM, IDE storage, Cirrus VGA, SB16 audio device, no network adapter. KVM support for the proposed CPU/hardware is unvalidated; TCG is a compatibility alternative, not a claim of timing equivalence. Do not use `-cpu host` as a historical CPU substitute. Pin the installed QEMU version and a supported versioned machine type after a successful boot; the initial `pc` alias is not a reproducible final configuration.

The CD may not be bootable. Supply a privately obtained, matching DOS/Win95 boot floppy with CD-ROM drivers using `--boot-floppy`. Install Windows inside the VM only. Record boot media hash, partitioning, CD-ROM driver and installation choices. No boot floppy or installed reference disk is present yet. Do not install IE4 desktop enhancements over the original shell unless a separate reference variant explicitly requires them.

Install the appropriate original Cirrus driver, set 800x600 and record the actual color depth. Prefer the reference's original supported setting; 256 colors is an initial candidate, not a measured requirement. Disable guest scaling. Host viewer zoom is disabled; capture framebuffer pixels rather than scaled viewer screenshots. SB16 audio requires a QEMU-version-specific audio backend before sound validation; the current plan defines the device only. Record audio configuration and capture startup/shutdown events.

Historical guest compatibility varies with CPU and QEMU version. Keep installation logs, vary one setting at a time, and document changes. No successful boot, audio or display configuration has been claimed. QEMU options: [official invocation manual](https://www.qemu.org/docs/master/system/invocation.html).

## VirtualBox alternative, not primary

Documented baseline: Windows95 guest type, 64 MiB RAM, one CPU, BIOS, PIIX3 chipset, IDE disk and CD, VBoxVGA with 8 MiB video memory, 3D disabled, PS/2 input, SB16 if supported, all NICs disabled. Check `VBoxManage modifyvm --help` for the installed release before creating a VM. Guest Additions and modern display drivers must not be assumed compatible. Modern hardware virtualization may expose CPU/timing incompatibilities; keep patches separate, hashed and documented. Do not disable host security to make the guest work.

Observed VirtualBox: 7.2.22r175245, warning that `/dev/vboxdrv` is absent. No VM was created and no driver repair was attempted. Older manual describes limited Win9x testing: [Oracle manual](https://download.virtualbox.org/virtualbox/5.2.10/UserManual.pdf). Do not interpret that as current support certification.

## Separate Xubuntu development VM

Downloaded `xubuntu-24.04.5-minimal-amd64.iso`; local volume label is `Xubuntu 24.04.5 LTS amd64`. See `reports/xubuntu-media.json` for size and SHA-256. Its hash matches the filename-specific entry in [Ubuntu-hosted SHA256SUMS](https://cdimage.ubuntu.com/xubuntu/releases/24.04/release/SHA256SUMS). The detached signature has not been independently verified.

Generate a plan with:

```sh
python3 tools/linux_vm.py --iso "$HOME/Downloads/xubuntu-24.04.5-minimal-amd64.iso"
```

Proposed Linux guest: 32 GiB private qcow2, 4 GiB RAM, 2 CPUs, virtio storage/network. User-mode networking is for maintained Linux package updates; the Windows VM remains offline. No host folder passthrough, port forwarding or privileged devices. Install Xubuntu to the VM disk, create a development account and an authenticated maintenance account, and select an XFCE X11 session. Confirm `XDG_SESSION_TYPE=x11` in the guest. Capture baseline state before theme changes.

The reference VM is now paused at its OEM Certificate of Authenticity page, with an internal `awaiting-oem-key` snapshot saved through QEMU. `reports/reference-checkpoint.json` records the state. Resume only when the user supplies their licensed number or chooses to enter it themselves: `python3 tools/qmp.py --socket private/run/windows95.qmp resume`. No keys have been invented, searched online, or entered.

## OEM input supplied by the user

The user subsequently supplied two possible OEM numbers. The first was accepted by the original installer, which advanced to User Information and hardware/component selection. Numbers are kept only in a mode-0600 file under ignored `private/licenses/`; they are not reproduced in documentation or reports. This records installer acceptance, not independent proof of license ownership. The reference now continues past the earlier key prompt using a generic “Win95LX Reference” identity, Typical installation, common components, and no new startup floppy.

The CAB files are sufficient for resource extraction and Linux development. Installing the offline reference is separately necessary for the project's requested original-shell geometry, interaction checks, installed registry state and reproducible screenshot measurements. The Linux desktop does not depend on Windows being installed or running.
