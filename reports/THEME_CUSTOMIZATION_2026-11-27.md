# Desktop Themes customization checkpoint — 2026-11-27

Save As, definition-only Delete, and Other/Open Theme now use the measured Plus! native dialog profile, shared filesystem navigation, transactional theme store, and actual wallpaper/pointer/sound/icon/color/font/metric providers. Save captures actual desktop settings; choosing a preset only changes pending selection. Save As is enabled for Current Windows settings and disabled for named themes, as measured in the original. Saving selects a pending definition and enables Apply; Cancel retains the saved definition without applying it.

## Original-VM evidence

Private evidence: `private/theme-customization-20261127/`. The reference checkpoint `before-theme-save-delete-20261127` was verified, restored after probes, floppy ejected, and QMP reported running. Modified original theme files used during research were confined to that reverted checkpoint.

* `save-current-metadata/STATE.JSN` and untouched BMP: Save Theme426×264; native HWND rectangles validated by the stager.
* `selected-nature-metadata/STATE.JSN`: despite the early directory label, the actual captured dialog title is Open Theme,426×264. This artifact is accepted only as Open Theme geometry, never as evidence for selected-Nature behavior.
* `delete-owned-metadata/STATE.JSN`: question366×119, Yes105,82,75,23; No186,82,75,23. Native Escape does not dismiss it.
* `external-saved-valid` and `external-reopen`: saving outside the managed folder scopes the combo to that folder; Cancel/reopen returns the default folder.
* Exported native definition `saved-definitions/T00.TXT` demonstrates actual component values, rather than only a preset name.

Delete's definition-only behavior is additionally supported by [Microsoft KB135959](https://jeffpar.github.io/kbarchive/kb/135/Q135959/). Native automation of the Yes post-state remained unreliable: a same-title popup caused ambiguous parent-window targeting. Those post-state attempts are rejected. No claim of observed automatic-next-preview behavior is made. External Apply/reopen folder persistence remains unverified.

## Validation

`dev/check_theme_customization.py` uses a disposable owned Xvfb and private HOME, actual GTK framebuffer captures, physical XTest SaveAs/button/filename input, and independent controller reopens. Reports distinguish actual physical-input checks from30 actual-provider composition workflows; these are not30 physical UI workflows. Compositions vary original Plus presets, color/background values, icon-font weight and caption metrics across30 component subsets. Each checks untouched providers, Save, Apply and reopen. Delete No retains the definition; Delete Yes leaves all seven live components unchanged. Real saved files are parsed through a fresh controller.

Passing evidence: `private/theme-customization-ui-800-final/` (800×600); `private/theme-customization-ui-1280-final/` (1280×1024, see generated report for result). Earlier v3 and1280 runs pass the simpler captured-current composition matrix; they are retained as earlier evidence, not substituted for the strengthened matrix. The separate theme CPU suite currently has115 passing cases. The full legacy Themes smoke also passes at `private/themes-crud-regression-800-v3/`, including native-region comparisons, physical input, rollback, conflicts, palette changes and all-preset reopen.

Defect discovery corrected: nonexistent first-run theme directory; canonical path matching on symlinked staged asset bundles; stale catalog on palette change; custom dictionary sounds/pointers crashing preset-only matching; missing wallpaper exception escaping drawing; unsupported checkbox provider activation; caption row spacing; unbounded long-name message text; absent Save/Open Other entry and definition operations. All current save/delete filesystem failures use native dialogs and plain Windows-style error text, without raw Linux exception paths.

## Honest visual/capability limits

Independent comparison of the original Delete question to actual GTK: question icon0/1024, body text0/4395 and No0/1725 differing pixels. Initial full question1257/43554 differed, including caption and shared default/focus button rendering. The focus/default mismatch came from this dialog's notify callback accepting GParamSpec as the selected response ID; the shared command renderer was correct. After correcting the callback and one native frame corner, the full366×119 Delete question matches0/43554 pixels at `private/theme-customization-ui-zero-800/pixel-diff.json`. This accepts this exact Delete question state, not Save/Open or the whole Themes applet.

Save/Open retains the shared GTK filesystem list behavior; its single-column list differs from the native multi-column common-file-dialog view. File/folder text is dynamic, not a baseline masked away. Main theme preview uses the prior static illustrative overlay; selected font/color/icon previews are not yet complete. Screen saver selection/configuration and Pointers, Sounds, etc. launch remain explicitly unavailable in this checkpoint. Raw legacy Microsoft `.theme` imports are rejected until their data-only translator is implemented; saved Win95LX `.theme` definitions work. No arbitrary registry or command sections execute. Full raw CPL recoloring and all system metrics are not claimed.

Recommended follow-up: finish native list-mode file dialog, measure and correct default/focus button state, implement data-only native theme import, wire complete preview components and saver capability, prove external Apply folder persistence, and independently compare original/custom long filenames, overwrite cancellation and repeated rapid modal transitions. Do not label the whole Themes applet complete based solely on this checkpoint.
