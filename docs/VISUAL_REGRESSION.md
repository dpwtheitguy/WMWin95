# Exact-pixel acceptance workflow

No authentic reference captures exist yet. Synthetic tests validate tools only; they do not demonstrate Windows fidelity. Seven acceptance screens and manual action sequences are in `config/acceptance.json`.

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
