# Classic Windows games: inventory and port research

Repository information was checked on November 26; the JSON retains observed upstream push dates where available. License labels below describe observed source terms, not a completed per-file/asset audit.

| Game family | Candidate | Actual fit / remaining work |
| --- | --- | --- |
| Space Cadet | [k4zmu2a/SpaceCadetPinball](https://github.com/k4zmu2a/SpaceCadetPinball), MIT | Native Linux SDL2 port/decompilation. Requires original data files, which upstream does not include. Best first integration candidate; test Plus! 95 data versus the XP implementation before claiming equivalence. |
| Solitaire, FreeCell, Spider; optional solitaire variants | [PySolFC](https://github.com/shlomif/PySolFC), GPL-3.0; [Aisleriot](https://gitlab.gnome.org/GNOME/aisleriot), license inspection pending | Rules/variant references. Their modern UI is not a native Windows 95 frame. Check Microsoft deal numbering, scoring, stock rules and undo behavior before reuse. |
| Minesweeper | Existing [Win95LX implementation](../src/win95lx/apps/minesweeper.py); [ReactOS games](https://github.com/reactos/reactos/tree/master/base/applications/games) | Existing game still needs its own fidelity acceptance. ReactOS source is a potential reference; inspect each file’s terms. |
| Reversi | [GNOME Iagno](https://github.com/GNOME/iagno), GPL-3.0 COPYING observed | Linux gameplay analogue, not a Windows 3.0 UI clone. Difficulty, passes, end conditions and artwork require comparison. |
| Internet games | [ZoneInternetGamesServer](https://github.com/provigz/ZoneInternetGamesServer), AGPL-3.0 | Replacement server/client routing, not a native Linux client. Original clients plus compatibility or a new client remain necessary. Bot support varies by game. Microsoft’s original services are retired. |
| Chip’s Challenge | [Tile World source fork](https://github.com/retrofw/tileworld), GPL-2.0 observed | Reviewed source is a handheld fork; trace a desktop upstream before adopting. Original Microsoft levels and graphics are separate from engine licensing. |
| SkiFree | [Original author’s Win32 release](https://ski.ihoc.net/); [JSkiFree](https://github.com/dimme/jskifree) | Original author states Wine compatibility for 1.04, but no open-source license was established. JSkiFree claims a Java rewrite; no explicit license was detected, so it is not approved for reuse. |
| Hover! | [sp00nznet/hover](https://github.com/sp00nznet/hover), MIT observed | Native static-recompilation tooling, bring original files. Recent, small project; not validated here. The similarly named shurcooL/Hover is an unrelated 2000 game. |
| Labyrinth | [Neverball](https://github.com/Neverball/neverball), GPL-2.0-or-later with asset exceptions to review | Engine/physics analogue only. It is not the Plus! game and does not supply its levels or UI. |
| Hearts, SegaSoft Marbles, Golf 1998 Lite, HyperBowl, Russian Square, InkBall and most retail-pack games | No exact native open-source port accepted in this pass | Keep as explicit research/rewrite work. “Similar mechanics” is not pixel or gameplay equivalence. |

Original proprietary art/data must remain in the private asset library unless their terms allow distribution. A public engine’s license does not change the original assets’ terms. No leaked Microsoft NT or XP source is needed or accepted for this plan. Compatibility execution of a preserved original is also a different implementation route from a native rewrite.

## Suggested implementation order and acceptance

1. **Audit existing Minesweeper** and build the shared card/rules infrastructure. Test first-click behavior, adjacency, chord input, timer/focus, mine count, win/loss, high scores, menu states and resizing against the selected original version.
2. **Solitaire and FreeCell**, then **Hearts and Spider**. Keep deterministic decks/deals and replay fixtures. Test legal/illegal drops with realistic margins, multi-card movement, scoring, undo, redeal/stock rules, AI turns, cancellation and persisted options. Match each version’s actual menus, card spacing and frames.
3. **Space Cadet native port evaluation**, keeping source and private data separate. Test launch, plunger/flippers/nudge, tilt, ball loss/multiball, mission scoring, pause/focus, sounds, high scores and frame-rate independence. Capture the original and port at the same table size before adding a launchable shortcut.
4. **Reversi, Taipei, SkiFree, Pipe Dream, Rodent’s Revenge, JezzBall and Chip’s Challenge**, selected by verified source/data availability. Use fixed seeds and state replays; validate original rule variants before reskinning.
5. **Internet games** need an explicit service design: faithful client, configurable private replacement service, reconnect/cancel flow, matchmaking, skill levels, restricted chat and multiplayer/bot tests. Do not ship a button that waits indefinitely for the retired Microsoft service.
6. **Plus! 98 and XP 3-D games**, InkBall and the retail puzzle/card packs. Treat these as separate projects with physics/rule fixtures and asset provenance, not a quick artwork substitution.

For each game, capture default, open-menu, disabled, focused, active-play, paused, won/lost, settings and error states. Compare 1:1 guest pixels first, integer scaling next, and fractional viewer/pointer alignment separately. Test sound-disabled behavior and independent volume settings. Record idle CPU and consistent simulation speed; preserve saves/high scores in per-user data. Use the existing native controls, dialogs, system-menu profiles and Start-menu placement skill. A working launch does not establish a working or faithful game.

## Remaining evidence work

- Independently inventory Windows 95 OSR1/OSR2.1, Windows 98 FE, Windows Me and XP setup manifests; local Win95 RTM/OSR2/OSR2.5, Win98 SE and Plus! 95/98 sources have been inspected.
- Verify XP Home/Professional service-pack differences, Tablet first-release/2005, Media Center 2002/2004/2005, Starter, x64 and IA-64. Do not infer edition exceptions from anecdotes.
- Obtain original Plus! Game Pack manifests or manual/box scans to confirm the 12 card variants and Pandora trial payload. Puzzle Collection’s ten games already have primary Microsoft documentation.
- Verify original Entertainment Pack 2 manifests for JigSawed, RattlerRace and Stones; other volume lists are substantially supported by Microsoft KB articles.
- Inspect full playable trial payloads and catalog versions before expanding the selected media-trial list. No claim is made for every historical OEM sampler.
- Find and audit exact native ports for the remaining games; validate per-file licenses and separate asset rights. Candidate status must not be converted into “implemented” without gameplay and visual evidence.

Inventory validation checked unique IDs, product-to-game links, evidence references and port-candidate links. These are data-consistency checks, **not game unit/regression tests**. There are no new before/after game screenshots because no game was implemented in this task.

## Shared-control lessons for future games — 27 November 2026

These are engineering requirements transferred from the accepted namespace-drop
iteration, not evidence that any additional game was built or accepted.

- A card/tile drag needs real pointer press, sub-threshold motion, threshold
  crossing, redraw while held, near-edge drops, release, cancellation and lost
  capture tests. Preserve the grab offset instead of snapping the object center
  to the pointer. Derive each game's legal target/tolerance from its original;
  do not reuse Explorer's measured margins as an assumed card-game rule.
- Inspect the actual framebuffer while the drag is held and while a resulting
  modal is open. Explorer left a stale ghost because repaint was queued after a
  blocking dialog. Include successful/illegal drops, dialog dismissal and
  focus/pause transitions; calling a renderer with cleared model state misses
  that timing defect.
- Verify logical mouse-button mapping before comparing references. A saved
  SM_SWAPBUTTON setting made physical-left act as right. Test multiple held
  buttons for Minesweeper/chording separately from ordinary drag behavior.
- Compare complete states: image plus label/selection/focus and adjacent bevels,
  menus with accelerators, and full scrollbar track/buttons/thumb. Independently
  measure window/control bounds before accepting a screenshot crop. A resource
  test that repeats an implementation's chosen ID can repeat its mistake.
- Keep Classic, IE4 and configured Plus references separate. A Plus asset override
  is not proof of every default installation. Name the game's exact binary/data
  edition when comparing cards, tables, sounds, rules and settings.
- Use bounded caches keyed by immutable artwork/state, keep decoding/discovery
  off the paint path and measure input-to-paint as well as component timings.
  Never infer whole-game speed from a fast isolated drawing helper.
- Installation tests must keep original game data private, preserve existing
  saves/high scores, and validate cancellation/failed writes in disposable HOME
  and install roots. A launchable shortcut is not gameplay acceptance.

Evidence and reusable checks: `reports/NAMESPACE_SHORTCUT_FIDELITY_2026-11-27.md`,
`dev/check_namespace_modal_ghost.py`, `dev/check_shortcut_visuals.py`, and
`docs/CONTROL_TOOLBOX.md`. Games remain secondary research until their separate
implementation assignment; these notes add no launcher/package by themselves.

Applet follow-up also reinforces two game acceptance requirements: use long,
realistic option lists so the initial selected row and Back/reopen focus are
visible; and verify actual playfield/sprite/audio effects after changing options,
not just the persisted settings. Preserve pending edits across conflicting
settings windows. Palette/decode/adapter behavior must be recorded separately:
a lossless source export is not automatically identical to the original visible
framebuffer. Keep source assets, native conversion derivatives and independent
reference screenshots separate, with hashes and named color-depth profiles.

For paletted games, also test foreground/background palette changes with other
windows open. The current compositor's ≤256-unique-color fast path preserves a
small scene, but extra colored windows can trigger a different quantizer. A
single card/table screenshot cannot establish global palette realization.
Capture the final framebuffer after all GTK/SDL filters, not only an offscreen
render function. Preserve logical image palettes separately from named adapter
output conversions; future Pinball/card artwork must not inherit a reference
VM's DAC profile without the matching display-depth evidence.

Automated QMP key acknowledgement is not a game-input consumption barrier. Wait
for the expected game/menu state before issuing the next action; screenshots
caught during painting or queued typing must not become reference evidence.
For timing-sensitive gameplay use a recorded simulation/input timeline and
state readback as well as settled screenshots, rather than stretching sleeps
until an intermittent run happens to pass.
