# Mouse typed command-button migration — 26 November 2026

Migrated ordinary Mouse Properties commands to the measured shared command-button renderer, retaining specialized MouseController, pointer/animation paths and the independently measured white pointer-list track. No global Painter replacement or other widget migration was performed.

## Behavior and scope

Mouse now registers command specifications before painting them. The complete enabled set resolves one default: enabled focused command, otherwise OK. Native raw labels include `&Apply`, `&Browse...`, `Use De&fault`, `Sa&ve As...`, `&Delete` and `&Change...`. Disabled commands have no enabled hit target or mnemonic. Enter invokes the focused enabled command rather than always applying OK. Holding a pointer outside removes pressed appearance; moving back restores it; release outside invokes nothing. The source frame's old default is replaced inside its actual HWND bounds.

MAIN.CPL dialog resources provide Pointer command labels; independently sampled native regions also verify enabled Change and footer labels. Native Save As and Change are enabled in their original source frames, while our unfinished scheme-save/driver-replacement capabilities remain disabled. Their native disabled **BUTTON state** is accepted separately; do not call our complete Pointers/General page identical to an enabled original. Capability behavior/reasons are unchanged.

Defect discovery during construction found that a deferred command pass placed after the original popup code would repaint Save As/Delete over an open scheme list. Corrected layering so the existing scheme popup paints last. Existing expanded-list interaction checks pass. Source changes remain confined to `apps/mouse.py`.

## Independent native matrix

Captured **64 original USER BUTTON cases**, eight actual Mouse labels × eight normal/default/focus/pressed/disabled combinations, 75×23 HWND plus a two-pixel parent margin, original 13-pixel MS Sans Serif, standard colors,96dpi, OSR2.5+IE4. Producer source/binary, raw BMPs, measured style/BM state/font metadata and hashes are private under `private/reference-tools/mouse-commands-native-20261126/`. Checkpoint `before-mouse-command-native-20261126` was verified, restored after capture, and the previous empty floppy state restored. No Mouse setting was committed in the original VM.

Reproduce private reference staging with:

```
python3 dev/check_mouse.py --stage-command-references private/reference-tools/mouse-commands-native-20261126 --output private/shell-assets
```

The script stages `mouse-command-references.json` and hash-verified native PNGs. Those are private QA fixtures, not public assets. It does not read a moving Git HEAD. The one-off before reproduction below archives its exact historical commit/source independently.

## Before and after

Same pending speed change and Apply focus. Before: **685 differing pixels** against the independent native focused/default Apply HWND plus parent margin. After: **zero**. Comparison rectangles, hashes and archived historical source identity are in `private/research/mouse-command-buttons-20261126/before-after-apply.json`.

![Before Mouse command correction](/home/dwilson/Documents/Windows95/private/research/mouse-command-buttons-20261126/before-apply-focused.png)

![After Mouse command correction](/home/dwilson/Documents/Windows95/private/research/mouse-command-buttons-20261126/after-apply-focused.png)

## Validation

**11 unit tests pass**: five new Mouse command tests plus six existing Mouse preference/controller tests. New tests cover deferred painting, enabled hit dispatch, unique default transfer, disabled-focus fallback, raw mnemonic/focused Enter routing, boundary/reenter/release tolerances and **all64 independent native button-state cases with zero differences**. Native matrix tests explicitly skip if licensed private fixtures are unavailable; no bitmap is embedded in public source.

Forced-X11 `dev/check_mouse.py` passed independently at **800×600 and1280×720**. Per run: **61 pixel comparisons, all zero**, and14 recorded functional groups. Pixel scope includes the entire default404×448 Buttons sheet, each actual command instance on all four tabs, focused/default/pressed/held-outside commands and Use Default after a real custom-CUR fixture enables it. Pointer/key events additionally verify held-out cancellation, reentry, release-in once, focused Cancel Enter, enabled Apply mnemonic and Ctrl+Esc pending preservation.

Existing actual isolated X11 mapping/acceleration, GTK double-click timing, original32-frame test animation, all14 cursor roles, scheme dropdown, pointer-thumb endpoints before/after custom cursor, Browse/Use Default, Apply/Cancel/persistence, Control Panel routes and reopening passed. The repeated pointer-thumb group uses distinct ordinary/custom-cursor contexts. These tests own a private Xvfb server and temporary HOME and restore its original pointer configuration; they do not change the user's visible desktop or physical pointer.

Final JSON, screenshots and source/test/reference identities: `private/screenshots/mouse-commands-final-{800,1280}-20261126/report.json`. Unit log/source hashes: `private/research/mouse-command-buttons-20261126/`. Compilation and diff checks pass.

This is standard-color96dpi command acceptance and recorded Mouse integration, not every Mouse control/theme/DPI/physical-device acceptance. Remaining Mouse trails, named-scheme management, Windows driver replacement, arbitrary-surface XOR cursors and broader window-manager focus/stacking work remain documented in the existing Mouse report. Root owns combined guest release review; no live Linux release was deployed by this work.
