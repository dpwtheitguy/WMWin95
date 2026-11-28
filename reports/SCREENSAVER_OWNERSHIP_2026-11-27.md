# Existing XFCE screen saver ownership — 2026-11-27

Display Properties Apply now works with an existing XFCE saver instead of treating every daemon as an unrecoverable conflict. The integration uses a private, persistent session D-Bus connection and reversible cookies. It never writes Xfconf, disables a daemon, changes lock settings, requests a password or asks for elevation.

## Policy and primary evidence

[Xfce's D-Bus API](https://docs.xfce.org/apps/xfce4-screensaver/dbus) defines Inhibit as blocking idle saving while leaving explicit Lock requests effective. Throttle suppresses graphical engines while the service remains active. Cookies disappear when the client connection exits. The implementation uses those two mechanisms rather than stopping the service.

The [installed-family4.18.3 preference definitions](https://github.com/xfce-mirror/xfce4-screensaver/blob/xfce4-screensaver-4.18.3/src/gs-prefs.h) identify the separate global lock and lock-on-saver flags, with conservative true defaults. When automatic idle locking is disabled, our Inhibit cookie lets Win95LX implement the selected saver and wait. When it is enabled or its policy cannot be read, we use Throttle and preserve the daemon's original activation/lock schedule. Wine stops whenever the daemon becomes active; the lock service takes precedence. Choosing None suppresses our animation while preserving any existing session lock behavior.

The [4.18.3 listener source](https://github.com/xfce-mirror/xfce4-screensaver/blob/xfce4-screensaver-4.18.3/src/gs-listener-dbus.c) also exposes GetInhibitors. Other clients' requests inhibit our animation; our unique cookie reason is excluded from that list. No SimulateUserActivity or SetActive(false) calls are used by the coordinator. Its dedicated connection releases cookies on normal close or process death. Unique service owners and display/PID verification prevent a stale cookie being sent to a replacement daemon or another X display.

The prior `pgrep -x xfce4-screensaver` check was defective because Linux process comm names truncate at15 characters. The new path identifies the actual D-Bus owner and its X display. A missing session bus with a detected same-display daemon fails closed with a native error rather than claiming coordination succeeded.

## Actual daemon acceptance

`dev/check_screensaver_ownership.py` ran a real xfce4-screensaver under an owned guest Xvfb and private dbus-run-session, with temporary HOME/config. Evidence: `private/screen-saver-owner-real/report.json` and daemon log.

Seven real-service workflows passed:

1. Non-locking policy acquired a visible Inhibit cookie without changing Xfconf values.
2. Manual activation remained possible; the coordinator did not force deactivation.
3. An independent movie inhibitor blocked our animation and released normally.
4. Enabling automatic locking switched to Throttle and removed the idle inhibitor; policy values stayed unchanged.
5. Normal close released our cookie without modifying settings.
6. Abrupt client exit automatically released its cookie in the actual daemon.
7. Daemon restart acquired a new cookie against the new unique service owner.

The explicit manual activation test used a non-locking disposable policy. It requested no authentication and never touched the user's desktop. The policy-transition test did not weaken the real user's configuration.

## Integrated UI and renderer acceptance

`dev/check_screen_saver_wine_ui.py ... --existing-owner`, launched under private dbus-run-session, ran the new applet with real Wine and an existing real daemon. Evidence: `private/screen-saver-ui-existing-owner-real/report.json` plus framebuffers. Physical selection/Apply, Nature full-screen Preview/Escape, keyboard return, genuine60.42second server-idle activation, owned cleanup and Display-window preservation all passed. The daemon remained running, exact Xfconf property output was unchanged, and the scoped cookie was gone after applet host close. Cold prefix preparation10.94s ran off GTK;3998 heartbeat samples had maximum56.74ms gap; dismissal plus cleanup619ms.

An actual GTK failure test injects failed ownership, clicks Apply and captures the native Display Properties error at `private/screen-saver-owner-ui-800/owner-failure-native.png`. Applied bytes and pending edits remain unchanged. This is an injected failure, separate from the actual daemon tests; denied/unreachable service branches also have CPU coverage.

Sixteen ownership CPU cases cover lock-policy transitions, missing bus, foreign display, external inhibitors, unreadable policy, acquisition failure, idempotence and restart. Three host preference tests cover stale queued Apply, exact-byte theme rollback and removal of newly introduced preferences. Combined saver CPU suite87 tests pass; Themes144 tests and the30-workflow Themes integration regression also pass at this checkpoint.

## Scope and remaining work

Ownership is accepted for the tested X11/XFCE service family. In locking mode, the original daemon's lock/blank schedule intentionally wins over the animation; this preserves policy rather than silently changing its timeout. Other screen saver implementations and Wayland idle ownership are not qualified. The embedded monitor preview remains a separate feature, and Settings still needs full per-option/native-pixel qualification.

Theme integration now exposes a reusable saver provider, warms selected typed original saver identities off GTK, disables OK/Apply while the selected saver prefix is not ready, and preserves independent Display pending edits during theme rollback. A generation check prevents a superseded queued scheduler update from overwriting restored settings. The original definition importer accepts only catalog identities, never arbitrary executable commands.

The actual Themes consumer was subsequently exercised with Wine, not a fake: `private/theme-saver-real/report.json`. Physical selection warmed the typed Nature association, Apply updated the shared real saver state, independent reopening reconciled it, and the native Themes Screen Saver button launched the original renderer. Escape retained the Themes window. An injected failure after actual Travel saver application restored every exact JSON byte and independent Display pending state; the scheduler converged to the restored selection. The QA catalog's twelve associations were derived from original private THM data using the production allowlist parser, not handwritten executable targets.

## Embedded preview follow-up

Original `/p HWND` rendering is proven in the separate compatibility work, but a Linux XID is not a Win32 HWND. A product monitor preview needs an owned Wine Win32 parent, its published true HWND, and an X11 child clipped to the monitor client. Because the shell renders several virtual windows on one GTK canvas, blindly reparenting a child would paint above unrelated virtual windows—the same class of desktop-spill defect previously reported for icons. The follow-up must handle occlusion/minimize/tab departure, dragged/rescaled windows, process cancellation and all resolutions before enabling it. This checkpoint does not expose an unclipped placeholder or claim embedded preview acceptance.
