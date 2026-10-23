# MIBR/3 controller build and evidence

## Provenance

The installed R57 service source is identified by the source-file SHA-256
below. Its settings implementation descends from
`harman-f/mhi2_altscreen_carplay@324b4f249883bb707e0d0a8995b2b6b5fe23be25`.
The public build links the canonical shared implementation in
`src/native/alt111-settings/`, with the current single registry
`settings/registry.json` (SHA-256
`818cfd7b635742c98e291c3a6eb4a4350bec873715245d2d888fcac360ccd098`).
This is the three-view registry used by the integrated public source tree; it
is not the older two-view registry from the upstream snapshot. MIBR/3 does not
carry a second registry.

The R57 reference `mibr-v3-service` SHA-256 is
`97177ddbfe78d49dc0d672c5b70e717a87c0aeebb6ac65ab4e1b7df12e60bb58`.
The public source-only QNX cross-build reproduced both R57 hashes exactly.
`mibrctl-v3` and `mibr-v3-genkey` also reproduced their recorded hashes; the
R57 changes the service and KEY40 support daemon.

| Component | Source SHA-256 | Installed/rebuilt binary SHA-256 |
|---|---|---|
| `mibr_v3_service.c` (R57) | `cf642daa6f525b6007a6c6f2ff8aff70e9466d5d4ba4acf3f2cf8b7306161d2a` | `97177ddbfe78d49dc0d672c5b70e717a87c0aeebb6ac65ab4e1b7df12e60bb58` (reproduced) |
| `mibr_v3_client.c` | `487fa0298ac55b80cf4a53ed9f686a7d7e4b6b3240ad4cccc6c2431e667649ea` | `fa4a580337a6a0a1d67e15ee1abc7f809591978cbfdecada5b87259fb8a5f351` |
| `mibr_v3_genkey.c` | `a51921f30a3f628b5c27169cc8cc2aa5dc557b89c0f572350d6c1cf3617b6415` | `328837d6df6daaeec25197d8cb9f7e9070c194e012f86dfc3c75256cb36d5474` |
| `mibr_key40d.c` + `mibr_v3_key40.c` (R57) | `878edb0044c48158dfa0463b977e6e90d73b3d8e00508395f362d5c7913c4ee6` + `114f4b8302340c36bbec112d59639791d11bdafbe6f30e84a73b64a66fcaeffe` | `3612c686a6de43c7cfbcb4e96645bca83ba9db33f8c03b19e33c0c73efbaf9d2` (reproduced) |
| `mibr_v3_readonly.c` + `.h` (R57) | `7c6ac5a6f5892954e2b5a40dd8554809e1d3d640bd6f12fcd1478f46b53a64d9` + `ed5db3159953179bc610b91c20bf4d365a2cae63d7396dcf4db834e19ef8e2f4` | linked into R57 service above |
| `mibr-view.ksh` (R57) | `eeb250ee790fa180d901cd68a948da38eea2614733b25b18d99fb5a7ad77e350` | `eeb250ee790fa180d901cd68a948da38eea2614733b25b18d99fb5a7ad77e350` |
| `mibr-engine.ksh` | `e4533241733f6e3afea3402fa58e131b065665734e0c053b25442d68ddbfd127` | Public helper includes the remount-before-staging fix; it intentionally differs from the installed R46 script (`05986352f312bf2dc7b46223ffa2aa666d7127d38e432b15efcaf133d3be2f31`) |
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
recovery behavior are qualified. R57 maps KEY40 short press to view-step
accounting, KEY40 long press to view resynchronization, and KEY44 long press to
the existing route-toggle request. The view helper applies the configured
safe-area mapping only when its existing follow option is enabled. These are
source/binary correspondence facts, not qualification of the physical input
port, action dispatch, or independently visible `ACTIVE` state. Those checks
remain open. The source
publication contains no on-unit test evidence and does not update the
downloadable reference release.

The public `mibr-engine.ksh` helper stages its replacement only after the
system filesystem remount succeeds, checks staging writes, and requests a
read-only remount after both failed and successful write paths. Host tests use
a mocked mount command to check ordering and cleanup; this does not establish
QNX or on-unit filesystem behavior. This narrow helper fix intentionally
changes the script bytes from the installed R46 helper and must not be
described as byte-for-byte correspondence.

## Source-level host tests

The R57 source-only validation passed the host build, all 25 module tests, and
the target-shell static check for `mibr-view.ksh`. Coverage includes KEY40 and
KEY44 event parsing, the view helper's defaults/persistence/resync rule, and a
host service VIEW_GET/VIEW_SET round-trip. The QNX cross-build passed and
reproduced the service and key-daemon hashes in the table above. These results
do not qualify the physical input path, target filesystem behavior, route
action, or live `ACTIVE` state. The source-only promotion includes no installer
or vehicle-test evidence.
