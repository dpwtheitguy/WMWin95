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
