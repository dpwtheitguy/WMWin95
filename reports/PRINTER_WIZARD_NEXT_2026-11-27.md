# Add Printer — working create-only implementation

Current delivery: release `ecf12b033a5104fe`; root verified real normal-session
creation, ownership journal/readback and exact owned-queue cleanup. See
[consolidated delivery](APPLET_DELIVERY_2026-11-27.md) for final checks and scope.

The five-page wizard now has a real installation executor and a narrowly scoped
service. Root owns registration, final immutable guest deployment, normal
non-admin session validation and the consolidated acceptance report. This report
does not claim that the complete original printer subsystem is implemented.

## Original reference and native controls

The independent Plus+IE4 Windows95C reference captures and child HWND metadata are
in `private/reference-tools/printers-native-20261127/`. The native wizard HWND is
441×323. Its observed page sequence is Welcome → manufacturer/model → port →
name → test page. This installed reference does not expose a local/network-choice
page. Back is(193,287,75,23), Next/Finish(268,287,75,23), and
Cancel(353,287,75,23). Original raw labels are `< &Back`, `Next >`, `Finish`,
`Cancel`; Next has no Alt+N mnemonic. The caption has **no Close button**.

`stage_wizard` in `tools/stage_printers_assets.py` checks every original capture's
HWND dimensions and the independently recorded command-button rectangles before
staging private frames/provenance. No original assets enter Git. The consumer
uses the shared measured command-button renderer, shared edit-selection model,
shared page-aware gray/stipple scrollbar and measured native radio artwork.
Original installed Windows drivers are not executed or copied into Linux CUPS.

The driver page uses the actual installed driver inventory and IPP Everywhere.
The port page adapts to a useful printer-address edit rather than pretending
Windows printer ports are Linux ports. These **adapted dynamic contents are not
claimed pixel-identical** to the original port or populated driver pages.

## Working behavior

- Normal construction immediately paints Welcome, then discovers endpoints,
  installed drivers and existing printer names on a background worker.
- Manufacturer and model lists support pointer selection, arrow/Home/End/Page
  keys, tab focus, overflowing lists, independent scroll position and gray
  scrollbar arrows/thumb dragging. Address/name entries preserve caret,
  selection and horizontal visibility; Back preserves values.
- IPP/IPPS, AppSocket and LPD addresses are validated. A USB serial/interface URI
  is accepted only when it exactly matches an actually discovered USB endpoint.
  Bare `ipp`/`ipps` backend advertisements never become invented printers.
- Finish revalidates the latest inventory in the service, creates a fresh
  internal destination, verifies its description/address, explicitly disables
  sharing, enables it, accepts jobs and checks actual ready/accepting attributes.
- Human descriptions remain separate from stable queue identifiers. Printers
  displays new generated destinations by human description and sorts display
  labels rather than random identifiers. Existing queue labels stay unchanged.
  The queue caption uses the human description after readback and a generic
  Printer label during initial load; it does not flash the random ID.
- Optional test-page Yes submits through the non-admin printing backend after
  creation. No is the default, so Finish does not unexpectedly print. The typed
  optional per-user-default path also stays in the non-admin client; there is
  no implicit server-default change and no exposed wizard default-printer toggle.
- Read-only discovery can be canceled immediately; late completion cannot reopen
  a destroyed window. Once Finish is dispatched, Cancel/Escape/repeated Enter or
  double-click cannot cause another request or pretend the request was undone.
  GTK drawing remains responsive while the bounded operation finishes.
- Failed discovery leaves a truthful status and disabled Next. Native-style
  errors use the shared dialogs. Have Disk is disabled with a concrete,
  keyboard-accessible compatibility reason; there is no visible Linux/sudo/UAC
  installation flow.

## Scoped service and failure semantics

`control_panel/printer_service.py` provides only `discover` and `install` through
an AF_UNIX socket. Production paths and CUPS endpoint are fixed, and the service
checks actual SO_PEERCRED against the desktop user's UID. Requests are serialized.
A disposable child process provides a20s bound around libcups discovery and IPP
negotiation; timing out a thread would not provide that guarantee. The client
also bounds response size and socket time.

`dev/guest_install_printer_service.sh` is a dedicated-guest/root-only installer.
It runs the module from the root-owned immutable current release, sets an
AF_UNIX-only systemd sandbox, and enables **and restarts** the service so a new
release is actually loaded. It grants neither lpadmin membership nor general
printer administration to the desktop account. No host printing policies were
changed in this agent's work.

CUPS Add-Modify cannot exclusively create a chosen display-name destination.
The executor therefore never passes a user-selected existing name as its target:
it allocates a cryptographically random128-bit `w95lx_…` identity internally and
checks collisions, while keeping the user's human name as printer-info. A
root-owned, fsynced atomic intent journal precedes mutation. Readback is explicit.
A server administrator remains authoritative; this is not a lock against root.

There is deliberately no optimistic delete rollback. Lost responses, journal
failure after mutation, changed readback or failed activation retain the new
queue and report partial completion with its known identity to the client.
Timeouts say to check Printers before retrying. Existing destinations, jobs,
server settings and defaults are not changed by the create service. Queue
removal/administration remains separate unfinished capability work.

## Tests, evidence and discovered defects

22 distinct deterministic unit tests pass. They cover device advertisements,
real driver identity, malformed/credential-bearing endpoints, exact discovered
USB serial addresses, stale drivers, case-insensitive names/descriptions,
navigation, random-ID collisions, actual transaction phases, pre/post-mutation
journal failures, lost add response, changed readback, partial activation and
atomic journal reopening. They do not substitute for actual guest effects.

Physical XTest UAT passed at800×600 and1280×720 in owned X11 displays with
disposable HOME. Six grouped scenarios exercise all five pages, keyboard model
navigation, actual scrollbar-arrow scrolling without changing selection, typed
fields, Back, exactly-once Finish under repeated input, cancellation during
slow discovery, late callback disposal, unavailable service and unknown keys.
The absence of a top-right phantom Close action is explicitly checked.
Each run compares the complete three Welcome command buttons to the original:
**zero differing pixels for Back, Next and Cancel**. This is six repeated region
comparisons, not six different controls or complete-page acceptance.

Evidence in the guest QA tree `/home/developer/win95lx-applets-qa-20261127/private/`:

- `printer-wizard-final-800/report.json` and PNG states;
- `printer-wizard-final-1280/report.json` and PNG states;
- `printer-install-actual-6/report.json`, helper/emulator/scheduler logs.

Earlier physical captures are copied locally under
`private/printer-app-20261127/`; their earlier wording precedes the final
immersion-only text correction. Root's final exact-source guest checks establish
the delivered wording. Independent original captures remain separate.

The real backend proof starts a private guest CUPS scheduler and an owned
`ippeveprinter` on loopback, runs the actual AF_UNIX RPC, verifies a real
negotiated IPP Everywhere PPD, ready/unshared destination and durable journal,
and sends the optional PostScript test page. CUPS correctly converts it to PWG
raster; actual PWG bytes arrive in the owned emulator spool. Eight grouped
scenarios also reject repeat names, preserve an existing owned destination when
another IPP endpoint is unreachable, reject a mismatched real peer UID and
handle an unavailable helper. The normal guest queue/default baseline is
identical afterward and all owned service/emulator processes exit.

Actual discovery measured1803.62ms and create/negotiation1562.30ms in that single
owned guest run. Both are off the UI thread. These are backend samples, not a
first-paint, boot-speed or sustained performance improvement claim.

Genuine defects found/corrected during this iteration:

1. getPrinters omits `printer-is-accepting-jobs`; using it as false made a ready
   printer falsely fail. Verification now explicitly requests actual printer
   attributes. Real CUPS caught this, not a mock.
2. A journal failure after successful add could lose the partial queue identity;
   every post-mutation failure now retains/report that identity without deleting.
3. The prototype's invisible caption Close hit canceled from an area where the
   original has no Close button. That hit is gone and its absence is tested.
4. Standard USB serial query URIs were filtered out; actual discovered safe
   serial/interface forms are now preserved and undeclared targets rejected.
5. The prototype registered every list row as a separate tab stop; explicit
   wizard ordering now treats each manufacturer/model list as one control and
   keeps focus on its selected row. Physical Tab/End/Home exercises this path.
6. Internal random destination labels could leak into the UI and sort randomly;
   display descriptions, caption fallback and display-label ordering are separate.

Test corrections are not counted as product defects: physical XTest colon input
needed Shift; the optional print proof initially looked for literal PS text in
correctly converted PWG bytes; and getPPD on the private Unix scheduler queried
the normal HTTP destination, so the owned scheduler's actual PPD file is checked
instead. Failing logs are preserved; no baseline was replaced to force equality.

## Remaining limits and delivery gate

Root must validate the final installed root service through the normal win95
non-admin desktop before claiming production-path acceptance. This agent did not
touch system CUPS, deploy, restart the visible VM or take any reference VM lease.
No physical USB/network printer has been available for hardware validation.

Not accepted: all native wizard page pixels/variants, full list/scrollbar
state matrix, driver package installation/Have Disk, user-managed port deletion,
sharing, fax/modem drivers, printer deletion or administration, all printer
properties, and every Classic/IE4/Plus release variant. The native source is the
measured Plus+IE4 configuration, not every Windows95 release. The existing
Printers queue functionality remains separately documented and tested.

## Live follow-up — reveal the actual selected driver

Root's normal-session test found that real CUPS inventory has enough manufacturers
before Generic and enough Generic models before IPP Everywhere to put both
initial selections outside their visible seven-row panes. The first fixture's
two manufacturers did not expose that defect. A correct saved selection is not
a usable selection if its control does not reveal it.

On entering/reentering the driver page, the wizard now requests a one-time
ensure-visible pass for both selected values and focuses the manufacturer list,
as shown in the independent native driver-page capture. This does not fight
subsequent user scrolling. Selecting another manufacturer resets/reveals that
manufacturer's first model. The expanded regression uses24 manufacturers and24
Generic drivers before the defaults; actual XTest verifies visible hit targets,
focus, forward/Back reentry and the new-manufacturer reset at both800 and1280.
Seven grouped physical scenarios now pass. Evidence:
`printer-wizard-deep-{800,1280}/report.json` in the guest QA directory. The prior
immutable candidate `ffb0f0a436369c4d` fails this new case as expected. Diagnostic
captures/JSON are written before the visibility assertion for before/after review.


## Root normal-session delivery validation

The visible non-admin guest successfully installed an owned IPP emulator through
Run → Control Printers → Add Printer, with actual QMP pointer/keyboard input.
Root inspected the real production service's readback and root-only ownership
journal: human description, device URI, ready phase, accepting state and unshared
state agreed. A second run used an explicitly observed complete name, UI Proof
Printer, and verified it appeared unchanged in the folder. Source screenshots
are under `private/applets-followup-20261127/`. Fast QMP typing in the first run
delivered a shorter name; the backend correctly preserved the received value.
The final run paced input and captured the full field before continuing.

Root removed only the two exact owned UAT queues after matching their identities,
descriptions, endpoints and journals, and confirming no pending jobs. Original
queues and daemon default were restored exactly; the emulator was stopped, while
the normal printing service remains running. This proves the normal non-admin
production creation path, not physical printer hardware.

The live pass also caught Add Printer's obsolete disabled-gray label; the shell
now uses normal black/selected white and its actual-renderer regression checks
both. The initial selected-driver reveal defect is covered above. Queue windows
now receive the known cached human caption immediately rather than a generic
placeholder while the asynchronous CUPS readback finishes. That last caption
change receives the root targeted Printers rerun; it changes no queue execution.

Candidate434dad738f4a021d passed the normal-session creation path. The final
consolidated applet report records the superseding release/checkpoint identity.
