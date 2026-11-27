# Isolated native window-manager feasibility — 2026-11-26

The integration defect is reproduced with the **actual copied Win95LX Shell**, Keyboard Properties, Mouse Properties and Notepad. A real WM fixes the desktop-covering-applications defect, but cannot fix shell-painted Start/Run overlays or interleave internal Explorer frames with native applets. No production WM was changed.

## Isolation and evidence

Harness: `dev/research/check_window_manager_spike.py`. It refuses primary display `:0` and requires `WIN95LX_WM_SPIKE`. Ran on guest-private Xvfb displays :91/:92/:93 with copied source, separate HOME directories and separate DBus sessions for WM cases. Read existing private assets; no applet Apply/OK calls, sound playback, privilege changes, LightDM changes or installed packages. Downloaded/extracted Ubuntu packages beneath `/home/developer/wm-spike/root`; no apt install. Own X servers and WM processes were stopped afterward. The user's visible VM/display remained untouched.

Versions: Xubuntu XFWM4 **4.18.0-1build3**, GTK **3.24.41-4ubuntu1.3**; extracted IceWM **3.4.5-1build2**, Xvfb **21.1.12-1ubuntu1.9**, xdotool **3.20160805.1-5build1**. Package copyright records are preserved under `private/research/wm-spike-20261126/license-evidence/`: XFWM4 GPL2+ and IceWM component grants as recorded there; no code copied from either. Candidate upstream pinned source and licensing research remains in the Explorer development plan; binary package versions here are the actual tested builds, not those newer source HEADs.

Artifacts: `private/research/wm-spike-20261126/manifest.json`, four `results-*/results.json` files, **36 state screenshots**, X root properties and WM/harness logs. Each state records XGetInputFocus, XQueryTree bottom-to-top root child order, native top ancestor, Gtk visible/mapped/active/decorated flags, and shell Start/dialog state. GTK mapped=true alone is insufficient: a mapped app can be fully covered.

## Results

| Case | Native apps after focusing shell | Start/Run painted overlay | Ctrl+Esc from Keyboard | Alt+Space |
|---|---|---|---|---|
| No WM | All three below fullscreen shell | Visible while applications hidden | Keyboard destroyed by Cancel | Not tested |
| XFWM4 | All three above shell | Covered by native applets | Keyboard destroyed by Cancel | XFCE system menu appears: unacceptable visible branding/extra choices |
| IceWM, taskbar disabled | All three above shell | Covered by native applets | Intercepted by IceWM's Programs/Windows/Settings/Logout menu | Not tested in this first case |
| IceWM minimal shortcuts disabled | All three above shell | Covered by native applets | Keyboard destroyed by Cancel | No competing WM menu in screenshot; our applet still needs native system-menu routing |

All actual app windows report decorated=false; WMs did not add titlebar chrome. Hide/show/present of Notepad mapped and restored as expected in the recorded states; this is not a complete taskbar/AltTab/modal acceptance pass. The existing Escape handler is independently confirmed defective: excluding a conflicting WM shortcut makes Ctrl+Esc reach Keyboard and close it.

**No WM, shell focused:** applets remain mapped but are covered.

![No WM covering apps](/home/dwilson/Documents/Windows95/private/research/wm-spike-20261126/results-none/shell_focus.png)

**XFWM4:** applets remain visible, but Start is behind them.

![Start behind applets](/home/dwilson/Documents/Windows95/private/research/wm-spike-20261126/results-xfwm/start_overlay.png)

**Independent native popup feasibility probe:** a generic `Gtk.WindowType.POPUP` can appear above both Explorer's painted surface and native applets without raising the desktop. This probe is deliberately not styled or integrated. Its success proves a layering mechanism, not correct menu grabs, keyboard routing or dismissal.

![Independent popup above apps](/home/dwilson/Documents/Windows95/private/research/wm-spike-20261126/results-xfwm/native_popup_probe.png)

**XFWM4 default shortcut conflict:** Alt+Space reveals its own system menu even on undecorated applets.

![Unwanted XFCE system menu](/home/dwilson/Documents/Windows95/private/research/wm-spike-20261126/results-xfwm/alt_space_applet.png)

Minimal IceWM configuration used only in its isolated HOME:

```
ShowTaskBar=0
TaskBarShowTray=0
KeySysMenu=""
KeyWinMenu=""
KeySysWinMenu=""
```

IceWM logged a missing default theme because extracted data did not occupy its compiled system path. Clients are undecorated, so this did not prevent measuring focus/stacking; it precludes any claim its decorations/themes were accepted. Linux-explorer's WM source was inspected previously but not built in this pass: simpler installed/extracted candidates already establish the architecture issue. Avoid loading a complete competing desktop to answer this narrow question.

## Minimally disruptive next implementation

1. Preserve every existing applet backend, controls and asset rendering. Adopt one native WM only after a checkpointed isolated acceptance gate. XFWM4 is already present; its shortcut configuration must be isolated and stripped of conflicting visible menus. Minimal IceWM is a viable alternative, with its own global menus/taskbar disabled. Do not deploy either configuration from this spike.
2. Fix modifier-aware Escape and establish exactly one owner of global Ctrl+Esc/AltTab/AltSpace. Native app controls must not interpret Ctrl+Esc as Cancel. Route applet system commands to existing Windows-style chrome/menu and preserve pending edits.
3. Extract Start/submenus/context menus and Run from fullscreen Cairo into dedicated native popup/dialog surfaces using the existing painters, hit logic and control metrics. Add explicit ownership/focus restoration/grabs; the generic popup probe is not enough.
4. Separate desktop background/taskbar layers and migrate one Explorer frame at a time into its own undecorated native window. Keep folder/browser/selection state and shared controls. Internal virtual Explorer frames cannot interleave independently with native applets under any external WM.
5. Accept mixed-app behavior before expanding applets: two Explorer folders, two pending-edit CPLs and unsaved Notepad; click/keyboard/taskbar cycle, popup overlap, minimize/restore, owner/dialog stacking, modal behavior, crash and launch while menu open. Test 800×600 and modern scaled modes; capture native Windows 95 comparison states. Real pointer tests and all six integration scenarios in `EXPLORER_DEVELOPMENT_PLAN.md` remain necessary.

No new UI behavior has been deployed. This spike identifies which layer solves each defect and offers a migration path that retains the applet work. Performance, pixel equality, global shortcuts and full desktop functionality remain unaccepted until measured in that integrated implementation.
