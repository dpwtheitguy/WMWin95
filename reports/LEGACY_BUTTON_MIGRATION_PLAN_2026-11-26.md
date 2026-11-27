# Typed legacy-button migration plan — 26 November 2026

Plan only. Do not replace `Painter.button` globally: 19 source sites include actual command buttons, owner-drawn tabs/arrows and inactive/fallback paths. Root assigns implementation later. Preserve current shared command-button state metrics and each consumer's actual native HWND rectangle.

Independent audit baseline: original classic Win95 stock BUTTON OK, 75×23 normal/default/pressed differs from legacy by38/606/224 pixels; measured command renderer differs by0. Exact comparison inputs/digests are in `private/research/control-defaults-20261126/legacy-button-comparison.json`. This does not establish native command metrics for a tab or a16×17 dropdown arrow.

| Consumer/site | Semantic role | Proposed treatment |
|---|---|---|
| `shell/app.py:Shell.button` | Generic legacy shell callback wrapper | Audit callers before changing wrapper. Carry command identity/enabled/default/focus/pressed/mnemonic separately from painting. Deprecated static-app fallback is not automatically a live path. |
| `control_panel/display_settings.py` Background/Settings | TabStrip fallback | Exclude from command migration. Use measured tab profile/artwork and selected-page behavior. |
| Same module Apply | Standard command, sometimes native sprite | Keep accepted native sprite branch; migrate fallback repaint only after verifying original HWND and disabled/default states. |
| Same module OK/Cancel fallback | Standard bottom commands | Measured command renderer with proper focused default transfer; preserve native-framed branch and Apply/confirmation rollback. |
| Same module `'v'`16×17 | Combo dropdown arrow fallback | Exclude. Native arrow/button-child profile, not literal text or command button. |
| Same module Advanced Properties141×23 | Standard command | Verify actual native command bounds/raw label, then migrate. Test future action disabled/capability reason separately from appearance. |
| Same module confirmation No75×23 | Standard default command | High-priority small fix: measured border stays inside HWND, designated No remains default; Enter/Escape/countdown rollback must retain behavior. |
| `control_panel/pattern_dialog.py` Edit Pattern | Standard command | Migrate with measured font/rectangle; check parent/child pending edits and Cancel. |
| Same module Edit Pattern OK/Cancel | Standard commands | Migrate together; test keyboard default transfer, pointer press out/back and persistence only on parent Apply. |
| `apps/dialogs.py:native_prompt` dynamic repaints | Standard commands over native/artwork/fallback branches | High priority: only repaint branch `not preserve or selected!=default`; use typed native labels/response IDs. Avoid doubling source-artwork default borders. Test focused nondefault choice, pressed mouse, disabled state and line-wrap/resized prompts. |
| `apps/mouse.py:MouseWindow.button` | Standard commands outside PropertySheet | High priority, but requires a local command-spec/default-resolution pass instead of only swapping the drawing call. Retain native frame's default OK, capability-disabled reasons, Browse/Use Default state, Apply/Cancel and pointer settings. |
| `control_panel/background.py` Background/Settings | TabStrip fallback | Exclude from command migration. |
| Same module ▼16×17 | Combo arrow fallback | Exclude; native arrow profile. |
| Same module Center75×21 | Selection ComboBox fallback | Exclude; closed-field focus and dropdown behavior belong to ComboBox. |
| Same module Browse/Pattern/OK/Cancel/Apply fallback loop | Standard commands | Migrate only actual command branch; frame-native states and default transfer must be compared independently. Preserve wallpaper/pattern pending state and file errors. |
| `apps/fonts.py:FontPreview.draw` Print | Disabled standard command with manual emboss repaint | Small bounded candidate: measured disabled renderer replaces duplicated manual text/face clear. Verify native Print control font/bounds and accessible unavailable reason. Do not enable printing merely by repainting. |

The machine inventory retains all19 exact line sites and source snapshots. Rows above combine repeated function/loop sites by semantic ownership; they are not19 accepted features.

## Suggested assignment order

1. Font Preview disabled Print and Display confirmation No: small independent commands with clear behavior boundaries.
2. Generic prompt's focused/default repaint branch: commonly reused, requires both native-artwork and resized/error forms.
3. Mouse command specification/default/focus integration, preserving its specialized sheet/controller.
4. Background/Display/Pattern ordinary commands and inactive legacy wrapper; only then retire remaining ordinary command uses of the old painter.
5. Tabs, combo arrows and closed combo fields get their own measured control migrations, not the stock command renderer.

For every migrated consumer, add a regression that failed before the change, a named native same-state crop including its full border and parent margin, and integrated mouse/keyboard/Cancel/error checks at800×600 and a larger size. Validate disabled commands have no enabled hit dispatch; default emphasis transfers to enabled focused commands; press-out removes the depressed visual; release-out does not invoke; mnemonic markers do not become text. Record owner-draw/image controls and unsupported font/DPI profiles explicitly. No all-buttons blanket success claim.

## Mouse stage completed

The Mouse-specific command-spec/default/focus stage is now implemented and validated; see `MOUSE_COMMAND_BUTTONS_2026-11-26.md`. Its64 native cases and per-consumer state checks do not imply completion of the other typed sites. No global Painter.button replacement was made.
