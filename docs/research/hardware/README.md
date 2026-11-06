# MMX, RCC, boot chain, clocks and read-only diagnostics

[Research library](../README.md) · [QNX safety contract](../../testing/MU1440_QNX_SHELL_COMPATIBILITY.md) · [Current feature status](../../status/FEATURE_STATUS.md)

**Scope and safety:** MU1440 MMX (Tegra/QNX) and RCC (Jacinto5) are **different boards**. The reports contain a mixture of live read-only observations, firmware-static reconstruction and untested hypotheses. **None of these reports authorizes clock/voltage/flash writes or confirms overclock stability.**

## Start with the consolidated study

- **[MU1440 Tegra T30 clocks, power and QNX timebase](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md)** — chronological R0–R14 index, measured baseline, remaining gates. Read this before individual R4–R14 reports.
- **[TegraDiag R1 offline-prepared kit](MU1440_TEGRADIAG_R1_OFFLINE_PREP_2026-10-12.md)** — host/mock preparation and validation limits, **not** a live QNX result.
- **[RCC Jacinto5 clock baseline R16](MU1440_RCC_JACINTO5_CLOCK_BASELINE_R16_2026-10-12.md)** — separate RCC source analysis; do not copy MMX assumptions to RCC.

## Tegra/QNX clock and memory evidence

- [R4 SKU and fuse](MU1440_TEGRA_SKU_STATIC_AUDIT_R4_2026-10-11.md)
- [R5 RAM_CODE / boot memory / clock separation](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md)
- [R6 MC error handler, not the memory governor](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md)
- [R7 QNX ASINFO RAM/imagefs](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md)
- [R8 startup script and PMU handoff](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md)
- [R9 clock initialization and Stage-2 IFS](MU1440_QNX_CLOCK_INIT_STAGE2_IFS_AUDIT_R9_2026-10-11.md)
- [R10 clock table / IFS loader](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md)
- [R11 nvclock frontend/backend](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md)
- [R12 original first-stage boot source](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md)
- [R13 CPU PLLX, qtime xrefs](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md)
- [MMX/RCC IOC and CAN access boundaries](MU1440_IOC_CAN_ACCESS_BOUNDARIES_2026-10-12.md)

## Original firmware packaging, NOR and recovery evidence

- **[Stage-1 OEM wrapper / NOR boundaries](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md)** — exact offline wrapper/repack evidence; not an endorsement of image flashing.
- **[R15 MMX native partition table and CRC](MU1440_MMX_FS0_NATIVE_PT_AND_STAGE1_HEADER_CRC_R15_2026-10-12.md)** — sample-specific flash layout and CRC evidence, with explicit unknowns.

## Interpretation and currency

Later R15 observations may close particular earlier unknowns (for instance original BCT/NOR scope), but **do not invalidate all R12 observations**. Follow the exact later reference cited by each report. An older study that has been refined remains a historical evidence record, not a current deployment instruction.

[Original firmware/portability research](../firmware/README.md) · [Research/archival rules](../AGENTS.md).
