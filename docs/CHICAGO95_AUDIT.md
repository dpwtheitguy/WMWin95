# Chicago95 preliminary audit

Reviewed upstream README, CREDITS, INSTALL.md and GTK3 entry stylesheet on 2026-11-04. This is source triage, not a measured comparison. A pinned source checkout and original-shell screenshots are required before reuse approval. No upstream code has been copied or installed.

Sources: [repository](https://github.com/grassmunk/Chicago95), [installation](https://github.com/grassmunk/Chicago95/blob/master/INSTALL.md), [GTK3 stylesheet](https://github.com/grassmunk/Chicago95/blob/master/Theme/Chicago95/gtk-3.0/gtk.css), [credits](https://github.com/grassmunk/Chicago95/blob/master/CREDITS).

| Component | Initial disposition | Required evidence |
| --- | --- | --- |
| GTK theme | Candidate with modifications | Measure padding, bevel colors, widgets, disabled states; source uses computed shades |
| XFWM decoration | Candidate with modifications | Compare frame widths, title height, controls and hit regions |
| Panel and Start | Configuration first; replacement possible | Geometry, menu organization, focus, activation, task grouping |
| Icons/cursors | Compare; select original private assets | Per-size bitmap/hotspot comparison, animation timing |
| Fonts | Original bitmap fonts preferred | Compare glyph metrics and rasterization; no substitution assumed equivalent |
| Desktop | Configuration first | Icon grid, selection rectangle, label wrapping, dragging |
| Sounds | Replace mapping after reference capture | Identify exact original files and event triggers |
| File manager | Audit Thunar; hide until accepted | Drive letters, Properties, menus, navigation, Linux terminology |
| App menus/dialogs | App-specific validation; shared controls if needed | No generic theme can establish matching content/behavior |

Nothing is approved for unchanged reuse. Visual defects and replacements are hypotheses until screenshots and interaction tests demonstrate them. Avoid broad masks or compositor effects that conceal differences.

Upstream declares GPL-3.0+/MIT and credits Grassmunk, AdrianoML and EMH-Mark-I. Before vendoring, pin a commit and inspect each component's license and inherited notices; preserve attribution, applicable license texts and modification notices, and satisfy applicable source obligations for distributed GPL derivatives. A repository-level declaration does not establish rights to every font, icon or sound. Microsoft originals stay private and are never bundled in distributable packages.

## Pinned local audit and runtime observations

Checkout: `private/upstream/Chicago95`, commit `5da19b8b1e2a886ebf6628403023d5fac3acc3ee` (2026-10-01). No source from this checkout was copied into Win95LX's runtime implementation.

The local XFWM `themerc` identifies GPL-3.0+, sets `frame_border_top=4`, `button_offset=2`, `button_spacing=0`, left alignment and a one-pixel title vertical offset. Those are candidate values to test, not accepted original measurements. The GTK entry stylesheet uses an 11px Whisker button label override; this does not establish matching original glyph metrics.

Actual runtime finding: while the first custom surface ran inside the developer's ordinary XFCE session, Ctrl+Esc opened XFCE's native menu over the surface. The dedicated Win95LX login session resolves that conflict by excluding the panel and shortcut daemon. No global shortcut settings or XFCE binaries were patched.

Reuse remains unapproved until original reference screenshots exist. The original FNT renderer and privately extracted icons provide a testable comparison surface; they do not by themselves justify replacing every native toolkit control. Complete per-component license/notice review before any future vendoring or public distribution.
