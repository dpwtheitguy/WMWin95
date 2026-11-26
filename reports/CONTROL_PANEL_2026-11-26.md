# Control Panel implementation and acceptance — November 26

This is an intermediate implementation report, not acceptance of every applet. Six applets have routes; several contain unfinished features. Original assets, installer keys, downloaded media and VM disks remain private.

## Demonstrated implementation

- Shared property-sheet drawing, hit targets, pending edits, Apply/Cancel and backend rollback. Keyboard, Date/Time, Regional Settings and System join Display and Mouse.
- Keyboard repeat and language changes reach X11/XKB; the taskbar language indicator switches the active group. Accepting an unchanged language preserves an existing variant. Four-layout capacity is explicit. Windows `.DRV` binaries are incompatible; normal device management is through the Linux kernel.
- Date/Time has a calendar, editable clock, native timezone labels and DST selection. The real backend uses timedatectl; automated interaction tests use a fake clock to avoid changing the host. Guest policy was installed successfully and is scoped to the active local non-admin account. End-to-end guest authorization and real-clock rollback remain acceptance work.
- Regional Settings controls number, currency, time and date formatting. Calculator, Notepad timestamps, WordPad date insertion and taskbar time consume applied preferences. Measurement units are persisted but do not yet change WordPad's ruler; this feature is unfinished. Additional locales, historical currency presets and non-Latin glyph coverage need work.
- System reports actual memory and devices from procfs/sysfs. Device type/connection grouping and refresh work. Hardware-profile editing, device removal and printing are unfinished and disabled with reasons.
- Resolution discovery retains 47 predefined modes and actual advertised modes within the server limits. Geometry tests cover all predefined sizes. This does not establish physical monitor, host-viewer or real RandR acceptance at all 47 sizes.
- Optional native palette conversion preserves the Python conversion exactly in tested random, boundary, alpha and 256-color cases. Private 4K CPU-render measurements improved from approximately 178 ms to 11–21 ms/frame depending on scene. This is not a boot-speed or end-to-end latency measurement.

## Evidence and test scope

`make test` passes 137 unit tests, including snapshot verification. `dev/check_control_panel.py` at 800×600 and 1280×720 exercises real isolated X11 repeat/layout changes, pending edits, Cancel, persistence, Control Panel routes, native popup input, real inventory and Regional Settings consumers. The full `make check-ui` run completed successfully inside the development guest, including Explorer transfers, menus, native file dialogs and reference regions at both resolutions. Its guest log is `/home/developer/control-panel-ui-latest.log`. Later Keyboard capacity/variant and Mouse work-area changes receive a separate targeted rerun.

The report at `private/screenshots/cpl-check-full-timezone-fixed-1280/report.json` records nine zero-difference full-sheet comparisons: Keyboard Speed, Keyboard Language and Date/Time Time Zone, each against classic, IE4 and Plus configurations. These claims cover those recorded default states only. Dynamic edited states, other tabs and all applets are not automatically pixel accepted.

Independent original captures: `private/screenshots/cpl-20261126/`. Implementation captures: `private/screenshots/cpl-check-full-timezone-fixed-1280/`. Performance inputs: `private/evidence/control-panel-20261126/performance-before-4k.json` and `performance-after-4k.json`.

## Better reference measurement

`tools/native/w95probe.c` uses original Win32 APIs to record actual child-window geometry, font metrics, visibility, enabled state, combo contents and slider ranges alongside a lossless BMP. It changes the selected tab, not settings. The first working IE4 capture is `private/reference-tools/ie4-probe-native/keyboard-0.JSN`, with 25 controls, 404×448 sheet, 201×29 trackbars and original ranges. The corresponding native bitmap was reviewed. Build for i386: a compiler's default i686 instructions fault on the reference's Pentium CPU.

Do not infer HWND geometry from a painted GroupBox border. The probe measures the Keyboard page origin at (13,51); template conversion therefore requires explicit measured origin and font base. Do not reuse a guessed global origin. Small PS/2 packets prevent the capture artifacts seen with huge monitor mouse deltas. Release mouse buttons before parking the pointer.

`dev/snapshot_vm.py` verifies snapshot existence and refuses name collisions or writable raw media that prevent complete snapshots. Verified IE4 checkpoint: `native-probe-i386-working-20261126`. Original working references remain visible.

## Version verification and installer blocker

Archive media was downloaded privately at the user's request and checked against Archive metadata size/SHA-1, with SHA-256 recorded. Hash agreement establishes transfer integrity, not vendor authenticity.

- Archive item `windows-95-oem` contains OSR2 build 1111, despite its apparent RTM suitability.
- Item `windows-95-CD-ROM-OSR1-English` contains RTM build 950 with no service-pack suffix, despite its OSR1 label.
- An archived Windows 95 service pack was obtained for an eventual separate OSR1 comparison; its INF specifies the `a` suffix. It has not been installed or accepted.

A separate visible FAT16 RTM VM boots original Setup, but rejects the previously supplied OEM keys. No keys were generated and no license check was bypassed. A matching licensed RTM key/media is needed before this reference can be accepted. Existing classic, IE4 and Plus VMs are three configurations of OSR2.5, not three OS releases.

## Remaining applets and Linux integration

| Applet | Intended backend | Remaining acceptance/implementation |
| --- | --- | --- |
| Accessibility Options | XKB AccessX | Sticky/Filter/Toggle/MouseKeys, visual alerts and Apply/Cancel |
| Add New Hardware | udev/kernel inventory | Safe discovery wizard, Linux driver details; Windows driver binaries unsupported |
| Add/Remove Programs | dpkg/APT | Package list, install/remove with authenticated transaction handling |
| Desktop Themes | Original Plus assets/session settings | Full atomic theme application and restore |
| Display | RandR/session renderer | Screen Saver and Appearance tabs; full resolution/input matrix |
| Fonts | Fontconfig/per-user font directory | Preview, installation/removal, cache refresh |
| Internet | Browser/proxy/certificate settings | Define supported browser integration and implement |
| Modems | ModemManager | Device detection and settings; gray hardware-specific controls only when no device exists |
| Mouse | X11/cursor library | Custom scheme management, trails, third-party cursors, remaining XOR/runtime states |
| Multimedia | PipeWire/PulseAudio/ALSA | Device selection, levels, recording and working playback tests |
| Network | NetworkManager | Profiles, identification, adapter configuration and authenticated changes |
| Passwords | PAM | Password-change flow without storing passwords |
| Power | DPMS/UPower/logind | Timeout, battery/AC capability detection and policy |
| Printers | CUPS | Add, configure, default, queue and print test |
| Regional Settings | Per-user formatters | Measurement-unit consumers, locale/font coverage and historical presets |
| Sounds | Event mappings/audio playback | Native Sounds UI and event routing; original command is `control mmsys.cpl @1` |
| System | procfs/sysfs | Remaining actionable hardware/profile functions and native visual states |
| Users | Account/session services | User/profile management with explicit authentication |

These are implementation gaps, not claims that Linux has no analog. Date/Time and Keyboard also retain the limitations above. Continue applet-by-applet, requiring real effects, failure rollback, keyboard and pointer paths, persistence, original state captures and pixel reports before acceptance.
