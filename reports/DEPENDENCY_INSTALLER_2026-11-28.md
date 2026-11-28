# Manifest-driven dependency installer — 28 November 2026

`tools/install_dependencies.py` consumes config/installer-dependencies.json.
The development-guest guard, maintenance-root identity and matching Ubuntu24.04
amd64 target are mandatory. Default mode simulates only. Explicit --apply adds
declared foreign architectures, refreshes APT indexes, simulates with no package
removals and installs the selected profile. No applet invokes this installer.

Actual guarded guest simulation of the windows95 profile passed:0 upgrades,
0 new installations,0 removals; all declared packages were already installed.
No host packages or guest package state changed during this validation. Private
log: private/dependency-installer-20261128/apt-simulation.log.

Ten dependency audit/installer tests pass, including native/foreign architecture
selection, default simulation, simulation-before-install, guest guard refusal,
wrong OS and non-root refusal. The --apply command ordering was tested through
mocked process calls; this checkpoint did not reinstall the guest's packages or
claim a clean-image installer run. Final hardware provisioner integration remains
outstanding.
