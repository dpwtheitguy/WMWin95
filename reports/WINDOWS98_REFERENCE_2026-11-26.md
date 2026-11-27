# Windows 98 reference and asset library — November 26

This background work prepares Windows 98 for future comparisons. It does not change the Windows 95 product baseline or silently substitute Windows 98 art into it. The original archives, executables, extracted resources and disks remain private.

## Sources and actual versions

- Windows 98 Second Edition ISO: [Archive item](https://archive.org/details/win98se_201607), `Windows 98 Second Edition.iso`, 655,591,424 bytes. Private metadata records SHA-1/size agreement and SHA-256. This verifies the transfer, not vendor authenticity.
- Plus! 98 ISO: [Archive item](https://archive.org/details/MicrosoftPlusforWindows98), `PLUS98.ISO`, 298,692,608 bytes, likewise hashed and preserved separately.
- Community preinstalled disk: [Archive item](https://archive.org/details/windows-98se-vmdk), `Windows 98 SE.zip`, 1,067,671,517 bytes. Contains a single 2,041,905,152-byte monolithic sparse VMDK representing a 100 GB disk. Its descriptor has no parent/backing reference. The source remains unchanged; QEMU uses a separately converted QCOW2 disk. No vendor programs were executed on the host, and no host filesystem was mounted/shared with the guest.

Version resources inside the ISO establish Kernel32 and Sysdm 4.10.0.2222, Explorer 4.72.3110.1 and Shell32 4.72.3612.1700. The community installation has Kernel32/Sysdm 4.10.0.2222, Explorer 4.72.3110.1 and updated Shell32 4.72.3812.600. Its splash includes Plus! 98. Installed `Program Files\Plus!\Themes.exe` is version 4.80.0.1998 and byte-for-byte identical to the separately extracted original Plus! 98 CAB executable. Plus! 98 theme folders and programs (including Spider, Marbles and DeluxeCD) are present, establishing more than a customized splash alone. This is an updated community SE/Plus configuration, not proof of an untouched retail SE or first-edition installation. No downloaded/generated keys or license-check bypasses were used.

## Extracted libraries

| Library | Location | Result |
| --- | --- | --- |
| Complete SE ISO filesystem | `private/reference-media/windows98-se-extracted/media` | 3,533 original files, with source hashes in `iso-inventory.json` |
| Main SE CAB chain | `private/cabsets/windows98-se/base` | 6,858 files; canonical complete extraction, cabinet hashes and log |
| SE raw resources and loose art | `private/resources/windows98-se` | 34,741 inventory records; includes 340 loose WAV files, 307 BMP, original ICO/CUR/ANI and fonts |
| SE icon/bitmap previews | `private/asset-libraries/windows98-se-complete` | 1,921 multi-image ICO files, 3,698 unscaled native PNG previews, 1,537 embedded BMP files |
| SE loose ISO resource previews | `private/asset-libraries/windows98-se-iso-loose` | 316 ICO, 520 PNG, 427 embedded BMP, 845 original loose assets |
| SE ancillary ISO CABs | `private/cabsets/windows98-se-ancillary` | Microsoft cabinets from PWS, terminal client and CPU driver directories; see per-chain logs |
| Ancillary raw resources | `private/resources/windows98-se-ancillary` | 12,319 records, no resource-parser failures |
| Ancillary icon/bitmap previews | `private/asset-libraries/windows98-se-ancillary` | 510 ICO, 885 PNG, 649 BMP |
| Complete Plus! 98 ISO filesystem | `private/reference-media/plus98-extracted/media` | 221 original files with inventory and hashes |
| Plus! 98 CAB | `private/cabsets/plus98` | 1,677 files extracted successfully |
| Plus! 98 raw resources/loose art | `private/resources/plus98` | 4,447 records, including 377 loose WAV files, 206 BMP and original ICO/CUR/ANI/fonts |
| Plus! 98 loose ISO resources | `private/asset-libraries/plus98-iso-loose` | 27 ICO, 33 PNG, 24 embedded BMP, 74 loose assets from outside the CAB |
| SE extra executable icons | `private/asset-libraries/windows98-se-extra-executables` | 96 ICO, 182 PNG, 210 BMP from SCR/OCX/ACM/AX/VBX files |
| Plus! 98 extra executable icons | `private/asset-libraries/plus98-extra-executables` | 98 ICO, 187 PNG, 104 BMP from those additional file types |
| Plus! 98 previews | `private/asset-libraries/plus98-complete` | 235 ICO, 466 PNG, 713 embedded BMP |

Each preview library also has a `loose` directory containing original JPG/GIF/BMP, icons, cursors, WAV/RMI/MIDI/AVI, fonts and .THE theme definitions with source hashes. The core SE library contains 1,672 such loose files; the Plus! 98 library contains 1,140. Separate ISO-loose libraries retain resources from original executables outside the CABs.

Every exported ICO retains all original image payloads and native sizes. PNGs are decoded previews without resizing. Embedded BMPs add only the required BMP file header around the original DIB. Inventories record source hashes, identifiers, languages, output paths and hashes. Unsupported resource parsing is recorded explicitly: 57 DOS/LE/non-resource executables in the SE core and four DOS executables in Plus! 98. The supplementary executable-type scan records 20 additional non-MZ script/data files in SE and two in Plus! 98; these are retained as originals rather than treated as executables. The SE loose-ISO resource scan records 103 unsupported DOS/legacy executables; the Plus! 98 loose-ISO scan records none. Counts are per scan and may include duplicate source programs, not unique defects. All icon groups in the supported files decoded successfully. Original files remain available even when the parser does not support their executable format.

Cabinet names are case-sensitive on the host (`PRECOPY1.CAB`, not `precopy1.cab`). Entering the chain through `BASE4.CAB` extracts the complete linked main cabinet set. Independent NET/DRIVER/CATALOG entry-point runs produced identical hashes for all 6,858 files. Starting at WIN98_21 alone failed to reconstruct `gm16.dls`; use the canonical `base` extraction. The failed run and its log are retained as evidence.

InstallShield cabinets need `unshield`, not Microsoft `cabextract`. The tool and its library were downloaded/extracted privately, without a host package installation. CPU-driver subarchives extract successfully. Merging the original two Citrix disk volumes recovers most files, but `Modemw.dll` (16-bit client) and `pn.exe` (32-bit client) still fail decompression. These ancillary client gaps are explicit; complete original cabinet bytes are preserved. No claim that every ancillary file extracted successfully is made.

## Visible VM and migration

Launch with `python3 dev/start_windows98_reference.py`. It uses visible GTK, offline networking (`-nic none`), IDE, Cirrus VGA and a dedicated `private/run/windows98-se.qmp` socket. It does not restore a snapshot implicitly. A recovery restore must be requested explicitly.

The archived VMware installation needs hardware migration under QEMU. Initial normal boot faulted in the obsolete `DRVWQ117` tape detector with no corresponding emulated tape device. In the guest DOS prompt, its complete original driver was reversibly renamed from `.VXD` to `.BAK`; no executable bytes were patched. Windows then reached GUI hardware discovery. Existing updated driver files under `C:\Windows\System` are being used where the CD controller has not yet been installed. Four unidentified hardware wizards were initially cancelled; after restart, local-only searches were completed through the native no-driver Finish page so they are recorded rather than repeatedly cancelled. These devices still need identification before hardware acceptance.

Verified recovery checkpoints include `win98-se-initial-boot-before-timing-test` and `win98-se-tape-driver-disabled-dos`. Neither is labelled a working desktop checkpoint. The first launch used instruction-count timing; a separate no-icount run progressed through hardware migration. End-to-end boot time is not accepted yet. Native PCI host, ISA, IDE and power-controller drivers have now been installed from local Windows INF files, and Windows requested a restart. Checkpoint `win98-se-qemu-pci-drivers-before-reboot` was saved and verified before accepting that restart. Cirrus display installation did not complete in the initial copy-file flow; original Cirrus/SuperVGA files were staged on a private read-only floppy for a retry. That initial failure was subsequently repaired through native Device Manager; see the final verification below.

An optional new 8 GB FAT32 copy was prepared with `dev/prepare_windows98_compact.py`, preserving the original boot code, its FAT32 second-stage sector, filenames, timestamps and attributes. It is not the default launcher and has not yet been boot-accepted. The smaller filesystem is intended to avoid the community disk's large DOS compatibility scans. Original source and migration disk are preserved.

## Tests and remaining work

Three automated tests pass for the asset exporter: native multi-image ICO payload/offset preservation, malformed-preview fallback retaining the original ICO, and BMP wrapping/new-output protection. A separate hash reread verified all 5,130 core SE ICO/BMP/loose output files and 2,088 Plus! 98 files with zero mismatches. Version evidence is in `private/asset-libraries/windows98-version-evidence.json`. Native boot/migration screenshots are retained under `private/screenshots/windows98-se-*`.

Normal desktop boot is now verified. The Cirrus Logic 5446 driver was successfully reinstalled through the native Device Manager, then activated by reboot. Settings was changed to 800×600 at 256 colors and explicitly kept in the timed confirmation dialog. PNG dimensions were checked after settling and again after an ordinary Windows Restart. A real PS/2 pointer double-click opened My Computer, whose contents completed loading. The visible VM is left at that usable state. The reviewed My Computer capture and its source/configuration metadata are also sealed read-only at `private/screenshots/reference/windows98-se-community-plus-my-computer/`; the metadata identifies the community OS source separately from the original driver ISO and explicitly limits acceptance to functionality, not a stock pixel baseline. Verified working checkpoints: `win98-se-working-desktop-800x600-256`, `win98-se-browser-ready-800x600-256`, and final `win98-se-working-final-800x600-256`. The temporary read-only driver floppy was ejected before the final checkpoint. A live restore of that final checkpoint succeeded, with the VM running, My Computer fully rendered, and its actual framebuffer still 800×600; evidence is `private/screenshots/windows98-se-checkpoint-restored.png`. Native evidence: `private/screenshots/windows98-se-desktop-800x600-256-settled.png`, `windows98-se-normal-reboot-verify1.png`, and `windows98-se-my-computer-settled.png`. The initial resolution Keep timed out once; that was detected by checking the actual 640×480 framebuffer, and the incorrectly named provisional checkpoint was removed. Subsequent confirmation was completed promptly and actual dimensions were verified.

Remaining hardware nodes, including the inherited VMware pointing-device entry and unidentified devices, still need classification; this is a working reference, not complete hardware acceptance. A clean Windows 98 first-edition installation and separate untouched stock SE baseline have not been established. Product-level Windows 95/98 feature/profile switching remains future work.
