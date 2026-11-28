# Morning delivery — 28 November 2026

Deployed release: /opt/win95lx/releases/86f0ce24d8a32c5d.

Themes now supports Save/Delete, data-only native theme import, original13-preset
appearance data and transactional saver associations. Original95/Plus savers
run through one shared private Wine environment with original fonts, quiet
preparation and preserved global/per-saver settings. Display selection, wait,
fullscreen Preview, Settings and coordinated idle activation have actual guest
proof; not every configuration parameter or pixel state is accepted.

Final CPU run:762 tests, one opt-in skip. Final eight isolated GUI runs pass at
800×600 and1280×720, plus the Makefile import wrapper passes both sizes.
See THEMES_SAVERS_RELEASE_REVIEW_2026-11-28.md for scope. Controlled live Mystify
Preview/Escape preserves Display; an earlier run was rejected after the user
confirmed concurrent VM input. No speculative input fix was made.

Deployment discovery: generated saver directory inherited private build mode700,
so copied root-owned assets were unreadable to win95. Installer now sets asset
directories755/files644, keeps source/release unwritable to normal users, and
checks guest-account catalog readability. Live Themes and Screen Saver pages
open; original Mystify renders fullscreen. Existing preferences were not applied
or replaced during this check; pending saver selection was cancelled.

Network's existing-profile backend passed genuine desktop UID1001/session-c10
socket authorization, dummy address/DNS modification, NM/kernel readback,
unrelated-profile denial and restoration. Temporary service/policy/socket/profile/
device were removed; primary routes/rules/ens2/resolver/hostname/resolv.conf match
baseline exactly. Network remains unregistered: physical-adapter production
policy and broader applet features are not accepted by the dummy-only proof.

Private evidence: private/morning-deploy-20261128/ and
private/network-service-qa-20261127/. Recovery checkpoint before deployment:
before-morning-deploy-20261128. Prior runtime checkpoint:
after-screensaver-gl-runtime-20261127. Working-release checkpoint `themes-savers-ready-20261128` was verified after
final desktop verification.

Remaining: embedded monitor preview, complete themed preview/raw CPL color-role
coverage, common-dialog multi-column layout, full native saver Settings fidelity,
external-theme-folder parity, final installer manifest consumption and physical
Network policy/functional acceptance. Explorer Recycle Bin menu-to-modal focus
validation is queued in EXPLORER_DEVELOPMENT_PLAN.md per user direction.
