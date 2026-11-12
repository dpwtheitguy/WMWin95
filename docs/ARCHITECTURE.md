# Win95LX architecture

Status: proposed architecture and working acquisition/comparison tools. No desktop shell has been deployed or measured.

The reference is the installed original shell, not Chicago95. Use an isolated Windows VM for evidence and a separate maintained Xubuntu/XFCE X11 VM for implementation. Never install experimental desktop settings onto the development host.

| Module | Responsibility | Initial boundary |
| --- | --- | --- |
| Shell and desktop | Start menu, taskbar, focus, icons, keyboard, mouse | Evaluate xfce4-panel, xfdesktop, xfwm4 before replacement |
| Explorer | Windows filesystem presentation, drive mappings | Audit Thunar before any fork; do not launch it in normal mode until approved |
| Control Panel | Applet registry, shared dialog navigation | Only registered, implemented applets appear |
| Applets | Display, input, system properties | Separate modules using shared geometry and resource IDs |
| Applications | Approved native replacements | Explicit allowlist, no automatic fallback to Linux apps |
| Assets | Resource selection and rendering | Private originals, content hashes, provenance; no assets in packages |
| Sound | Original event mapping and playback | User process, no root service; mapping remains empty until extracted evidence exists |
| Installer | Guest-only session/profile packaging | Stage, inspect, approve, apply with backup and rollback |
| Regression | Sealed references, captures, exact diffs | Independent Python standard-library tools |

Use configuration and small patches before proposing forks. If GTK dialog geometry or text rasterization cannot reproduce the reference, prototype a shared bitmap-font and classic-controls renderer. Define bevels, focus rectangles, menu state, hit regions and accelerators once, then test each control. Do not implement isolated cosmetic lookalikes.

A drive-letter model maps C: to an authorized user data root. Canonicalize paths and enforce boundaries before filesystem operations; a display name must never grant additional access. Device permissions, filesystem ACLs, modern kernel protections and updates remain intact.

Normal mode exposes only accepted applications and applets. Unsupported features are hidden. Administrators enter a separate maintenance session through the display manager using normal system authentication/PAM. Hiding Linux interface elements is presentation, not an authorization mechanism. No shared admin password, automatic privilege elevation, disabled updates, or Win95 security emulation.

Record keyboard/focus ordering, double-click timing, drag thresholds, menu opening/closing, selection, resize limits, modal behavior and shutdown cancellation alongside visual screenshots. Pixel equality alone does not establish behavioral equivalence.

## Implemented milestone

`src/win95lx/assets/bitmap.py` decodes private original glyphs/icon images. `shell/model.py` manages internal window/menu state independently of GTK. `shell/widgets.py` defines the shared pixel primitives, bevels, buttons and bitmap text. `shell/app.py` binds GTK events to the desktop surface. `explorer/presentation.py` enforces the bounded read-only drive view; `control_panel/applets.py` registers the currently informational applets.

The renderer is a development harness and first shell surface, not a complete window manager. Only internal windows are managed. No unreviewed external application is launched. This permits controlled study of bitmap text, hit regions and classic widgets while the XFCE configuration baseline is evaluated. No XFCE/Thunar fork has been created.

The shell is a separate X11 login session. Omitting XFCE panel/shortcut components removes the observed Ctrl+Esc conflict without modifying global key settings. A non-admin guest account runs the shell; authenticated maintenance uses a separate developer account. Releases are root-owned, content-addressed and promoted after runtime import validation. Virtual-disk checkpoints provide recovery independent of the user profile.
