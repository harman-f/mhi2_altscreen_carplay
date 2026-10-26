# Product delivery pipeline — source, package, installation and release

**Status snapshot: 2026-10-26.** This is the public integration map and acceptance contract for the MU1440/AID10 product line. It distinguishes existing public facilities from proposed changes and independently qualified results. It is not an installation instruction or permission to publish a release.

## Source of truth and separation

- Product-owned implementation, public-safe build/test logic, sanitized documentation and eventual distribution belong in this repository. Development changes enter `develop` through scoped PRs; `main` is the reviewed release line.
- OEM firmware, private device exports, proprietary J9/SDK inputs and unredistributable artifacts are **not** copied into public source, Actions logs, artifacts or release assets. Availability of a private build is not evidence of redistribution clearance.
- Immutable historical kit evidence, an experimental build, an offline installable candidate, a physical Unit test and a public vehicle-qualified release are **five different states**. Never replace one with another by version naming alone.
- Feature development (including 1.4.x, Suggest-UI, Scaling and GPS) and SEAT/MU1409 qualification remain on their own review lines. This delivery document does not select their commits, merge their PRs or alter runtime behavior.

## Current public implementation (verified 2026-10-26)

| Stage | Present public implementation | What is **not** closed |
| --- | --- | --- |
| Source provenance | PR [#73](https://github.com/harman-f/mhi2_altscreen_carplay/pull/73) carries a 266-path committed source allowlist, deterministic source archive with per-file hashes/provenance, target-shell preflight, public-content audit and host/QNX workflow integration; PR currently open, CI green. | Source archive is not an install kit; three-day CI artifact retention is not permanent release provenance. |
| Builds | Existing pinned QNX 6.5 ARMv7 toolchain workflows build native components and support tools; host and publication checks exist. | Exact historical J9/OEM menu byte reproduction, some legacy helper lineage and complete product payload attribution are not established publicly. |
| Developer deployment | `tools/prepare_mu1440_sd.sh` and `deployment/mu1440/{install,status,uninstall,compatibility-report}.sh` already assemble/check/install/restore the **older seven-payload developer reference path**, with exact-target checks and recovery precautions. | Not a complete, versioned 1.3.2 product package; no generalized product manifest/receipt, end-to-end journaled upgrade or integrated future firewall mutation. |
| Installer design | Existing [installation guide](../INSTALLATION.md) and [Type-111 PF contract](../installation/TYPE111_FIREWALL_INSTALLER_CONTRACT.md); simplified additive integration is described in **draft** PR [#78](https://github.com/harman-f/mhi2_altscreen_carplay/pull/78). | The PR is docs-only. The current developer installer does not automatically patch/restore PF. Some separate-firewall command descriptions in the older public contract conflict with the newer ordinary-install integration direction; reconcile them in #78, not via a second implementation. |
| Version identity | Draft PR [#74](https://github.com/harman-f/mhi2_altscreen_carplay/pull/74) provides build/target/config identity groundwork and a read-only Advanced → Version page. | Installed-file verification, transactional install receipt, binary-set/package identity closure and immutable public product release are not integrated. |
| Release history | Historical `dev-current` GitHub Release and its assets were withdrawn; the alias tag remains. Draft PR [#75](https://github.com/harman-f/mhi2_altscreen_carplay/pull/75) removes unrelated historical-release/tag deletion from the old publisher. | The legacy workflow still contains destructive cleanup on `develop` until #75 lands. The movable alias is not a versioned immutable release. There are currently no public GitHub Releases. |
| Integration gates | `develop` has an active strict required-check ruleset (`PR source gate`, `Publication integrity audit`). | Require explicit PR-based review and verify effective `main` protection: API readback did not report `main` as protected, and the existing Main ruleset has no included refs or required named checks. Tag immutability is also not configured. |

The historical [developer reference page](../../release/CURRENT.md) documents a pinned **former** test payload; after withdrawal of the GitHub Release it must not be presented as a current download. Do not edit its trigger-sensitive file as an incidental documentation cleanup.

## Canonical forward pipeline

```text
Reviewed public-owned source at exact commit
  -> source-only provenance/audit gate
  -> pinned host + QNX builds
  -> authorized J9/OEM-dependent build in separated environment, if required
  -> provenance and license clearance for EVERY distributable payload
  -> complete target/config/binary-set/package manifest + independent validator
  -> deterministic immutable candidate archive and checksums
  -> read-only target inventory and full candidate-specific preflight
  -> durable external recovery set; check -> plan -> apply -> verify
  -> controlled normal restart and effective-state verification
  -> separately authorized Unit/iPhone/vehicle acceptance
  -> immutable versioned release with retained evidence
```

**Build identity, package identity, installed-file identity, active process/runtime identity and observed visual/phone effect must be independently represented.** Never infer a later state from a preceding PASS.

### Packaging and release integrity

1. Pin source commit, dependencies/toolchain, exact target (firmware/J9/cluster), config profiles and input artifact hashes. Record both provenance and redistribution status.
2. Define the **canonical** versioned manifest schema/validator once, integrating PR #74 rather than adding a parallel schema. Manifest lists every shipped file, size, mode and SHA-256, its component/build origin, target compatibility and binary-set/package IDs.
3. Package from validated inputs into a deterministic archive, verify the archive by independent extraction and matching full closure, and retain immutable evidence. An unknown/missing binary input is a hard block for the *complete product* but does not invalidate a scoped public source build.
4. Versioned product tags and release assets must be immutable: unique name and tag; abort on collision/mismatch, never overwrite or sweep earlier releases. Only publish after integrity, rights and acceptance gates. CI run artifacts are transient.
5. Keep release workflow privileges separate from ordinary PR verification. Never accidentally activate the legacy `release-mu1440-aid10.yml` by changing `release/CURRENT.md` on `main`.

### Ordinary install / upgrade / recovery contract

The installer must work with the actual QNX shell and commands, preserve stock ownership/handback, and fail closed on target, version, ABI, preimage or filesystem uncertainty.

- `CHECK`: read-only target/installed-version inventory and full payload validation. Unknown foreign Java, unit configurations and preimages are classified; never silently normalized or removed.
- `PLAN`: durable, hash-bound, per-path KEEP/ADD/REPLACE/BLOCK operation list; exact ownership, permissions, destination mapping, backup and restoration plan. Classify known upgrades separately from reviewed unknown-compatible states. No generic force bypass.
- `APPLY`: explicit candidate authorization, verified external recovery bytes/metadata, same-filesystem staging, recheck immediately before each write, journaled transaction with interrupted-run recovery. Keep unrelated SSH, user config, third-party state and historical files untouched.
- `VERIFY`: independently inspect installed hashes, effective startup/classpath, selected settings and active native owner; mark reboot-dependent outcomes pending until after the normal controlled restart. A successful copy is not ACTIVE or visual acceptance.
- `ROLLBACK/UNINSTALL`: restore only project-owned edits when current postimages match the journal, preserve user preferences according to the installed version contract and stop on foreign modifications. Re-verify original STOCK networking/navigation and provide recovery without the UI.

**Type-111 PF:** use the actual configured/advertised port (MU1440 default TCP 6031), recognize existing matching `carplay0` allowlists including ranges, otherwise make only the minimal additive change. Back up each actually affected preimage in the ordinary transaction and never replace other projects' rules. If a valid rule exists, write nothing. Do **not** introduce a competing second `--apply-firewall` step, blind whole-file preimage templates, PF hot reload, SSH/inetd restart or automatic profile rewrite on unqualified targets. A file containing the rule is not proof that the running policy permits the phone; verify after restart and relevant profile changes.

Where the older published PF contract requires separate `firewall --apply` commands, **PR #78 is the pending reconciliation owner** for the normal-installer integration decision. Until reconciled and implemented, the public developer install retains its documented external PF prerequisite. No change in this document authorizes an on-Unit write.

## Integration order and ownership (no implicit merge)

1. **Foundation:** finish review and integrate [#73](https://github.com/harman-f/mhi2_altscreen_carplay/pull/73), retaining its exact source-only scope. Correct the effect of `main` and `develop` rules and ensure required checks are truly produced on every applicable PR.
2. **History safety:** rebase/retest [#75](https://github.com/harman-f/mhi2_altscreen_carplay/pull/75) against the new audit and remove global tag/release cleanup before any old publisher can run. Keep it disabled; its mutable `dev-current` semantics remain deprecated.
3. **Identity/installer:** rebase [#74](https://github.com/harman-f/mhi2_altscreen_carplay/pull/74) for version identities and reconcile/implement [#78](https://github.com/harman-f/mhi2_altscreen_carplay/pull/78) in the **existing** installer, preserving tests and recovery semantics. Promote only public-safe, provenance-cleared product-owned code.
4. **Product closure:** integrate the canonical validator, payload provenance, ordinary journal/receipt and deterministic package/immutable publisher; separately verify packaging, upgrade, idempotence, failure and exact rollback.
5. **Qualification:** exact-target Unit/phone/vehicle acceptance and publish only an appropriately qualified immutable versioned release.

Do not use this closure effort to merge or rewrite active 1.4.x feature branches, [Suggest-UI #67](https://github.com/harman-f/mhi2_altscreen_carplay/pull/67), [GPS design #77](https://github.com/harman-f/mhi2_altscreen_carplay/pull/77) or SEAT PRs #68–#72. Existing experimental and historical branch/tag identities remain available; branch inventory/cleanup is a later non-destructive governance review.

## Release/acceptance decision states

| Gate | PASS means | Do not infer |
| --- | --- | --- |
| `SOURCE_READY` | Cleared public source closure and reproducible declared source build | Full product payloads |
| `PACKAGE_ASSEMBLED_UNQUALIFIED` | Whole named package passes manifest/provenance/identity tests | Unit-safe install |
| `UNIT_PREFLIGHT_READY` | This exact candidate and current preimages have a validated recovery/operation envelope | Installation completed |
| `INSTALL_VERIFIED` | Post-restart installed, effective settings/PF, owner/handback and receipt verified | iPhone and driving behavior |
| `VEHICLE_QUALIFIED` | Separately scoped real phone/VC behavior and recovery witnessed on the named target | All firmware and cluster families |
| `PUBLIC_RELEASED` | Rights-cleared immutable exact package and evidence retained under a version tag | Any stronger qualification than stated |

Keep historic evidence and older source files for traceability; consolidate by pointing readers here, not by deleting old experiments or rewriting history.
