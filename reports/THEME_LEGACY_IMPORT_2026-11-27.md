# Native Windows 95 theme import checkpoint — 2026-11-27

## Implemented and verified

The Themes applet's existing Other/Open workflow now reads complete original Windows 95/Plus INI `.theme` definitions as data. It resolves local original wallpaper, all fourteen cursor roles, event WAV files, and four desktop icon roles; imports original colors, fonts, and metrics; and maps only installed, allowlisted screen saver identities. It does not run theme commands or write arbitrary registry sections. Existing owned Win95LX definitions retain their versioned format and corruption checks.

Open changes the pending preview only. Cancel preserves every preference-file byte. Apply uses the existing transactional providers, and an independent controller reopening reconciles the imported definition. Icon decoding creates bounded content-addressed private cache PNGs; cancellation does not delete that reusable cache, but leaves user preferences untouched. Source definitions and media are never changed. Missing media produces a native framed error and retains the previous selection. Overwrite and deletion use the same store/token contracts as managed themes; deletion removes the definition, not its media.

The parser supports original CP1252 and BOM UTF16/UTF8, quoted filenames, case-insensitive local media names, and the installed Microsoft Sound alias. An original WIN95HC.THM contains a stray valueless `av` line: it is harmless INI noise and no longer blocks import. Original `[Metrics]` NONCLIENTMETRICS/ICONMETRICS bytes are decoded, rather than relying on the empty WindowMetrics section. Unknown application sound scopes cannot replace global sound events.

## Acceptance evidence

- `python3 -m unittest discover -s tests -p 'test_theme*.py'`: **186 passing**; 42 dedicated legacy import cases cover genuine encodings/data, typed components, resource bounds, malformed media, paths, collisions, caching, preference isolation, and no executable evaluation.
- `python3 -m unittest discover -s tests -p 'test_screensaver*.py'`: **119 passing**, including queued warmup cancellation and releasing the scheduler's own group lease before preparation.
- `private/legacy-theme-import-20261127-v3/all-original-imports.json`: all twelve original Plus definitions import eight components, fourteen cursor roles and four icon roles. Genuine reference assets remain private.
- `private/legacy-theme-import-20261127-v3/native-current-import.json`: native saved Current Settings definition imports eight components, including default/reset associations.
- `private/theme-import-ui-800-v2/report.json` and `private/theme-import-ui-1280/report.json`: physical Other/Open filename input, missing-media error dismissal, preview-only Open, Cancel/no writes, repeat Open/Apply, and independent reopen pass. Seven actual host providers; Wine absent on host, so screen saver is omitted rather than simulated.
- Isolated guest `/home/developer/win95lx-legacy-import-real-proof-v2/report.json`: actual eight-provider Open/Cancel/Apply/reopen pass with installed Wine/runtime catalog. No visible user desktop restart was performed. A subsequent SSH attempt on port 22295 was closed, so the latest quiet runtime recipe was not rerun in this checkpoint.
- `private/theme-import-shared-regression-800/report.json`: physical Save As/Apply/reopen/Delete-No/Delete-Yes pass; thirty distinct component compositions save/apply/reopen successfully. These thirty compositions are provider integration workflows, not thirty separate physical GUI runs.
- `private/themes-full-preset-regression-800-v2/report.json`: all thirteen genuine presets apply/reopen, including Windows Default. Construction 3.30 ms, first draw 12.11 ms, measured Apply 152.05 ms in isolated host QA; these are samples, not a percentile performance claim.

## Original appearance catalog staging

New `tools/stage_theme_appearance.py` enriches the existing private catalog from original source INI definitions with colors/fonts/metrics, and adds original Windows Default data. It records thirteen source hashes/provenance records. Run it after the base theme/icon stages. Parent release packaging owns integrating this stage into `prepare_assets.py`; this checkpoint used a separate private QA catalog.

A real defect found by the thirteen-preset smoke test was the Themes sound factory dropping built-in Windows Default when loading Plus schemes. The factory now merges built-ins with the staged schemes. The initial failing run is retained separately from the passing rerun.

## Remaining discrepancies and limits

This is functional import acceptance, **not full imported-theme pixel acceptance**. Frozen preview illustration layers and raw Control Panel bitmap art do not yet follow every imported color/font/metric; semantic runtime providers are only the supported subset. Arbitrary modern partial `.theme` definitions, unknown DLL/EXE icon-resource libraries, and executing custom saver binaries are explicitly unsupported. Captured original default COOL.DLL icon indices map to the native default/reset provider; genuine ICO media imports without rescaling. Source filename extensions must be `.theme` in this Open workflow; raw installer THM files are private corpus fixtures, not a newly advertised UI format.

The embedded monitor saver preview remains disabled with a reason. A Win32 HWND host must be clipped and occluded correctly within the shell's virtual windows before enabling it; a Linux XID or unbounded foreign overlay would be incorrect. Full-screen Preview and original Settings remain separate existing lifecycle features.

No production release, VM deployment, or git commit was performed by this child task.
