# DOS prompt research — 2026-11-25

Status: research only. No shell was installed, no login shell changed, and no DOS command interpreter was implemented in this iteration. Recommendations below are engineering hypotheses until measured in the Win95LX guest.

## Recommended direction

Prototype DOSEMU2 with FDPP first for a real DOS prompt that can run DOS programs and exchange files with the Linux desktop. Compare DOSBox-X as the alternative. Retain Bash for system services and development. Do not make PowerShell the default merely because it has DOS-like command aliases.

Windows 95's MS-DOS Prompt runs COMMAND.COM; `cmd.exe` is the later NT command interpreter convention. We can accept `cmd.exe` as an explicitly documented compatibility alias in Run while presenting the historical MS-DOS Prompt title and icon. The choice of executable alias must not silently promise NT batch semantics.

## Candidates

| Candidate | What it provides | Fit and unresolved work |
|---|---|---|
| DOSEMU2 + FDPP | DOS programs under Linux, host-directory drive mappings, per-user configuration and boot hooks | First candidate for integrated desktop file workflows. Validate nested virtualization availability and fallback, long names, clipboard, keyboard, focus and cold startup. |
| DOSBox-X | A DOS emulator with broad application support and configurable startup | Second candidate, especially for compatibility. Its documented `-fastlaunch` suppresses BIOS splash and welcome banner. Measure its actual prompt readiness; do not equate that flag with zero startup cost. |
| DOSBox Staging | A DOS gaming environment with modern presentation and audio | Prefer as optional game launcher; its project scope is games. Evaluate ordinary utilities before offering it as the everyday prompt. |
| FreeDOS in QEMU | A complete bootable DOS guest | Useful for isolated compatibility and reference testing. A separate boot and disk integration layer make it a less direct default desktop prompt. Boot speed is unmeasured. |
| SvarDOS / Enhanced DR-DOS | An alternative DOS kernel and command interpreter | A real DOS alternative to investigate after the first two. Review each packaged component's license and runtime integration; do not assume historical OpenDOS restrictions or modern licensing from its name. |
| Bash with functions/aliases | Familiar command spellings on the Linux filesystem | Fast access to Linux tools, but aliases do not implement DOS paths, wildcard rules, batch grammar, code pages or DOS executables. Suitable as an optional Linux console with a clearly stated contract. |
| PowerShell | A modern object-oriented shell with aliases including familiar DOS commands | Useful optional administration tool. Aliases map to cmdlets; they do not turn it into COMMAND.COM or provide DOS executable compatibility. Keep it out of the default boot/session dependency set. |

## Source evidence

DOSEMU2 documents `dosemu -K <unix_dir> -E <dos_cmd>`, direct Unix-path program invocation, per-user `.dosemurc`, and `userhook.sys`/`userhook.bat`. These are useful integration points for launching a selected folder without booting a full PC guest. [Project README](https://github.com/dosemu2/dosemu2).

FDPP is a FreeDOS-derived C++ DOS core hosted by DOSEMU2. It is a library needing a host, not a standalone bootable replacement for a Linux kernel. [FDPP README](https://github.com/dosemu2/fdpp).

DOSBox-X documents configurable autoexec commands and its fast-launch option. [Official introduction](https://dosbox-x.com/wiki/Home). DOSBox Staging describes its gaming-oriented design and configuration model. [Official manual](https://www.dosbox-staging.org/0.83/manual/introduction/what-is-dosbox-staging/).

FreeDOS recommends running in a virtual machine and publishes installation and QEMU guides. [Downloads](https://www.freedos.org/download/), [QEMU guide](https://help.freedos.org/docs/howto/qemu.html).

The Enhanced DR-DOS repository maintains the kernel and command interpreter used by SvarDOS, with builds and licensing materials. [Source repository](https://github.com/SvarDOS/edrdos). Pin and review the selected revision before packaging.

PowerShell aliases are alternate command names and differ by platform; for example `ls` remains a native command on Linux. This does not establish DOS syntax compatibility. [Microsoft alias documentation](https://learn.microsoft.com/en-us/powershell/scripting/learn/shell/using-aliases). Bash aliases substitute command words within Bash's own language. [GNU Bash manual](https://www.gnu.org/software/bash/manual/bash.html).

## Proposed integration contract

The launcher receives the Explorer folder and maps it consistently into the DOS drive view. It starts as the logged-in non-admin desktop user. A DOS process must never gain more access than that user. Initially expose a per-user DOS working directory and selected folder; explicitly decide whether the root filesystem should be mapped read-only, writable, or omitted. Do not mount arbitrary external disks automatically.

Preserve byte contents and timestamps on desktop-to-DOS round trips. Test spaces, mixed case, non-ASCII names, long filenames and 8.3 aliases, symlinks, hidden files, read-only locations and removable media. Show historical errors in the prompt rather than silently rewriting ambiguous paths. Decide whether a DOS program's exit returns to the prompt or closes the window.

A native-looking terminal needs the original raster font at integer sizes, VGA text colors, correct caret blink, selection and clipboard behavior, configurable window/fullscreen sizing, and correct Alt+Tab/Alt+Enter focus handling. Rendering a screenshot of a prompt is insufficient: run COPY, DIR, CD, TYPE and a real DOS executable. Validate the close-with-running-program confirmation.

## Benchmark and acceptance plan

Run each candidate at least 20 times after a clean guest boot, then 100 warm launches. Record launch-to-first-visible-prompt, first keystroke echo latency, idle CPU, resident memory, executable launch latency and close time. Report median and p95, hardware, package versions and cache state. Separate emulator initialization from terminal rendering. Target an initially proposed warm prompt p95 below 250 ms; change the target only with measurements and a clear explanation.

Use the same corpus across candidates: small real-mode COM, DOS EXE, protected-mode application, text utility, mouse application and representative game. Test Ctrl+C, Ctrl+Break, pipes, redirection, batch arguments, environment expansion, drive changes and file-copy failure cases. No compatibility percentage should be reported from one successful game.

A/B the terminal against a real Windows 95 MS-DOS Prompt at equal guest resolution, font dimensions and color depth. Capture empty prompt, DIR output, selection, running program and close confirmation. Keep original media and copyrighted fonts private.

## Decision still pending

No local startup measurements or application-compatibility results exist yet. DOSEMU2 is the first prototype recommendation based on its documented Linux file integration, not an accepted performance winner. The classic Windows 95 reference should establish exact prompt controls and behavior before implementing the launcher.
