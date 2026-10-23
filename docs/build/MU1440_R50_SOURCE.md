# MU1440 R50 source baseline

This source-only baseline publishes the project-authored MU1440 implementation through the R48 menu, R49 supervisor and R50 owner. It includes an additional owner safety correction described below. It is a **partial vehicle-matched source publication**, with explicit OEM prerequisites and unresolved support-file lineage. It does not replace the downloadable reference release, supply an installer, or qualify SEAT MU1409.

## Modules and ownership

The four core components remain separate: GEN2 owns Type-111 negotiation/control and H.264 AU production; `parity-session` owns exclusive takeover, bridge lifecycle and stock restoration; `direct-ts-parity` owns the M1AU/PES/TS media worker; the DisplayManager-side native guard owns native/custom arbitration and its proof. The existing historical isoTX2 gate remains a separate prerequisite alongside the guard. This publication does not consolidate the two interposers.

The R49 supervisor orchestrates sessions. The R46 MIBR/3 service owns one settings/control API, linked directly to the canonical settings core. Java is an asynchronous OEM-widget adapter and has no independent settings store or media sender. Vehicle data uses the existing authenticated session and remains experimental.

| Source | Reference version | Build evidence |
| --- | --- | --- |
| [GEN2 and vehicle data](../../src/native/altscreen111-gen2/) | R38 overlay | Exact installed QNX output reproduced |
| [Canonical settings](../../src/native/alt111-settings/) and [registry](../../settings/registry.json) | Installed three-view overlay | Exact installed CLI reproduced |
| [Media worker](../../src/native/direct-ts-parity/) | Installed source-time transport | Exact installed QNX output reproduced |
| [Owner](../../src/native/parity-session/) | R50 plus publication safety correction | Original R50 reproduced; corrected owner host/QNX checked, not installed |
| [Native guard](../../src/native/altscreen111-gen2/src/alt111_native_gate.c) and [legacy gate](../../src/native/isotx2-gate/) | Installed interposers | Both installed QNX outputs reproduced |
| [Supervisor and wrappers](../../runtime/parity/) | R49 | Installed behavior retained; public comments curated |
| [Controller](../../src/native/mibr-control/) | R46 service; installed client/genkey/KEY40 support | Four exact installed QNX outputs reproduced |
| [OEM menu](../../src/hmi/oem-menu/) | R48 | Own adapter/generator/tests published; exact J9 rebuild blocked by external compiler/API inputs |

The installed three-view registry contains 48 keys and permits three negotiated areas. This is a reference implementation snapshot; it does not establish that every control has independent live effect. Switchable lockout semantics remain unresolved and are **not** silently replaced by the pause marker. This publication makes no claim of a complete configuration/control surface. Existing input gesture mappings remain experimental source, not a new approved assignment.

## Build native source

Use Linux or WSL2 with Bash, Python 3, a C compiler, Git and Docker. The standalone helpers require no private repository. Build the existing public pinned QNX 6.5 ARMv7 environment:

```sh
bash tools/build_qnx65_image.sh /path/to/new/qnx-toolchain mhi2-qnx65-source:4.9
docker run --rm -v "$PWD:/src" -w /src --entrypoint /bin/bash \
  mhi2-qnx65-source:4.9 -ec 'bash tools/build_mu1440_source.sh'
```

The toolchain source is pinned to `luka-dev/qnx65-armv7-toolchain@56a66557245af14077678cd28a83ce3a337d9e2d`; the helper checks its Dockerfile and applies the documented Debian security snapshot bootstrap. It does not distribute or relicense the toolchain. Native outputs and a SHA-256 manifest are written under `build/mu1440-source`. Build at the canonical container path `/src` for matching debug metadata. The bridge is built before the owner, which embeds its exact SHA-256. Do not substitute an arbitrary prebuilt bridge.

```sh
bash tools/test_installed_gen2_host.sh
bash tools/test_gen2_components_host.sh
bash tools/test_parity_host.sh
bash tools/build_mibr_control.sh host
MIBR_V3_NATIVE_HOST_BIN="$PWD/build/mibr-control/mibr-v3-service-host" \
  python3 -B -m unittest discover -s tests/mibr-control -v
python3 -B -m unittest discover -s src/hmi/oem-menu/tests -v
```

The parity decode regression needs FFmpeg with libx264. CI installs that dependency and executes the synthetic predictive-frame decode test. Tests use synthetic input and mocks; they do not contact a vehicle. See [GEN2 build details](INSTALLED_GEN2_SOURCE.md), [controller details](../architecture/mibr-control/BUILD_AND_EVIDENCE.md), and [Java build prerequisites](../../src/hmi/oem-menu/README.md).

## Installed hashes and deliberate correction

| Installed artifact | SHA-256 reproduced from source |
| --- | --- |
| GEN2 R38 | `304b5079374a08ed9a763528217476b29ad49e000ba25d0372ed4147cbb9a705` |
| Settings CLI | `b0d61578452a93b966f268e2bd400029bb1b6fa249dfd18e8895f851ca89073c` |
| Direct-TS parity | `3098cdd4469a4a3b4ee92c583518b3af362e02e41921ed3d80641853ced0827b` |
| Native guard | `cad06d69c698c8940dec9596b96c6b90ec822bdd437c4b0d02a35881ad71fae4` |
| Legacy gate, stripped | `05673010a88c25022145ffb4e75d3715eaf686f4127ac188e91a52f512b9d957` |
| Original R50 owner | `b343743f02258bb1c952dabb3722b7645ac43fe881ecfbd027bdc8099db03c7e` |
| Pre-R50 owner | `c16965ec11caec738141d348253d74cf6a6799000deccfe9b11d50117dc122b2` |

The four controller hashes are recorded in its linked build document. The installed R48 JAR is identified by `2090427867ab5de3390071d07a6e7c749587a2c1cb799e78ebfbaa60a78a0989`; retaining that identity does not demonstrate an exact rebuild.

Original R50 unconditionally sent CONT after a failed gate-grace wait. The public canonical owner now leaves the bridge stopped until bounded termination is confirmed. A TERM-resistant host child demonstrated the original extra resume and the regression passes with the correction. No control/default/core-boundary change is introduced. The historical transformation is retained in `tools/source-overlays/` for source provenance and reproducing the installed version from public reference `324b4f249883bb707e0d0a8995b2b6b5fe23be25`; it is not the canonical owner and must not be installed by the current build. Host POSIX signal tests do not qualify QNX process-handle/SignalKill behavior on the vehicle.

The corrected QNX owner built at `/src` has SHA-256 `87b7ece6be005b9ad821a2c899c5a503cbeea7b27504300337676a5590d26b36`.

## Remaining source and reproduction limits

- The OEM menu needs an independently obtained, exact MU1440 `lsd.jar`, IBM J9 SDK and local OEM source views for guarded preparation. No OEM JAR, JXE, original class body or generated OEM implementation is included. Class-file major 46 is enforced by the build. Exact R48 JAR reproduction remains open.
- Eight original tile/skin images derive from OEM resources and remain local external prerequisites. Four independently authored flat-color scrollbar images are included with hash-checked provenance. Missing external art leaves custom HOME tile artwork incomplete.
- Exact installed DirectVCPolicy and early BootProbe source lineage is unresolved. DirectVCPolicy's candidate source contains decompiled OEM bodies and is excluded. They are not required to build the published native modules or the owned R48 adapter, but their coexistence remains a separate installation concern.
- The installed legacy `direct_ts_auto_stop.sh` and `writev_gate.sh` variants are not fully source-matched; installed `common.sh` and several patch/restore helpers differ from the current public reference helpers. Historical public Git objects retain some exact variants. No old auto-direct path is substituted for the canonical parity owner.
- Legacy remux artifacts, automatically written profile backups, unit configuration, patched OEM startup/iAP2/JSON files and original artwork are not exported as current source. Existing public remux/source tools remain available; exact installed legacy remux build identity is not newly proven.
- The installed current stack and this safety correction have no complete combined vehicle acceptance. Source reconnect, writer-gate recovery, independently visible route/ACTIVE confirmation, physical input and optional phone vehicle-data acceptance retain separate gates.

An external contributor can build the published project-owned native modules using only this repository and the public toolchain. Java's owned source can be inspected and its host checks run without OEM inputs; compiling its target JAR and reproducing the full installed visual stack requires the legitimate external inputs above. This is not a claim that every installed vehicle byte is reproduced.
