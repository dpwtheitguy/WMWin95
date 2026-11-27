# Native Windows 95 command buttons — 2026-11-26

The reusable renderer is accepted for the measured standard-color, 96-dpi command-button states. This is component acceptance; live property-sheet integration remains a separate check.

## Implementation and contract

`src/win95lx/shell/command_button.py` exposes `draw_command_button`, `metrics`, `parse_label`, and `resolve_default`. The renderer accepts a Painter, raw Win32 mnemonic label, HWND rectangle, default/focused/pressed/enabled flags, and optional explicit mnemonic. Returned metrics expose text origin, focus rectangle, and exact hit containment. Text, bevels, underlines and focus remain clipped inside the HWND. `resolve_default` transfers default emphasis to the enabled focused command, otherwise the designated enabled command.

Measured details corrected relative to legacy Painter.button:

- Default black border is inside the HWND. Legacy code painted 200 pixels outside a 75×23 HWND; the new renderer paints zero outside.
- A 13-pixel font in a 23-pixel button starts at y+4, with pressed text shifted one pixel right/down.
- Focus rectangle is solid in the measured native Windows 95 BUTTON states: inset3 normally and inset4 inside a default button.
- Default pressed border differs from normal pressed border. Disabled text and its mnemonic have the original white/shadow emboss.
- Ampersand mnemonics, escaped ampersands, exact integer bounds, enabled default transfer and disabled focus suppression are explicit behavior.

## Independent source evidence

`tools/stage_command_button_assets.py` contains a small Win32 harness that creates the original Windows USER32 BUTTON class and captures GDI pixels inside the Classic reference VM. Its compiler targets i386/Pentium, without newer CPU instructions. Private binary, C source, raw BMPs, native BM_GETSTATE/style/font metadata and SHA256 provenance remain private.

The matrix contains **80 independent native captures**: widths75/108, height23, five labels and eight states (normal/default/focused/focused-default/pressed/pressed-focused-default/disabled/disabled-default). Eight additional real CPL controls validate focused Add, focused Properties, normal Add, disabled Remove, normal OK, disabled Set as Default and focused/default Add Language OK/Cancel. These are **88 unique source cases**, not 176 independent source cases because two viewport sizes replay the same native references.

Private accepted source matrix: `private/reference-tools/command-buttons-native/W95BTNS/`. Staged original PNGs and catalog: `private/command-button-assets/`. No original images or binaries are added to public source files.

## Results

- 10 unit tests passed: `python3 -m unittest discover -s tests -p test_command_button.py`.
- 800×600: **88/88 exact, zero differing pixels**. Report/screenshots: `private/screenshots/command-buttons-final2-800/`.
- 1280×720: **88/88 exact, zero differing pixels**. Report/screenshots: `private/screenshots/command-buttons-final2-1280/`.
- Cases are placed at three canvas origins, exercising translation and edge placement without resampling.
- Median draw CPU time: **0.1028ms** at800×600 and **0.0988ms** at1280×720; excludes image encoding, native process startup and event-loop latency.
- Legacy default-border out-of-HWND defect is reproduced by the regression harness; the accepted renderer clips all state painting, including overlong text and small rectangles.

## Genuine native geometry lessons

Raw Win32 spy metadata is in `private/reference-tools/command-button-spy-metadata/{KEYBOARD,ADDLANG}.JSN`. Keyboard is404×448. Add/Properties/Remove rectangles are(33,202,108,23), (147,202,108,23), (261,202,108,23); Set as Default is(261,236,108,23). Raw labels are `A&dd...`, `P&roperties` (no ellipsis), `Re&move`, `&Set as Default`, `OK`, `Cancel`, `&Apply`.

Add Language actual HWND origin is(33,55), size347×171; OK is(177,133,75,23), Cancel(257,133,75,23). An older template crop started at(35,57), omitting frame pixels. Acceptance now uses HWND metadata, not a cropped template's origin. Both real child-button comparisons remain exact with corrected HWND-relative metadata. This geometry discrepancy was reported to the integrating agent.

## Sounds field follow-up

A native Sounds spy and selected-scheme screenshot were captured without Apply, then the Classic VM was restored to the verified `before-sounds-field-spy-20261126` checkpoint. Sounds HWND origin(132,120), size367×448. Schemes control id5382 is CBS_DROPDOWNLIST, rectangle(33,332,300,21), field item height15, MS Sans Serif13/ascent11/external-leading0; there is no Edit child and EM_GETRECT is inapplicable. Exact original bitmap-glyph matching against the selected Windows Default screenshot proves text origin **(37,336)**, offset(+4,+4), with zero glyph-pixel mismatch. Metadata: `private/reference-tools/sounds-control-spy-metadata/`; screenshot: `private/screenshots/command-buttons-20261126/sounds-field-selected3-native.png`. A previous unsaved scheme generated the native Save Scheme prompt; No was chosen and no scheme was applied.

## Capture failures and limitations

An earlier W95P2 floppy launch failed with Cannot Find; six subsequently named press captures showed an error/Start menu and are excluded. A second floppy hot-swap triggered a native disk-change error; that capture is also excluded, with checkpoint restoration before the successful fresh spy run. These are reference-tooling failures, not product defects. The first matrix harness had JSON escaping errors; only the corrected v2 matrix metadata is accepted. The checker additionally fixed relative --assets paths before writing evidence identity.

Scope is Classic Windows95 OSR2.5 standard colors, 96dpi, MS Sans Serif13, the measured text-command states and one independently supplied IE4 focused-Add crop. This does not claim all releases, large-font DPI, arbitrary control heights, checkboxes, radio buttons, caption controls, owner-draw/image buttons, GTK interaction, viewer scaling, or keyboard command routing. Root owns live PropertySheet integration and its functional input checks. No Linux desktop restarts or deployments were performed during the user's manual testing.

## Shared PropertySheet integration follow-up

The measured renderer is now integrated into PropertySheet's deferred command drawing. Native raw command labels register mnemonics; enabled command focus chooses the single default border. Bottom OK/Cancel/&Apply are drawn dynamically, including disabled Apply. Keyboard Language uses actual command HWND bounds and raw mnemonics. Add Language uses the corrected347×171 frame, initial OK focus, true button/combobox coordinates, reverse Tab and Enter on focused Cancel. Ctrl+Esc forwards to the shell without Cancel or discarding pending edits; this does not establish a complete global hotkey grab or solve keyboard routing through every unrelated modal toolkit window.

Defect discovery found that dragging a held command pointer outside its hit rectangle retained a pressed appearance. PropertySheet now retains the command for release validation while removing its pressed visual outside the bounds; dragging back in restores the pressed appearance. Release outside does not invoke the command. Disabled command rectangles are excluded from enabled hit dispatch.

Final isolated GTK/X11 evidence is `private/screenshots/buttons-x11-final-{800,1280}/report.json`:14 comparisons per resolution, all zero pixels, including two complete Keyboard sheets, focused/default transfer, disabled states, actual handler pointer press/drag-outside/release tolerances and both Add Language focus states. Alt+D/R dispatch, Alt+A Apply, reverse Tab, focused Cancel Enter, and Ctrl+Esc pending preservation are exercised against a deterministic backend. The display is asserted to be X11 and match DISPLAY; WAYLAND_DISPLAY is unset and GDK_BACKEND=x11 is forced. Earlier GTK runs inherited `wayland,x11` and are excluded as display-isolation acceptance evidence, even though their separately rendered Cairo pixels matched.

Full Control Panel checks also passed in the Linux guest at800×600 and1280×720 inside their own Xvfb sessions and `/home/developer/win95lx-buttons-qa` source copy:18 pixel comparisons and10 functional groups per size, no failures. Local copies: `private/screenshots/buttons-full-guest-{800,1280}/`. These runs validate real X11 repeat/layout Apply/readback, pending Cancel/persistence, Control Panel/shortcut routes, System inventory, Date/Time three-profile pixels and mocked clock backend, and Regional integration with Calculator/Notepad/WordPad. Full checks preceded the final pointer-outside visual adjustment; the final targeted X11 checks validate that adjustment. No host or guest live display/settings were changed. Shared preview assets/source were untouched; corrected child frames were staged only in a private test view. Root will regenerate shared assets and run the consolidated final suite.

`docs/CONTROL_TOOLBOX.md` now directs command buttons to this renderer and separates caption-button scope.
