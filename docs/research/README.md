# Research index

This directory collects research that is useful to contributors before it becomes a vehicle-approved implementation.

> [!NOTE]
> Start with the [current research preview](CURRENT_RESEARCH_PREVIEW_2026-10-05.md). It summarizes the newest
> media/timing, HMI/menu and steering-wheel findings and clearly labels what is vehicle-proven vs static/design-only.

## CPU / Tegra clock and QNX timebase (exact MU1440; read-only)

- [R4: exact MU1440 libnvsku static audit](MU1440_TEGRA_SKU_STATIC_AUDIT_R4_2026-10-11.md) — confirms board-SKU wrapper only; speedo/fuse qualification remains open.
- **[R11: exact nvclock API front-to-backend and special-clock audit](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md)** — confirms QNX resource-manager proxy, 5 backend SCLK/CCLK/HCLK/PCLK/EMC CAR branches vs only 3 named stock-default calls, and outstanding PLLX0/PMIC/qtime gates. No live writes.
- **[R13 follow-up: original MU1440 /50/ Stage-1 OEM-exact unpack/repack, module map, SWDL integrity layers and NOR boundaries](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md)** — 3-MiB original OEM wrapper reassembled byte-identically, first-page CRC32 at 0x264 measured, harmless offline byte-differential re-decode passed; unknown outer integrity fields and actual NOR update path remain OPEN. [Full toolkit step-by-step](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/docs/mu1440-stage1-oem-roundtrip/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) (docs branch, protected main).
- **[R13: first-stage CPU-clock/PLLX read and QNX qtime /2 ARM XREF audit](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md)** — verifies CAR+0xE0 PLLX getter, CAR+0x20 CCLK policy selector and direct CPU-source-rate/2 initialization of qtime with interrupt 27. The original 900-MHz PLLX writer and safe dynamic retiming remain unresolved. Offline only.
- **[R12: exact MU1440 QNX first-stage startup extraction and Tegra30 BCT source audit](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md)** — identifies the original 106,760-byte Stage-1 startup payload by exact package bytes and R7 RAM boundaries; reports BCT/SDRAM profiles as not found in available offline sources. Static only; no live changes.
- **[R10: exact clock_init clock-table static audit and IFS-loader observation](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md)** — confirms clock-writing API and identical SKU2/SKU5 PLL tables with no direct PLLX0/PLLM0 record; reconciles 84-MiB IFS reservation with 74-MiB mounted image. Read-only research.
- **[R9: exact QNX clock_init handoff and Stage-2 84-MiB IFS reservation](MU1440_QNX_CLOCK_INIT_STAGE2_IFS_AUDIT_R9_2026-10-11.md)** — first confirmed post-kernel clock initializer call, driver ordering, exact ASINFO gap correlation and prioritized private clock_init binary audit. Research only.
- **[R8: binary QNX startup-script / PMU-I²C5 handoff audit](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md)** — actual boot command/argument order, mNAND clock vs SDRAM distinction, I²C5-before-power sequence and next-stage `/usr/sbin/startup.sh` target. Research only.
- **[R7: exact QNX ASINFO startup/imagefs and RAM-layout audit](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md)** — records 2,047-MiB QNX RAM mapping, 104-KiB startup region, 6.42-MiB imagefs, early SKU metadata and the next startup.script/boot-image acquisition gate. Read-only.
- **[R6: exact MU1440 nvmemctrl MC error-handler audit](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md)** — disassembly identifies MC IRQ/fault logging at 0x7000F000, not the RAM training/EMC frequency governor; redirects SDRAM profile work to the original early boot/BCT. Research only.
- **[R5: RAM_CODE physical strap and boot-memory/CPU-clock separation](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md)** — exact devg-nvsku ARM disassembly, 0x70000008 bits [7:4], RAM_CODE=2 selector, BCT/SDRAM investigation, nvmemctrl next target and boot-vs-runtime risk matrix. Research only; no clock-changing code.

- **[MU1440 Tegra T30 CPU clock, power, QNX Global Timer/timebase and Stream-111 load — consolidated research audit (2026-10-11)](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md)** — live four-core 900-MHz confirmation, industrial vs non-IT 1.4/1.3-GHz distinction, on-unit getter inventories, proprietary-binary fingerprint/ARM function-map without publishing vendor bytes, unresolved voltage/OPP and 450-MHz QNX timebase, controlled CP/VC performance A/B/C, corrected native-navigation-only Most20FPS scope and read-only next gates. **Research only: no validated overclock, no runnable clock-changing commands.**

## Current cross-topic preview

- [Current research preview — 2026-10-05](CURRENT_RESEARCH_PREVIEW_2026-10-05.md)
  - source-timestamp / AU / MPEG-TS design;
  - configurable frame/time keyframe policy;
  - DMDT vs vehicle-proven writev ownership;
  - dual ViewArea/SafeArea direction;
  - HMI settings registry;
  - menu/ViewHandler and steering-wheel findings.

## Native Wireless CarPlay (separate, experimental project)

- [Wireless research handoff](mhi2-native-wireless-2026-10/README.md) — one starting point for the October 2026 study.
- **[Firmware and iOS binary findings ↔ actual prototype source](mhi2-native-wireless-2026-10/FIRMWARE_SOURCE_CROSS_REFERENCE.md)** — module-by-module links to research and project-authored C/H/INC/tests.
- [Prototype source and publication review](mhi2-native-wireless-2026-10/prototype/README.md) · [source hash manifest](mhi2-native-wireless-2026-10/prototype/SOURCE_MANIFEST.tsv).

**Scope warning:** this Wireless bootstrap/session prototype is not vehicle-validated; it is independent of the vehicle-tested Stream-111 / Virtual Cockpit path below. Proprietary firmware binaries are not included.

## CarPlay / Stream-111 / control plane

- [Stream-111 protocol](STREAM111_PROTOCOL.md)
- [CarPlay cluster configuration index](CARPLAY_CLUSTER_CONFIGURATION_INDEX_IOS26_7_1_2026-10-01.md)
- [CarPlay cluster function / frontend-effect matrix](CARPLAY_CLUSTER_FUNCTION_FRONTEND_MATRIX_IOS26_7_1_2026-10-01.md)
- [iOS sender lifecycle](IOS27_SENDER_LIFECYCLE.md)
- [PlatformControl flight recorder](PLATFORMCONTROL_FLIGHT_RECORDER.md)
- [VC ViewArea state](VC_VIEWAREA_STATE.md)

## HMI / settings / input

- [MU1440 HMI menu and ViewHandler architecture](../architecture/MU1440_HMI_MENU_AND_VIEWHANDLER_ARCHITECTURE.md)
- [MU1440 steering-wheel / hardkey API](MU1440_BUTTON_INPUT_API.md)
- **[MU1440 wheel DSI / decoded vehicle evidence / Omonob Java bytecode / VC zoom video (2026-10-11)](keypanel/MU1440_WHEEL_DSI_AND_OMONOB_2026-10-11.md)** — distinguishes `updateKey2` from `updateEncoder2`, documents the public Omonob KEY38/39-only interception, and defines a passive next-step probe.
- [Sanitized physical key/encoder evidence matrix](keypanel/MU1440_CAPTURE_SANITIZED_MATRIX.tsv) · [updated raw-key mapping](../testing/MU1440_MFW_RAW_KEY_MAPPING.md).
- **[New actual 12-detent MU1440 five-int mapping](keypanel/MU1440_F902_FIVE_INT_ENCODER_CAPTURE_2026-10-11.md)** — right 4/40 ±1 and left 4/44 ±1; supersedes earlier warnings-only uncertainty; [offline read-only decoder](../../tools/decode_keypanel_f902.py).
- **[Primary: omonob/MHI2-Carplay-Maps (owner: omonob/QCDWJ) — exact MU1440/790 wheel-input correction and JAR patch options](keypanel/MU1440_OMONOB_MHI2_WHEEL_ENCODER_BINARY_PATCH_OPTIONS_2026-10-11.md)** — the relevant Free790 `CarPlayClusterControls.jar`, `updateEncoder2` gap, real 4/40 ±1 detents, Omonob core zoom worker and safe adapter strategy. Design only; no patch installed.
- [Ready-to-submit upstream issue draft for omonob/MHI2-Carplay-Maps](keypanel/OMONOB_MU1440_WHEEL_ZOOM_UPSTREAM_ISSUE_DRAFT_2026-10-11.md) — GitHub issue creation was denied by the current integration (403); **not posted upstream**.
- **[Separate comparator: yuedizhibo/MHI2Q-CarPlay-AltScreen (owner: yuedizhibo)](keypanel/MU1440_MHI2Q_ALTSCREEN_ZOOM_PORT_BINARY_PATCH_OPTIONS_2026-10-11.md)** — Audi MHI2Q/AUG22 absolute-magnification/pacing reference, **not** the Omonob MHI2 implementation or a compatible MU1440 binary.
- [Java / IBM J9 build notes](JAVA_J9_BUILD_NOTES.md)

Current status:

```text
menu/ViewHandler architecture        exact-target static + compile-only PoC
WidgetFactory injection              offline/build-proven, not vehicle-proven
steering-wheel ASL APIs              exact-target static
physical MFW press subset           vehicle-log mapped / isolated recheck
rotary five-int baseline           12 direct f902 events / offline-parsed
actual semantic zoom/focus path     OPEN / targeted map-versus-menu correlation
```

## Media / transport / comparator research

- [Comparator findings / non-portable traps](COMPARATOR_FINDINGS.md)
- [Omonob 790/791 artifact audit](OMONOB_790_791_ARTIFACT_AUDIT_2026-10-03.md)
- [Omonob 791 30-fps / 1-s IDR test plan](OMONOB_791_30FPS_1S_IDR_TEST_PLAN_2026-10-03.md)
- [Direct VC video path](../architecture/DIRECT_VC_VIDEO_PATH.md)
- [Keyframe recovery vehicle finding](../findings/KEYFRAME_RECOVERY_2026-09-27.md)

The newest parity/keyframe/ownership design is summarized in the
[current research preview](CURRENT_RESEARCH_PREVIEW_2026-10-05.md) and is intentionally marked unvalidated
until the next vehicle run.

## Firmware / platform portability

- [MU1440 stock reference](MU1440_STOCK_REFERENCE.md)
- [MU1440 GEN2 hook map](MU1440_GEN2_HOOK_MAP.md)
- [MHI2 firmware profile map](MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)
- [MHI2 patch portability estimate](MHI2_PATCH_PORTABILITY_ESTIMATE_2026-09-28.md)
- [MU1438 vs MU1440 comparison](MU1438_MU1440_OFFLINE_COMPARISON_2026-09-28.md)
- [Audi B9 compatibility lead](AUDI_B9_MU1438_COMPATIBILITY_LEAD_2026-09-28.md)
- [Cluster/display transport knowledge base](MIB2_CLUSTER_DISPLAY_TRANSPORT_KNOWLEDGE_BASE.md)
- [FPK firmware/control access](FPK_FIRMWARE_AND_CONTROL_ACCESS.md)

## Prior art and methodology

- [Public references](PUBLIC_REFERENCES.md)
- [Research method](../RESEARCH_METHOD.md)
- [Acknowledgements](../../ACKNOWLEDGEMENTS.md)

## Evidence rule

Please preserve this distinction when contributing:

```text
vehicle-proven
  !=
exact-target static
  !=
offline/build-proven
  !=
design/inference
```

A useful research result can be published before vehicle validation as long as its evidence class is explicit.
