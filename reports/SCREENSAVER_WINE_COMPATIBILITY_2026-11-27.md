# Original Windows95/Plus95 screensavers under Wine — 2026-11-27

Research checkpoint; no product saver registration, idle policy, live desktop or reference VM changed. All execution below used an independently created Xvfb display and disposable32-bit Wine prefix inside the development guest, with Wine9.0 already installed.

## Main finding: Nature renders with the actual shared runtime

The earlier Nature probe's black frame was reproducible. Native installation manifest `private/reference/media/plus/PLUS.INF`, section MT_ss, installs **both WL32DLL.DLL and WILDLB32.DLL**. The earlier guest directory had only WILDLB32.DLL. MT_Nature_scr additionally installs NATURE.DLL as Nature.dll and WL32SCR.EXE as Nature.scr.

The corrected controlled experiment retains identical Nature.scr/shared-engine bytes and adds the **genuine original WL32DLL.DLL**. Loader logging confirms the genuine shared runtime and Nature.dll load. The actual framebuffer shows leaves and moving caterpillars. Between second3 and7,19818 of480000 pixels differ; final frame contains468598 nonblack pixels and156 colors. Physical mouse movement exits with code0.

Two negative controls distinguish this from a launch-only result:

- Missing WL32DLL.DLL: black at both samples, zero changed pixels, engine stays alive and dismisses on mouse.
- Incorrectly renaming Nature.dll to WL32DLL.DLL: likewise black, zero changed pixels. Nature.dll exports Initialize/DoDraw/Close, while the genuine runtime exports InitWildlife/GetSaverWindows/InitPreview/DisplayPreview/SuspendAnimation/DoWakeUp/ClosePreview. **Do not substitute or rename the themed library into the runtime's name.**

This is evidence for a missing dependency causing this particular failure, not a general claim that every black saver frame is a missing DLL.

Minimum Nature file set actually exercised:

| Installed name | Original CAB member |
|---|---|
| Nature.scr | WL32SCR.EXE |
| Nature.dll | NATURE.DLL |
| WL32DLL.DLL | WL32DLL.DLL |
| WILDLB32.DLL | WILDLB32.DLL |

Wine's builtin MSVCRT20/Win32 DLLs supplied ordinary system dependencies. Genuine WL32DLL also imports WINMM and WILDLB32. Logs contain ALSA32 Pulse configuration warnings, so this probe does **not** accept saver audio.

## Measured fullscreen cases

The source called windows95 is the existing local media extraction; this is not an independently verified RTM shipping-list classification.

| Case | Actual changed pixels3→7s | Dismissal | Result |
|---|---:|---|---|
| Nature, complete runtime |19818|mouse; exit0|Visible animation candidate|
| Starfield, ssstars.scr |142|mouse; exit0|Visible animation candidate|
| Mystify, ssmyst.scr |24094|mouse; exit0|Visible animation candidate|
| Plus Windows95/Blocks engine |165505|mouse; exit18|Visible animation candidate; nonzero exit still needs lifecycle interpretation|
| Plus Lens engine, unpatterned fixture |0|mouse; exit18|Initial fixture inadequate; see corrected patterned test below|

Lens manipulates underlying imagery. A subsequent owned Win32 popup paints a deterministic multicolor40px checkerboard and label before launch. The actual Lens framebuffer then shows a moving refracting sphere; its3s/7s frame digests differ. Mouse dismisses it cleanly with exit18. The initial uniform blue field was therefore a fixture deficiency, not evidence of incompatibility. Evidence: `private/screensaver-wine-20261127/lens-pattern/`. Native timing/geometry matching remains separate.

All savers were alive at7seconds. No comparison to original animation phase, timing or exact GDI output was performed, so these are compatibility candidates, not pixel-perfect acceptance.

## Remaining Plus95 themed aliases

Every remaining original WL32-themed alias was staged using the exact installer names and genuine shared runtime, then visibly rendered changing frames and exited0 on physical mouse movement. Each7s frame was visually inspected.

| Installed SCR/DLL base name | Original themed DLL |
|---|---|
| Dangerous Creatures | DANGEROU.DLL |
| Leonardo da Vinci | DAVINCI.DLL |
| The Golden Era | MODERNE.DLL |
| Sports | SPORTS.DLL |
| Mystery | MYSTERY.DLL |
| Inside your Computer | PCINSIDE.DLL |
| Travel | TRAVEL.DLL |

Together with Nature, all eight shared-engine thematic aliases now have positive fullscreen compatibility evidence. This does not imply every setting, sound, preview or native animation timing is accepted. Per-case installed-file SHA256 values, loaded-DLL logs and changing framebuffer digests are preserved in `private/screensaver-wine-20261127/plus-aliases/`. Fresh prefix initialization in this run took13.81seconds under concurrent probes; prior isolated preview took6.93seconds. Avoid inferring a production warm-start latency from either.

## One original settings persistence path

An additional owned Win32 automation helper locates the original Nature Mute Sound checkbox and OK/Cancel buttons, reads BM_GETCHECK, sends BM_CLICK through the real native control handler, then invokes the actual OK button. Checkbox state changes0→1. Reopening the original configuration as a new process reads1; the helper closes that second dialog with Cancel without changing it. After the owned Wine server exited, the persisted prefix user.reg still contains:

`HKCU\Software\Microsoft\Windows\CurrentVersion\Screen Savers`, DWORD value `Mute Sound`=1.

This is a shared Plus runtime preference, not a Nature-only field. Private `nature-settings/disk-persistence.json` records the exact persisted section and source-file digest. The control-state report records `0 1` then `1 1`; its original `dismissal_input: Escape` label is a checker reporting defect—the native helper actually used OK then Cancel. Current checker reports those native actions accurately. No other settings are accepted by this single path, and this was native message automation rather than a physical mouse click. Evidence: `private/screensaver-wine-20261127/nature-settings/`.

## Configuration probes

`/c` displays original configuration content for Nature, Starfield, Blocks and Lens; physical Escape dismisses each. Nature/Blocks/Lens returned1, Stars0. This is launch/cancel evidence only: no settings modifications, persistence or every-option acceptance is claimed.

The viewed Nature dialog under default Wine colors/fonts has visible layout/font differences and text overlap by the monitor/options section. Original binary execution does not automatically make its Wine-rendered controls match our native95 toolbox. Its system-agent/hot-corner wording also refers to a component we have not integrated. Do not advertise that original dialog as complete.

## Expanded parameter, Cancel and repeat qualification

The checker now performs three original configuration processes per tested presentation: change one real control and choose OK; launch the fullscreen saver and dismiss it; reopen, change the control again and choose Cancel; reopen a third time and verify the earlier saved value remains. These operations send native BM_CLICK through the original control handlers; they do not write the preference directly.

- All eight WL32 thematic aliases pass the Mute Sound cycle. As this is a shared runtime preference, successive aliases intentionally inherit and alternate the same saved value. Nature, Dangerous Creatures, Leonardo, Golden Era, Sports, Mystery, Inside your Computer and Travel each reopen with the correct value after the canceled second modification. All eight post-save fullscreen processes remain alive until physical mouse dismissal.
- Lens passes a distinct engine-specific radio cycle: Glass Sphere→Black Hole+OK; launch; Black Hole→Glass Sphere+Cancel; reopen still Black Hole. Original Options changes labels/defaults with lens type: Glass Sphere uses Index of Refraction, whereas Black Hole uses Mass and a different default size. That conditional UI is a requirement for the future native configuration renderer.
- Blocks passes its distinct Use Wallpaper checkbox cycle: Off→On+OK; launch; On→Off+Cancel; reopen still On.
- Physical Escape keyboard dismissal passes for Nature, Starfield, Blocks and patterned Lens, twice each. Every repeated run shows changing framebuffer digests. Cleanup reports confirm each owned Wine server was waited out and Xvfb exited0; no probe Wine/Xvfb process remained in the final scoped process check.

Evidence folders: `plus-settings-cycle/` (24 original dialogs+8 fullscreen post-save launches), `engine-settings/` (six original dialogs+two post-save launches), and `keyboard-repeat/` (eight repeated fullscreen runs), all under the private evidence root. A single parameter per presentation is covered; these results must not be inflated into every-option acceptance.

The first expanded configuration runs used capture delays3+1seconds. Their legacy filenames/JSON keys still say3s/7s, but metadata `capture_delays:[3,1]` gives actual samples at3s and4s. The current checker generates filenames from actual timing. These configuration stills are not being used as animation timing measurements.

Native persistent engine schemas observed after Wine-server exit:

- `...\Screen Savers\BLOCKS`: SizeOfBlock string, Speed DWORD, UseWallpaper string On/Off.
- `...\Screen Savers\LENS`: KindOfLens string; each of GlassSphere/InsideOut/BlackHole/Dent/Spiral has Size/Speed DWORDs and Parameter string; FlipBackground and UseWallpaper strings On/Off.

Exact installed aliases have now been tested separately: Science.scr persists under the Science section; The60'sUSA.scr under The 60's USA; Windows95.scr under Windows 95. Each passes change+OK/fullscreen/change+Cancel/reopen. These are independent sections despite identical engine bytes. Preserve installed identity and configuration scope in package metadata. Evidence: `exact-alias-settings/report.json` and `registry-sections.json`.

## Real Win32 preview probe

The owned CRT-free i386 helper creates a Win32 parent and child, publishes the decimal child HWND into its disposable prefix, and closes the parent on an explicit private-file signal. `/p HWND` was exercised against that actual child handle.

- Nature displays a160x112 representative leaf/caterpillar image at the top-left of a300x200 child. Frames3 and7 are identical. Preview rendering and parent-destruction lifecycle work; expected native preview sizing/static behavior requires reference comparison before acceptance.
- Starfield renders changing pixels inside the child; frames3 and7 have different pixel digests.
- Moving the mouse does not terminate these embedded previews. Destroying the owned parent causes both saver processes to exit0 within the bounded wait. The helper also exits.
- Fresh prefix initialization took6.93seconds in this run. This supports pre-provisioning/reusing the approved user prefix rather than initializing on each click; it is not a measured warm animation startup latency.

Actual preview frames/logs/report: `private/screensaver-wine-20261127/preview/`. An earlier concurrent preview fixture failed GDK's implicit default-display initialization; the checker now explicitly opens its exact owned display and assigns it to the GDK display manager. That failed attempt did not run a saver and is not a compatibility failure.

## Reproduction and evidence

`dev/check_screensaver_wine.py` accepts explicit `--media`, `--output`, `--xvfb`, bounded `--cases` and `--mode s|c|p`. It creates its own display with `-displayfd`, disallows live display0, creates a disposable prefix, never reuses an existing prefix/display, captures actual GDK framebuffer, logs DLL loads and kills its own Wine server and Xvfb afterward. No package installs.

Guest fullscreen command used (media directory pre-staged from private sources):

```
/usr/bin/python3 /home/developer/w95uat-saver-compat-media/check_screensaver_wine.py \
  --media /home/developer/w95uat-saver-compat-media \
  --output /home/developer/win95lx-saver-compat-proof-v2 \
  --xvfb /home/developer/win95lx-ui-qa.eK9O7BgJ/Xvfb
```

Configuration adds `--mode c --cases nature-complete,stars,blocks,lens` and a fresh output directory. Output locations retained locally:

- `private/screensaver-wine-20261127/fullscreen-v2/`: seven cases, actual frames, DLL logs, report and exact frame-differences.json.
- `private/screensaver-wine-20261127/config/`: four original settings dialogs and cancellation logs/report.
- `private/screensaver-wine-20261127/binary-inventory.json`: local SCR PE32/import inventory.
- `private/screensaver-wine-20261127/preview_host.c`: owned Win32 parent/child HWND helper source. A Win32 HWND is required for `/p`; an X11 XID must not be passed as though it were a HWND.

Earlier rejected fixture run moved the mouse to the same absolute coordinates across cases. Later savers therefore received no movement; its dismissal failures are invalid. Corrected proof resets the pointer before each launch. An early overly restrictive display1 guard also left an owned Xvfb process; that exact process was identified and removed. Subsequent cleanup is scoped to owned processes.

## Native aliases and future packaging

PLUS.INF maps eight theme libraries to WL32SCR.EXE aliases: Dangerous Creatures, Leonardo da Vinci, The Golden Era, Sports, Mystery, Inside your Computer, Nature and Travel. The themed DLL uses the **same installed base name** as its SCR. Store exact source/installed names in a per-package manifest; arbitrary renaming can change engine lookup. Windows95 theme uses BLOCKS.SCR renamed Windows95.scr; Science and The60'sUSA use LENS.SCR under their installed names. These mappings are established from the actual installer, not file-extension guessing.

Future98/ME/XP and third-party support should use the same bounded backend contract: package identity and source hashes; PE32/PE32+ architecture; exact install aliases/dependency list; tested configure/fullscreen/preview switches; settings scope; required DirectDraw/OpenGL/media runtimes; launch/render/dismissal statuses separately. This probe did not test those future packages. Wine is a compatibility runtime, not a security boundary; a disposable prefix alone does not contain an untrusted executable.

## Final bounded acceptance status

- All eight original WL32 thematic aliases: changing fullscreen output and mouse dismissal; each has one native Mute Sound Save/launch/change-Cancel/reopen cycle.
- Exact installed Science and The60'sUSA Lens aliases plus Windows95 Blocks alias: one engine-specific Save/launch/change-Cancel/reopen cycle each. This makes11 unique Plus95 saver presentations with one setting cycle; the two raw-engine source-name checks are additional engine probes, not extra shipped presentations.
- Patterned Lens and Blocks animate; generic Starfield/Mystify GDI baselines animate.
- Four engine representatives pass physical keyboard dismissal twice, and two preview representatives pass owned-parent destruction.
- Expanded test cleanup artifacts report owned Wine-server wait completion and Xvfb exit0. Final scoped process inventory found no remaining probe saver, helper or Xvfb. No live guest desktop setting was changed.
- Original reference pixel/timing comparisons, every-option coverage, audio, original-VM3D equivalence, untested stock95 options and production idle integration remain outside this acceptance. Windows98/ME/XP remains future scope.

All controls in parameter cycles use real Win32 messages against the original binaries, not unit mocks; physical mouse/keyboard is separately exercised for saver dismissal. No complete-fidelity claim follows from these compatibility results.

## Remaining engineering before product support

1. Turn the proven owned preview HWND/parent-destruction test into the product host/IPC contract; verify native thumbnail sizing/static behavior before accepting Nature preview fidelity.
2. Match original95 reference captures at identical resolution/color depth and named geometry/state; record animation, not one still.
3. Expand the proven Mute Sound setting to every supported option, testing change/OK/Cancel/reopen and persisting only approved registry/INI state.
4. Verify keyboard, buttons, mouse tolerance, focus loss, preview removal, rapid repeated starts and no orphan windows/grabs.
5. Measure first visible animation latency, warm/cold prefix startup, CPU and memory. Three-second sampling is only an upper bound, not a measured startup time. Do not initialize a prefix on every user click.
6. Compare the now-proven patterned Lens and all eight themed aliases against the original reference; verify audio separately.
7. Integrate user-session idle notifications and visible95 Display applet controls only after these acceptance gates. No locking/UAC/system-agent assumptions should leak into the user experience.

## Primary documentation

Microsoft describes full-screen creation, timer-driven animation, config entry points and dismissal semantics in [Handling Screen Savers](https://learn.microsoft.com/en-us/windows/win32/lwef/screen-saver-library). Its [Screensaver Sample](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms686421(v=vs.85)) documents `/s`, `/c` and `/p HWND`. This modern sample establishes the interface contract, not proof that every historic binary implements every optional mode identically.

### Preview reproduction

Build private CRT-free helper with the existing `tools.stage_command_button_assets.build_harness` using `private/screensaver-wine-20261127/preview_host.c` (helper output filename remains W95BTNS.EXE). Copy only that built helper to the guest's isolated probe media directory, then:

```
/usr/bin/python3 /home/developer/w95uat-saver-compat-media/check_screensaver_wine.py \
  --media /home/developer/w95uat-saver-compat-media \
  --output /home/developer/win95lx-saver-preview-proof-v2 \
  --xvfb /home/developer/win95lx-ui-qa.eK9O7BgJ/Xvfb \
  --mode p --cases nature-complete,stars \
  --preview-host /home/developer/w95uat-saver-compat-media/preview-host.exe
```

The output directory must be new; choose a fresh suffix on rerun. `--media` requires exact original CAB members used by chosen cases. The probe makes installed aliases only inside its own temporary tree. No live desktop or installed saver is altered.

### Extended probe commands

- Remaining thematic aliases: `--cases dangerous,davinci,modern,sports,mystery,pcinside,travel`.
- Patterned Lens: `--cases lens --background-host /home/developer/w95uat-saver-compat-media/background-host.exe`. Build helper from private `background_host.c` with the same existing CRT-free harness builder.
- Native settings proof: `--mode c --cases nature-complete --repeat 2 --config-editor /home/developer/w95uat-saver-compat-media/config-editor.exe`. Build helper from private `config_editor.c`; the checker restricts native parameter automation to known95/Plus95 families; repeat2 tests Save/reopen and repeat3 tests Save/change-Cancel/reopen.
- Physical keyboard/repeat engine qualification: `--cases nature-complete,stars,blocks,lens --dismiss keyboard --repeat 2 --background-host /home/developer/w95uat-saver-compat-media/background-host.exe`.

All commands also require the explicit media/output/Xvfb arguments above and a fresh output directory. Helper outputs need distinct installed probe filenames; the harness builder's default W95BTNS.EXE output is not itself a semantic name.

### Reproduce the authored Win32 helpers without private source files

The checker embeds only our own small C test fixtures (no original saver art/binary content). Export them using:

```
python3 dev/check_screensaver_wine.py --emit-helper-sources /tmp/w95-saver-helper-sources
```

Then compile the desired source with the existing CRT-free Win32 harness builder and give the resulting EXE a distinct probe filename (preview-host.exe, background-host.exe or config-parameter-editor.exe). Source export was verified byte-identical to the fixture used in the runtime proof. The original SCR/DLL media still comes from the private media catalog.

A complete three-phase setting test uses `--mode c --repeat 3 --config-editor <helper> --post-save-launch`. The accepted case list includes the eight WL32 aliases and `science,sixties,windows95`; the parameter helper chooses Mute Sound, Black Hole radio or Use Wallpaper according to the bounded known case. The report contains actual native before/after control state, post-save launch liveness/dismissal and installed-file hashes. Default capture delays are3+4seconds; shorter config cycles may use3+1, recorded explicitly.

## Stock95 follow-up

SCREENSAVER_STOCK95_2026-11-27.md records actual remaining GDI successes, initial five-engine OpenGL failures and the controlled guest-only GLX/OSMesa dependency fixes, after which all five render and dismiss at800/1280, independent Pipes/Text parameter persistence, and a measured original-FON Wine configuration typography improvement. Catalog/package validation must not be presented as rendering acceptance.

The stock95 follow-up now includes the passing16-package installed-version audit, explicit GLX versus OSMesa dependency proof, Maze Overlay actual-effect/Cancel persistence and verified postinstall recovery checkpoint. See its resource-cleanup lesson before using many disposable Wine prefixes.

## Shared runtime implementation follow-up

SCREENSAVER_RUNTIME_GROUPS_2026-11-27.md records the implemented one-prefix trusted95 group, genuineFON profile, quiet preparation, actual shared General/per-basename state proofs and the successful real LinuxGTK Lens capture. Existing identity prefixes are preserved; native pixel equivalence remains a separate gate.
