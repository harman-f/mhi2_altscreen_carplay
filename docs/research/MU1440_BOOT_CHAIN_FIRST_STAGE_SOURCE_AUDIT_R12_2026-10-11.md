# MU1440 QNX First-Stage Startup and Tegra30 BCT Source Audit (R12, 2026-10-11)

**Issue:** [harman-f/mhi2_altscreen_carplay#37](https://github.com/harman-f/mhi2_altscreen_carplay/issues/37)  
**Target:** `MHI2_ER_SKG13_P4526_MU1440`, QNX 6.5 / Tegra30  
**Scope:** Issue phases 0–4; offline source inventory, extraction, and minimal static classification.  
**Historical R12 source-scope update:** The result below reflects the available update/Unit-export sources at this checkpoint. Later R15 analysis of a separate original MMX NOR backup identified BCT copies and the native partition map; see [R15](MU1440_MMX_FS0_NATIVE_PT_AND_STAGE1_HEADER_CRC_R15_2026-10-12.md). Neither finding proves the running unit's present flash image.

**Result:** The original QNX first-stage startup payload was identified and extracted from the exact MU1440 update. A Tegra30 BCT and SDRAM profiles were **not found or validated in the available sources**.

This is a static research result. No firmware was executed, and no live unit, flash, clock, EMC, or PMIC operation was performed. No overclocking was attempted. This audit does not authorize a clock change or vehicle test.

> **Later work (not part of the original R12-only evidence):** Follow the [consolidated CPU/overclocking research map](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md) and [R13 exact startup ARM/XREF analysis](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md) for direct proof of PLLX register reading, CCLK source selection and **initial** qtime CPU-rate/2 setup. The [separate exact OEM wrapper roundtrip/NOR audit](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md) and [Toolkit guide on `main`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) cover offline 3-MiB reconstruction. [R14 Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41) tracks outstanding original backup and voltage-source collection. The original R12 conclusion that **no validated BCT was found** remains unchanged.

## Executive findings

- The 106,760-byte QNX startup region is the `/memory/startup` span in the exact MU1440 first-stage image. It begins with a 256-byte `startup_header`; it is not uniformly executable code. The header-declared entry point and segment arithmetic validate against the R7 ASINFO bounds in both Stage-1 variants 50 and 70.
- Static markers place early PLL/clock and QNX timer/qtime setup plausibly in this startup. Instruction-level disassembly and register/XREF tracing have not yet established the source of `PLLX0=900 MHz` or the register path behind `qtime=450 MHz` / interrupt 27.
- The inspected full update archive has no standalone BCT-named member. The byte-identical Quickboot files are unvalidated selector candidates, not established BCTs. The inspected Unit filesystem export has no raw NOR/mNAND boot-storage image.
- No SDRAM profile table or mapping from physical `RAM_CODE=2` to an `SDRAM[n]` entry was recovered. In particular, this audit does **not** infer `SDRAM[2]`.

## Phase 0 — requirements and source reuse

The R5–R11 research records and the MHI2 firmware profile map were read before analysis. The existing corpus catalog, local-run registry, and MU1440 extraction closure were consulted. Analysis reused the successful indexed toolkit-r2 extraction; it did not create another firmware extraction tree.

The exact stock update archive was rehashed in place: 2,288,860,862 bytes, SHA-256:

```text
b23225d68999f0613f2652c898ce36c74d6c1d63a36f29ff5d4faf500c60e5a5
```

The archive, corpus, Unit export, and staging-source mappings are retained in the private handoff inventory. Public documentation omits local absolute paths, identifiers, and OEM binary contents.

## Phase 1 — candidate inventory

The complete archive listing contains the two Stage-1 members below, two Quickboot selector candidates, and later-stage material. No standalone BCT-named member was listed.

| Candidate | Package member | Bytes | SHA-256 | Assessment |
|---|---|---:|---|---|
| Stage-1 variant 50 | `MMX2/mifs-stage1/50/default/mifs-stage1.img` | 3,145,728 | `694c707035fea415842d222f2993e90aad69ca539c1b3608631bd8182ceffc6c` | Exact stock package member |
| Stage-1 variant 70 | `MMX2/mifs-stage1/70/default/mifs-stage1.img` | 3,145,728 | `511bdba0f12e8a7510930ca689f7a9020656c777b11301c7eb70176825f7af0a` | Exact stock package member |
| Quickboot primary | `MMX2/qb-primary/50/default/qb_primary.img` | 102,431 | `292870a4b5cf054f47b63f8de5d20f21bc4884645c1198f5c7a5a4cbc98c7000` | Opaque selector candidate; not validated as BCT |
| Quickboot recovery | `MMX2/qb-recovery/50/default/qb_recovery.img` | 102,431 | `292870a4b5cf054f47b63f8de5d20f21bc4884645c1198f5c7a5a4cbc98c7000` | Byte-identical to primary; not validated as BCT |

The independent Unit source is a filesystem export, not a raw boot-storage dump. Its `procnto-smp-instr` differs by hash from the Stage-1 variant-70 package file and is retained only as a separate provenance clue.

## Phase 2 — startup extraction and verification

The existing successful extraction run records the toolkit commit and decoder/module hashes in its manifest. The 6,841,260-byte decoded Stage-1 kernels and 6,734,492-byte inner ImageFS outputs were reused and copied to the private handoff. For each variant, kernel bytes `[0x1A110, end)` are byte-identical to its corresponding ImageFS. The common prefix `[0, 0x1A110)` is 106,768 bytes and is identical between variants.

The QNX startup region is kernel bytes `[0x8, 0x1A110)`, length 106,760, SHA-256 `9a7d54a69a5672cf13e532b262670b3ab4146d1e4d942b6cd2424a346a223b39`; both package variants contain identical bytes. Header fields were parsed using the QNX 6.5 `startup_header` layout documented by [QNX IPL documentation](https://get.qnx.com/developers/docs/6.5.0SP1.update/com.qnx.doc.neutrino_building/load_process.html) and the [QNX 6.5 `mkifs` image-layout reference](https://www.qnx.com/developers/docs/6.5.0SP1.update/com.qnx.doc.neutrino_utilities/m/mkifs.html). The file offset below is relative to the decoded Stage-1 kernel; header offsets are relative to the startup-header start at kernel offset `0x8`.

| Header field | Value | Header offset |
|---|---:|---:|
| `signature` | `0x00FF7EEB` (little-endian bytes) | `0x00` |
| `version` | `1` | `0x04` |
| `flags1 / flags2` | `0x01 / 0x00` (raw values) | `0x06 / 0x07` |
| `header_size` | `0x100` (256 bytes) | `0x08` |
| `machine` | `40` (`EM_ARM`) | `0x0A` |
| `startup_vaddr` | `0x80A06B40` | `0x0C` |
| `paddr_bias` | `0` | `0x10` |
| `image_paddr / ram_paddr` | `0x80A00808 / 0x80A00808` | `0x14 / 0x18` |
| `ram_size / stored_size` | `0x006863A4 / 0x006863A4` | `0x1C / 0x24` |
| `startup_size` | `0x0001A108` (106,760 bytes) | `0x20` |
| `imagefs_paddr` | `0` (IPL-populated field in the image) | `0x28` |
| `imagefs_size` | `0x0066C29C` (6,734,492 bytes) | `0x2C` |
| `preboot_size` | `8` bytes | `0x30` |

The eight bytes at kernel offset `[0,0x8)` are therefore the QNX boot prefix before the header, not part of the header or the declared startup entry. Header offset zero is kernel file offset `0x8`. Consistency checks pass for both variants: `startup_size + imagefs_size = stored_size`; `stored_size = kernel_file_size - preboot_size`; and the decoded ImageFS starts at kernel offset `0x1A110`, exactly `preboot_size + startup_size`. This is also R7's `/memory/startup` interval `0x80A00808–0x80A1A90F`, immediately followed by `/memory/imagefs` at `0x80A1A910`.

With `paddr_bias=0`, the header maps its declared `startup_vaddr` to startup-region-relative offset `0x80A06B40 - 0x80A00808 = 0x6338`. The corresponding original kernel file offset is `preboot_size + 0x6338 = 0x6340`; it is ARM-aligned and lies after the `0x100)-byte header and before `startup_size). In both variants, a read-only ARM-mode disassembly at that declared VMA begins with `mrs`, `bic`, `orr`, `msr`, and CP15 `mrc` instructions; subsequent instructions establish the initial stack and call a target inside the same startup region. This validates the header-declared executable entry, not every byte in the startup span.

QNX documents the bootable image as boot prefix, startup header, startup code/data, startup trailer, then image header/files. The available fields delimit the full startup region and the ImageFS boundary, but do not by themselves distinguish internal code, literal/data pools, and the startup-checksum trailer. Those internal sub-bounds remain unresolved here. No full-span disassembly is implied.

The variant-70 `/proc/boot/startup.script` is 4,828 bytes, SHA-256 `055fda81956df20d0a9b00e90a5590d9b85cec4c40d5579b68d10f5a74b84e20`; it matches the independent Unit-export copy and R8. This binary-encoded QNX script is distinct from the recovered first-stage startup code. The Unit-export `clock_init` is 12,894 bytes, SHA-256 `14f98073333c0ee6200384ae54f10e883213183ecf55a4c59bb27c0257439cda`, and matches the R10 evidence.

No firmware binary was run. The private handoff includes the exact package members, validated decoded files, startup-payload slice, the extraction script, inventories, and SHA-256 manifest. The multi-gigabyte archive remains in its catalogued source location rather than being duplicated.

## Phase 3 — minimal static classification

Static ASCII-marker locations in the decoded kernel are consistent with early clock and timer setup:

| Area | Kernel file offset |
|---|---:|
| PLL initialization marker | `0x13C68` |
| Clock-source detection marker | `0x13C74` |
| Clock/reset initialization diagnostics | `0x14CAF` |
| EMC initialization diagnostics | `0x14DE3` |
| Timer setup diagnostic | `0x15A7C` |
| qtime structure/diagnostic vocabulary | `0x1604C` |
| Timer validation diagnostic | `0x1682C` |

These are string-marker locations, not instruction addresses. They support the conclusion that early clock/PLL and qtime/timer setup plausibly reside in the startup region. The entry was decoded only to validate its location and ARM execution; the clock/timer routines have not yet had instruction-level XREF/call-graph analysis. The markers do not prove a particular PLL write, frequency, timer source, or execution path.

R10/R11 remain important boundaries: the later stock `clock_init` path directly invokes SCLK/HCLK/PCLK, while separate backend CCLK/EMC capability is not proof those handlers ran in the stock path. Neither record establishes the startup's exact `PLLX0` origin.

## BCT and SDRAM conclusion

**Status: NOT FOUND / NOT VALIDATED IN AVAILABLE SOURCES.**

The archive listing did not identify a standalone BCT. The two 102,431-byte Quickboot candidates remain opaque and identical; no BCT format, Tegra30 layout, or embedded BCT location was established. The inspected Unit export contains no raw NOR/mNAND boot-storage image. No `bct_dump` or `cbootimage` analysis was performed because no input was first validated as a BCT.

Consequently, no `SDRAM[n]` profiles, profile count, or RAM_CODE-to-profile binding can be reported. R5 identifies `RAM_CODE=2` as a physical strap selector; it does not identify which BCT SDRAM entry that selector chooses.

The next evidence gate is an already existing offline boot-storage backup or an authenticated OEM boot container that includes the MU1440 Tegra30 BCT and sufficient variant/layout metadata to validate its location. No live extraction is requested or attempted.

## R5–R11 context

- [R5 — RAM_CODE strap and boot-memory/CPU-clock separation](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md): RAM_CODE is bits [7:4] of the physical strap at `0x70000008`; value 2 is a selector, not proof of an `SDRAM[2]` profile.
- [R6 — nvmemctrl MC error-handler audit](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md): nvmemctrl handles memory-controller errors/interrupts, not SDRAM training or an EMC frequency governor.
- [R7 — QNX ASINFO startup/ImageFS layout](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md): supplies the exact startup and ImageFS RAM boundaries used above.
- [R8 — binary QNX startup-script audit](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md): distinguishes the binary `/proc/boot/startup.script` from later shell startup.
- [R9 — clock_init handoff and Stage-2 reservation](MU1440_QNX_CLOCK_INIT_STAGE2_IFS_AUDIT_R9_2026-10-11.md): documents the post-kernel clock_init handoff.
- [R10 — clock_init and IFS loader](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md): static clock-table findings; does not locate the first-stage PLLX0 origin.
- [R11 — nvclock API/backend audit](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md): separates API/backend capability from the stock initialization calls.

## Phase 4 — handoff and next work

The original package members and extracted startup evidence are stored only in the private research handoff. No proprietary bytes or local absolute paths are published in this repository. Its inventory includes source mapping, artifact class, sizes, SHA-256, copy checks, phase notes, and a reproduction script.

Useful next static work, if requested:

1. Disassemble the 106,760-byte payload and trace instruction/XREF paths around clock/reset, EMC, PLL, and timer/qtime initialization.
2. Reconcile any recovered timer setup with QNX `qtime.CPS=450,000,000` and interrupt 27, without inferring a timer source from strings alone.
3. Continue BCT analysis only after an exact offline BCT-bearing source and its container/layout metadata are located.

This documentation change does not alter any governed MU1440 control, default, HMI surface, runtime component boundary, or implementation.
