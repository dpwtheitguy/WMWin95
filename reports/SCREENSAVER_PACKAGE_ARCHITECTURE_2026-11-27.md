# Screensaver packages and import architecture — 2026-11-27

Research proposal only. No runner, importer, idle policy or live Wine configuration implemented by this report. Read alongside SCREENSAVER_OPTIONS_2026-11-27.md and SCREENSAVER_WINE_COMPATIBILITY_2026-11-27.md. The initial black Nature frame was reproduced and traced by controlled positive/negative tests to its omitted genuine WL32DLL.DLL dependency. The corrected isolated probe renders original animated leaves/caterpillars and dismisses. This establishes compatibility, not complete native pixel/timing/idle acceptance.

## Evidence and concrete initial inventory

Local read-only `file` inspection identified all eleven files below in `private/cabsets/windows95` as PE32 Intel386 GUI executables. These are extracted media observations, not a statement that every Windows95 edition installs all eleven by default.

| File | Working catalog label, to confirm against native Display list |
| --- | --- |
| bezier.scr | Beziers |
| scrnsave.scr | Blank Screen |
| ssflywin.scr | Flying Windows |
| ssmarque.scr | Marquee |
| ssmyst.scr | Mystify Your Mind |
| ssstars.scr | Starfield Simulation |
| ss3dfo.scr | 3D Flying Objects |
| ssflwbox.scr | 3D Flower Box |
| ssmaze.scr | 3D Maze |
| sspipes.scr | 3D Pipes |
| sstext3d.scr | 3D Text |

The local RTM extraction also contains these eleven filenames. The OSR1 extraction currently exposes six; incomplete extraction is not evidence that the other five never shipped. Labels, installed defaults and version-specific hashes still need native confirmation.

Original private media `private/reference/media/plus/PLUS.INF` supplies stronger installation evidence than extension scanning:

| Source engine | Installed presentation aliases in that INF |
| --- | --- |
| BLOCKS.SCR | Windows 95.scr |
| LENS.SCR | The 60's USA.scr; Science.scr |
| WL32SCR.EXE | Dangerous Creatures.scr; Leonardo da Vinci.scr; The Golden Era.scr; Sports.scr; Mystery.scr; Inside your Computer.scr; Nature.scr; Travel.scr |

All three source engines inspect as PE32 Intel386. These eleven aliases are not eleven independent engine implementations. For example `[MT_Nature_scr]` installs NATURE.DLL as Nature.dll alongside WL32SCR.EXE renamed Nature.scr (lines926–928), and `[MT_Dangerous_scr]` installs DANGEROU.DLL as Dangerous Creatures.dll (lines522–524). Preserve aliases and matching resources exactly. Whether engine lookup is based on executable basename must be confirmed by tracing; the installation layout makes renaming to a common `saver.scr` an unjustified shortcut.

Local Plus98 extraction exposes additional SCR names, but its complete installation dependency graph has not been audited here. Windows98 media also contains driver scripts with SCR extensions. Extension alone cannot establish a runnable screensaver. Me/XP inventory and compatibility remain future work, not completed coverage.

## Package boundary and identity

Use separate immutable package, engine and presentation identities. Suggested package ID is product/release plus a manifest content hash; engine ID identifies exact executable bytes and runtime recipe; presentation ID identifies its installed alias and companion resources. Display names are editable labels, never identity keys. Identical engine bytes can be deduplicated in storage while retaining product provenance and independent configuration.

Each manifest records source-media digest, source paths/CAB members, original installed relative paths, size and SHA256 for every executable/DLL/data/font, PE/NE architecture, imported libraries, dynamically observed loads, runtime version/build/architecture, required graphics backend, working directory, known registry/INI locations, mode support and evidence IDs. Keep payloads private and retain provenance separately from distributable implementation. Do not silently combine Windows95 and98 DLLs merely because filenames match.

Package extraction is a staged operation: reject traversal, absolute archive names, symlink escape, case-fold collisions, oversized entries and mismatched hashes; validate complete dependency closure; then atomically publish the manifest. Ownership/refcounts allow removal of one presentation without deleting a shared engine still in use. Importing or selecting a package never starts it.

## Wine architecture and dependencies

The Wine9.0 manual documents separate WINEPREFIX state and architecture selected when a prefix is created; existing prefix architecture cannot be changed. It also documents native/builtin DLL ordering. Pin runner version and resolved dependency set in acceptance evidence rather than assuming whatever `wine` happens to resolve on PATH. [Wine9.0 loader manual](https://raw.githubusercontent.com/wine-mirror/wine/wine-9.0/loader/wine.man.in).

Start with an explicit tested PE32 compatibility recipe for the observed95/Plus engines. Detect available Wine32/WoW64 support before enabling them; do not assume a64-bit Wine executable proves every32-bit dependency is present. A separate runner capability probe can later qualify a newer WoW64 implementation. PE32+, NE/Win16 and unsupported architectures require distinct recipes and evidence. Do not promise Win16 compatibility through the PE32 recipe.

Static imports provide a starting graph, not full dependency closure: themed DLLs may be loaded by name at runtime. Capture loader traces in an isolated test prefix and compare them with original installation INF entries. Validate GDI and OpenGL rendering separately; Xvfb process survival is not proof that a3D saver can render there. Prefer Wine builtins initially, adding exact native helper DLL overrides only when an identified compatibility defect and successful regression evidence justify them. Never replace system libraries globally.

## Configuration persistence and isolation

Measured implementation supersedes the initial per-presentation isolation proposal: trusted original95/Plus packages now share one versioned runtime prefix. Actual original binaries intentionally share Plus General settings while keeping engine settings under the installed executable basename (Science and The60'sUSA remain distinct). One prefix also avoids roughly581MiB duplicated per presentation. Future third-party trust groups remain isolated; a prefix is not a security sandbox. Do not hard-link mutable registry hives. See SCREENSAVER_RUNTIME_GROUPS_2026-11-27.md for actual state, ownership, migration and disk evidence.

Record configuration as an opaque versioned profile plus documented typed settings where known. For each saver, measure changed registry values, INI files and application files during native and Wine configuration. Before opening Settings take a checkpoint. Successful native OK commits its actual state; native Cancel is checked against the checkpoint, with integration restoring accidental changes if required. Host dialog Cancel must not lose unrelated settings changed by another applet. Serialize saver configuration/launch operations within its prefix.

Configuration import must not execute REG files or commands from a theme. A theme associates a catalog presentation ID and configuration-profile digest; the resolver maps historic SCR paths to installed known identities. Missing packages produce an unavailable selection and a native-looking explanation. Saving a theme preserves the reference/settings, not a machine-dependent arbitrary command string.

A Wine prefix separates registry/application state; it is not a host-filesystem security boundary. An eventual third-party executable installer needs an explicit installation action and reviewed execution policy. That is separate from normal theme selection and does not require adding UAC-like prompts to ordinary applet use.

## Launch and UI contract

Expose typed operations `configure(presentation_id)`, `preview(presentation_id,parent)` and `fullscreen(presentation_id)`, with fixed argument builders and direct argv execution. Never pass imported shell command lines. Common `/c`, `/s`, `/p` forms are compatibility candidates, not a guarantee for every historical engine. Microsoft describes separate configuration, preview and fullscreen behavior; per-engine tests must establish exact invocation. [Microsoft screensaver architecture](https://learn.microsoft.com/en-us/windows/win32/lwef/screen-saver-library).

A Win32 preview parent HWND and Linux X11 window ID are different handle domains. Use a tested Wine-side host/helper to create the Windows parent and bridge geometry/lifecycle; do not simply pass a GTK XID as HWND. Until embedding is verified, keep preview explicitly unavailable or use an honest separate preview window rather than presenting an empty monitor as working.

Launch asynchronously after package/runtime preparation. Idle starts should reuse an initialized recipe without waiting for wineboot or package installation. Record cold and warm timings independently. Own child processes and stop them when the preview closes, selection changes, applet closes or desktop session ends. Avoid killing the user's unrelated Wine applications. Fullscreen input dismissal, focus loss, cursor restoration and grab cleanup are acceptance gates. A screensaver is not automatically a Linux screen locker; retain any lock mechanism as a separate host policy.

Future native/OpenGL/SDL engines can implement the same presentation/configuration/lifecycle contract. Their inclusion requires visual comparison rather than silently substituting an analogue for an original.

## Arbitrary third-party SCR installation

Support a loose SCR plus explicit companion files, a known manifest bundle, and eventually a separately reviewed legacy installer recipe. Inspect executable headers and dependency candidates; do not accept extensions as proof. Installation copies owned files into a package, allocates a recipe/prefix, records provenance and configuration locations, and runs a user-requested qualification flow. A missing DLL, architecture mismatch or unsupported setup program yields a specific reason and leaves the previous saver intact.

Unknown executables can be installed as unverified entries but must not be scheduled for idle launch until configure/render/dismiss tests pass. Failures should not remove the files needed for diagnosis. Removal drops catalog/profile ownership and only unreferenced assets; existing themes retain an unavailable reference that can later be repaired by reinstalling the matching identity.

## Required tests before delivery

| Area | Tests and acceptance evidence |
| --- | --- |
| Import | Headers vs extension; corrupt/truncated PE/NE; missing/dynamic DLL; hash mismatch; case collisions; traversal; Unicode/space aliases; interrupted extraction leaves catalog unchanged |
| Identity | Two releases with same filename remain distinct; identical shared engine keeps aliases; uninstall one alias preserves other owners |
| Configuration | Each option native/Wine parity; OK/reopen; Cancel byte comparison; per-saver isolation; reset defaults; theme save/reapply; interrupted write rollback |
| Render | Original VM and Wine same resolution/settings; multiframe capture at fixed times; visible nonblack content where expected; animation cadence/palette; named-region differences and explain nondeterministic seeds |
| Preview | Open/change/close repeatedly; resize; parent destruction; no orphan/grab; unavailable embedding accurately reported |
| Fullscreen | Idle and explicit preview independently; movement tolerance, click/key/focus dismissal; repeat100cycles; correct resolution and cursor restoration |
| Runtime | Cold/warm p50/p95 start; frame cadence; CPU/memory idle/active; stopped process cleanup; no package/prefix initialization on menu click |
| Display | At least640×480,800×600,1024×768,1280×720,1366×768,1920×1080,2560×1440,3840×2160; integer/noninteger viewer scaling and actual hardware separately |
| Failures | Missing runtime, unsupported graphics, dependency failure, settings crash, fullscreen crash, stale profile, resource removed; previous selection and shell remain usable |

These are proposed package acceptance tests, not a completed product test suite. Subsequent isolated X11 evidence in SCREENSAVER_WINE_COMPATIBILITY_2026-11-27.md proves corrected Nature animation and dismissal, plus simple GDI saver animation, original configuration launch/Cancel, and real Win32 HWND preview parent-destruction lifecycle. Exact native UI/timing, settings persistence, idle integration and3D-engine qualification remain separate gates. Keep Wine installation optional and outside click-time paths; this architecture report adds no product integration success claim.

## Backend implementation checkpoint

A subsequent authorized implementation added `control_panel/screensaver_runtime.py`, `tools/stage_screensaver_assets.py` and `tests/test_screensaver_runtime.py`. These provide a typed catalog;22 private95/Plus presentation recipes with46 hashed file entries; PE32 header checks; original alias/dependency staging; bounded worker-owned Wine preparation (subsequently grouped as described below); explicit `/s`, `/c`, `/p` launch; positive Win32 HWND validation for preview; and owned-prefix cleanup. Preparation is explicitly a worker operation and never happens implicitly in `launch`. The UI must supply a genuine Wine-side preview host. Per-mode manifest status distinguishes probe-supported operations from unverified modes.

Idempotent staging replaces only ownership-marked generated bundles and preserves the previous bundle if generation fails. Group leases now prevent two runtime instances using the same trusted runtime concurrently, including different presentations. UI configuration and idle instances should share the same state directory so native settings persist, while the UI inhibits idle during configuration/preview and calls stop after normal child exit to release the lease. Other Wine prefixes are never selected for cleanup.

Validation at this checkpoint:49 fake-process/catalog/staging tests passed; combined backend+preferences/scheduler tests59 passed. A read-only private-source staging check validated all22 presentations and46 hashed file entries, without executing media. These CPU/package checks are distinct from the newer isolated Wine probe evidence described above and do not establish native pixel fidelity or live idle integration. Renderer settings, physical-input dismissal and the final applet remain separate integration acceptance gates.

## Shared runtime and quiet initialization follow-up

SCREENSAVER_RUNTIME_GROUPS_2026-11-27.md supersedes the early per-presentation storage layout:22 staged presentations share one approximately583MiB prefix, with actual global/per-basename persistence evidence, original NE font profile, quiet headless preparation, guarded explicit updates and cold/warm measurements. Existing old prefixes are preserved. The original LinuxGTK Lens probe also caught and then verified correction of a visible Wine updater popup; Lens itself correctly captures the real GTK desktop. Embedded-helper operation ownership remains future work because no embedded companion is shipped here.
