# MIBR/3 controller build and evidence

## Provenance

The installed R46 service source is identified by the source-file SHA-256
below. Its settings implementation descends from
`harman-f/mhi2_altscreen_carplay@324b4f249883bb707e0d0a8995b2b6b5fe23be25`.
The public build links the canonical shared implementation in
`src/native/alt111-settings/`, with the current single registry
`settings/registry.json` (SHA-256
`818cfd7b635742c98e291c3a6eb4a4350bec873715245d2d888fcac360ccd098`).
This is the three-view registry used by the integrated public source tree; it
is not the older two-view registry from the upstream snapshot. MIBR/3 does not
carry a second registry.

The R46-installed `mibr-v3-service` SHA-256 is
`993618f9aa213ed9dc02f8deed625d27486af06003681d2c4048f70481ad5e08`.
The QNX cross-build reproduced this hash exactly. The same build also reproduced
the installed `mibrctl-v3`, `mibr-v3-genkey`, and `mibr-key40d` hashes exactly;
those three binaries are from earlier source snapshots, not newly introduced by
R46.

| Component | Source SHA-256 | Installed/rebuilt binary SHA-256 |
|---|---|---|
| `mibr_v3_service.c` (R46) | `064fe9c4a854ac48ed1c3039e800262ac60e3261bcb0845db666bfc6b6e53e99` | `993618f9aa213ed9dc02f8deed625d27486af06003681d2c4048f70481ad5e08` |
| `mibr_v3_client.c` | `487fa0298ac55b80cf4a53ed9f686a7d7e4b6b3240ad4cccc6c2431e667649ea` | `fa4a580337a6a0a1d67e15ee1abc7f809591978cbfdecada5b87259fb8a5f351` |
| `mibr_v3_genkey.c` | `a51921f30a3f628b5c27169cc8cc2aa5dc557b89c0f572350d6c1cf3617b6415` | `328837d6df6daaeec25197d8cb9f7e9070c194e012f86dfc3c75256cb36d5474` |
| `mibr_key40d.c` + `mibr_v3_key40.c` | `85f8e5400b499bda9e3c188dd53e1fcbb483e9f1881c111f9cf48dda450dc16d` + `6cbb8f728e956dfd3feb7fdfcfff65e118cf7887a3a165c3f126dfd2e42a947c` | `2b9143412b7aa64fd8159056023cec8cb2ad60577a9e97368de61aa6d95c8a61` |
| `mibr-engine.ksh` | `05986352f312bf2dc7b46223ffa2aa666d7127d38e432b15efcaf133d3be2f31` | Same bytes as installed script |
| `mibr-v3-boot.ksh` | `5334b7689c587a4b805779486efec16c1a1e43227a7497d50d78bf2da321c6ca` | Same bytes as installed script |

## Build inputs

`tools/build_mibr_control.sh` supports a host build, a QNX 6.5 ARMv7
cross-build through Docker, and `qnx-container` mode for an already running
toolchain container. For reproducible toolchain preparation, follow the pinned
repository revision, Dockerfile digest, and base target in
[`docs/build/INSTALLED_GEN2_SOURCE.md`](../../../docs/build/INSTALLED_GEN2_SOURCE.md).
The QNX build emits named `NOT-INSTALL-READY` outputs. No release package or
unit mutation is produced.

The QNX service command links these project modules with the one canonical
settings core and uses the ARMv7 soft-float/QNX6.5 target flags shown in the
build script. The service ELF header reported ELF32, little-endian, ARM, EABI5.
Exact hash reproduction depends on compiler image contents, source paths, and
every linked source byte; a successful ELF compile alone is not hash
reproduction.

## Evidence categories

| Evidence | What it proves | What it does not prove |
|---|---|---|
| Host regression | The tested source contracts behave under the host test setup | QNX command behavior, on-unit filesystem safety, or live effect |
| QNX cross-build | The source links for the specified QNX6.5 ARMv7 ABI | Installed hash reproduction, installability, or target behavior |
| Installed SHA-256 | Identity of the named unit artifact | Source equivalence unless a reproducible build matches it |
| `stored=VERIFIED` | Profile write/readback met the storage adapter contract | TEMP materialization or runtime apply |
| `materialized=1` | Original TEMP compatibility layer readback matched | Live consumer activation |
| `apply=PENDING` | An action is not yet confirmed complete | Active/visible state |
| `active=UNKNOWN` | Independent runtime evidence is unavailable | A successful live change |

The route gateway and KEY40 input seams are present as project-owned source but
are not proof of an attached exact-target owner or independent AID-visible
observer. Route capability must remain off until those providers and their
recovery behavior are qualified. The existing `mibr_key40d` source includes a
long-hold route-toggle mapping; this is preserved installed-source evidence,
not approval of a physical gesture assignment. Physical input port, action,
and independently visible `ACTIVE` validation remain open. The source
publication contains no on-unit test evidence and does not update the
downloadable reference release.

## Source-level host tests

The included tests cover KEY40 event parsing/classification and engine helper
read/write behavior against synthetic configuration. Service-level host
regressions additionally require a host build linked to the canonical core;
the repository workflow provides the complete module-level test gate. Test
results are reported with the exact command and build inputs in the publication
receipt.
