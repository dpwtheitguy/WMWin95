# Planned desktop profiles

Keep three choices independent:

1. Explorer generation: classic pre-IE4 shell or IE4 Desktop Update layout/features.
2. Active Desktop: HTML desktop content on/off, where the selected shell supports it.
3. Optional Plus! customization: cursor schemes, themes, sounds and other implemented components.

IE4 Explorer can show folder Web View while the desktop itself uses the classic desktop setting. Therefore `active_desktop=false` must not implicitly select a pre-IE4 Explorer implementation.

The current delivered customization is the Mouse pointer catalog. Basic pointers are the default; 3D, large, extra-large, Animated Hourglasses and the available original Plus! pointers remain optional. Selecting a pointer set must not silently change wallpaper, colors, fonts, sounds, or Explorer generation. Future full-theme application should expose those choices explicitly.

These are architectural requirements for later profile work, not a claim that all desktop profiles are already implemented. Each profile needs its own original-VM baseline, state captures, behavior checks, and migration/persistence tests. The reference set retains separate pre-IE4, IE4 and Plus! machines for that purpose.
