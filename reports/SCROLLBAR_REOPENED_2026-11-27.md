# Scrollbar fidelity reopened

The user reported the live Notepad vertical bar again after the ten-applet
handoff. Root captured the unmodified live framebuffer at
`private/screenshots/notepad-scroll-review-20261127.png`. The original empty
Notepad capture is `private/screenshots/gtk-scrollbars-20261126/native-notepad-empty.png`.
Both contain a white track: changing it wholesale to gray would contradict this
reference. The earlier GTK audit explicitly accepted only exposed track colors
and visibility, not the entire arrow/thumb/border/corner geometry. That limited
scope did not satisfy the user's full-control requirement.

Full GTK control comparison and fixes are assigned to the existing controls
worker; Printers work is temporarily parked. No live user document was changed
or closed to obtain the capture. No fix is claimed by this report.

Inventory reviewed: Notepad, WordPad and both common-dialog GTK scrollers;
Cairo Explorer file lists, namespace horizontal/vertical bars, Web View details,
Display backgrounds/patterns, Mouse role list/scheme popup, Sounds, Device
Manager, Fonts and font preview, ChoicePopup and unregistered Add/Remove lists.
The seven existing shared scrollbar rendering unit tests pass; that establishes
only their tested primitive states, not acceptance of every consumer.

Acceptance must include complete native control regions, empty and overflowing
documents, top/middle/end, corner geometry, Word Wrap, resize, focus/disabled and
physical pointer states at multiple resolutions. The controls skill now states
this full-control gate explicitly. Deployment follows corrected guest tests;
the visible VM remains available to the user meanwhile.

## User correction

The user subsequently withdrew the defect report and confirmed Notepad matches
the original. No appearance change or deployment is needed for this report.
The controls worker has returned to Printers. The isolated shared consumer check
completed with zero failures; full-control coverage remains a future validation
improvement, not evidence of a newly reproduced defect.
