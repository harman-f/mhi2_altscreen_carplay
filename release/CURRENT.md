# MU1440 / AID10 developer test — current

## Current three-profile beta build status (2026-11-09)

The MIB Runtime `1.5.0-beta.12` source on `main` includes all three owner-approved menu JARs and the [opt-in beta package pipeline](../docs/build/MULTIPROFILE_RELEASE.md). The checked-in Java artifacts may be reused only while the reviewed Git-object content lock for menu/profile/registry sources is unchanged; new Java changes require separately validated local J9 rebuilds and updated provenance. The separate `ghcr.io/harman-f/mhi2-qnx65-armv7` **package is a pinned QNX cross-compiler Docker image**, not a deployable CarPlay release, and must remain available to CI while `tools/qnx65-image.lock` references it.

This beta workflow still requires a private runner for the extender and native navigation dependencies. It uploads only time-limited Actions artifacts when enabled. **No new GitHub Release or complete end-to-end pipeline build has been published at this point.** The frozen historical MU1440 developer package described below remains a distinct release lineage; do not silently transfer its vehicle acceptance to the beta.


This is the currently pinned **MU1440-specific developer prerelease**, not the newest experimental source line. Documentation-only main-branch updates do not mutate the already published ZIP or retroactively re-qualify its binary hashes. See [current integration status](../docs/status/INTEGRATION_STATUS_2026-10-21.md), [latest known issues](../docs/findings/KNOWN_ISSUES.md) and [dated vehicle test evidence](../docs/status/MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md).

The 29 September Most20/D2 update (kept at the end of this file as a historical implementation note) is already incorporated into the consolidated statements below; later release-tag decisions require their own verification.

## Release readiness after module migration (2026-11-03)

> **2026-11-04, MIB Runtime cutover:** current sources use the single unit root `/mnt/app/root/mibr/`. The pre-MIBR 7-payload developer ZIP (altscreen-u2 layout, hash-pinned binaries) is a **frozen legacy line**: it is no longer assembled from the current tree and is only built from its frozen tag. The next installable package is the MIB Runtime beta ZIP with the root migration (`installer/lib/migrate-root.ksh`).

The [release-readiness workflow](../.github/workflows/release-mu1440-aid10.yml)
is now a **fail-closed CI audit**, not an automatic GitHub release publisher.
It reads [canonical module ownership](../modules/module-index.json), calculates
affected modules including declared reverse dependencies, and reports changes
that have no canonical owner. For actual QNX builds, the existing source-build
workflows remain the authority; this impact report is **not a newly built binary
receipt**.

The release audit checks the canonical runtime module inputs **and every
on-unit shell script actually staged into the frozen MU1440 SD-root bundle**.
It runs the [vehicle-derived QNX command preflight](../docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md)
and host syntax checks, verifies exact pinned vehicle-media hashes and separately
build-confirmed SHA/tee helpers, then re-opens the assembled ZIP to verify
the complete file and payload manifest. These static host checks cannot prove
that a dynamically composed command is available on MMX or RCC; the actual
target command/option inventory and vehicle test still govern acceptance.

**No ZIP is uploaded as a distributable artifact and no GitHub release/tag is
created or replaced by this workflow.** The old seven-payload SD-root archive
(`..._LEGACY_CI_ONLY.zip`, never uploaded, tagged or released; any "release ZIP" mentioned below means the historically published one)
is deliberately still generated *inside CI* for compatibility regression checks,
but it does **not** satisfy the [R3 modular distribution contract](../docs/build/PACKAGE_LAYOUT.md).
The R3 validator is run on the actual legacy archive to prove that it is
rejected; its separate negative-fixture self-test is not treated as release
approval. The missing shared/common, profile, exact-fingerprint and inventoried
source layers must be implemented and the **actual completed R3 ZIP** passed
to `tools/validate_modular_package.py` before any future publication job
can be enabled. Existing historical releases and tags are not modified.

See [release pipeline design](../tools/release/README.md) for module impact
rules, source-build boundaries and the QNX-script inventory gates. The
[digest-pinned QNX toolchain image contract](../docs/build/QNX_TOOLCHAIN_IMAGE.md)
describes the archived compiler environment. The five native CI workflows
already consume the digest-pinned image in `tools/qnx65-image.lock` through
`tools/ci_qnx65_image.sh` instead of rebuilding GCC on each job (PR #126). Still
open: recording the actual image digest in `MODULE_BUILD_LINEAGE.json`. None of
this changes or requalifies this pinned developer prerelease.

## Validated reference target

- MHI2 train: `MHI2_ER_SKG13_P4526_MU1440`
- exact LSD/J9 target hash:
  `a55d9cfb69c5756f8202b7f7aa4079d4d5b637ae4c2fd0fe723f1d6816cbeea8`
- cluster: project shorthand **AID10-class** 10.x-inch MQB Virtual Cockpit reference family
- not yet validated for the older/larger 12.3-inch AID family or other cluster generations

Compatibility is defined by target identity and hashes, not by internal development-run numbers.

## Self-contained test payload

The release ZIP contains every project-supplied file required for the currently validated path:

- `libaltscreen111.so`
- `direct-ts-remux`
- `libmibr_isotx2_gate.so`
- `sha256sum`
- `tee`
- `MIBR-NavIgnore.jar`
- `MIBR-Most20FPS.jar`

No additional project payload needs to be downloaded before testing. The publication audit checks
that every payload reference in the shipped scripts resolves to a file inside the ZIP and that the
payload directory contains no unmanifested extra dependency.

Pinned hashes:

- GEN2:
  `094e3f1abfbf949f8c11b27e048e8213e5fc71178e62efd3c56deed8ee3bf8d8`
- direct-ts-remux:
  `b761a8741682e3cbc6e05f5fe1705475c34c4805d1cd1ce09333274a301e735e`
- isoTX2 gate:
  `05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957`
- NavIgnore:
  `b065bab0e1c58f8439a3bdd73d2d4cb6060cbac1c943e5b425425eb453c94b34`

The gate artifact is the byte-reproduced vehicle-tested binary. The tester-facing package intentionally
uses hashes and validated-target identifiers rather than internal run labels.

## NavIgnore provenance

The release includes the exact vehicle-tested `MIBR-NavIgnore.jar`.

Its provenance is documented in `THIRD_PARTY/NavIgnore/`:

- pinned public upstream: `jilleb/mib2-toolbox`
- pinned upstream commit: `7ec3b7540d48acfebb5d331820b4ee55eff66772`
- upstream license copy: MIT
- deterministic splitter: `tools/split_navactiveignore.py`

The split removes the MOST20FPS `ChangeDataRateSequence.class` and keeps the NavIgnore portion.
The release does **not** contain the full `lsd.jxe` or an LSD firmware dump.

## Existing Java patches on a tester vehicle

The installer does not silently overwrite an unknown Java state.

If an older or foreign bootclasspath/JAR state is detected:

1. `install.sh --check` archives the current Java state to the SD and returns
   `PREFLIGHT=ATTENTION`;
2. no target-side Java state is changed during `--check`;
3. `install.sh --apply` offers:
   - `C` — retain the recovery archive, normalize the conflicting Java state and continue with the
     bundled exact NavIgnore;
   - `Q` — abort without changing target-side Java state;
4. the full preflight runs again after normalization before the normal deployment proceeds.

## Unknown target / compatibility contribution

For a firmware, brand or cluster that is not yet validated, start with:

```sh
./compatibility-report.sh
```

Do **not** start with an installation attempt just to discover compatibility.

The collector is read-only with respect to the vehicle filesystems. It creates a timestamped SD
session containing:

- the normal sanitized `vehicle-summary.txt`;
- `compatibility/component-hashes.txt`;
- `compatibility/runtime-observation.txt`;
- read-only snapshots of `displaymanager.json`, `dio_manager.json`, and
  `smartphone_integrator.json` when present.

This standardizes the evidence needed to compare an Audi/VW/SEAT/CUPRA target with the MU1440
reference before deciding whether any hook/installer path is appropriate. The repository Discussion
template now points contributors with an unvalidated target to this collector first.

## SD layout

Extract the ZIP contents **directly to the SD-card root**.

There is no `esd/` wrapper and no `MHI2AltScreen/` wrapper.

Start with:

```sh
./install.sh --check
```

If the preflight is understood and acceptable:

```sh
./install.sh --apply
```

Then reboot and run:

```sh
./status.sh
```

## Logs for issues

`compatibility-report.sh`, `install.sh`, `status.sh` and `uninstall.sh` create timestamped sessions under
`mhi2-altscreen-logs/` on the SD card.

For a public issue, attach:

- `session.log`
- `vehicle-summary.txt`

VIN, FAZIT and device serial numbers are intentionally not collected in that summary.

The `archive/` directory is for local recovery and can contain copied JAR bytes. Review it before
sharing it publicly.

## Deliberately not part of the current validated release

These remain development/research items rather than hidden prerequisites:

- SafeArea-capable GEN2 candidate;
- dynamic ViewArea experiment;
- DirectVCPolicy experimental Java work;
- unqualified variants of the existing Most20FPS patch;
- legacy combined Java patch;
- newer experimental parity/clockdiag/Zoom/HMI/vehicle-data/controller candidate implementations.

The current public D2 same-session keyframe policy is **persistently enabled by default** as described in the 29 September update below, with its conservative 1-second watchdog and a documented opt-out. It is not evidence of a later recovery candidate's full qualification.

A documentation merge into `main` must not be described as recreating the frozen developer-release tag. Check the actual GitHub release/tag and ZIP hashes independently whenever making a new release.

This remains a developer prerelease: the media-path payload bytes are vehicle-tested, while the
integrated standalone installer, logging and foreign-Java recovery flow is undergoing broader
vehicle validation.


## Historical implementation change incorporated in the above effective release description (2026-09-29)

The MU1440/AID10-class developer package now includes the vehicle-validated standalone Most20 patch
and enables the conservative D2 keyframe policy persistently by default.

Most20 payload:

```text
MIBR-Most20FPS.jar
SHA-256 dbd45609fe4ba69948d39e9e649b224484f680f6aa7934b68c261a4d360ea5bb
```

Vehicle capture at the stock DisplayManager -> `/dev/mlb/isoTX2` boundary measured:

- stock: 1010x376 H.264 Baseline, 10 fps, 105 x 12,032-byte writes in about 4 s;
- Most20: 1010x376 H.264 Baseline, 20 fps, 210 x 12,032-byte writes in about 4 s;
- five-frame GOP retained, so native I/IDR cadence changes from about 0.5 s to about 0.25 s.

GEN2 D2 remains a separate source-side recovery mechanism. Its public default is now persistent
with a 1 s source-IDR watchdog and 1 s minimum request gap; it can be disabled at runtime and
persistently with `gen2_keyframes.sh off`.

Packaging gate: the current self-contained SD package is audited as a closed seven-file payload set, including both split Java JARs and the published persistent-D2 runtime controls.
