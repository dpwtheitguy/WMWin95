# Themes and Screen Savers release review — 28 November 2026

This review uses the newly rebuilt `private/shell-assets`, not the isolated experimental appearance catalog. It does not certify complete Windows 95 visual equivalence.

## Accepted functional subset

The native preset catalog now retains original color/font/metric definitions and Windows Default. Actual-provider thirteen-preset Apply/reopen checks pass at800×600 (256-color profile) and1280×720 (truecolor profile): `private/final-theme-20261128-{800,1280}/report.json`.

Physical Save As/Apply/reopen/Delete-No/Delete-Yes checks and thirty distinct provider composition save/apply/reopen workflows pass at both sizes: `private/final-customization-20261128-{800,1280}/report.json`. These are thirty provider integration scenarios per run, not thirty independent physical GUI cases.

Display Screen Saver selection, Wait input, Apply/Cancel/reopen, nonblocking callbacks and lifecycle UI checks pass at both sizes: `private/final-saver-20261128-{800,1280}/report.json`. These two UI harnesses explicitly use a fake runtime and do not establish Wine rendering. Actual original executable, grouped prefix, quiet preparation, Linux desktop capture and XFCE idle-owner evidence remain in the separate runtime/ownership reports and private proofs; they must not be counted as effects of these fake-runtime runs.

Full exact visual acceptance from the prior native comparisons remains scoped: Delete question366×119 is0/43554 pixels different, and Screen Saver page404×448 in the captured None/focused/disabled-Wait1/Apply-enabled state is0/180992. The final functional harness does not extend those exact claims to other control states.

Complete native .theme physical Other/Open/missing-asset-error/Cancel/no writes/Apply/reopen also passes at both final sizes: `private/final-import{800,1280}-20261128/report.json`. Seven actual host providers are exercised; the host has no Wine and this test does not simulate an eighth provider. Source media remain unchanged and eight original icon cache variants are produced.

All eight final UI processes exited0; no new product defect was found.

## Remaining capability gaps

| Area | Current behavior | Release assessment |
|---|---|---|
| Main Themes preview | Illustrative captured layers plus supported dynamic components | Incomplete: imported font/color/icon/metric appearance does not perfectly reproduce every sample layer. |
| Themed applet bodies | Semantic live controls honor supported roles | Incomplete: original raw gray CPL art needs per-role masks/redraw; whole-window themed pixels not accepted. |
| Save/Open file list | Shared filesystem behavior, bounded filenames and native frame/profile | Incomplete: single-column GTK file list differs from original multi-column common dialog. |
| Embedded saver monitor | Disabled with reason | Incomplete: needs trusted Win32 HWND host and correct clipping/occlusion with shell virtual windows. Full-screen Preview remains separate. |
| Original saver Settings | Launches genuine original configuration applet | Functional controls have bounded actual proofs; all configurations and Wine typography are not pixel accepted. |
| Native theme import | Complete95/Plus INI definitions, data-only, bounded local media | Partial/modern definitions, arbitrary DLL resources and executable commands unsupported; explicit native errors. |
| External theme-folder persistence | Managed imports apply/reopen tested | Native external Apply/reopen directory semantics are not independently accepted; preserve that discrepancy. |
| Lock/password/power | Existing XFCE lock policy preserved; unsupported controls explain ownership | Do not claim a replacement lock/password or power implementation. |

Earlier reports contain checkpoint statements subsequently superseded: legacy `.theme` import now exists; Themes can include the screen saver component; existing XFCE daemon coordination is implemented and actual-tested. This table preserves the remaining gaps rather than carrying those old blockers forward.

## Regression entry points

The Makefile currently exposes `check-themes` but omits dedicated customization/import/saver/ownership/appearance UI targets. Recommended: add bounded isolated targets with both guest sizes; prepare the disposable import fixture as an explicit dependency; keep genuine Wine/runtime and owner tests separately capability-qualified. Parent owns Makefile/release wiring. No product source or visible user desktop was modified by this review.
