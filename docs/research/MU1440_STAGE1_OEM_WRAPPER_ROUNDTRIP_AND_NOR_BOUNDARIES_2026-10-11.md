# MU1440 Stage-1 OEM wrapper offline roundtrip, SWDL module map and NOR-scope boundaries

**Date:** 2026-10-11. **Source classification:** exact-original offline /50/ wrapper+kernel; separate R12/R13 startup ARM analysis. **No vehicle work, flash or overclock attempted.** This document is a public, sanitized research handoff. It does not distribute original/modified OEM images, raw binary contents, personal private paths or executable clock patches. Research trail: [R12 source audit](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md), [R13 CPU/qtime XREF](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md), [issue #39](https://github.com/harman-f/mhi2_altscreen_carplay/issues/39). The corresponding firmware tooling source and detailed procedure are in the [Firmware Toolkit guide on `main`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) ([Toolkit PR #6 merged](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/6)).

**Navigation:** [Consolidated CPU/overclocking overview and R4–R14 research map](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md) → [R12 original startup](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md) → [R13 direct ARM PLLX/qtime proof](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md) → **this Stage-1 wrapper/NOR report** → [complete Toolkit unpack/repack guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) → [R14 existing-source data handoff #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41). The R14 task is **OPEN**; no exact-unit raw NOR boundary/voltage source has yet been certified by that handoff.

**R15 supplement, higher evidence than historical size similarity:** [Native original 64-MiB MMX PT, Recovery/Primary and exact /70/ installed correspondence](MU1440_MMX_FS0_NATIVE_PT_AND_STAGE1_HEADER_CRC_R15_2026-10-12.md). In archived BACKUP-SNAPSHOT-06 native PT (13 entries, 64 identical records), KERNEL_PRIMARY 0x760000..0xA60000 is the original OEM /70/ 3-MiB image **byte-for-byte except four transport magic bytes**; distinct 6-MiB KERNEL_RECOVERY begins 0x160000. Formerly opaque extended 0x7FC is now directly proven to be CRC32 of header bytes [0:0x7FC) calculated for the installed ANDROID! magic (including original OEM 50/70 normalized tests). Historical-only and UNKNOWN statuses in this earlier document are **superseded for this original archived source**, not for current-car identity, modified-image boot acceptance or actual flash erase geometry. [Toolkit PR #8](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/8).

## 1. Architecture: what lives where and what is built versus booted?

```text
OEM customer update archive (2,288,860,862 B; distribution only)
  └─ metainfo2.txt -> OEM SWDL module/variant selection, chunked checksums
     └─ MMX2/mifs-stage1/<50|70>/default/mifs-stage1.img  fixed 3 MiB payload
          ├─ 0x800-byte original custom extended wrapper header
          └─ zlib stream (variable compressed kernel_size; begins at outer 0x800)
               └─ decoded first-stage QNX kernel (6,841,260 B)
                    ├─ [0,8) preboot
                    ├─ [8,0x1A110) exact 106,760-B startup region
                    │    ├─ 256-B startup_header; entry decoded-kernel file offset 0x6340
                    │    ├─ mixed ARM code, data and literal pools
                    │    ├─ early CAR/PLLX read, CPU source selection and qtime init (R13)
                    │    └─ terminal QNX additive checksum word
                    └─ [0x1A110,end) ImageFS, separate additive checksum
     ├─ MMX2/mifs-stage2/... LZOZ/LZO1Z later stage (not the zlib Stage-1 wrapper)
     ├─ MMX2/app/...       separate raw QNX6 app filesystem
     ├─ MMX2/efs-*         separate QNX embedded filesystems
     ├─ MMX2/qb-*          opaque original quickboot candidates, not proven BCT
     └─ RCC/...            separate processing domain and flash/storage
```

No part of this map permits substituting an **outer file offset** for an **inner decoded-kernel offset**, a **startup virtual/physical RAM address** or a **physical NOR partition address**. Original update variants `50`/`70` have distinct full kernels/ImageFS: their 106,760-byte startup prefix alone matches by hash and bytes.

| Component type | The authoritative location for its exact files/logic |
| --- | --- |
| Archive inventory, variant selection and raw-member extraction | [Firmware Toolkit `tools/extract_firmware.py`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/tools/extract_firmware.py) |
| Custom Stage-1 first page, zlib decode, QNX bounds/ImageFS carve | [Firmware Toolkit `tools/android_image.py`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/tools/android_image.py) |
| Stage-2 different `LZOZ` framing and ImageFS | [Firmware Toolkit `tools/mifs_stage2.py`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/tools/mifs_stage2.py) |
| SWDL metadata audit for existing module payloads | [Firmware Toolkit `tools/metainfo2.py`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/tools/metainfo2.py) / [`tools/update_txt.py`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/tools/update_txt.py) |
| Detailed package→wrapper→QNX unpack/repack validation guide | [Toolkit guide, documentation branch](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/docs/mu1440-stage1-oem-roundtrip/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) |
| Early startup ARM clocksource/PLLX/qtime origin | [R13 instruction-level audit](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md) |
| Early bootstrap/BCT, exact original 50/70 source and QNX startup header | [R12](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md) |
| Measured historical MMX NOR partitions, not exact-unit guarantee | [Toolkit flash layout](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MHI2_FLASH_LAYOUT_AND_RECOVERY.md) |

## 2. Verified authentic OEM wrapper /50/ (not inferred from a synthetic fixture)

The user supplied original `mifs-stage1.img` is **3,145,728 bytes**, SHA-256 `694c707035fea415842d222f2993e90aad69ca539c1b3608631bd8182ceffc6c`: an exact R12 **variant-50** update member. It decodes to **6,841,260 bytes**, SHA-256 `2dc088bb719fcb42ec0f12260f1f3a451bd328bbf0cecdec3647f5f07cb703ba`. This is a different complete kernel from the R13 variant-70 first input; its startup span `[0x8,0x1A110)` is byte-identical to /70/ with SHA-256 `9a7d54a69a5672cf13e532b262670b3ab4146d1e4d942b6cd2424a346a223b39`.

| OEM outer offset | Observed item |
| --- | --- |
| `0x0–0x7` | `41 FF 44 FF 4F FF 44 FF` magic |
| `0x8` | compressed `kernel_size=2,984,374` (LE32) |
| `0x24` | `page_size=0x800`; actual zlib stream starts at file offset `0x800` |
| `0x260` | extra word `0x00000001`; meaning NOT established |
| `0x264` | extra word `0xFA04A09A`; **directly proven CRC32 of the compressed zlib stream** |
| `0x400` | extra word `0x00000675`; meaning NOT established |
| `0x7FC` | extra word `0x89513F41`; meaning/integrity policy NOT established |
| after original zlib bytes | 1,610 zero bytes to page boundary; then 157,696 `0xFF` bytes to `0x300000` |

The zlib stream begins `78 DA` and its SHA-256 is `d34d78358701275598d7f368bcaadcb034b0e897f03a7436623119915e029b8b`. Original /50/ ImageFS is **6,734,492 bytes**, SHA-256 `90142756958b1991b507a75628ee35cd7de386803b98253aedabd9ff318271cb`. The QNX startup and ImageFS **each** have an independent terminal additive checksum whose full LE32 word sum (including that terminal word) equals zero mod `2^32`.

## 3. Exact original, unmodified unpack→repack→fresh-unpack result

All work was local and offline on private copies. The recorded host runtime was Python **3.13.5** with linked zlib **1.3.1**. The exact original decoded **variant-50** kernel was zlib-compressed at level 1/6/9 and compared with the original wrapper stream:

| Level | Recompressed bytes | Fits fixed 3 MiB? | Exact OEM compressed stream? |
| ---: | ---: | --- | --- |
| 1 | 3,193,837 | **NO**, exceeds total module capacity by 50,157 B | No |
| 6 | 2,988,743 | Yes | No |
| **9** | **2,984,374** | Yes | **YES, byte-for-byte** |

With the unchanged, fully preserved original 0x800 first page plus OEM-matching compressed stream, observed 0x00 page fill and remaining 0xFF module fill, the **whole newly reconstructed 3-MiB outer image** was byte-identical to the original, SHA-256 `694c707035fea415842d222f2993e90aad69ca539c1b3608631bd8182ceffc6c`. Fresh independent decode restored all **6,841,260** original kernel bytes and both QNX checksum checks passed. This is a *stronger result than decoded-file equivalence*: it is exact outer OEM equality **in the measured runtime and specific source variant**, not a guarantee for arbitrary zlib versions, other variants or altered content.

### Controlled inert-byte differential study

A single **non-executable diagnostic ASCII** character was changed privately (`init_pllA` → `init_pllB`); this was not a PLL/CPU policy or instruction edit. The independent QNX startup checksum at kernel `0x1A10C` changed `0xDF031729 → 0xDF031728`. ImageFS remained byte-identical. The modified kernel recompressed to **2,984,373 bytes** and known outer fields were updated: `kernel_size` and the observed compressed-stream CRC32 `0xFA04A09A → 0x9FC6E736`. A fresh independent decode proved exactly the intended ASCII byte and checksum difference, original full ImageFS bytes and valid measured lengths/checks. The altered OEM-like wrapper is **private only, NOT boot qualified**, because outer fields at `0x260/0x400/0x7FC` and possible bootloader verification remain unresolved.

## 4. Distinguish five separate build/integrity stages

| Stage | Validation requirement | Proven vs unproven |
| --- | --- | --- |
| A: decoded QNX | header bounds, startup trailer and independent ImageFS additive checksum | Proven on original and inert offline test |
| B: zlib | exact decoded data, compressed stream length/EOF and size capacity | Proven on original and inert offline test |
| C: custom MIFS wrapper | correct original 0x800 page, `kernel_size`, CRC32 at `0x264`, observed zero/FF alignment; understand unknown extended words | Known fields validated; opaque words not established for modified-image acceptance |
| D: existing SWDL module tree | module/variant selection, `metainfo2.txt` FileSize and chunked `CheckSumN` SHA-1, directory `hashes.txt`, existing transaction integrity / signed prefix | Metadata helpers exist; **not** a proof of signed/accepted modified update |
| E: physical install/boot | unit-specific NOR partition table, actual logical-to-physical module routing, erase granularity, trusted stage loader, recovery | **NOT validated and no write attempted** |

Consequently a few altered *uncompressed* ARM bytes are NOT a few writable NOR bytes: zlib may change dispersed compressed bytes, length and package integrity fields. A complete **3-MiB logical Stage-1 module** is the sensible changed-artifact boundary; whether the installer writes an entire 3-MiB partition, smaller physical sectors or a full 64-MiB device is a distinct unproven target-specific question.

## 5. Physical NOR: what “full NOR flash” does and does not mean

Historical (not exact-MU1440-verified) G11 MMX NOR maps describe a 64-MiB device with a separate **`KERNEL_PRIMARY=[0x00760000,0x00A60000)` = exactly 3 MiB** and a distinct 6-MiB `KERNEL_RECOVERY` area. The actual original MU1440 Stage-1 wrapper is also 3 MiB. This strong numeric correspondence warrants a targeted *offline provenance check* against a genuine unit-specific raw partition table or trusted update-module transaction evidence. It is **not proof** that the precise unit uses this address, that modifying it is accepted, or that a full 64-MiB NOR image must or need not be physically erased. BCT, recovery/primary bootloaders, Stage-2, app, system and persistent data are distinct stages and must not be touched based solely on this size coincidence.

The external developer's statement that selecting a high *boot* frequency required a “full NOR flash” is evidence about that developer's available method/experience, **not a demonstrated universal container-format constraint**. Our present proof establishes an offline reconstructible Stage-1 image and independently checks its inner checksums; the physical updater remains unproven.

## 6. Why this matters for R13 CPU/qtime, without turning it into a clock patch

[R13](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md) found the original startup maps CAR, reads **`PLLX_BASE` (`CAR+0xE0`)**, selects an active CPU source through **`CCLK_BURST_POLICY` (`CAR+0x20`)**, and initializes the QNX timekeeping source as **selected CPU clock >> 1**, assigning **interrupt 27**. Original stock live readings are CPU/PLLX0 **900 MHz** and qtime **450 MHz**. A later PLLX change without coordinated qtime/Global-Timer handling could corrupt system time calculations; an early clock change is a *design hypothesis*, not a demonstrated safely executable procedure or a proven way to avoid boot risk. Original pre-QNX PLLX writer, legitimate OPP/PMIC voltage, timer relocation and exact physical boot acceptance are still UNKNOWN. No runnable clock edit, voltage/EMC/flash command or image is offered.

## 7. Next exact evidence gates (collection only; analysis in this project)

1. Validate the opaque outer fields `0x260/0x400/0x7FC` and any original stage-loader integrity/authentication checks from trusted **offline** boot-chain source; do not infer acceptance from an image that merely re-decodes on the host.
2. If second-variant generalization is needed, perform the same byte-exact no-change check against the exact original **/70/** 3-MiB wrapper, not just its shared startup.
3. Establish this unit's real MMX NOR/PT/primary-versus-recovery selection and actual SWDL module-to-partition routing from **existing non-invasive archives or authenticated source**. The historical G11 layout alone is insufficient.
4. Keep all OEM raw originals, local build outputs, full decompilations, temporary image fixtures and sensitive file paths private. Preserve a forensic manifest with hashes, tool versions and independent decoded crosschecks. Do not execute a firmware image or alter a running vehicle.
