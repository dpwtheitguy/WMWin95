# Local Windows95 saver engines and Wine configuration fidelity — 2026-11-27

Independent isolated compatibility research. No live desktop, reference VM, shared product module, host package or catalog activation changed. Source is the project's existing `private/cabsets/windows95` media extraction; this report does not establish the exact RTM shipping list. Wine9.0, owned800x600 Xvfb and disposable32-bit prefixes only.

## Actual support matrix (updated after dependency fixes)

Keep launch, rendering, settings and dismissal separate. A catalog entry or clean process exit is not evidence of visible animation.

| Original file | Rendering evidence | Input/lifecycle | Configuration evidence |
|---|---|---|---|
| bezier.scr | Changed nonblack3/7s frames | Physical mouse exits0 | Not qualified |
| ssflywin.scr | Changed sparse colored pixels; recognizable logo fidelity unverified | Physical mouse exits0 | Not qualified |
| ssmarque.scr | Changed nonblack text frames | Physical mouse exits0 | Not qualified |
| ssstars.scr | Prior changing star frames | Mouse and repeated physical Escape exit0 | Original config launch/Cancel only |
| ssmyst.scr | Prior changing colored-line frames | Physical mouse exits0 | Not qualified |
| scrnsave.scr | Correct intended black output at both samples | Physical mouse exits0 | No configurable effect claimed |
| sspipes.scr | Animated after32-bit GL install,800x600 and1280x720 | Mouse and physical Escape exit0 | Multiple/Single pipe selection Save→changed-Cancel→reopen passes |
| sstext3d.scr | Animated after32-bit GL install,800x600 and1280x720 | Mouse and physical Escape exit0 | Text/Time selection Save→changed-Cancel→reopen passes |
| ssmaze.scr | Animated after32-bit OSMesa install,800x600 and1280x720 | Mouse and repeated physical Escape exit0 | Maze Overlay Save/launch/change-Cancel/reopen passes; visible map effect confirmed |
| ss3dfo.scr | Animated after32-bit GL install,800x600 and1280x720 | Mouse and physical Escape exit0 | Not qualified |
| ssflwbox.scr | Animated after32-bit GL install,800x600 and1280x720 | Mouse and physical Escape exit0 | Not qualified |

These are compatibility results on this guest, not original-VM pixel equivalence or complete applet acceptance.

## Initial OpenGL blocker: direct evidence and controlled fixes

All five OpenGL engines launched and dismissed but produced zero nonblack pixels at both samples. The controlled Pipes diagnostic enables Wine WGL/errors and records:

```
Failed to load libGL: libGL.so.1: cannot open shared object file: No such file or directory
OpenGL support is disabled.
```

Read-only inventory confirms no `/usr/lib/i386-linux-gnu/libGL*` or32-bit DRI driver directory, while64-bit GL libraries are present. No relevant32-bit GL packages were reported by dpkg-query. This identifies a concrete missing32-bit OpenGL runtime on this guest; it does not prove the original savers are incompatible with Wine.

The subsequent authorized guest-only installation is documented below. Those initial black results are retained as negative controls; they no longer describe the final installed guest state. Hardware versus software Mesa performance still requires separate measurement.

Evidence: `private/screensaver-wine-20261127/stock3d-fullscreen/` and `pipes-wgl/`.

## Native3D parameter loops despite the rendering blocker

The existing checker and authored Win32 control helper now support bounded Pipes and3DText radio controls. Each uses three original processes:

1. Read initial state0; invoke the real Multiple(Pipes) or Time(Text) radio control; read1; invoke actual OK.
2. Reopen and read1; invoke the inverse Single/Text radio; read0; invoke actual Cancel.
3. Reopen and read1; leave it unchanged and invoke Cancel.

Both produce `0 1`, `1 0`, `1 1` and pass automatic assertions. These are actual original control handlers and application persistence, not mocked unit state or direct registry edits. These initial loops intentionally omitted a positive fullscreen claim while OpenGL was missing. The renderer was subsequently qualified after the controlled dependency installation below.

First discovery used physical Escape without explicitly establishing foreground ownership for the old3D config dialogs. It did not dismiss Pipes/Text and required terminating their owned processes; those negatives are retained as input-hosting discrepancies, not classified as original saver incompatibility. The native-control loops prove actual OK/Cancel handlers work. Product config hosting must explicitly manage focus and retest keyboard dismissal.

Evidence: `stock3d-config-discovery/` and `stock3d-settings/` under the same private root. Authored helper source is embedded in `dev/check_screensaver_wine.py`; no proprietary saver code is embedded.

## Authorized guest-only runtime installation and final3D qualification

`dev/guest_install_saver_gl.sh` guards require-guest, root identity, win95lx-dev hostname, amd64 and Ubuntu24.04. It ran only through the existing authenticated guest_admin helper. The recovery checkpoint before-screensaver-integration-20261127 was independently verified by a read-only QMP query before installation. No host packages, user-desktop reset, Wine prefix or idle/locking policy was changed by this script.

The first transaction installed the requested GL/GLX/DRI:i386 components using apt simulation followed by `--no-install-recommends --no-remove`:25 new packages,9 multiarch dependency upgrades,0 removals,76.4MB download/212MB disk. Versions:

- libgl1:i3861.7.0-1build1.
- libglx-mesa0:i386 and libgl1-mesa-dri:i38625.2.8-0ubuntu0.24.04.5.

Four engines then rendered changing actual frames and dismissed on mouse0 at800x600 and Escape0 at1280x720. WGL traces identify Mesa llvmpipe LLVM20.1.2, not hardware acceleration. Those images were visually inspected: Pipes,3DText,3DFlyingObjects and3DFlowerBox.

Maze required a second independent dependency. Its filtered API trace showed successful window SetPixelFormat and CreateDIBSection, followed by DescribePixelFormat returning0 for the bitmap/memory DC. The Wine9 DIB OpenGL driver uses OSMesa, a separate library from GLX. The installed Wine32 binary included that loader, but32-bit OSMesa was absent. An app-specific Win95 version-profile negative control did not solve it. No binary patch was attempted.

Adding **libosmesa6:i38625.1.7-1ubuntu2~24.04.2** via the same guarded script (one new package,3.5MB download/15.9MB disk) immediately produced a textured moving blue-brick Maze at800x600. Both sampled frames contain480000 nonblack pixels and different digests; physical mouse exits0. At1280x720, two successive Maze runs each show921600 nonblack pixels, changing frames, physical Escape exit0 and clean owned-process shutdown. The config dialog now appears too. No Win95 version override is needed for this successful result. [Wine9 DIB OpenGL source](https://raw.githubusercontent.com/wine-mirror/wine/wine-9.0/dlls/win32u/dibdrv/opengl.c).

Thus all five3D engines now have visible rendering and mouse/keyboard compatibility evidence at800/1280. This remains separate from original-VM pixel/timing acceptance, every-option acceptance or production idle integration.

Private evidence folders:

- `gl-runtime/preinstall-checkpoint.txt`, `install.log`, `install-with-osmesa.log`: recovery verification and complete simulation/transactions/versions/ldd.
- `stock3d-after-gl/`: first four positive engines and retained Maze negative control.
- `stock3d-keyboard-1280/`: four positives and retained Maze negative before OSMesa.
- `maze-pixel-format/`, `maze-win95/`: API-path diagnostic and unsuccessful version-profile control.
- `maze-after-osmesa/`, `maze-keyboard-1280/`: positive Maze800 and repeated1280 results.
- `gl-runtime/before-after-rendering.json`: installed-dependency black→visible comparison with frame hashes; **not an original-Windows pixel difference report**.

The root's installer dependency manifest now declares Wine32, GL/DRI and OSMesa. Its read-only installed-version audit was executed and retained under `gl-runtime/installed-dependency-audit.json`. That first auditor has a known multiarch parsing defect: unqualified libfontconfig1/libsystemd0/libx11-6 return two installed rows, which its single-row parser incorrectly marks missing. `multiarch-audit-proof.txt` records both actual installed architectures/versions. The root owner fixed that checker. The corrected tool was copied back to the guest and rerun against the unchanged manifest (SHA256648c575b2fea057bf21c545b7f4a20775ab2a4dacc243c7d7d1fa7706dc521): all16 declared packages installed, zero missing. The initial defective audit is retained as initial-multiarch-audit-defect.json; installed-dependency-audit.json now contains the passing actual version/architecture audit.

## Configuration typography improvement: original bitmap fonts

Fresh Wine's FontSubstitutes maps MS Shell Dlg to Tahoma. In a separate disposable prefix the probe:

- Copies original95 `sserife.fon` and `vgasys.fon` into that prefix's `C:\windows\Fonts` and registers those files in the prefix's Fonts key.
- Maps MS Shell Dlg and MS Shell Dlg2 to MS Sans Serif in that prefix's FontSubstitutes.
- Applies a bounded classic95 system-color map in that prefix only, then restarts only its owned Wine server.
- Reopens the original Nature config under font tracing and captures the actual framebuffer.

The font trace proves the selection is the original `sserife.fon`, not a similarly named fallback:

- Requested logical font MS Shell Dlg, height−11.
- Mapping to MS Sans Serif.
- Selected original `C:\windows\fonts\sserife.fon`, bitmap cell height13, font scale1.

The new actual dialog uses bitmap text and the prior monitor/options overlap is absent. The observed body geometry and color also change. Because both font and colors were applied in this experiment, color changes cannot be attributed to font substitution alone. Native color/geometry comparison remains necessary. No original reference VM was touched, and the improved dialog is **not** reported pixel-perfect.

This is consistent with Microsoft's documented95 logical-font mapping and dialog-unit conversion: dialog font metrics affect control/window geometry, so replacing a screenshot border cannot fix a wrong base font. [MS Shell Dlg mapping](https://learn.microsoft.com/en-us/windows/win32/intl/using-ms-shell-dlg-and-ms-shell-dlg-2), [MapDialogRect](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-mapdialogrect).

Evidence: baseline `config/nature-complete-7s.png`; improved `classic-font-probe/nature-complete-5s.png`; full trace and bounded excerpt `classic-font-probe/font-selection-excerpt.log`. This profile is English/Western95 bitmap-font evidence; other scripts/locales need their corresponding original font mapping.

## Reproduction

Use fresh output directories and the explicit media/Xvfb arguments documented in SCREENSAVER_WINE_COMPATIBILITY_2026-11-27.md.

- OpenGL engine sweep: `--cases pipes,text3d,maze,flyingobjects,flowerbox`.
- WGL cause diagnostic: `--cases pipes --debug-profile wgl`.
- Remaining GDI sweep: `--cases bezier,flywin,marquee,blank`.
- 3D parameter loops: `--cases pipes,text3d --mode c --repeat 3 --config-editor <authored helper EXE> --first-delay 3 --second-delay 1`.
- Typography profile: `--cases nature-complete --mode c --classic-fonts <directory containing original sserife.fon/vgasys.fon> --classic-colors --debug-profile font --first-delay 4 --second-delay 1`.

`--emit-helper-sources <new directory>` reproduces the authored C fixtures. Original SCR/DLL/FON media stays private. Report metadata records checker/helper/media hashes, explicit capture delays and graphics/font profile. Configuration sample field names inherited frame3/frame7, but actual delays are recorded and current image filenames use actual sample times.

The final syntax and diff checks passed. Owned Wine-server wait/Xvfb cleanup is recorded; the final scoped process audit must exclude any other agent's separately owned sessions. No22-working-savers claim is made: this report records actual local successes, settings-only successes and explicit graphics failures.

## Production prefix/stager integration recommendation

The original font profile should be a separately validated/hashed runtime asset group: FON is an NE bitmap-font container and must not be inserted into presentation.files, whose existing validator deliberately requires PE32 executable dependencies. On the prefix preparation worker, copy only the validated fonts into the owned real Windows/Fonts directory (reject linked/out-of-prefix destinations), import the tested prefix-local logical-font/color recipe, then stop only that prefix's server before first app launch. Include profile asset hashes and recipe version in prepared.json fingerprint so existing incorrectly prepared prefixes are refreshed. Do this during preparation, not every click. No shared runtime/stager edit was made in this task.

## Final Maze parameter and resource regression

After OSMesa installation the Maze Overlay checkbox was exercised through original Win32 handlers:0→1 and OK; actual fullscreen launch visibly displays the yellow maze-map overlay; second process1→0 and Cancel; third process reopens1. All original config processes close0 and the fullscreen process dismisses0. Evidence: `maze-settings-final/`, including original bitmap-font hashes and post-save effect image. This is the third independent3D engine setting loop, not every Maze option.

An additional attempted loop exposed a genuine harness resource defect: completed test prefixes had been retained at roughly581MB each, filling the32GB guest disk after many probes. All completed captures/logs were already copied to the host. The27 inactive checker-created `/tmp/w95uat-saver-compat-*` prefixes were uid/path/active-process checked; their registry/INI evidence was streamed into a verified host archive before removal. Guest free space returned to15GB. No product prefix or user data was removed. Archive/manifest/cleanup evidence is under `gl-runtime/`.

The checker now archives its small registry/INI evidence and removes its own disposable prefix by default after stopping its owned Wine server/Xvfb. `--keep-prefix` is explicit debug-only; a1GiB-free preflight is required. The final Maze retry verifies automatic cleanup: prefix_removed=true, registry archive hash recorded, no archive error, owned Wine wait completed and Xvfb exit0. This prevents the test mechanism itself exhausting the development VM. The failed ENOSPC attempt is not misclassified as an original-saver failure.

Runtime planning consequence: a persistent per-presentation prefix for22 savers would consume roughly12.5GiB, and incorrectly isolates the historically global Plus General options. A trusted95/Plus runtime group with preserved per-basename engine registry keys is preferable; third-party trust groups can remain separate. Grouped process ownership must prevent stopping one preview from killing another. This architectural recommendation was sent to root; no shared runtime edit was made here.

Recovery checkpoint `after-screensaver-gl-runtime-20261127` was saved and independently verified after installation, cleanup and successful final tests. QMP confirms the development guest is running. There was no user desktop reset. Artifacts: `gl-runtime/postinstall-checkpoint.json` and postinstall-vm-status.json.

## Shared runtime implementation follow-up

SCREENSAVER_RUNTIME_GROUPS_2026-11-27.md records the implemented one-prefix trusted95 group, genuineFON profile, quiet preparation, actual shared General/per-basename state proofs and the successful real LinuxGTK Lens capture. Existing identity prefixes are preserved; native pixel equivalence remains a separate gate.
