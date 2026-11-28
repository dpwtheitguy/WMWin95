# Wine screen saver lifecycle research — 2026-11-27

Research proposal, not delivered functionality. No original saver was executed for this report; runtime compatibility results belong to the independent Wine runtime report. Private reference media stays private.

## Native contract and desktop boundary

Microsoft documents `/s` for full screen, `/p <HWND>` for a preview parent, and `/c` for configuration in its [screen saver sample](https://learn.microsoft.com/en-us/previous-versions/windows/desktop/ms686421(v=vs.85)). Its [native library documentation](https://learn.microsoft.com/en-us/windows/win32/lwef/screen-saver-library) describes the screen saver procedure and host dispatch. The modern RSS sample is useful for the command protocol; it is not evidence that every Win95 saver has identical dismissal thresholds or multi-monitor support. Probe each original binary and version independently.

A GTK/X11 window ID is not a Win32 HWND. Passing GTK's XID directly to Wine `/p` is therefore an invalid integration assumption. Preferred experiment: a tiny Wine Win32 host creates a real child HWND, invokes the saver with that HWND, and owns its lifetime. Embed that host's X11 window in the GTK preview only after measuring Wine X11 parent/child behavior. A Wine virtual desktop is another containment experiment; it does not prove preview parenting. Wayland embedding is a separate unsupported capability until tested. Avoid automatic unrestricted root-window reparenting.

`/c` runs as a transient setup interaction with the owning applet disabled only while the configuration window is alive. Closing or cancelling must reenable the applet and release any input grab. `/s` preview is explicitly user initiated and must restore the previous focus and pointer after dismissal. Neither path may alter the selected theme or persist a new saver unless Apply/OK commits it. A legacy setup dialog may write its own prefix registry immediately; snapshot/version that per-saver configuration for Cancel semantics if our applet promises cancellation.

## One idle owner

[Xfce documents](https://docs.xfce.org/apps/xfce4-screensaver/start) that its saver combines blanking and locking, uses the X11 ScreenSaver extension for idle/inhibition, and supports XScreenSaver-compatible engines. Wine `.scr` is not automatically such an engine. Keep exactly one idle timer and one activation authority: preferably use the existing session daemon through a narrowly scoped compatibility adapter. Do not add an independent shell timer while xfce4-screensaver is still activating. Explicit full-screen Preview need not change idle configuration.

Locking remains the existing session lock service, separate from an untrusted legacy animation. A Win95 password dialog inside Wine cannot authenticate a Linux session. Follow the project's configured non-locking test experience; do not silently change system locking policy. Power-manager display blanking, DPMS, suspend and user inhibition must remain coordinated with the selected owner.

## Supervisor proposal

Use one dedicated managed compatibility prefix, initialized before selection. Launch with argument arrays and an explicit environment. State machine: idle → starting → preview/config/fullscreen → stopping → idle; failures enter a bounded cleanup path then idle. Assign a generation ID so stale exit callbacks cannot destroy a replacement preview. One saver instance per preview owner. Close the previous instance before changing selection, closing the tab, destroying the applet, logging out, or changing resolution.

Own a process group and record exactly the children launched for this operation. Ask its windows to close, wait a short bounded interval, terminate the owned group, then verify it is reaped. Never run a global `wineserver -k` against a prefix shared with other applications. A dedicated prefix allows escalation scoped to this compatibility subsystem if a child escapes its group, but other saver/config operations in the same prefix must still be coordinated. Do not stop an unrelated Wine program.

Capture the original focus and pointer location. After stop, verify both pointer and keyboard can interact with the applet, taskbar, and another application. Suppress the launch click/release and initial pointer warp from instantly dismissing a full-screen preview. Measure the original saver movement threshold; do not assume a guessed tolerance is historically correct. Avoid permanent grabs; if containment needs a temporary grab, pair every acquisition with cleanup in success, cancellation, exception and child-crash paths.

## Concrete acceptance matrix

| Area | Cases | Evidence required |
|---|---|---|
| Preview parent | valid Wine HWND; invalid HWND; host destroyed; tab closed; rapid10 selections | child tree, clipped framebuffer, no desktop spill or survivors |
| Configuration | OK; Cancel; caption Close; Escape; saver crash; missing DLL | applet unblocked, before/after prefix settings, native error |
| Full screen | mouse move/click/wheel; key/Escape; Alt+Tab; initial launch release | original-vs-port dismissal threshold and focus restoration |
| Cancellation | stop during prefix start, binary load, child creation, rendering | no retained grab, bounded stop latency, no orphan |
| Idle ownership | timeout; inhibited video; resumed session; DPMS; suspend | exactly one activation, policy retained, no immediate relaunch |
| Displays | 640×480,800×600,1024×768,1280×1024,1920×1080,2560×1440,3840×2160 | dimensions, aspect, visible bounds, pointer restoration |
| Multi-monitor | two screens; negative origin; mixed scales; unplug while active | no uncovered/stranded windows, defined stretch/per-monitor policy |
| Scaling | 100%,125%,150%,200%; resolution switch during preview | nearest-neighbor UI art; saver viewport correctly resized |
| Isolation | another Wine app active; two setup launches; stale exit callback | unrelated process survives, generation guard works |
| Performance | cold install; cold prefix; warm prefix;30 starts/stops; idle CPU | median/p95 start/stop, peak RSS, CPU, frame timing |
| Historical coverage | each original95/Plus95/98/Plus98/ME/XP binary+dependencies | hash+architecture+version, mode-specific pass/fail, screenshot |

No performance number is fabricated: recommended initial budgets are warm preview visible within250ms, focus restored within100ms after exit, bounded forced cleanup2s. Treat those as targets to measure on the T480-class target and VM, not claims of current performance. Keep a warm prefix only after measuring idle cost; initialize in the background without blocking applet opening.

## Delivery sequence

First prove one 32-bit saver `/s` and all stop paths, then `/c` transactional settings, then real Win32 preview hosting, then idle adapter. Enable only individually passing modes in the catalog with a specific reason beside unavailable modes. Historical16-bit3.x/95 savers need separate runtime proof and may require a VM rather than current Wine. Packaging and native rewrite fallbacks remain independent decisions. Preserve original profile, assets, version and screenshot provenance for each accepted saver.
