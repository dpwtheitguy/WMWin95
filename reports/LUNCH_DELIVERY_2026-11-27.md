# Lunch delivery validation — 2026-11-27

Status: deployed supported subset; remaining native-fidelity and wizard gaps are explicit below.

## Namespace icon movement

The missing My Computer/Control Panel drag-start branch is implemented separately
from filesystem transfers. Stable namespace/view/label keys persist positions.
Large and Small icon modes permit manual placement when Auto Arrange is off;
List and Details remain ordered. Escape and outside-client release cancel.
Root independently reran actual XTest pointer checks in the Linux guest at
800×600 and 1280×720; both passed seven behavior groups. Captures and reports are
under `/home/developer/win95lx-lunch-qa-20261127/private/screenshots/` in the guest.
The existing full namespace/computer regressions are being rerun. Native default
Auto Arrange and broader fidelity verification remain separate acceptance work.

## Printers

The distribution Python CUPS binding was installed in the development guest,
without creating queues or changing authorization/defaults. Existing isolated
backend tests and measured queue UI are being integrated into Explorer.
Root review found malformed PostScript font commands: receiving raw bytes did
not establish renderable test-page output. A second finding is that successful
read-only GetServerSettings does not establish queue administration privileges.
Both are corrections required before the new applet is accepted.

## Recovery

Verified checkpoint: `before-printers-namespace-lunch-20261127`. Preserve user
files and preferences on session refresh. Do not call an unfinished wizard or
absent hardware functional; state remaining capabilities precisely.

## Integration review findings and corrections

- Original shell32 GROUP_ICON29 is the shared-folder hand, not the shortcut
  arrow. Desktop and Explorer now use GROUP_ICON30. The previous shortcut pixel
  test incorrectly called resource29 an arrow; corrected to the independently
  inspected original arrow resource, with real renderer identity checks in the
  Printers shell suite for both consumers.
- Shared namespace clipping cut two columns (30 pixels in the selected-label
  reference) off Control Panel's selection label in My Computer. Reserve two
  pixels of client padding without moving the measured icon origins. Keep the
  existing exact original comparison; do not change its baseline.
- The prepared native IE4 My Computer view has Auto Arrange unchecked. Default
  new My Computer views accordingly, preserving explicit saved preferences.
  Native nesting under View/Arrange Icons remains an acknowledged menu-layout
  discrepancy in this functional increment.
- Printer test-page font commands corrected and validated by Ghostscript.
  Read-only settings access no longer grants a presumed administration flag;
  production defaults to own-document operations and empty password callback.

Printers is a supported subset: real inventory, existing queue windows, user
default, test-page submission and own-document cancellation. Add Printer remains
unimplemented, gray-labeled with a reason; no installed virtual test queue is
left in the user's session. Physical printing on real hardware and full wizard,
properties/menu parity remain unaccepted.

## Delivered evidence

Release `/opt/win95lx/releases/59dbd3dd304c5c52` is active in the visible guest.
The desktop session was refreshed without deleting user files/preferences.
Root opened Control Panel (11 entries), navigated normally to Printers, verified
empty real CUPS inventory and the gray Add Printer entry, then returned to
Control Panel. Actual QMP tablet pointer input moved C: by60×25 guest pixels.
The live desktop shortcut now visibly has the arrow overlay.

Final combined guest log: `private/lunch-20261127/final-combined.log`:355 tests
run, two skips (opt-in AccessX unit test and unavailable licensed Fontconfig
fixture); no reported failures. The UI suite additionally exercises AccessX
input on an owned server. All `check-ui` targets completed, including existing
reference, common-dialog, folder-window and menu checks. Independent final
namespace target passed both resolutions; log `final-namespace.log`. The SSH
client disconnected before the combined command returned; completion was
verified from the final1280 reference output, absence of make/errors, and exit
of the owned make process rather than an asserted captured exit code.

The source snapshot remained frozen during these final checks. The inactive
Desktop Themes prototype was excluded from deployment; it is not a new applet
in this release. Full hardware printing remains untested. Recovery checkpoints:
`before-lunch-activation-20261127`, `printers-namespace-ready-20261127`.

Live framebuffer evidence (unscaled):
- `private/lunch-20261127/live-desktop.png`
- `private/lunch-20261127/live-computer-before.png`
- `private/lunch-20261127/live-computer-dragged.png`
- `private/lunch-20261127/live-control-panel.png`
- `private/lunch-20261127/live-printers.png`
