# Type-111 firewall persistence — installer and contributor-test contract

**Status: required design and acceptance gate; target-side automatic patch/restore is NOT implemented by the current public developer installer.** Applies to the MU1440 reference and to proposed SEAT/CUPRA MU1409 adaptations after their exact firmware-specific preflight. Read alongside [developer installation](../INSTALLATION.md), [vehicle test protocol](../testing/VEHICLE_TEST_PROTOCOL.md) and [QNX shell compatibility](../testing/MU1440_QNX_SHELL_COMPATIBILITY.md).

## Why this is an installer responsibility

The CarPlay auxiliary stream is advertised on a **target-confirmed** TCP port (default `ALTSCREEN111_PORT=6031`). The iPhone reaches a listener on the head unit's CarPlay-facing interface `carplay0`. A correct SETUP response, open socket, edited file or successful temporary `pfctl` reload alone does **not** establish persistent reachability.

A head unit may load a different PF source as its network state changes. Known MHI2 profile candidates in other implementations include `pf.conf`, `pf.ecm0.conf`, `pf.mlan0.conf`, and `pf.ppp0.conf` (commonly under the actual target's `/etc`); an LTE/ECM activation can replace the initially loaded rules. **Do not assume all four exist, use a fixed `/mnt/system` mapping, or are used on every train. Discover and record the exact startup/reload selection and mounted source/target mapping on the particular unit.** The MU1440 reference's original startup has a `pfctl -ef /etc/pf.conf` step, but later reloads/other target trains are separate evidence.

The intended narrow effective permit for the default port may look like:

```pf
pass in quick on carplay0 proto tcp from any to any port 6031 allow-opts
```

A compatible existing `carplay0` allowlist covering the target TCP port is equally acceptable. Verify actual order relative to preceding `block quick` or other effective PF policy. **Do not disable PF, add a generic `pass all`, expose external WLAN/cellular/SSH/debug interfaces, or open the local loopback H.264 tee (`127.0.0.1:19820`) as a CarPlay ingress port.** Retain all non-project PF policy and any existing third-party modifications.

## Required implementation interface

The future installer and each target-specific test package must provide explicit, separately gated firewall functionality:

| Action | Minimum semantics |
| --- | --- |
| `firewall --check` | **Read-only** inventory: running PF state/rules (e.g. verified `pfctl -sr`), actual active profile and its loader if observable, all existing/referenced profile candidates, file hashes, matching rule/order, configured + advertised Type-111 port, actual listening socket, and existing changes/backup ownership. No remount, active reload, write or service restart. Distinguish missing tools/permissions from missing permit. |
| `firewall --plan` | Construct an **offline proposal** for every profile that can become active, preserving each original's bytes/line endings and unrelated rules. Explicitly list every would-change file, original/proposed hashes, syntax-validation capability, dependency and recovery route. Fail closed if the relevant profile set is unresolved, different mounted paths/loader are ambiguous, or another project's changes cannot be preserved. |
| `firewall --apply` | Separate explicit owner approval, exact target/firmware and hash-qualified preimages, recoverable backup of **all** affected profile variants, temporary same-filesystem staging, syntax validation for **every** candidate, then a guarded all-or-none profile-file transaction. No non-transactional first-file-success result. Do not force a live PF reload while SSH/CarPlay relies on the connection; use a reviewed controlled-reload/reboot plan specific to the unit. |
| `firewall --verify` | After normal boot **and** the relevant network profile transitions, read the **effective** loaded PF policy, loaded profile/loader evidence when available, correct listener and actual accepted phone connection/advancing Type-111 counters. If a profile switch removes the permit, result is FAIL even when `pf.conf` still contains the desired text. |
| `firewall --restore` | Separate hash-qualified, project-owned rollback; restore only the exact preimages when current contents match our known installed state, otherwise stop with a conflict and preserve third-party changes. Verify restored profile contents, PF syntax and normal stock networking after the approved reboot/reload. Uninstall must not delete an existing/foreign permit as though we owned it. |

The command names are **proposed public API**, not claims that these commands exist in the current deployment scripts or contributor bundle. A target test package may initially implement only host-only `--check`/`--plan` on explicit copied snapshots; in that case `--apply`, `--verify` and `--restore` must report `NOT_IMPLEMENTED`, never a false PASS.

### Transaction/syntax constraints

- A patch must be idempotent. Detect an already compatible `carplay0` TCP permit (including a port range), otherwise make only the smallest scoped delta in its actual existing rule/allowlist. Never append duplicate conflicting permits blindly or assume where an effective `block quick` appears.
- Verify the locally installed target `pfctl` command path and supported options. The QNX 6.5 manual documents `-n` with `-f` for parsing without loading; only use `pfctl -nf <candidate>` after verifying the actual target binary's capabilities, syntax and command availability. Never silently replace this with a live `pfctl -f` in preflight.
- Check *every* candidate first, preserve permission/ownership and exact original bytes for recovery, and handle read-only/missing variant profiles deterministically. A missing/unrelated profile is not automatically safe to fabricate. If all-or-none rollback cannot be guaranteed on that filesystem, block the automatic install.
- Reconcile the existing omonob/M.I.B./other AltScreen installation and PF modifications: detect owners/preimages, do not stack blind overwrites. The original operating-system PF loader must remain in charge; a project runtime/startup hook must not race it by loading an incompatible transient ruleset.
- A source-publishable patcher needs host unit tests for single-port and range allowlists, different whitespace/line endings, all discovered profiles, duplicate/idempotence, block-rule ordering, syntax error, mid-transaction failure, foreign edit/rollback conflict, and fake postboot profile replacement. Test **no write/no reload** on `--check`.
- Apply the mandatory [target-shell compatibility gate](../testing/MU1440_QNX_SHELL_COMPATIBILITY.md) to every proposed target-side `.sh`/`.ksh`, then qualify every used binary, mount and flag against the fitted SEAT/MU1409 unit independently. Host mocks alone do not establish vehicle compatibility.

### Honest result states and install blocking

Proposed machine-readable status labels:

```text
PF_PROFILE_UNRESOLVED
PF_ALREADY_ALLOWED
PF_PLAN_READY
PF_SYNTAX_FAILED
PF_APPLY_DEFERRED
PF_PERSISTED_UNVERIFIED
PF_EFFECTIVE_CONFIRMED
PF_ROLLBACK_CONFLICT
PF_NOT_IMPLEMENTED
```

**Preflight is blocking:** do not label video-install success or instruct replacement of a working third-party port while the persistent and postboot effective ingress requirement is unresolved. A temporary, explicitly marked experiment may proceed only under separate owner-approved recovery controls. Port 6031 is the project reference default; read the actual configured/advertised port instead of assuming all future targets use it.

## Contribution/test-package handoff

For a SEAT/CUPRA P4708_1/MU1409 contributor:

1. First take a **read-only snapshot** of the PF rules and *all actual* startup/reload profile candidates, preserving hashes and any observed loader/active-profile change; redact private unit data before sharing.
2. Perform host-only analysis/patch preview and report what still needs exact-target validation. The current first-stage bundle is **not** an approved in-car auto-patcher.
3. Before first installed video tests, independently review an exact-target, reversible persistent profile transaction and its no-disconnect operational sequence. Recheck after boot and after LTE/WLAN/PPP changes relevant to this fitted firmware.
4. Separate transport state: `listener bound` ≠ `PF permits incoming iPhone TCP` ≠ `socket accepts phone` ≠ `Type-111 source frames advance` ≠ `DIRECT cockpit output`. Test and report each independently.
5. After uninstall/rollback, verify PF preimages and the original stock networking; do not restore a stale shared PF file over subsequent legitimate edits.

## Public references

- [QNX Neutrino 6.5 PF utility manual](https://qnx.com/developers/docs/6.5.0SP1.update/com.qnx.doc.neutrino_utilities/p/pfctl.html) for option semantics; unit availability remains train-specific.
- [MHI2 CarPlay cluster PF profile handling](https://github.com/maxim-smirnov/mhi2-carplay-cluster/blob/main/docs/build-and-deploy/DEPLOY_AND_RELEASE.md) for documented multi-profile design (independent third-party implementation, not a validated patch for this project).
- [MHI2Q AltScreen profile-switch issue](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/main/README_EN.md) for an independent LTE profile-reload failure description; do not transplant another platform's binaries or automatic fallback blindly.

**Evidence policy:** publishing this contract updates installer requirements; it does not certify a newly implemented on-target PF patcher or show that the colleague has already installed anything.
