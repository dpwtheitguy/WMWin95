# Guest privilege requirements ledger

User direction, November 26: settings should work like Windows 95, without sudo, terminal prompts or UAC-like elevation. This ledger tracks requirements for a later declarative installer manifest. It is not yet an installer-consumed permission manifest.

Keep the desktop account non-admin. Install only guest-scoped permissions and helpers. Ordinary executable permission (`chmod +x`) does not grant authority to change protected settings. Prefer an explicit service/policy or device ACL for the required operation. No blanket executable ownership/mode change is planned.

| Operation | Account and mechanism | Current status | Validation |
| --- | --- | --- | --- |
| Time zone | Active local `win95`; timedate1 `set-timezone` policy | Guest rule installed | Corrected visible non-admin UI round trip Los Angeles → Anchorage → Los Angeles passed without elevation; NTP stayed enabled and clock fields were not edited. Evidence: `private/date-time-live-corrected.log` |
| Clock edit | Active local `win95`; timedate1 `set-time` | Guest rule installed | Conversion, DST gap and rollback unit tests; real clock edit not yet exercised |
| Network-time toggle | Active local `win95`; timedate1 `set-ntp` | Guest rule installed | Backend tests; actual zone-only edit kept NTP enabled |
| Fixed-offset zones for DST off | Installer writes `/usr/share/zoneinfo/Win95LX/` | Guest files installed | TZif/date conversion tests; real UI application still needs verification |
| Keyboard repeat/layout | Desktop X11 session ownership | Working without root | Actual isolated X11 repeat/XKB and active group tests |
| Mouse mapping/cursor | Desktop X11 session ownership | Working core controls | Mouse and pointer catalog tests; remaining capability gaps in Mouse report |
| Playback/recording selection and level | User-owned PulseAudio/PipeWire session | Implemented | Owned null sink/input integration with restoration; no system permission change required |
| Sound file selection/playback | User-readable WAV plus session audio | Implemented | All source hashes/headers; real decoder test; event and scheme regressions |
| Display resolution | Desktop RandR ownership | Implemented | 50 driver modes applied/read back; 11 real-pointer Start checks through 8K; original mode restored |
| Per-user font install/remove | User font directory, per-owned-file bitmap acceptance and native Fontconfig cache | Implemented in workspace; not live yet | Disposable TTF/FON import/removal, independent discovery, external same-family rejection and failure rollback passed; no host font changes |
| System font changes | Scoped guest administrative helper | Planned | No grant or acceptance yet |
| Power/reboot/suspend | Guest logind policy/helper | Existing normal requests; policy audit pending | Must validate active non-admin UI with maintenance sessions present |
| Package install/remove | Scoped guest package transaction service | Planned | No broad APT/root grant yet |
| Network/hardware/account administration | Per-operation guest service/policy | Planned | Define required calls alongside each applet and test normal UI and rollback |

The future manifest should identify the operation, beneficiary account/group, exact policy/helper or directory/device ACL, installer action, rollback/removal action, and a test proving the real non-admin UI works. It must distinguish required grants from unimplemented applets and hardware absence. Developer SSH/sudo is maintenance tooling, not the desktop interaction.

## Printer binding development install (2026-11-27)

`dev/guest_install_printers.sh` installs only the distribution `python3-cups`
binding after the existing guest identity guard and root UID check. It does not
create queues, change defaults, install authorization policy or grant desktop
administration. The existing guest CUPS service is retained. Actual installer
packaging must declare this dependency instead of relying on development setup.
Read-only GetServerSettings success is not evidence that a user can administer
queues; privileged action capability and actual server errors require separate
validation. Test-page output syntax needs validation beyond raw byte receipt.

## Create-only Add Printer service (2026-11-27)

`dev/guest_install_printer_service.sh` installs the reviewed module from the
root-owned immutable guest release, enables and restarts its systemd unit. The
script requires the existing QEMU guest identity guard, root UID and dedicated
guest hostname. No corresponding host policy is installed.

The desktop remains non-admin. `/run/win95lx-printers/control.sock` accepts only
the configured `win95` UID through SO_PEERCRED. Its two typed requests are
read-only discovery and new-printer creation; it cannot delete printers, change
server settings, modify a named existing queue, install packages or set the
server default. Requests are serialized and run in bounded disposable workers.
CUPS has no exclusive Add-Modify primitive, so the helper allocates unpredictable
internal queue identities and stores human names separately. A durable intent
precedes mutation; uncertain outcomes preserve the new queue and report partial
completion instead of deleting potentially changed data. Server administrators
remain authoritative. The root-only journal is under
`/var/lib/win95lx/printer-installations/`.

The unit restricts address families to AF_UNIX, protects home/system files,
limits writable paths to its runtime directory and journal, and uses
NoNewPrivileges. CUPS itself handles configured printer transports. No lpadmin,
sudo or general administrative group is added to the desktop account. Optional
test pages and per-user defaults use the normal user's existing printing path.

Root validated the deployed service from the visible non-admin session: real
wizard Finish created a ready unshared queue against an owned IPP emulator,
readback and journal agreed, and the entered human name appeared in Printers.
Only the exact owned test destinations were removed through reviewed developer
maintenance, with original queues and daemon default restored. Evidence:
`private/applets-followup-20261127/`. This is a simulated printer endpoint, not
physical-hardware acceptance. Queue deletion/configuration administration is a
separate unfinished capability; this service does not silently grant it.
