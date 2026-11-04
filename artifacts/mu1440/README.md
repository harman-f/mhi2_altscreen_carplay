# MU1440 binary reference inventory

These are pinned historical inputs and evidence, not the output directory for new builds. Keep each artifact and its checksum at its existing path; build candidates separately. The current legacy SD-root packager is [`tools/prepare_mu1440_sd.sh`](../../tools/prepare_mu1440_sd.sh); its exact pinned inputs and the release audit remain authoritative.

| Area | Role | Evidence / provenance |
| --- | --- | --- |
| [`altscreen111/vehicle-tested-2026-09-27`](altscreen111/vehicle-tested-2026-09-27/) | Legacy installer input and vehicle-tested reference | Directory README and SHA-256 sidecar |
| [`direct-ts-remux/vehicle-tested-2026-09-27`](direct-ts-remux/vehicle-tested-2026-09-27/) | Legacy installer input and vehicle-tested reference | Directory README and SHA-256 sidecar |
| [`isotx2-gate/vehicle-tested-2026-09-27`](isotx2-gate/vehicle-tested-2026-09-27/) | Legacy installer input and vehicle-tested reference | Directory README and SHA-256 sidecar |
| [`altscreen111/experimental-gen2-2026-09-25`](altscreen111/experimental-gen2-2026-09-25/) | Earlier development checkpoint, not the legacy installer input | README, SHA-256 and ELF/build evidence |
| [`direct-ts-remux/vehicle-proven-run143`](direct-ts-remux/vehicle-proven-run143/) | Earlier vehicle-proven checkpoint, not the legacy installer input | README, SHA-256 and build evidence |
| [`isotx2-gate/build-confirmed-current`](isotx2-gate/build-confirmed-current/) | Build-confirmed candidate, not the vehicle-tested gate | Directory README and SHA-256 sidecar |
| [`sha256sum-compat/build-confirmed-current`](sha256sum-compat/build-confirmed-current/), [`tee-compat/build-confirmed-current`](tee-compat/build-confirmed-current/) | Build-confirmed compatibility helpers included by the legacy packager | Directory READMEs and SHA-256 sidecars |
| [`most20fps/vehicle-tested-2026-09-29`](most20fps/vehicle-tested-2026-09-29/) | Third-party-derived legacy installer input | [Most20FPS provenance](../../THIRD_PARTY/Most20FPS/README.md) |
| [`navignore/vehicle-tested-2026-09-27`](navignore/vehicle-tested-2026-09-27/) | Third-party-derived legacy installer input | [NavIgnore provenance](../../THIRD_PARTY/NavIgnore/README.md) |

An SD-root compatibility build is not the three-profile R3 installer, and these historical vehicle observations do not qualify a new build. See [`release/CURRENT.md`](../../release/CURRENT.md), [third-party notices](../../THIRD_PARTY_NOTICES.md), and the [module index](../../modules/module-index.json).
