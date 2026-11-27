# Asynchronous tray volume updates — 2026-11-26

Ready for parent review; no staging or commit performed by this worker. This iteration changes only VolumePopup, its new independent playback-update module, their tests/checker, and this report. UI registration and other apps are unchanged.

## Result

Opening, dragging and keyboard volume changes no longer run pactl on GTK's thread. The initial actual-device read is asynchronous, the popup paints immediately, and optimistic slider changes are reconciled with verified backend results. Mute waits for the initial actual read rather than toggling a guessed state.

New `control_panel/audio_updates.py` provides a single serialized worker, one last-write-wins pending volume/mute dictionary, sequence-numbered main-loop callbacks and asynchronous close draining. The initial actual default device is pinned; subsequent default changes reject stale popup intent rather than redirecting it. Only sink state is read/written: recording and default devices are never changed. Channel ratios remain canonical across this worker's own writes, including zero; external channel changes reseed the ratio.

Closing suppresses callbacks into the destroyed popup and drains the final intent. A new popup waits for its predecessor off the UI thread, so an old closing popup cannot overwrite a newer popup's requested level. Completed predecessor/callback references are cleared. A failed final user intent notifies the still-realized shell through a weak owner reference and the shared native error dialog; it does not invoke the destroyed popup. Initial-query-only errors after close do not generate a late alert.

Failure reconciliation reads actual device state instead of blindly restoring an old snapshot. A command can have succeeded before a client-side error or an external program can have changed the setting; speculative rollback could overwrite that newer state. The popup returns to actual readback and reports failure. If the service has disappeared, no actual readback is claimed.

## Defects reproduced and corrected

1. Existing motion handling synchronously made nine pactl calls: four-command snapshot, one write, another four-command snapshot. The private slow-service baseline measured181.34ms median handler at20ms per command.
2. Closed popup work could overlap a reopened popup and overwrite newer intent. The predecessor barrier and quick-reopen tests fix ordering without waiting on GTK.
3. Suppressing every post-close callback hid final-write failures and could retain optimistic tray mute. Independent weak-shell error delivery now reports and reconciles that case.
4. Repeated legacy per-channel scaling from already rounded values drifted(65536,32768) to(65536,32836) after levels1→100. The popup worker retains a canonical ratio across its own writes. Evidence: `private/performance/volume-pipeline-20261126/balance-drift.json`. The separate Multimedia adapter is unchanged; centralizing this improvement there is a possible later task.

## Tests and acceptance evidence

**14 new unit tests pass**, plus12 existing audio-preference tests:26 targeted tests total. They cover asynchronous startup, sink-only reads, coalesced volume/mute, exact zero/restore and repeated balance, external balance, default changes, vanished device/service, failure before/after writes, preserving external changes, close flush/cancel, no surviving workers, quick reopen ordering, late failure delivery, initial-read-only error suppression, and input validation.

Final isolated guest GTK checks ran with GDK_BACKEND=x11, WAYLAND_DISPLAY unset, and display identity asserted, at800×600 and1280×720. Each also started and destroyed its own private PulseAudio daemon with disposable null sinks on a private Unix socket. No user server, live display, user audio/defaults or shared preview source was modified.

Evidence directories:

- `private/screenshots/volume-async-reviewed-800/`
- `private/screenshots/volume-async-reviewed-1280/`

Both report zero failures. They retain the existing tray preference/placement, pointer and keyboard volume/mute, persisted show/hide and Cancel coverage, plus coalescing, actual GTK painting, failure reconciliation, close/reopen and destroyed-popup safety checks. The real private service ends at channels(47841,23920), volume73%, muteFalse, with recording/defaults unchanged. Switching to a second owned default rejects the old intent with no channel writes; terminating the private server produces a reported error and an exited worker. The daemon is reaped and temporary server directories are removed.

## Performance

Measured with a deterministic20ms delay per audio command, inside the actual popup and isolated GTK display:

| Measurement |800×600|1280×720|
|---|---:|---:|
|Constructor|1.45ms|1.45ms|
|First actual paint|25.27ms|44.16ms|
|Maximum input handler|0.057ms|0.071ms|
|Maximum event-to-draw delay|15.22ms|26.32ms|
|Maximum main-loop heartbeat gap|10.15ms|25.58ms|
|Backend volume writes for40 slider inputs plus final73|3|3|

Feedback remained under the50ms goal in both runs. Event-to-draw timing begins at the oldest pending input since the preceding paint. These are controlled slow-service measurements, not real hardware audio latency or universal scheduler guarantees. Final sound-server completion remains asynchronous and depends on backend response time. The production adapter's existing subprocess timeout remains five seconds per command; a stalled service can leave bounded background work after popup close, while GTK remains responsive.

## Limits and next review

Native popup screenshot acceptance is still pending, as before this change; geometry derives from original SNDVOL32 dialog106. The ready-state rendering is unchanged; Mute temporarily appears disabled until actual state arrives. This report does not claim new pixel acceptance for the popup.

The worker is daemonized. Popup close and quick reopen are validated; whole-process termination can still interrupt outstanding audio work. A global application-shutdown drain policy would require separate shell lifecycle integration. Default-device read/check and explicit sink write are not an atomic server transaction: a concurrent switch after the check can still leave a write to the original pinned sink, but never changes a default or silently redirects that write to the new sink.

Root should review the new API/error lifecycle and run the consolidated suite before committing or deployment. No live-session deployment was performed.
