# Desktop functional profiles and component setup

Decision, November 26: use **Add/Remove Programs → Windows Setup** for compatibility presets, shell features and optional components. Do not add another default Control Panel icon. A normal installed-program entry named Desktop Enhancements may lead to the same component settings if needed. Keep the original applet layout, controls and terminology.

The initial catalogue is `config/functional-profiles.json`. It records existing code, research and future work separately. It is not a working profile switch or a claim that every listed feature exists. No packages are installed from this catalogue. Office-style software remains future work.

Classic versus IE4 Desktop Update is one axis; Plus! is another. Support presets for their combinations and validated custom selections. Win98/XP asset collections do not silently turn the shell into those OS versions. Separate component installation, feature availability, profile defaults and per-window/user preferences. A module that exists is not automatically globally switchable.

Resolve dependencies, conflicts and installed capabilities at Apply time. Only expose a toggle once its setting changes the actual consumer and has Apply/Cancel, rollback, persistence, native-state and performance evidence. Unsupported combinations need a specific reason; do not offer nonfunctional switches. Keep window/frame/control variants tied to measured reference configurations.

## Responsiveness contract

Load and validate configuration once, compile immutable resolved profile values and pass that snapshot to Explorer, applets and shared controls. Click/paint paths use memory only: no JSON reads, filesystem probes, APT queries or subprocesses. This is a design contract, not an achieved latency benchmark.

For live-safe changes, publish one change notification to affected consumers. Preserve paths, selections and unsaved documents. Reopening a window, session restart or reboot is acceptable when needed and must be stated before Apply. Package installation/removal runs in a background transaction through the eventual scoped guest service and curated package allowlist, with a native progress/error flow. Never expose sudo or an elevation dialog.

APT packages belong to a component registry with display names, dependencies, optional asset imports and placement rules. Show user applications, not Debian's internal dependency packages. Games and Entertainment Packs remain optional; no Office implementation or game installation is authorized by this design step.

## First integrations

Start with already understood Explorer toolbar/address/Web View defaults, then explicit IE corner/logo and menu profiles. Classic layout and full frame/control profile changes require additional reference coverage before calling a whole preset accepted. Boot artwork needs a separate privileged installer operation; package inventory is refreshed only after transactions. Each feature declares live, reopen, session-restart or reboot behavior.

The catalogue starts with a bounded set of evidence-linked features. Extend it as confirmed differences are discovered; record research candidates without presenting them as historical facts or available settings.


## Active Desktop and feature boundaries

Keep these distinct in the component registry and resolved settings:

- Classic/IE4 shell presentation: menus, toolbar/address bar, Web View, corner
  animation and browsing defaults, with measured visual variants.
- Plus enhancements: themes, pointers, sounds, backgrounds and screensavers.
- Desktop HTML presentation: a separately implemented rendering capability; an
  IE4 visual preset alone does not imply a working browser or Active Desktop.

The user clarified that the requested feature is Active Desktop, not ActiveX.
No ActiveX runtime work is requested. Support classic wallpaper and patterns
independently from Active Desktop. Model IE4 shell enhancements, Web View and
HTML desktop content separately where the original permits; switching modes
must preserve wallpaper, icon positions, user files and per-mode preferences.
Only expose implemented combinations with native-reference and behavior tests.
Keep resolved settings cached, with no configuration reads in paint/click paths.

Easter eggs are fidelity features documented in `docs/EASTER_EGGS.md`. The
Volcano behavior depends on the 3D Text screensaver component. CLSID folder
resolution belongs to the shared namespace registry independently of an ActiveX
runtime; a recognized GUID is not permission to execute arbitrary COM code.
