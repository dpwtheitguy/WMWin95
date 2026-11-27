# Network service authorization findings — 2026-11-26

No Network policy was installed. This records the remaining authorization gate before registering the prototype.

The actual guest NetworkManager is 1.46.0. Nonadmin queries return `auth` for modify-system, modify-own and network-control. The backend deliberately requires `yes`, never uses `--ask`, and real normal-account attempts to edit an owned test profile were refused without changing it. Maintenance-root owned-dummy transactions passed and cleaned up; that is a different acceptance scope.

Primary documentation: [NetworkManager authorization configuration](https://networkmanager.dev/docs/api/latest/NetworkManager.conf.html), [connection ownership/permissions](https://networkmanager.dev/docs/api/latest/settings-connection.html). Root requests bypass polkit; disabling authorization globally would grant all users and is not the proposal.

Source review at [NetworkManager 1.46 auth manager](https://github.com/NetworkManager/NetworkManager/blob/1.46.0/src/core/nm-auth-manager.c) shows polkit receives an empty details dictionary for these checks. Therefore a proposed rule such as `action.lookup('connection-uuid') == ...` has no demonstrated per-profile input here. Do not claim it scopes access to one QA profile. [Settings connection authorization](https://github.com/NetworkManager/NetworkManager/blob/1.46.0/src/core/settings/nm-settings-connection.c) chooses modify-own when old and new ACLs each contain one permitted user, otherwise modify-system, subject to ACL checks. Merely adding `connection.permissions=user:win95` does not itself grant the account the action. Downloaded source URLs/hashes are in `private/research/network-policy-20261126/sources.json`.

For a narrowly scoped next QA integration, prefer a small guest service over broad NetworkManager polkit grants:

- Authenticate the D-Bus caller's uid and active local session through system credentials; require the immutable guest identity marker. Do not trust uid/account supplied in a request.
- Maintain a root-owned allowlist of connection UUID/interface/type, initially only a disposable dummy. Refuse primary interfaces, profile additions/removals, ownership/credentials/routes/default-route/global-DNS/hostname changes in this QA capability.
- Accept a typed IPv4 update document only. Validate address/mask/DNS limits with the existing model; bound command duration/output; forbid shell strings and prompts. Check baseline generation/values before writing and verify authoritative readback after activation.
- Roll back only attempted profiles; report partial recovery honestly. Keep a monotonic request ID, serialize operations per connection and rate-limit requests. Return native-domain error codes to existing Windows-style dialogs.
- Preserve profile's never-default/private route-table/IPv6/DNS route-domain restrictions during QA. Make policy/service installation/removal explicit installer-manifest actions later, after root review. No global executable mode changes or sudo invocation from UI.

Before production registration, independently test nonadmin success through that reviewed boundary, another uid/remote session denial, unrelated profile/interface denial, stale state, malformed updates, cancellation/timeouts, activation/readback failures and cleanup. The desired eventual Network applet must configure real user-selected adapters, so a dummy-only helper is a QA capability, not a claim that the complete applet works. Expanding its allowed operations needs explicit service contract and normal-account acceptance evidence. Hostname/sharing/WINS/multiple gateways/profile installation remain separate incomplete features.
