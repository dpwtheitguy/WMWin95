# Sounds scheme field correction — November 26, 2026

The scheme text clearing rectangle began at x26, outside the native combo HWND
at x33. It erased the border and surrounding padding; the text at x29 was eight
pixels left of the measured native x37.

The corrected field preserves the native bevel and arrow, clips the label inside
the client, and aligns drawing, popup placement and pointer hit bounds with the
300×21 native HWND. The text origin is (37,336), independently established by
matching the original Windows Default glyph pixels.

## Evidence

Original classic Windows 95 reference: native metadata
`private/reference-tools/sounds-control-spy-metadata/SNDSEL.JSN`; framebuffer
`private/screenshots/command-buttons-20261126/sounds-field-selected3-native.png`.
The original reference was restored to its verified pre-spy checkpoint.

`dev/check_sounds.py` passed at 800×600 and 1280×720. At both resolutions, the
310×25 region including GroupBox padding, full closed combo and selected scheme
text had **zero differing pixels**. Reports and full captures:

- `private/screenshots/sounds-alignment2-20261126-800/report.json`
- `private/screenshots/sounds-alignment2-20261126-1280/report.json`

Long-label clipping checks preserve all surrounding edges and arrow. Existing
Sounds interaction scenarios also passed, including selection, preview process
control, browse, custom scheme confirmation, Apply, Cancel, reopening, failure
rollback, event dispatch and silent No Sounds. Audio decoding used a null sink;
this does not establish hardware audibility.

This acceptance covers the closed scheme field and listed regression scenarios.
Open-list pixels, custom Save Scheme dialog fidelity and all system sound event
hooks remain separate work. The correction has not been deployed to the user's
visible manual-test session. No new latency claim was measured for this fix.

The corrected Sounds fields and native command-button integration also passed
the complete isolated guest `make test check-ui` run; consolidated log
`private/combined-ui-20261126.log`. Save As uses the native Alt+S mnemonic; the
shared renderer transfers its default/focus state.
