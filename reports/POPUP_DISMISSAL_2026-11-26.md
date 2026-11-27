# Popup dismissal and input grabs — November 26, 2026

The user's deployed Multimedia dropdown trapped pointer interaction. Escape recovered the live session without a restart. Its shared ChoicePopup listened for button presses on the child DrawingArea, but GTK redirects outside clicks to the grabbed popup Window. Consequently an outside tab click never reached its dismissal handler.

The corrected popup listens on its Window as well, translates root coordinates explicitly, releases its own grab on every exit, and replays an outside press to the actual target once. Parent destruction, direct destruction, broken grabs and focus loss clean up without stealing focus back. Late events cannot call the closed popup. Tab transfers focus after committing; Ctrl+Escape/Alt+F4 reach the parent without cancelling unrelated pending edits. Callback/parent references are cleared on close.

The same pattern was found in VolumePopup and FontMenu. All three now use `apps/popup_events.py` for shared coordinate translation/outside-event replay. Each retains its own lifecycle/controller behavior. FontMenu also guards deferred actions if its parent has closed.

## Evidence

`dev/check_popup_dismissal.py` uses actual XTest pointer events on an isolated matching X11 display, a fake audio service and disposable HOME. Ten cases cover the Multimedia dropdown → Video tab sequence, Escape, Return, real row selection, outside-window click delivered once, Tab, actual focus transfer, Fonts File → View menu switching, Fonts parent destruction and dropdown parent destruction. Initial completed runs at both resolutions covered the shared dropdown; the extended Fonts/shared-helper run is under `private/screenshots/popup-dismissal-shared-20261126-800/`. Combined guest regression supplies the final two-resolution checkpoint.

Volume's independent eight-case pointer audit passed at 800×600 and 1280×720, including a held-button parent destruction, slider clamping, cleanup and worker termination. Removing its new Window press listener reproduced the original causal failure: grab remained, target activation count zero. Evidence: `private/performance/volume-grab-20261126/REPORT.md`.

The standalone no-window-manager focus test must explicitly transfer GDK focus; `present()` alone did not change focus. That fixture was corrected before accepting its result. These checks establish event/grab behavior, not complete native popup pixels or general X11 window-manager stacking. Native volume-popup pixel acceptance and broader global-modal routing remain separate work.
