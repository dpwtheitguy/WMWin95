# Network inventory follow-up — 27 November 2026

Unregistered secondary prototype slice; no service policy, catalog route or live
network configuration changed. The existing Network/TCP-IP model and renderer
were retained. Full Network delivery remains blocked on normal-account service
authorization and wider dynamic-control acceptance; see the November26 Network
and policy reports.

## Actual backend and historical fit

Read-only guest inspection confirms NetworkManager active, systemd-networkd
inactive, nmcli present and netplan files in use. The existing backend parsed the
actual configured profile and adapter; a separate `ip -j address` query recorded
its active leases without editing them. Evidence:
`private/network-followup-20261127/actual-guest-readonly.json`. No secrets, Wi-Fi
credentials, new profile, policy or ens2/SSH mutation was requested.

No redundant native Network capture was necessary for this slice: independently
reviewed original Network/TCP-IP frames, HWND geometry, System font and radio
states already exist from November26. The classic reference briefly inspected
for Power was restored to its verified checkpoint and released, running with
empty floppy. There is no claim that an IE4 capture establishes every release.

## Genuine defects corrected

1. NetworkWindow constructed NetworkController by synchronously reading all
   profiles on the GTK thread. An intentionally blocked read now runs on a daemon
   worker; the window draws, timers dispatch and Escape cancels while it waits.
   Destroyed windows ignore late callbacks. Initial failure is explicit and OK
   remains disabled, including Return fallback; no empty fake state is applied.
2. The main list rendered only the first five profiles with no overflow access.
   It now uses the shared page-aware scrollbar, physical thumb/arrow/wheel input,
   Home/End/PageUp/PageDown/arrow navigation and reveal of the selected adapter.
   Manual scrolling preserves selection. Long names are clipped inside list and
   description viewports. Last-row Properties targets its actual UUID.
3. Async Apply completion ignores a destroyed owner; in-flight mutation cannot
   be canceled by a window delete event. Unexpected worker exceptions reach the
   native error path instead of leaving the interface permanently busy.

The model's optional initial snapshot lets the UI start without synchronous
service I/O. It does not fabricate a discovered adapter or imply authorization.

## Tests and evidence

All32 existing Network backend/radio tests pass. Existing Network UI regression
passes at800×600 and1280×720, preserving zero differences for the recorded native
caption/tabs, command buttons, typed IPv4 interior and normal radio/label regions.
The new scrollbar's complete native strip/focus states are not accepted here.

`dev/check_network_inventory.py` owns its Xvfb process, isolated HOME/config and
actual XTest pointer/keyboard input. Five grouped scenarios pass at both sizes:
blocked loading/cancel/late result;12-profile keyboard reachability and long
labels; actual thumb/arrow/wheel preserving selection; correct last-profile
Properties and child/parent Cancel with zero service writes; and discovery error
with disabled OK/usable Escape. Captures use actual GDK framebuffer pixels.

Evidence: `private/network-followup-20261127/{final-800,final-1280}/`,
`existing-{800,1280}/`, and `units.log`. Constructor samples were approximately
3–5ms in the owned host tests while the fixture read remained blocked. The old
committed UI source fails the new constructor regression after its full five-
second fixture wait, proving detection; this is not a whole-applet speedup claim.

The initial old-source attempt was rejected: importing another QA helper had
prepended the active checkout, so it accidentally tested the fixed UI. The
checker now reasserts and verifies the requested source module path before
loading it. Verified old-source failure and construction metadata are in
`before-verified-800/` and its log; the misleading first attempt is retained as
rejected harness evidence, not counted as a product pass.

Next: narrow authenticated existing-profile service with ownership/stale-state
checks, bounded activation/readback and deliberate rollback tests, then actual
normal-account success. Do not substitute the existing maintenance-root dummy
proof for that user path. Further UI work includes complete original list focus/
scrollbar states, keyboard Help/error state coverage and the remaining unsupported
bindings/WINS/sharing/identification features. No applet-completeness claim made.
