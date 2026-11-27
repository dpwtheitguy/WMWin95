# Windows 95 hidden features

Requested 2026-11-27. These are product requirements, not currently accepted
features. Continue Control Panel development independently.

## Product-team credits

Verify the exact ordered desktop-folder rename sequence against an original
Windows 95 reference. Trigger on successful normal folder creation/rename, not
merely on finding a final filename. Keep state per folder identity, clear it on
an unrelated rename, and do not modify or delete its contents. Capture the actual
credits animation, text, timing and music; preserve original assets privately.
Do not invent Microsoft credits or substitute a modern credits window.

Tests: ordered sequence; wrong order; final name alone; two interleaved folders;
canceled and failed renames; unrelated names; escape/close; repeat launch;
references at native size and larger viewport. Document release differences.

## Volcano 3D Text screensaver

Verify which prepared Windows/Plus configuration contains the screensaver and
capture its settings and Volcano behavior. Implement through the screensaver
settings and preview, not an unrelated menu command. Obtain the actual word list
from authorized local resources and verify case matching, rotation, font, color,
motion, idle entry and pointer/key dismissal. No assumed volcano geography.

Tests: ordinary custom text; Volcano trigger; save/cancel/reopen; preview versus
idle activation; pointer/key exit; focus restoration; multiple resolutions and
animation CPU cost. This requires the missing screensaver runtime/settings path.

## CLSID namespace folders

This is shell functionality, not an Easter egg. Verify recognized directory
suffixes in the original. Implement a central allowlisted mapping from GUID to
existing namespace providers; never execute arbitrary COM, programs or shell
commands from a name. Cover My Computer, Control Panel and Recycle Bin first;
validate Fonts, Printers and other providers as each becomes functional.

Preserve the real directory and its contents. Unsupported/malformed GUIDs must
remain ordinary folders. Files with similar names must not become namespaces.
Use one resolver for folder opening, names, icons, address bar, shortcuts and
keyboard activation; do not implement an open-only shortcut that looks broken.

Tests: mixed GUID case; valid prefix/suffix parsing; unknown and malformed GUIDs;
regular files; rename in/out; copying/moving; restart; keyboard and pointer open;
provider icon and friendly name; normal folder fallback and preserved contents.

## Acceptance

For all three, record reference edition/shell version, native and implementation
captures, source identity, behavior tests and remaining discrepancies. No feature
is complete merely because this requirements document exists. Deploy only after
reference and guest validation, following the applet handoff policy where relevant.
