# MU1440 Final Drive package provenance and upstream separation

> Historical archive manifest only. No original ZIP, executable package or installer is supplied by this documentation import.

The SD Final Drive operator ZIPs were created as separately staged artifacts after the pinned CI v1 checkpoint. **They are not a new CI-built native transport**, not part of the original v1 source commit, and must not be represented as released/tested solely because documentation is upstreamed. The source-controlled v1 lineage exists at [3a91204b6169eafcc525991fdf10c2aab3fb8d72](https://github.com/harman-f/mhi2_altscreen_carplay/commit/3a91204b6169eafcc525991fdf10c2aab3fb8d72).

This file is an exact manifest for the locally staged ZIPs. The binary ZIP files themselves, raw vehicle logs and identifying phone/vehicle footage are **not added to this PR**. Distribution of a future source-only or developer release must independently verify the entries below against the archive actually attached to the release.

## Whole-ZIP SHA-256 (local staging)

| File | Size, bytes | SHA-256 |
| --- | ---: | --- |
| `MU1440_FINAL_DRIVE_V1_20261010.zip` | 2219490 | `6ed32a69618d0f84e1342f6ff3ea2f58db02582d2c1fba05d3a9a6acc2a1e826` |
| `MU1440_FINAL_DRIVE_V1_2_REDUCED_DEFAULT_20261010.zip` | 2227115 | `fc0dd62951ba136da2565d3452eb579ebc86dcb27ecf0a7541735780f37e74b1` |
| `MU1440_FINAL_DRIVE_V1_3_TELEMETRY_FIX_20261010.zip` | 2228585 | `8d4b8eccb9175cb40b9ed5d2af72e3ebd7c67375b62870f2df41948ef34fd74a` |
| `MU1440_FINAL_DRIVE_V1_4_CENTERED_OPTION_20261010.zip` | 2230153 | `37c4702bfea4a2760897f32430debea3486f243323e6724af0b221a4a6ce511a` |
| `MU1440_FINAL_DRIVE_TELEMETRY_FIX_UPDATE_20261010.zip` | 8993 | `6f81348785170a09c1d34f5fc190b1f11a97bb881e34ddc21bd767551ffd55cc` |
| `MU1440_FINAL_DRIVE_CENTERED_OPTION_UPDATE_20261010.zip` | 12496 | `5c611238364f2a875ab8dc9bf1d484528b52a1c7bfc161def108e5078a0ec245` |

Native identity in both full v1 and v1.4:

```text
10350fb7dc715ec9b99c6b2acadb2a1b3e2ac7342c9281ca57e889fd7d3a4e31  final-drive-v1/baseline-v1/direct-ts-parity
232cc5f76feb105230712afd902d0c053339a94051ed8c6910a4e79c388b90ec  final-drive-v1/baseline-v1/parity-session
```

The original CI archive and every `switch-reference/` entry in the full ZIPs were kept byte-identical in the comparison. `switch-reference/` is not automatically installed.

## Exact entry delta: full v1 -> full v1.4

Added:

```text
final-drive-v1/CENTERED_TEST_README.md
final-drive-v1/HMI_SAFEAREA_BINDING.md
final-drive-v1/MU1440_SAFEAREA_BAR.sh
final-drive-v1/SAFEAREA_BAR_README.md
final-drive-v1/TELEMETRY_HOTFIX_README.md
```

Modified:

```text
final-drive-v1/MU1440_FINAL_DRIVE.sh
final-drive-v1/PACKAGE-SHA256SUMS.txt
final-drive-v1/README-DE.md
final-drive-v1/SUPERVISOR_DELTA.md
final-drive-v1/runtime/parity_drive_supervisor.sh
```

All other archived entries unchanged. Script delta: v1.2 added temporary two-slot SafeArea, v1.3 removed QNX-incompatible `tr` from gate telemetry, v1.4 added optional `safearea-centered` only. The existing successful vertical reduced default remains `[0,58,1010,248]`.

## Promotion checklist

1. Import/review individual **text script** additions from the exact v1.4 staging ZIP against frozen source. Do not execute the original historical master installer on today's vehicle.
2. Preserve executable modes and file checksums, `ksh -n`, fail-closed guards and dependency/ownership semantics; regression-test stop/stock fallback.
3. CI-check package contents, all listed archive hashes and byte identity of pinned bridge/owner.
4. Test v1.3 telemetry correction and optional v1.4 centered geometry in the parked vehicle **separately** before claiming them vehicle-proven.
5. Do not publish private original camera clips, vehicle identity, raw host/network diagnostics or any third-party restricted binary through this documentation-only PR.
6. Do not merge the frozen v1 implementation into `main` blindly: at preparation time `main` and v1 are divergent, with the main-to-v1 compare showing 445 commits unique to v1 and 58 unique to main. Rebase/merge independently with CI and review.

See [status](../../docs/status/MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md) and [switch matrix](../../docs/testing/MU1440_FINAL_DRIVE_SWITCH_MATRIX_2026-10-11.md).