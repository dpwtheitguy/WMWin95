> Scope update: this is a research catalog, not an installation target. Focus on familiar games that fit a mid-to-late-1990s Windows PC. Entertainment Packs are optional and off by default. Continue documenting licensed open-source reimplementations and analogs; game implementation and packaging are paused at the user’s direction. A private Pinball prototype predates that clarification and is not integrated into the OS.

# Classic Windows games inventory

Checked November 26, 2026. This is a research inventory and implementation queue. No new games have been built or installed; Control Panel development remains the primary task. The machine-readable catalog is [classic-games-inventory.json](../config/classic-games-inventory.json).

The catalog has **75 game/variant/trial records, 31 product profiles and 61 evidence sources**. That count is deliberately broader than “75 different games bundled with Windows”: it includes separately sold Entertainment Packs, distinct Bicycle implementations, and selected CD sampler trials. The principal Windows/Plus roster has **19 entries**, including Hover! as a CD extra and InkBall as a Tablet-specific game. No claim is made that every OEM disc, language, prerelease or XP edition has been exhaustively checked.

## Windows and Plus! roster

| Product | Games | Evidence and limits |
| --- | --- | --- |
| Windows 3.0 | Solitaire, Reversi | Microsoft’s original [User’s Guide](https://bitsavers.trailing-edge.com/pdf/microsoft/windows_3.0/Windows_3.0_Users_Guide_198909.pdf). |
| Windows 3.1 and non-Workgroups 3.11 | Solitaire, Minesweeper | Microsoft Press [Windows 3.1 guide](https://vtda.org/books/Computing/OperatingSystems/ConciseGuideWindows3.1_KrisJamsa.pdf). Do not assume every 3.11 installation includes Hearts. |
| Windows for Workgroups 3.1 / 3.11 | Solitaire, Minesweeper, The Microsoft Hearts Network | Microsoft [KB Q90561](https://jeffpar.github.io/kbarchive/kb/090/Q90561/) identifies MSHEARTS as a NetDDE game; original [WFW 3.11 disk listings](https://www.pcjs.org/software/pcx86/sys/windows/3.11/) provide file evidence. |
| Windows 95 RTM, OSR2 and OSR2.5 | Solitaire, Minesweeper, FreeCell, Hearts | Independently inspected local original `applets.inf`, `[wingames.files]`, in each source set. Optional component; setup choices affect installed shortcuts. |
| Windows 95 OSR1 / OSR2.1 | Expected same four | Family expectation, not independent media acceptance. OSR1/OSR2.1 discs have not been verified. |
| Windows 95 CD extras | Hover! | Original `FUNSTUFF/HOVER/HOVRREAD.TXT` is present in local media. Not a standard Add/Remove Games entry. |
| Windows 98 FE / SE | Solitaire, Minesweeper, FreeCell, Hearts | SE’s original `appletpp.inf` verified locally. FE remains an independent media check. |
| Windows Me | Classic Solitaire, Classic Hearts, FreeCell, Minesweeper, Pinball, Spider Solitaire; Internet Backgammon, Internet Checkers, Internet Hearts, Internet Reversi, Internet Spades | Complete eleven-game list in Microsoft [KB306862](https://ftp.zx.net.nz/pub/mirror/ftp.microsoft.com/MISC/KB/en-us/306/862.HTM). |
| Windows XP Home / Professional 32-bit family | Solitaire, Hearts, FreeCell, Minesweeper, Pinball, Spider Solitaire; the five Internet games above | Microsoft [KB307768](https://ftp.zx.net.nz/pub/mirror/ftp.microsoft.com/MISC/KB/en-us/307/768.HTM), [support corroboration](https://learn.microsoft.com/en-us/answers/questions/2491864/where-can-i-get-find-the-old-hearts-game-not-inter), Me’s original list and Microsoft’s [Internet games history](https://blogs.windows.com/windowsexperience/2009/02/19/the-new-internet-games-in-windows-7/). Original XP manifests are still needed for exact SKU/service-pack acceptance. |
| XP Tablet PC family | Inherited XP games plus InkBall | An original [Motion Tablet PC manual](https://ptacts.uspto.gov/ptacts/public-informations/petitions/1547245/download-documents?artifactId=GIrU8vmRkWeLXZeLHzmP2QZXBFuA0xMGAA1cSdQr3xGjR9iysFs_UQU) documents InkBall. Earlier OEM manuals also list it: the frequently repeated claim that it first arrived only with Tablet 2005 is not accepted without media checks. |
| XP Media Center editions | Expected XP family set | No extra built-in game asserted here. Partner/OEM downloads and the online gallery are not stock OS components. 2002/2004/2005 media checks remain open. |
| Plus! for Windows 95 | 3D Pinball for Windows — Space Cadet | Original local `PLUS.INF` Pinball sections. |
| Plus! 98 | Microsoft Golf 1998 Lite, Lose Your Marbles, Spider Solitaire | Original `PLS98GAM.INF` plus Microsoft’s [launch announcement](https://news.microsoft.com/source/1998/06/25/microsoft-announces-immediate-availability-of-microsoft-plus-98/). The registry describes the Marbles build as Lite; do not substitute the full retail release silently. |
| Plus! for Windows XP | HyperBowl Plus! Edition, The Labyrinth Plus! Edition, Russian Square Plus! Edition | Microsoft’s [product announcement](https://news.microsoft.com/source/2001/09/26/microsoft-announces-microsoft-plus-for-windows-xp/) names all three and specifies 40 Labyrinth levels. |
| Plus! Digital Media Edition | No additional game identified | Microsoft’s [feature announcement](https://news.microsoft.com/source/2002/12/16/microsoft-announces-plus-digital-media-edition-the-ultimate-photo-music-and-movie-enhancement-pack-for-windows-xp/) describes photo, music and video tools. Dancer and Party Mode are not games. |
| Plus! SuperPack | The same three Plus! XP games | Microsoft [confirms it combines Plus! XP and Digital Media Edition](https://news.microsoft.com/source/2004/10/19/microsoft-announces-immediate-availability-of-plus-superpack-for-windows-xp/). Not three extra game titles. |
| Plus! for Kids (1997) | No conventional game title established | Microsoft [describes Talk It!, Play It! and Paint It!](https://news.microsoft.com/source/1997/02/18/microsoft-plus-for-kids-is-a-quick-and-easy-way-to-make-using-windows-95-even-more-secure-and-fun-for-kids/), with themes, clip art and parental controls. Play It! is a music keyboard/recorder. No separate “Plus! 98 for Kids” release was confirmed. |

No dedicated product named “Plus! for Windows Me” or “Plus! for Windows 3.x” was confirmed. The real Me-era **Plus! Game Pack** is covered below rather than inventing a product profile.

### Names and variants that must stay separate

- **Space Cadet is not stock Windows 98 Pinball evidence.** Our SE CD’s `tools/mtsutil/pinball.inf` explicitly says it installs Pinball **from the Plus! for Windows 95 CD**. A helper INF is not a bundled game payload. The SE sampler’s **Microsoft Pinball Arcade** trial is a different game.
- **Full Tilt! Pinball** is a separate retail game. Its Dragon’s Keep and Skulduggery tables were not included in Plus! 95 Space Cadet.
- **Golf** in Entertainment Pack 1 is a solitaire card game. **Fuji Golf** in Pack 3 is a sports game. **Golf 1998 Lite** is a different Plus! 98 application.
- **SegaSoft Lose Your Marbles** is not Mark Pilgrim’s unrelated 1994 Macintosh game of the same name. Search results for a GPL “Lose Your Marbles” can point to the wrong game.
- **Classic Hearts** and **Internet Hearts** are separate programs, with different play and network behavior. The Windows for Workgroups NetDDE edition is another behavior profile.
- A 64-bit Pinball anecdote is insufficient proof that every XP x64/IA-64 release omitted it. Microsoft’s author later [clarified the early port history](https://devblogs.microsoft.com/oldnewthing/20220106-00/?p=106122). Verify actual target media.

## Plus! Game Pack: Cards & Puzzles (2000)

This is a separate Plus-branded retail product for the Windows 95/98/2000 era. Microsoft [KB Q282167](https://jeffpar.github.io/kbarchive/kb/282/Q282167/) establishes the product and supported systems; [KB Q272333](https://jeffpar.github.io/kbarchive/kb/272/Q272333/) confirms its Puzzle Collection component. It is relevant to the user’s “all Plus packs” request even though it is not branded Plus! for Me.

| Component | Titles | Confidence |
| --- | --- | --- |
| Bicycle Card Collection — 12 | Crazy Eights, Old Maid, Go Fish, Hearts, Spades, Pinochle, Oh Hell!, Gin Rummy, Skat, Euchre, Schafkopf, Cribbage | Product-description roster; original local manifest still required. These are separate implementations from similarly named built-in Windows games. |
| The Puzzle Collection — 10 | Fringer, Mixed Genetics, Rat Poker, Finty Flush, Color Collision, Jewel Chase, Lineup, Spring Weekend, Charmer, Muddled Casino | Microsoft [KB Q168868](https://jeffpar.github.io/kbarchive/kb/168/Q168868/) names and describes all ten; the original retail pack is also cataloged separately. |
| Pandora’s Box trial | One trial application, described as eight puzzles | [Product-description transcription](https://www.ebay.com/p/170314078); original trial manifest needed. The full retail game is not established as included. |

The card and trial roster is explicitly provisional: a seller transcription is weaker than an original Microsoft installer or manual. Do not promote it to accepted evidence merely because multiple sellers repeat the same wording.

## Optional Windows 3.x Entertainment Packs

These separately sold packs explain many games people remember “coming with Windows,” especially on OEM PCs. They are not stock Windows 3.x components. This broader catalog makes room for them without changing a faithful Windows 95 default Start menu.

| Product | Complete seven-game roster | Evidence |
| --- | --- | --- |
| Entertainment Pack 1 | Cruel Solitaire; Golf; Minesweeper; Pegged; Taipei; Tetris; TicTactics | Microsoft KB descriptions: [Cruel](https://jeffpar.github.io/kbarchive/kb/066/Q66859/), [Golf](https://jeffpar.github.io/kbarchive/kb/066/Q66874/), [Pegged](https://jeffpar.github.io/kbarchive/kb/066/Q66351/), [Minesweeper](https://jeffpar.github.io/kbarchive/kb/066/Q66352/), [Taipei](https://jeffpar.github.io/kbarchive/kb/066/Q66354/), [Tetris](https://jeffpar.github.io/kbarchive/kb/066/Q66356/), [TicTactics](https://jeffpar.github.io/kbarchive/kb/066/Q66353/). |
| Entertainment Pack 2 | FreeCell; JigSawed; Pipe Dream; RattlerRace; Rodent’s Revenge; Stones; Tut’s Tomb | [Microsoft Best-of provenance](https://jeffpar.github.io/kbarchive/kb/130/Q130026/) establishes four selections; [Pipe Dream KB](https://jeffpar.github.io/kbarchive/kb/096/Q96714/) supplies original behavior. JigSawed/RattlerRace/Stones need original manifest verification. |
| Entertainment Pack 3 | Fuji Golf; Klotski; Life Genesis; SkiFree; TetraVex; TriPeaks; WordZap | Microsoft KB descriptions: [Fuji Golf](https://jeffpar.github.io/kbarchive/kb/096/Q96137/), [Klotski](https://jeffpar.github.io/kbarchive/kb/098/Q98930/), [Life Genesis](https://jeffpar.github.io/kbarchive/kb/098/Q98932/), [TetraVex](https://jeffpar.github.io/kbarchive/kb/098/Q98933/), [TriPeaks](https://jeffpar.github.io/kbarchive/kb/098/Q98937/), [WordZap](https://jeffpar.github.io/kbarchive/kb/098/Q98935/); [SkiFree’s original author](https://ski.ihoc.net/). |
| Entertainment Pack 4 | Chess; Chip’s Challenge; Dr. Black Jack; Go Figure!; JezzBall; Maxwell’s Maniac; Tic Tac Drop | Microsoft KB descriptions: [Chess](https://jeffpar.github.io/kbarchive/kb/099/Q99159/), [Chip](https://jeffpar.github.io/kbarchive/kb/098/Q98909/), [Black Jack](https://jeffpar.github.io/kbarchive/kb/098/Q98936/), [Go Figure!](https://jeffpar.github.io/kbarchive/kb/098/Q98931/), [JezzBall](https://jeffpar.github.io/kbarchive/kb/098/Q98938/), [Maxwell](https://jeffpar.github.io/kbarchive/kb/099/Q99158/), [Tic Tac Drop](https://jeffpar.github.io/kbarchive/kb/098/Q98934/). |

**The Best of Microsoft Entertainment Pack (Windows)** contains 13: Golf, Taipei, Tetris, FreeCell, Pipe Dream, Rodent’s Revenge, Tut’s Tomb, SkiFree, TetraVex, TriPeaks, Chip’s Challenge, Dr. Black Jack and JezzBall. This is the exact [Microsoft KB Q130026 list](https://jeffpar.github.io/kbarchive/kb/130/Q130026/); its seven-game Game Boy Color counterpart is a different product. IdleWild and its modules are screensavers and are not included in the game count.

FreeCell also appeared as a Win32s demonstration on Windows 3.x; that does not make it a stock Windows 3.1 game. MS-DOS/QBasic Nibbles and Gorillas, Microsoft Arcade, OEM retail games, Windows CE/Game Boy releases and post-XP Windows games are separate possible expansions, not silently added to this roster.

## CD sampler boundary

The inspected Windows 95 OSR2/2.5 media contains playable **Hellbender** and **Pac-Man / Return of Arcade** trials. The original Pac-Man readme specifies the first two levels, not the full Return of Arcade compilation. Entries for **Deadly Tide** and **Monster Truck Madness** in that sampler point to AVI trailers, so they are not counted as playable games.

The inspected Windows 98 SE media contains `mspinbal.exe`, `msaoex.exe`, `msmtm2.exe`, `msmcI smm.exe`, and `msgolf99.exe`: Pinball Arcade, Age of Empires: The Rise of Rome, Monster Truck Madness 2, Motocross Madness, and Golf 1999 trials. Some identities still require internal version/help verification. The source files and hashes are in the JSON catalog. This does **not** establish every sampler ever issued on every Windows SKU, and none is a full retail-game entitlement.

## Port and rewrite candidates

No candidate was downloaded, built, run or pixel accepted in this research task. Repository information was checked on November 26; the JSON retains observed upstream push dates where available. License labels below describe observed source terms, not a completed per-file/asset audit.

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
