# Exact-pixel acceptance workflow

Seven acceptance screens and manual action sequences are in `config/acceptance.json`. Use original VM captures to judge Windows fidelity.

1. Boot the recorded reference disk, restore the same state, resolution, color depth, theme, locale and window positions. Record pointer position and whether the capture includes the cursor. Wait for disk activity and menu animation to settle. Use the same policy for the Linux capture.
2. In QEMU monitor, issue `screendump /absolute/private/path/capture.ppm`. This captures the guest framebuffer, excluding viewer decorations. Whether the pointer is present must be recorded; don't mix framebuffer and host viewer captures.
3. Convert without resizing: `python3 tools/ppm_to_png.py input.ppm output.png`. The converter accepts QEMU's P6, 8-bit format without comments. Other PNG sources must use RGB/RGBA 8-bit noninterlaced encoding; palette and other formats are rejected explicitly.
4. Prepare capture metadata with `iso_sha256`, `vm_version`, `guest_version`, `color_depth`, `capture_method`, `steps` and `pointer_position`. Include actual CPU, machine type, display driver, font settings and scaling as additional fields.
5. Seal the capture: `python3 tools/seal_reference.py capture.png clean-desktop --metadata capture.json`. Sealing copies into a new directory, stores a hash and marks files/directory read-only. These protect against accidental edits, not malicious owner/root access. Keep a separate offline read-only reference backup. Never update a baseline to make a failing implementation pass.
6. Create a comparison JSON (paths relative to its location):

```json
{
  "reference": "../private/screenshots/reference/clean-desktop/reference.png",
  "reference_sha256": "COPY_HASH_FROM_CAPTURE_JSON",
  "actual": "../private/screenshots/implementation/clean-desktop.png",
  "masks": []
}
```

7. Run `python3 tools/compare.py config/clean-desktop.json --output results/clean-desktop-run-001`.

Results contain the exact config, SHA-256 of both images, differing pixel count and percentage, masked/compared count, exclusive XYXY bounding box and magenta difference image. Equality compares decoded RGBA values, including alpha, with no tolerance. Different PNG encodings can represent equal pixels. Size mismatch is an error, never a resize. Exit codes: 0 exact match, 1 mismatch, 2 invalid inputs. Output directories must be new. Reference hash mismatch aborts before producing a result.

Masks are optional rectangles `{ "rect": [x,y,width,height], "reason": "specific dynamic content" }`. They require a reason, valid bounds and a nonempty comparison area. The tool reports excluded pixels. Review each mask; there is no percentage threshold that makes broad masks acceptable. Prefer fixing the clock/time and pointer state instead of masking. Do not mask text, borders, menu geometry or font defects. Only an actual zero-difference run may be described as pixel-equal for its particular screen/configuration.

## Current implementation smoke run

`dev/capture_shell.py` records seven deterministic input sequences against the real guest. `private/screenshots/implementation/run-004/` includes the corrected modular shell, full-size PNGs, source hashes and action histories. The seventh image is explicitly a development “Close Desktop” dialog, not the required authentic shutdown acceptance screen. These runs do not compare to an original reference and cannot pass pixel-accuracy acceptance. New reference captures must be sealed separately; never move these implementation images into the reference baseline.

## Menu-to-content boundary

Run `make check-menu-seams` after changing a built-in app's menu, frame, or content border. The target needs the GTK/Pycairo runtime, `xvfb-run`, and the staged private shell assets. It renders the actual app windows at 800×600 in a disposable X11 display and reports unexpected color rows around each menu's bottom edge.

The expected rows preserve Notepad's gray-and-black inset, WordPad's toolbar edge, Calculator's separator, and Minesweeper's raised board edge. Compare with an original capture before changing an expected boundary.

Run `make check-ui` for the accessory checks plus the rendered Explorer seam, Notepad File menu geometry, and native pixel-region checks for Start, the Background tab, centered wallpaper, and the task button frames. It runs at 800×600 and 1280×720. It also drags the Background scrollbar thumb and switches tasks. Use `dev/check_reference_ui.py --output <new-private-directory>` under the same Xvfb geometry to save implementation screenshots. See `docs/CONTROL_TOOLBOX.md` for reusable controls and the inventory.

## Compare a control at different window origins

Capture lossless guest framebuffers from each VM. Run these commands from the checkout with the guests showing the same state.

```sh
python3 tools/qmp.py --socket private/run/windows95.qmp capture private/screenshots/original-control.png
python3 tools/qmp.py --socket private/run/xubuntu.qmp capture private/screenshots/win95lx-control.png
```

Add a region to the comparison JSON. Use the independently measured top-left origins in the two captures and one shared width and height.

```json
"region": {
  "reference_rect": [66, 66, 404, 415],
  "actual_origin": [100, 65]
}
```

The report shows the exact changed-pixel count, bounding box, affected rows and columns, and the most common reference-to-actual color changes. Coordinates and any masks are relative to the compared region. The region run also writes `comparison.png` with the original crop, implementation crop, and magenta difference map at 1:1. Compare a neighboring row or column when testing seams. A narrow stripe can indicate an extra bevel or a displaced edge. A repeated color pair across a solid region can indicate an incorrect palette value.

Measure three things separately. Check native control pixels at 800×600. Repeat the same regions at a larger guest resolution to catch layout or font scaling. Then resize the host viewer and check the outer control bounds and click targets at native size and at a fractional zoom. Record the host zoom and framebuffer size. A guest pixel match and a viewer input match are separate results.

For every screenshot bug, capture the exact failing state, add a region check that includes the defective pixels, and add an input test when selection, focus, drag, or keyboard input changes that state. Re-run the new check against the old build when practical to prove it detects the defect. The Settings tab currently checks the native idle frame and Apply artwork, plus slider dragging, keyboard endpoints, confirmation, and rollback flow.

Display Settings now also checks the full open Color palette and Font size lists against the original. The interaction check applies Large Fonts, verifies mouse hit testing at 125%, checks the taskbar icon and preference persistence, and verifies Cancel. Color depth choices convert Win95LX wallpaper rendering while X11 remains at its configured depth. Advanced Properties reports guest information.

The Explorer regression uses temporary files for Edit menu commands, Cut, Copy, Paste, folder drag, and Close. Unit coverage verifies that moving into an occupied destination preserves both files and that copying a folder into itself fails without creating a partial folder.

## Common file dialogs

The file dialog check in `make check-ui` runs at both guest sizes. It compares Open and Save As caption, toolbar, list seam, and action rows to the original Notepad captures. It checks the full Untitled close prompt and the static regions of missing-file and overwrite prompts. It exercises directory navigation, filtered lists, extension handling, and both overwrite responses. Dynamic folder contents, the editable filename, and application-specific filters are tested separately from the original artwork.

Notepad Help is checked through the real menu and About action. The check verifies the popup width, row order, separator, hidden F1 accelerator text, dialog size, and native caption, default button, and frame pixels at both guest sizes. The content identifies Win95LX and uses the app's icon.

## Independent folder windows

`dev/check_folder_windows.py` runs through `make check-ui` at 800×600 and 1280×720. It opens separate Source, Target, and Nested windows over a disposable filesystem and drives the real pointer and keyboard handlers.

| Check | Required result |
| --- | --- |
| Switch and reopen | Each path retains its own selection and scroll position. An already open canonical folder regains focus. |
| Move and Ctrl-drag | Folder-to-folder and desktop-to-folder moves update both listings. Ctrl-drag preserves the original, including an already selected source. |
| Folder to desktop | The moved file appears on the desktop and disappears from the source listing. |
| Collision and cancellation | Occupied destinations preserve both files. Escape cancels a drag. |
| Open folder moved | An open child window follows its directory to its new path. |
| Icon placement | Positions persist under a key specific to the folder. Another folder's positions stay independent. |
| Window overlap | Covered windows cannot receive drops through the covering window. |
| Font scaling | At 120 dpi, real pointer coordinates still reach the intended source and destination. |
| Native regions | Compare the compact menu strip and a 32×32 folder icon at its measured origin against original VM captures. |

The large-icon grid is measured at 75×75 pixels, with its first icon image at (27,55) relative to the compact window. Captures `native-independent-folders.png` and `native-independent-folders-compact.png` record the original guest's two-folder state. These are regional comparisons. They do not establish equality for the entire Explorer screen or its other view modes.

For icon rearrangement, redraw the drag preview before delivering the button release. The desktop's moving folder sprite can appear under the pointer in the new hit map. Dragged items are excluded from folder drop targets. The regression verifies that rearranging a desktop folder or ending a short folder-icon drag over itself never calls the filesystem transfer operation. Re-enabling the previous target behavior makes this test fail by attempting to transfer `Desktop/Loose Folder` into itself.

## Complete My Computer profile

`make check-computer-view` checks the full File popup, not a single Close glyph. Exercise empty selection, a drive, Control Panel, and ordinary file/folder selections through their respective profiles. Verify disabled rows have no active hit target, Alt+F chooses the first enabled row, mnemonics only invoke enabled commands, a blank click clears selection, and shortcut creation preserves existing files. Compare pressed headings, full bands, status hints and adjacent edges. Keep device inventory and clock settings separate from drawing defects. See `reports/EXPLORER_PARITY_2026-11-25.md` for the original fifty-observation disposition and remaining functionality.

## Combo field clearing and text bounds

Do not compare only the glyph rectangle after fixing a field alignment defect.
Capture the complete HWND plus adjacent GroupBox padding independently from the
implementation. Check the left/top bevel, client fill, arrow and lower edge
together. A dropdown list has no Edit child: use measured selection text pixels
rather than applying an Edit control's EM_GETRECT offsets. Clip long labels to
the client field and verify that they leave the arrow and borders unchanged.

Sounds native scheme geometry is `(33,332,300,21)` with text origin `(37,336)`;
its editable Name combo uses different geometry. The regression is in
`dev/check_sounds.py`, including a long custom label. Native evidence and
implementation captures remain separate under private screenshots.
