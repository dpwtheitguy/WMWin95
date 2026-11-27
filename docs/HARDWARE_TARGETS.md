# Hardware validation targets

User decision, November 26: ThinkPad T480 is the primary physical target; L570 and T14 AMD are additional targets selected partly for their restrained business-PC appearance. All are **planned targets, not hardware-validated support claims**. Exact machine types, panels, Wi-Fi cards and other device variants must be recorded before certification.

The installed development base is Xubuntu 24.04 LTS amd64. Win95LX supplies the custom desktop and built-in applications; Ubuntu supplies kernel, drivers and packaging. Keep broad Linux/x86-64 compatibility rather than hard-coding Lenovo-only checks. The present QEMU guest guard is a development safeguard, not a future hardware allowlist.

Prefer an 8th-generation Core i5 T480 with integrated graphics and matte 1080p IPS as the first representative configuration. An L570 with its optional installed DVD drive adds real optical-media testing. Select a specific Linux-supported T14 AMD generation/configuration when that machine is acquired. T480 has no internal optical drive.

For each machine, validate installation/live boot without destructive disk changes, boot time, graphics modes/scaling, pointer hotspots, TrackPoint and touchpad, real drag traces, keyboard controls, Wi-Fi/Ethernet/Bluetooth, audio, display brightness, battery/charging, suspend/resume, storage/removable media and external monitors. Record exact device/driver IDs and failures. Device Manager should present those actual Linux devices through native-looking General/Driver/Resources/Diagnostics pages, with future management actions separately scoped and tested.

Steam is a later optional gaming component. No Steam, Proton, game or Office-style software is installed by this plan. Gaming capability is per hardware configuration; do not imply the integrated-GPU T480 is a universal modern-game target.
