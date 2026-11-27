# Multimedia Properties — November 26, 2026

The Audio tab now changes actual PulseAudio/PipeWire preferred playback and recording endpoints and master levels. Advanced displays actual endpoint properties. This is not acceptance of every Multimedia feature or an entirely pixel-identical applet.

## Implementation

`MultimediaWindow` uses the shared property sheet, five original tab frames, shared dropdowns, native bitmap text and transactional pending settings. Original frames come from the reviewed classic reference at (22,22), 366×448. Native `MMSYS.CPL` and `SNDVOL32.EXE` version resources report 4.0.0.950. The source VM is the existing OSR2.5 installation using its classic shell configuration.

The Audio backend reads the service's real defaults and channel volumes. It changes playback and recording defaults independently, preserves stereo balance and existing mute state, and restores touched defaults/levels if application fails. The master slider remembers a nonzero channel ratio when crossing zero so raising the level again does not center a previously unbalanced stereo mix. A fresh backend with no prior nonzero observation cannot recover information absent from an all-zero service state.

Only the saved volume-icon preference is reused when opening the sheet; actual defaults and levels win over stale persisted values. An unrelated change while the sheet stays open also merges fresh endpoint/level values. Deliberate device or level changes retain the selected target. Default changes affect the session's preferred devices; this does not forcibly migrate every already-running application's stream.

`AudioPreferences.tray` and the Apply callback expose the volume-icon setting to the shell. The root implementation owns the corresponding tray and popup integration. `PulseAudio.set_playback_volume()` and `set_playback_mute()` operate on the current default output without changing recording settings. Original speaker-wave and muted-speaker icons are staged from SNDVOL32 groups 304 and 303. Group 300 is the mixer-window application icon and must not be used as the tray speaker.

## Tests and evidence

- **12 unit tests pass** in `tests/test_audio_preferences.py`. They cover actual defaults, monitor exclusion, default selection, volume/mute preservation, channel balance through zero, external-setting merges, unrelated changes, device disappearance, failed-transaction rollback, invalid inputs, Cancel and persistence.
- `dev/check_multimedia.py` passes at **800×600 and 1280×720** in a separate guest QA checkout. It exercises slider pointer release, keyboard endpoints and steps, device-popup keyboard selection, pending isolation, Apply, tray callback, Cancel, reopen after external changes, tray-only Apply after an external level change, unavailable devices/service, and Advanced properties.
- Both runs exercise actual PipeWire/Pulse operations on two owned null sinks and one remapped test input: default selection, 37% playback, 63% recording, mute/unmute, 44% playback and service readback. Tests restore previous defaults/levels and unload their modules. They do not change physical endpoint levels or establish audible microphone/speaker operation.
- **13 named region comparisons per resolution pass with zero differing pixels**: caption/tabs and bottom command area across all five tabs, Audio group right border, and both enabled combo arrows. This does not establish whole-sheet equality of active audio controls, edited fields, dropdown-open states, Advanced contents or disabled Video/CD controls.
- Direct Audio-sheet drawing over 20 frames measured median **0.630 ms at 800×600** and **1.122 ms at 1280×720** during the recorded guest runs. These are CPU render timings with simulated endpoints, excluding service calls, PNG encoding, compositor, viewer and input latency.

Accepted captures and identity-bearing reports:

- `private/screenshots/multimedia-20261126/check-accepted-800x600/`
- `private/screenshots/multimedia-20261126/check-accepted-1280x720/`

The isolated guest checkout is `/home/developer/win95lx-multimedia-qa`. Integration through the live Control Panel route and the shell's volume popup requires the root agent's combined checks and deployment.

## Defect discovery

1. A label's broad clear rectangle erased 56 pixels of the group-box right border. It now clears measured text width; the added border comparison detected the old capture and passes after correction. Before: `private/screenshots/multimedia-20261126/check-800-r2/audio-reopened-actual-level.png`.
2. Moving to a tab with no active custom controls focused OK and introduced an 84-pixel bottom-button mismatch. Tab changes now preserve the tab's native focus state until the user traverses controls.
3. Enabled preferred-device fields initially reused the disabled gray arrow and placed its gutter one pixel too far right. They now use the original enabled arrow and 17-pixel gutter; independent native-arrow comparisons cover both fields.
4. Old saved levels could override external changes on reopen or an unrelated tray-only Apply. Actual state now seeds the sheet, and untouched endpoint/level pairs merge current service values on Apply.
5. Root's popup integration exposed loss of stereo balance after 0→100%. Both backend application paths now retain the last nonzero channel ratio, covered by a regression.
6. With no audio service, accepting unchanged unavailable-device settings could fail instead of closing. That no-device operation now succeeds; the controls remain unavailable with reasons.

## Remaining capabilities

| Control/tab | Status and reason |
| --- | --- |
| Playback preferred device and level | Functional via PulseAudio/PipeWire; actual audibility and physical-device acceptance still need guest hardware checks. |
| Recording preferred device and level | Functional for genuine inputs. Playback-monitor sources are excluded as microphones. Physical recording quality/input remains separate acceptance work. |
| Volume icon | Preference and callback implemented; combined shell/popup behavior is owned by root's integration. Native popup whole-window comparison remains pending. |
| Preferred recording quality / Customize | Disabled: shared recording/export configuration has not been connected to a recording application. This is unfinished integration, not a Linux limitation. |
| Use preferred devices only | Disabled: per-application forced routing is not implemented. Normal preferred-device defaults work. |
| Video window/full-screen defaults | Disabled: no shared media-player integration yet. Original layout is retained; complete changed/disabled-state comparison remains pending. |
| MIDI | Disabled: Linux MIDI output/synthesizer configuration has not been implemented. Windows driver binaries cannot be installed into Linux. No unsupported claim of missing MIDI hardware is made. |
| CD Music | Disabled: analog drive/headphone mixer integration is unfinished. Digital playback uses the ordinary output endpoint. No unsupported claim of missing physical CD hardware is made. |
| Advanced | Actual audio endpoint inventory and properties work. This is not yet the complete native tree of codecs, MIDI, capture, joystick and media drivers. |
| Common property-sheet behavior | Shared base provides Apply/Cancel, tab navigation, caption drag, close and Help. Full native system-menu behavior remains shared acceptance work. |

## Root integration

Route `MultimediaWindow(shell)` through the applet catalog/accessory builder. Add `stage_multimedia_assets.stage(output)` to asset preparation and merge its returned provenance records. Add `dev/check_multimedia.py` at both viewport sizes to the regression target. Preserve all original media, frames, icons and device evidence under `private/`; the public code contains no original assets or keys.
