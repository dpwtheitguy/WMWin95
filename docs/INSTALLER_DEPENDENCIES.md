# Installer dependencies

The authoritative inventory is `config/installer-dependencies.json`. Update it
whenever a runtime library, external executable, architecture, private asset or
optional service requirement is discovered. `dev/guest-packages.txt` is a legacy
development bootstrap list, not the complete runtime contract.

The current target is Ubuntu/Xubuntu24.04 amd64 with optional i386 packages.
Profiles separate the base desktop, original95/Plus savers, development tools,
printers, NetworkManager and existing-XFCE-saver coordination. The saver profile
includes Wine32, 32-bit GL/Mesa DRI and OSMesa: 64-bit libraries alone do not
satisfy the original32-bit executables. Package availability is not evidence
that an individual saver renders or that all settings work.

List the deduplicated packages for an installer profile:

```
python3 tools/check_dependencies.py --profile windows95
```

Audit installed versions **inside the target environment**:

```
python3 tools/check_dependencies.py --profile windows95 --check-installed --output dependency-audit.json
```

The audit is read-only and exits nonzero for missing packages. Archive its
manifest hash, package versions/architectures, apt resolver transaction and
functional acceptance evidence with a release. Let apt resolve transitive
packages rather than copying machine-specific dependency versions into the
portable requirement list. Enable i386 before resolving its packages.

`tools/install_dependencies.py` now consumes this manifest in the guarded
development guest. It checks the guest marker, root maintenance identity, OS and
architecture, then runs a no-removal APT simulation. `--apply` enables declared
foreign architectures, refreshes package indexes, simulates and installs the
selected profile. No package commands run on an applet click. The existing
bootstrap scripts remain useful references; final hardware installer integration
and a clean-image end-to-end install are still outstanding. Per-user Wine
initialization runs asynchronously and is reused.

Original SCR/DLL/font/art payloads are private inputs, separately hashed in the
asset catalogs. A Linux package manifest does not provide those files. Import
from authorized local media, preserve exact installed filenames and retain
source provenance. Future98/ME/XP compatibility will add profiles and measured
requirements instead of assuming the95 recipe covers every engine.

Permission/service policy is separate from dependencies: package installation
must not grant broad sudo or change session locking or active network settings.
Scoped helper installation and its normal-account tests remain independently
reviewable requirements.
