# Configuration matrix — source-defined defaults (beta)

> Status: source-defined defaults inventory (reviewed 2026-11-05). This table describes **compiled presets and fallback values**, not a report of a live installed unit or a qualified three-profile beta ZIP. The registry and firmware profiles have since been integrated into public source, but the values below are not proof of what a target has stored or applied. Do not confuse the three CarPlay *presets* below with the three *firmware profiles* (Škoda MU1440, SEAT MU1409, SEAT MU1447).

## Reading this matrix

- **Default** means the value used when no higher-priority stored/temporary override applies. The 48 CarPlay settings come from [`settings/registry.json`](../../settings/registry.json) and use resolution order `temp > persistent > profile > compiled`. The actual active CarPlay preset and effective runtime value must be read from the target; this file does **not** declare which preset the new installer selects.
- Broker-owned navigation/other switches are a separate set of 13 durable values, defined in [`mibr_durable_switch.c`](../../modules/broker/source/mibr-control/mibr_durable_switch.c). A valid `mibr-platform-defaults.conf` entry may override their compiled default; an existing user-written switch file may then provide a different active value.
- **Apply** indicates the code's declared activation boundary, not proof that an operation is already effective on a vehicle. `session`, `reconnect`, `unit_reboot`, `presentation` and `live` must not be collapsed into a generic on/off claim. **RO** means read-only in the menu metadata.
- **Menu presence is not enablement.** The layout in [`standard-menu.txt`](../../tools/menu-editor/standard-menu.txt) controls order/visibility; it does not set the CarPlay or broker values. The checked-in standard menu currently has `brand=skoda`; brand-specific SEAT menu output still belongs to the future package assembly.

## A. CarPlay registry — all 48 source-defined settings

| Setting key | `classic_single_view` | `mibr_dual_view` | `mibr_legacy` | Apply | Menu classification | Runtime basename / field |
| --- | --- | --- | --- | --- | --- | --- |
| `preset.id` | `classic_single_view` | `mibr_dual_view` | `mibr_legacy` | `reconnect` | `advanced` | `mibr-carplay111-compat-profile` |
| `carplay.enabled` | `1` | `1` | `1` | `session` | `normal` | `mibr-carplay111-enabled` |
| `maxFPS` | `40` | `40` | `30` | `unit_reboot` | `advanced` | `mibr-carplay111-fps` |
| `sourceVersion` | `950.7.1` | `950.7.1` | `1005.8.1` | `reconnect` | `advanced` | `mibr-carplay111-sourceversion` |
| `keyframe.mode` | `source_frames` | `source_frames` | `source_frames` | `unit_reboot` | `advanced` | `mibr-carplay111-keyframes.conf / mode` |
| `keyframe.interval_frames` | `20` | `20` | `20` | `unit_reboot` | `advanced` | `mibr-carplay111-keyframes.conf / interval_frames` |
| `keyframe.interval_ms` | `2000` | `2000` | `2000` | `live` | `advanced` | `mibr-carplay111-keyframes.conf / interval_ms` |
| `keyframe.showui` | `1` | `1` | `1` | `live` | `advanced` | `mibr-carplay111-keyframes.conf / showui` |
| `keyframe.gap_recovery` | `1` | `1` | `1` | `live` | `developer` | `mibr-carplay111-keyframes.conf / gap_recovery` |
| `keyframe.latency_recovery` | `1` | `1` | `1` | `live` | `developer` | `mibr-carplay111-keyframes.conf / latency_recovery` |
| `ownership.backend` | `writev_gate` | `writev_gate` | `writev_gate` | `session` | `developer` | `mibr-carplay111-ownership.conf / backend` |
| `viewarea.selected` | `0` | `0` | `0` | `live` | `normal` | `mibr-carplay111-viewarea-selected` |
| `viewareas.enabled` | `1` | `1` | `1` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / enabled` |
| `viewareas.count` | `1` | `2` | `2` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / count` |
| `viewareas.initial` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / initial` |
| `viewareas.transition_ms` | `0` | `0` | `0` | `live` | `advanced` | `mibr-carplay111-viewareas.conf / transition_ms` |
| `viewarea.0.x` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.x` |
| `viewarea.0.y` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.y` |
| `viewarea.0.w` | `1010` | `1010` | `1010` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.w` |
| `viewarea.0.h` | `376` | `376` | `376` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.h` |
| `viewarea.0.safe.x` | `202` | `202` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.safe.x` |
| `viewarea.0.safe.y` | `16` | `16` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.safe.y` |
| `viewarea.0.safe.w` | `606` | `606` | `1010` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.safe.w` |
| `viewarea.0.safe.h` | `344` | `344` | `376` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.safe.h` |
| `viewarea.0.adjacent` | `0` | `1` | `1` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view0.adjacent` |
| `viewarea.1.x` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.x` |
| `viewarea.1.y` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.y` |
| `viewarea.1.w` | `1010` | `1010` | `1010` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.w` |
| `viewarea.1.h` | `376` | `376` | `376` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.h` |
| `viewarea.1.safe.x` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.safe.x` |
| `viewarea.1.safe.y` | `58` | `58` | `58` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.safe.y` |
| `viewarea.1.safe.w` | `1010` | `1010` | `1010` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.safe.w` |
| `viewarea.1.safe.h` | `248` | `248` | `248` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.safe.h` |
| `viewarea.1.adjacent` | `0` | `0` | `0` | `reconnect` | `advanced` | `mibr-carplay111-viewareas.conf / view1.adjacent` |
| `display.widthPixels` | `1010` | `1010` | `1010` | `reconnect` | `developer` (RO) | `mibr-carplay111-display.conf / widthPixels` |
| `display.heightPixels` | `376` | `376` | `376` | `reconnect` | `developer` (RO) | `mibr-carplay111-display.conf / heightPixels` |
| `display.widthPhysical` | `202` | `202` | `200` | `reconnect` | `developer` | `mibr-carplay111-display.conf / widthPhysical` |
| `display.heightPhysical` | `75` | `75` | `74` | `reconnect` | `developer` | `mibr-carplay111-display.conf / heightPhysical` |
| `display.uuid` | `b7e6c5a0-2222-4000-8000-000000000002` | `b7e6c5a0-2222-4000-8000-000000000002` | `b7e6c5a0-2222-4000-8000-000000000002` | `reconnect` | `developer` | `mibr-carplay111-display.conf / uuid` |
| `navigation.url` | `maps:/car/instrumentcluster/map` | `auto` | `auto` | `presentation` | `advanced` | `mibr-carplay111-url` |
| `navigation.query` | `0` | `0` | `0` | `presentation` | `normal` | `mibr-carplay111-nav.conf / query` |
| `navigation.surface` | `map` | `map` | `base` | `presentation` | `normal` | `mibr-carplay111-nav.conf / surface` |
| `navigation.ETA` | `yes` | `yes` | `yes` | `presentation` | `normal` | `mibr-carplay111-nav.conf / showETA` |
| `navigation.speedLimit` | `user` | `user` | `user` | `presentation` | `normal` | `mibr-carplay111-nav.conf / showSpeedLimit` |
| `navigation.compass` | `user` | `user` | `user` | `presentation` | `normal` | `mibr-carplay111-nav.conf / showCompass` |
| `navigation.maneuver` | `none` | `none` | `none` | `presentation` | `normal` | `mibr-carplay111-nav.conf / maneuverLayout` |
| `presentation.suggested_urls` | `maps:/car/instrumentcluster/map` | `maps:/car/instrumentcluster\|maps:/car/instrumentcluster/map\|maps:/car/instrumentcluster/instructioncard` | `maps:/car/instrumentcluster/map` | `reconnect` | `developer` | `mibr-carplay111-ui-urls.conf / urls` |
| `legacy.autodirect` | `0` | `0` | `0` | `session` | `developer` (RO) | `mibr-carplay-autodirect` |

## B. MIBR broker — all 13 durable switches

The compiled fallback values below are **shared source defaults**, not a claim that they override per-platform settings or an existing vehicle configuration. For firmware-dependent defaults the intended override location is `/mnt/app/root/mibr/config/platform/defaults.conf` (`capability=value`). The stored broker values belong to their owner-specific `mibr/config/` group paths after the M1 root migration. Older basenames in the table indicate legacy physical formats, not a second active writer.

| Capability / menu ID | Valid values | Compiled default | Stored file |
| --- | --- | --- | --- |
| `carplay_nav` | `on\|off` | `off` | `mibr-carplay-nav.conf` |
| `sd_log` | `on\|off` | `off` | `mibr-sd-log.conf` |
| `nav_line` | `dist\|street\|off` | `dist` | `mibr-nav-line.conf` |
| `nav_night` | `auto\|light\|dark` | `auto` | `mibr-nav-night.conf` |
| `nav_source` | `auto\|stock\|phone` | `auto` | `mibr-nav-source.conf` |
| `nav_display` | `side\|top\|both` | `side` | `mibr-nav-display.conf` |
| `nav_bottom` | `eta\|rtt` | `eta` | `mibr-nav-bottom.conf` |
| `nav_side` | `on\|off` | `on` | `mibr-nav-side.conf` |
| `nav_lanes` | `on\|off` | `on` | `mibr-nav-lanes.conf` |
| `safe_voll` | `Rectangle x,y,w,h` | `0,58,1010,248` | `mibr-safe-voll.conf` |
| `safe_wide` | `Rectangle x,y,w,h` | `200,58,590,248` | `mibr-safe-wide.conf` |
| `safe_center` | `Rectangle x,y,w,h` | `370,58,256,248` | `mibr-safe-center.conf` |
| `expert_mode` | `on\|off` | `off` | `mibr-expert-mode.conf` |

**Navigation distinction:** `carplay.enabled=1` enables the auxiliary CarPlay display in the registry, while the independent `carplay_nav=off` is the default for **phone-sourced route arrows**. Their presentation options (`nav_source=auto`, `nav_display=side`, `nav_side=on`, `nav_lanes=on`) are preconfigured but cannot cause phone-route arrows to become active by themselves.

## C. Menu entries without an independent default in A or B

These entries exist in the checked-in standard menu but do **not** have a one-to-one identical ID in the 48-setting registry or 13-switch broker table. Some are aliases or subcontrols of those registered settings (for example `expert.mode` corresponds to the broker's `expert_mode` capability); others are pages, actions, transient view controls or OEM/platform-dependent widgets. Do not infer `on`/`off` from their presence. Review the relevant HMI/owner implementation before claiming a default for any such control.

| Menu ID | Catalog type | Default status |
| --- | --- | --- |
| `nav_hints` | `page` | Layout only; not a value |
| `nav_demo` | `toggle` | No single compiled default in the two registries; inspect owner/firmware |
| `views` | `page` | Layout only; not a value |
| `view.follow` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `view.now` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `view.resync` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `view.area_voll` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `view.area_wide` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `view.area_center` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `view.sport` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `calib.image` | `toggle` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_voll.x` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_voll.y` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_voll.w` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_voll.h` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_voll.reset` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_voll.hint` | `hint` | Informational; not a value |
| `safe_wide.x` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_wide.y` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_wide.w` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_wide.h` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_wide.reset` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_wide.hint` | `hint` | Informational; not a value |
| `safe_center.x` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_center.y` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_center.w` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_center.h` | `number` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_center.reset` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `safe_center.hint` | `hint` | Informational; not a value |
| `advanced` | `page` | Layout only; not a value |
| `engine.type` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `menu.language` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `gps.demo` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `menu.load` | `action` | No single compiled default in the two registries; inspect owner/firmware |
| `expert.mode` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `scaling` | `page` | Layout only; not a value |
| `scaling.main.zoomFactor` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `scaling.cluster.zoomFactor` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `scaling.cluster.physicalSize` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `scaling.main.physicalSize` | `list` | No single compiled default in the two registries; inspect owner/firmware |
| `scaling.hint` | `hint` | Informational; not a value |
| `diagnostics` | `fixedpage` | Layout only; not a value |
| `version` | `fixedpage` | Layout only; not a value |

The menu catalog itself may also contain functions not in the checked-in default menu. Those are **available functions, not automatically visible options**; see [`function-catalog.json`](../../tools/menu-editor/function-catalog.json) and the menu editor's [format contract](../../tools/menu-editor/MENU_FILE_FORMAT.md).

## D. Legacy MU1440 installer reference, not common beta defaults

The current MU1440 developer `deployment/mu1440/install.sh` explicitly uses the `map-rich` navigation profile, prepares Auto-Direct persistence, and leaves the DisplayManager writer gate in STOCK as the fail-safe setting. The exact NavIgnore and Most20 JARs are supplied for this older reference path. This does not prove that the same startup behavior has already been bundled or exercised on either SEAT firmware.

A direct source check of `deployment/mu1440/install.sh` confirms that the **current MU1440 developer installer enables the persistent D2 keyframe policy** (`/mnt/app/root/mibr-alt111-keyframe-policy.enabled`) with a **1,000 ms watchdog and 1,000 ms minimum request gap**. Older installation prose saying otherwise was stale. This is the MU1440 developer reference behavior, not evidence that the unfinished multi-profile beta ZIP already installs it on SEAT.

## E. Required release-documentation checks

For the future single beta ZIP containing all three firmware profiles:

1. Derive an **installer README** with the effective chosen beta preset, common settings, firmware overrides, version/commit, and a concise summary of non-default/experimental options. Include this full matrix (or a byte-identical copy) under `docs/` inside the ZIP.
2. Verify that the shipped standard menu, every compiled Java/Broker fallback and each `mibr-platform-defaults.conf` used by an identified firmware agree with the declared defaults. Explicitly record overrides; **do not overwrite user-persisted settings without an intentional migration policy**.
3. Confirm all three firmware profiles are included. A missing or conflicting original `lsd.jxe` SHA-256 must fail profile selection; neither a successful host build nor this documentation is vehicle acceptance.
4. Validate the **actual staged and zipped artifact**, including QNX shell compatibility, inventories, SHA-256, runtime/README correspondence and source lineage, before making a test ZIP downloadable.

This page is a current-source inventory. The proposed centralized beta-default schema and executable release-time defaults-to-README generation are **not yet implemented** by this documentation-only change.
