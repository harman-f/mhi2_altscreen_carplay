# MU1440 Final Drive switch matrix (2026-10-11)

**Exact-target developer controls, not in-car HMI.** Original registry / installed master scripts are at the [frozen v1 source checkpoint](https://github.com/harman-f/mhi2_altscreen_carplay/tree/3a91204b6169eafcc525991fdf10c2aab3fb8d72/runtime/master). The Final Drive SD wrapper is a separate, volatile observational layer around those installed components. A ZIP being staged/offline-tested does not mean it has been installed or tested in the vehicle.

## Frozen runtime contract

- `/mnt/app/root/altscreen-u2/bin/alt111-settings` is the authoritative current registry.
- `/mnt/app/root/altscreen-u2/scripts/` contains the installed master wrappers; list presence with Final Drive `switches`.
- SD-only operator directory on the tested vehicle: `D=/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/final-drive-v1`.
- Volatile marker `/tmp/mibr-final-drive.enabled` controls the temporary Final Drive supervisor. `enabled=0` in the *persistent* parity-drive status is compatible with `final_drive_enabled=1`. No boot hook/profile is applied by this SD wrapper.
- Never use an old CI ZIP's historical master installer blindly over a vehicle with a different installed base; first verify the exact original bridge/owner SHA-256 listed in the [live status](../status/MU1440_FINAL_DRIVE_LIVE_STATUS_2026-10-11.md).

## Apply semantics

| Key/group | Example | Apply category / remarks |
| --- | --- | --- |
| `preset.id` | `mibr_legacy` | reconnect |
| `carplay.enabled` | `1` | session |
| `maxFPS` | `30` (experimental `40`) | reconnect; advertised ceiling, not measured source/display FPS |
| `sourceVersion` | `1005.8.1` | reconnect |
| `keyframe.mode` | `source_frames` | live |
| `keyframe.interval_frames` / `interval_ms` | `20` / `2000` | live; retain observed original baseline during comparison |
| `keyframe.showui`, `gap_recovery`, `latency_recovery` | `1` | live |
| `ownership.backend` | `writev_gate` | session; native stock fallback mandatory |
| `viewareas.enabled/count/initial` | `1/2/1` | reconnect |
| `viewarea.0/1` canvas and `safe.x/y/w/h` | below | reconnect |
| `viewarea.selected` | `0` full / `1` reduced | live **request**, never assume acknowledgment from the registry value |
| `display.widthPixels/heightPixels` | `1010/376` | reconnect |
| `navigation.url` | `auto` | presentation |
| `navigation.query` | `1` (was `0` stock) | presentation |
| `navigation.surface` | `base`, `map`, `instructioncard` | presentation |
| `navigation.ETA/speedLimit/compass` | `yes/no/user` | presentation; iOS app decides actual rendering |
| `navigation.maneuver` | `none/left/right/top` | presentation; wire URL `leftAligned/rightAligned/topAligned` |
| `presentation.suggested_urls` | `maps:/car/instrumentcluster/map` | reconnect |

The displayed values in `alt111-settings status` are the desired registry values, not by themselves proof of a negotiated `/info`, `showUI` completion or VC image.

## ViewArea preset inventory

All cases use only two advertised indices, never a third ViewArea:

| Operator selection | Index 0 outer/safe | Index 1 outer canvas | Index 1 SafeArea | Evidence |
| --- | --- | --- | --- | --- |
| `safearea-default` | `[0,0,1010,376]` | `[0,0,1010,376]` | `[0,58,1010,248]` | vehicle observed; `initial=selected=1` |
| `safearea-chinese` | unchanged | unchanged | `[202,16,606,344]` | comparator geometry; no pixel-equivalence guarantee |
| `safearea-centered` | unchanged | unchanged | `[202,58,606,248]` | optional v1.4 offline only; **not** the selected vehicle default |
| `safearea-full` | select index 0 | — | — | live selection request |
| `safearea-select` / `safearea-reduced` | select/prep index 1 according to script | — | — | selection must be checked visually |

Geometry preparation is fail-closed: parked/stopped Final Drive, no active owner/lock, native gate STOCK, CarPlay fully disconnected (`source` not streaming), verified native pair, expected two-slot profile, revision-checked temporary registry transaction. Reconnect for a fresh advertisement. The operator cannot add a runtime third view by naming index 2. After unit reboot the volatile default must be reapplied **before** the next CarPlay negotiation if the reduced initial view is desired.

## Navigation composition: observed useful setting

Current recommended observational setup (all TEMP):

```sh
H=/mnt/app/root/altscreen-u2/bin/alt111-settings
S=/mnt/app/root/altscreen-u2/scripts
"$H" batch --input - <<'EOF'
navigation.query=1
navigation.surface=base
navigation.ETA=yes
navigation.speedLimit=yes
navigation.compass=yes
navigation.maneuver=top
EOF
/bin/ksh "$S/gen2_nav_config.sh" apply
```

The installed tool reports `PRESENTATION_REFRESH_REQUIRED` when the batch changes presentation settings. The apply wrapper may report `runtime_result=QUEUED`; this is **not** an iOS acknowledgment. Do not repeatedly dispatch refresh during the drive.

The previously tested `right` form was logged in GEN2 `/info` as:

```text
maps:/car/instrumentcluster?showSpeedLimit=yes&showCompass=yes&showETA=yes&maneuverLayout=rightAligned
```

Changing only `navigation.maneuver` to `top` in the running vehicle produced an operator-reported visible movement of the Apple Maps arrival panel toward the middle. The resulting `topAligned` presentation has not been isolated under a full driving route. There is no independent ETA-center key.

Available shorthand preset names in the installed `gen2_nav_config.sh` are `stock`, `base-rich`, `base-right`, `base-left`, `base-top`, `map-rich`, `map-clean`, `maneuver-only`. Prefer explicit `alt111-settings` values for reproducible comparisons.

## Minimal parked operation

```sh
D=/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/final-drive-v1
H=/mnt/app/root/altscreen-u2/bin/alt111-settings

/bin/ksh "$D/MU1440_FINAL_DRIVE.sh" preflight
/bin/ksh "$D/MU1440_FINAL_DRIVE.sh" switches
/bin/ksh "$D/MU1440_FINAL_DRIVE.sh" safearea-status
/bin/ksh "$D/MU1440_FINAL_DRIVE.sh" start
/bin/ksh "$D/MU1440_FINAL_DRIVE.sh" status
# Visually confirm VC rendering and native fallback before driving.
# Stop only when safely parked, unit still on:
/bin/ksh "$D/MU1440_FINAL_DRIVE.sh" stop
# Require STOCK_CONFIRMED and STOP_PASS_NO_PERSISTENT_BOOT_OR_PROFILE_CHANGE
```

For a 40-fps *negotiation* experiment, clean stop first, disconnect CarPlay, set `maxFPS=40` TEMP, reconnect CarPlay and verify a **new** GEN2 `/info ready ... maxFPS=40` log, not just `configured_max_fps=40` in source telemetry. Restore `maxFPS=30` through another disconnected negotiation if comparison requires the frozen baseline. No SSH interaction while the vehicle is moving.

## SD package revision semantics

- **v1**: original pinned v1 owner/bridge, fail-closed temporary observational wrapper; installed vehicle-tested.
- **v1.2**: optional two-slot SafeArea preparation, original vertical reduced default; actual `initial=1` was observed.
- **v1.3**: `tr` removal from SD telemetry `gate_raw` formatting, offline-only; native media untouched.
- **v1.4**: optional centered reduced geometry, offline-only. No physical HMI/steering wheel button added.
- `switch-reference/` shipped inside local SD archive is reference material, not an automatic installer or statement about installed files.

Do not silently replace or promote the original v1 executables by staging a later script-only ZIP.