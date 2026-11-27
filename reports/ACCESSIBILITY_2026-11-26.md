# Accessibility Options — November 26, 2026

**Workspace-integrated prototype; not deployed or accepted as a complete applet.** The enabled subset has actual nonadmin XKB input effects, Apply/Cancel/persistence/rollback tests and narrowly scoped pixel evidence. Unsupported integrations are disabled with reasons. No live Linux VM, physical keyboard/pointer, host font configuration or system policy was changed by this work.

## Native reference and assets

Existing five-tab captures under `private/screenshots/cpl-20261126/classic-reviewed-run2/` were reviewed before implementation. New independent captures and HWND metadata are preserved under `private/accessibility-20261126/{native,metadata}/`. The classic VM was checkpointed and deliberately restored after each capture session:

- `before-accessibility-capture-20261126`
- `before-accessibility-filter-capture-20261126`

Both checkpoint creations were verified. The probe floppy was ejected before restoration, returning its original empty state. No Accessibility changes were committed in the Windows reference. The classic reference was released to the parent agent afterward.

Measured native main window: **367×443**, origin **(132,125)** in the new captures, page (13,51,341,349). This corrects the provisional image-only estimate of366×442. StickyKeys/MouseKeys Settings measure347×374; FilterKeys and its Slow/Repeat advanced sheet347×407; ToggleKeys and advanced Bounce sheet347×201. The 13-pixel MS Sans Serif font has dialog base6×13 at96dpi.

`tools/stage_accessibility_assets.py` stages eleven measured frames, two genuine checkbox sprites, two genuine radio sprites, native layout metadata and source hashes. It also extracts and asserts the original ACCESS.CPL timing tables; **SlowKeys includes1400ms, not an assumed1500ms**. Its19 provenance records retain binary hash/data offsets, capture hashes and measured rectangles. Original binaries, probe programs and art remain private.

## Working subset

`access_preferences.py` implements a pure validated model and session XKB backend. Changes merge with current controls, preserving ordinary keyboard repeat, layout/group/per-key state and unrelated AccessX bits. It detects external changes in represented options, verifies applied state, bounds native buffers/masks, and restores on failure. An unrelated repeat change from Keyboard Properties is preserved without a false conflict. Wayland is explicitly unavailable: changing an Xwayland virtual keyboard must not be described as configuring the compositor's physical input.

`AccessibilityWindow` uses the shared PropertySheet/CommandButton, mnemonic parsing, ChoicePopup and word-wrapping helpers. The measured child dialogs keep edits pending in their parent; child Cancel discards them. Parent Apply updates the real session, atomically saves JSON and keeps the sheet open. Parent Cancel discards only unapplied edits. Save failure restores the previous real XKB settings and previous JSON, with a native error message that does not expose a Linux path. Reopening reads actual session state rather than overwriting it with stale saved values. Root has registered the saved-session hook in Shell startup. It is verified through fresh Shell/backend processes and a newly spawned isolated X server; an actual guest reboot remains unaccepted.

The currently enabled UI supports StickyKeys, modifier locking/two-key cancellation, FilterKeys Bounce/Slow modes with original nonzero timing choices, MouseKeys on/off, and idle-reset enable/minute selection. Existing server values outside the original preset lists are shown rather than silently replaced on open.

## Tests and exact evidence

`WIN95LX_XKB_UAT=1 WIN95LX_ACCESS_EVIDENCE=private/accessibility-20261126 PATH=<extracted-test-tools>:$PATH python3 -m unittest discover -s tests -p test_access_preferences.py` passes **25 tests:24 CPU/model/persistence/fixture-guard cases and one actual-input regression**. Without opt-in,24 pass and the input regression is skipped. The final unit log is `private/accessibility-20261126/startup-unit-verified.log`.

The input regression creates and owns its Xvfb server using `-displayfd`, `-nolisten tcp` and `-noreset`, selects only that returned display, removes Wayland inheritance and terminates only its owned server. It proves:

1. A released Shift latches for one following letter and then clears.
2. Pressing a modifier twice locks it across letters; another press unlocks it.
3. Two simultaneous modifiers actually disable StickyKeys.
4. SlowKeys suppresses a brief key and accepts a key held beyond200ms.
5. BounceKeys suppresses an immediate repeat and accepts another after its delay.
6. MouseKeys moves the actual isolated pointer from x400 to456 using the keypad.
7. Idle reset disables StickyKeys after subsequent input and the configured timeout.

It restores and byte-compares the original raw XKB controls. `-noreset` prevents a test-only server from resetting state between short-lived clients. Actual input output is preserved at `private/accessibility-20261126/actual-input.log`.

`dev/check_accessibility.py` independently creates its own Xvfb and disposable HOME/config/data/cache, verifies the actual X11 display before any window is created, and tests real XKB/file effects as **uid1000**. Final evidence:

- `private/accessibility-20261126/startup-800-verified/`
- `private/accessibility-20261126/startup-1280-verified/`

Both runs pass at exactly800×600 and1280×800. They test the complete checkbox hit rectangle at its bottom-right edge, outside-release cancellation, Alt+U, pending edits, Apply, child Cancel, nested Bounce/Slow slider keyboard endpoints, MouseKeys activation, timeout dropdown keyboard selection, actual service readback, injected save failure with exact real-state/JSON rollback, reopening, disabled-control routing and accessible Help reasons. The six-choice popup is asserted to have no scrollbar gutter; this applet owns no vertical scrollbar. No custom white scrollbar track was introduced.

Each run has **ten zero-difference named comparisons**: five caption/tab bands, focused unchecked StickyKeys, checked FilterKeys radio, wrapped multiline FilterKeys radio, Bounce slider minimum and Slow slider original default. This is not whole-dialog acceptance; checked/disabled/focused controls, other thumb positions, tooltips and full applet geometry still need more original-state captures.

Current single-run timings, on warm test processes:

| Display | Constructor | First draw | Open plus fixed150ms test settling |
| --- | ---: | ---: | ---: |
| 800×600 | 7.933ms | 11.575ms | 161.641ms |
| 1280×800 | 8.730ms | 17.476ms | 163.206ms |

The settling column must not be reported as render latency. These are small operation samples, not statistical or boot performance guarantees. Reports contain source/test/manifest/provenance hashes, actual backend/display, uid and successful raw-state restoration.

## Defects found and corrected

- Native flags need both ControlsEnabled and the selected feature mask. MouseKeys timing belongs to **MouseKeysAccel**, not MouseKeys. Real service/input checks caught these mistakes.
- Dormant feedback bits must not accidentally become active when another feedback option is enabled.
- A second outer rollback after the backend already rolled back was redundant and could cause unnecessary writes; it was removed.
- The native write boundary now validates snapshot length/type and allowed masks before C memory access or display writes.
- Immediate action after switching tabs could read stale layout metadata and fail opening the timeout dropdown; layout selection now updates in tab_changed.
- Checkbox text starts atx+18; its13-pixel box starts aty+1; native focused text has a solid16-pixel rectangle. Initial renders were wrong; measured regions now have zero differences.
- A mnemonic at index0 was omitted by shared Painter.menu_text. Root corrected that helper; the local workaround was removed and both final viewport runs use the shared fix.
- Filter radio wrapping now uses the shared width-aware label helper instead of guessed line breaks.
- Trackbar thumb origin, half-up tick rounding, three/four-pixel tick heights and recessed track edge pixels were measured and corrected. Source-derived timing data avoids an incorrect1400→1500ms assumption.

## Remaining integrations and disabled features

| Feature | Current status / reason |
| --- | --- |
| StickyKeys | Enabled subset and real latch/lock/two-key effects verified; complete checked/focus/disabled visual states remain unaccepted. |
| FilterKeys | Nonzero Slow/Bounce modes work. Repeat override, no-repeat mode, zero-hold SlowKeys combined with repeat filtering, and the local pending-settings test field are unfinished. Ordinary Keyboard Properties repeat remains untouched. |
| Individual feature shortcuts | Disabled: XKB groups Sticky/Slow shortcuts; independent Windows shortcut and native warning handling is unfinished. Mouse/Toggle shortcut integration is unfinished. |
| ToggleKeys / feedback sounds | Disabled: audible route/output and original sound behavior have not been validated. A stored XKB flag is not accepted as working audio. |
| MouseKeys Settings | Disabled: native speed/acceleration mapping, Ctrl/Shift speed modifiers, Num Lock routing and shortcut/status integrations are unfinished. Main MouseKeys enable works and actual pointer movement is proven. |
| Status indicators | Disabled: taskbar/status integration is unfinished. |
| SoundSentry | Disabled: central sound-to-visual-warning integration is unfinished, not a lack-of-hardware claim. |
| ShowSounds | Disabled: program notification/caption integration is unfinished. |
| High Contrast | Disabled: shared bitmap-control palette/theme integration is unfinished; changing GTK theme alone would not recolor custom controls correctly. |
| Extra keyboard help | Disabled: shared-application hints integration is unfinished. |
| Feature warning | Disabled: native shortcut warning dialog integration is unfinished. |
| SerialKeys | Disabled: serial device selection and serial-to-input service integration are unfinished. Hardware absence has not been assumed; no blanket input permissions were granted. |
| Startup persistence | Workspace Shell hook, fresh backend/process restoration and a new isolated X server session pass. Actual guest reboot persistence remains unaccepted. |
| Integration/version scope | Root integrated the workspace catalog, launch route, staging and Makefile checks. No guest deployment/live-entry acceptance. Measured classic96dpi reference only; independent IE4/Plus/large-font-state coverage remains. |

Primary technical references: [X.Org XKB library specification](https://xorg.freedesktop.org/releases/current/doc/libX11/XKB/xkblib.html), [X.Org XKB protocol specification](https://x.org/releases/current/doc/kbproto/xkbproto.pdf), [XkbGetControls](https://xorg.freedesktop.org/archive/X11R7.5/doc/man/man3/XkbGetControls.3.html). Original VM pixels/metadata and local licensed ACCESS.CPL data determine the Windows presentation and preset values.


## Startup follow-up acceptance

The final GUI harness now restricts its fixture backend to the exact still-running, same-user Xvfb PID/display created by its parent, and checks the `-displayfd`/`-nolisten tcp` arguments. Wrong displays, missing PIDs, non-Xvfb processes and Wayland inheritance are rejected before enabling writes. The production guest identity guard was not bypassed globally; only the startup backend constructor is replaced inside the disposable test process by this owned-server fixture.

At each viewport, the harness saves a valid profile, resets raw XKB state, then launches a fresh Shell/backend process and proves that startup restores the saved values. It repeats on an independently spawned Xvfb server with a new disposable HOME seeded from that prior profile: the new server's defaults actually change to the saved state. The nine `startup-*.log` artifacts per run record the distinct displays, uid1000, actual guard calls and mutation/no-mutation result.

Malformed JSON, a list, null, a non-boolean option and unknown keys all leave the original raw control bytes unchanged. A denied startup fixture guard is called but cannot mutate controls; a subsequent valid startup still succeeds. This exposed a real startup error-handling gap: unknown keys/list/null can raise TypeError, which the original Shell catch did not include. Root added TypeError to that catch; the final fresh-process tests exercise the fix. Both viewport runs still pass all ten named pixel comparisons and restore the original raw controls at completion. This does not substitute for a full guest boot/reboot acceptance test.
