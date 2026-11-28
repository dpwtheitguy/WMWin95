# Screensaver interoperability research — 2026-11-27

Status: research and isolated compatibility probe; no completed screensaver delivery claim.

Windows SCR files are executable programs. The local Plus95 WL32SCR.EXE, BLOCKS.SCR and LENS.SCR are 32-bit PE programs; themed savers also require companion DLLs. Extracting artwork does not extract the animation algorithm, timing or configuration behavior.

## Options

1. **Original binaries under Wine.** Best first fidelity candidate for the original Plus animations and setup dialogs. Install exact original filenames and dependencies in a dedicated user prefix. Integrate with our selection, preview, idle and dismissal lifecycle. Do not launch arbitrary commands from imported theme files. Cost: Wine32 dependencies, cold prefix initialization and compatibility testing.
2. **Extract resources and implement a native renderer.** Reuse bounded PE resource, bitmap and palette extraction; inspect custom DLL resource types as needed. Reconstruct motion, timing, palette effects and settings against recordings from the reference VM. Assets alone are insufficient. Offers predictable startup and native preview embedding, but requires substantial per-saver work.
3. **Adapt existing open implementations.** XScreenSaver pipes.c explicitly describes a from-scratch Windows NT-inspired implementation and includes permission terms. It is a candidate analogue, not proof of pixel identity. ReactOS has source for 3D Text, Maze and Starfield among other savers; those are Windows-targeted implementations, not ready-made Linux binaries. Review each component license and compare visuals before adoption. No complete verified native port of all Plus95 savers was established by this search.
4. **Targeted reverse engineering.** Ghidra supports disassembly and decompilation. Use it where resource formats or animation behavior remain undocumented. Decompiled pseudocode is not recovered original source and cannot simply be rebuilt for Linux. Retain original assets privately; distributing a rewritten engine and distributing original artwork are separate questions.

## Initial probe (superseded by controlled follow-up)

Wine 9.0 installed in the development guest only. Original Nature.scr/shared engine, Nature.dll and helper DLL staged in a disposable user-owned environment under isolated Xvfb at 800x600. The process was alive at six seconds, exited on synthetic mouse movement and returned zero. Captured six-second frame was black. Therefore launch/dismissal passed, rendering remains UNVERIFIED/FAILED visual acceptance. Do not advertise original Nature as working yet. No live desktop saver or lock policy changed.

Private evidence: private/theme-completion-20261127/nature-6s.png; guest /home/developer/win95lx-saver-proof/report.json and wine.log. Repro probe: private/theme-completion-20261127/compat_probe.py. Before-change VM checkpoint: before-theme-customization-20261127.

## Controlled follow-up

The missing original WL32DLL.DLL dependency was isolated with positive and negative controls. Supplying the genuine runtime produces original animated Nature graphics and clean dismissal. All eight Plus95 shared-engine aliases now render and dismiss; Lens also animates when its owned background fixture contains meaningful imagery. See SCREENSAVER_WINE_COMPATIBILITY_2026-11-27.md for exact aliases, native configuration/preview probes and remaining acceptance gaps. This updates compatibility evidence; it does not declare product idle integration or pixel equivalence complete.

## Acceptance gates

For each saver: exact installed aliases/dependencies; settings Apply/Cancel and restart persistence; visible animation across multiple captured frames; native-reference timing and colors; preview start/stop; fullscreen idle start; mouse, keyboard and focus-loss exit; no orphan process or retained grab; repeated launch; CPU/memory/startup measurements; multiple resolutions. Test rendering separately from a process merely remaining alive.

Recommendation: continue Wine investigation first for Plus originals, use native open implementations where fidelity can be established, and reserve extraction/reimplementation for incompatible engines. Expose neither a blank preview nor an unverified saver as a completed feature.

## Sources

- Microsoft screen saver architecture and input dismissal: https://learn.microsoft.com/en-us/windows/win32/lwef/screen-saver-library
- XScreenSaver Pipes source (read-only mirror; upstream is jwz.org): https://raw.githubusercontent.com/Zygo/xscreensaver/master/hacks/glx/pipes.c
- ReactOS saver inventory: https://raw.githubusercontent.com/reactos/reactos/master/modules/rosapps/applications/screensavers/CMakeLists.txt
- ReactOS base saver inventory: https://raw.githubusercontent.com/reactos/reactos/master/base/applications/screensavers/CMakeLists.txt
- Ghidra upstream: https://github.com/NationalSecurityAgency/ghidra
