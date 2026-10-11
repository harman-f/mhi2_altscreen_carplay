# MU1440 R16 — separate RCC / TI Jacinto 5 CPU-clock research baseline (2026-10-12)

> **Source and safety boundary:** Read-only offline study of the privately supplied R14 original **RCC** 64-MiB fs0 archive, plus externally cited example bootlogs for a similar Harman MIB2 platform. No unit/vehicle access, clock adjustment, I²C/PMIC probe, original binary redistribution, NOR edit or stress test. A PLL/clock log from an *external unit* is NOT an observed operating frequency of the user's car.

**Start at [the consolidated CPU/clock/power overview](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md) for MMX/Tegra T30. This report covers a physically and logically separate processing domain, the RCC.** Separate raw imaging/boot structure: [R14 RCC Toolkit PR #7](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/7); independent MMX native PT/Primary mapping: [R15](MU1440_MMX_FS0_NATIVE_PT_AND_STAGE1_HEADER_CRC_R15_2026-10-12.md) and [Toolkit PR #8](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/8).

## 1. Exact original RCC evidence: not NVIDIA and not Jacinto 6 by default

R14 original complete `RCC_fs0.bin`: 67,108,864 B, SHA-256 `45c88eb7fa44a721c4eb1e95f57a3331e110a6756896b7639a66ac81471136d3`. Its separate Emergency and Root QNX startup programs explicitly contain **`PL_qnx_startup-jacinto5-v7`**, **`startup-jacinto5`** and **`Cortex A8`**, with independent original startup builds `Dev_MibJ5_13372A` (Emergency) and `Dev_MibJ5_16302A` (Root). This is direct exact-source family/CPU-core evidence; the separate MMX is Tegra T30 / four Cortex-A9 cores.

The early original RCC IPL (a separate boot component) includes:
- Format string **`CLK: %d/%d/%d MHz (ARM/DSP/DDR)`**. This means it has a three-domain boot-clock reporting facility; the raw binary does not contain the actual clock values reported by a live run.
- Revision selectors for `J5,PG1.x`, `J5,PG2.1`, `J5,PG3.0` **and** `J5eco,PG1.0` through `J5eco,PG2.1`. These are *multiple supported silicon-detection branches*; the existence of a string does not identify which chip/revision is fitted to this exact current vehicle.
- PLL-timeout diagnostics; existence of PLL initialization/detection code, **not** a reconstructed validated live clock setter or approved altered boot profile.
- Original Root QNX build embeds **`startup-jacinto5`** and the command fragments `0x87000000,0x01000000`, `750,0`, `-wa`; the command reported in *external example logs* is `-x 0x87000000,0x01000000 -C 750,0 -wa`. Do not misrepresent `750` alone as measured hardware MHz; it is a board-specific startup argument whose full semantics in the original build have not been decoded.

Exact original IPL SHA-256 for raw `[0,0x20000)`: `f1681fb45fd01c0b79559d9f18d71dc7a6dc5c6a032931c5feed155292c47a55`. The actual standalone IPL occupied-program boundary differs from this entire fixed-size sample span and remains separately unresolved.

## 2. Independent external corroboration — similar hardware, not exact car measurement

Public Harman MIB2 RCC boot logs describe **`J5,PG3.0`** with IPL `CLK: 720/600/400 MHz (ARM/DSP/DDR)`, followed by `PL_qnx_startup-jacinto5-v7_Dev_MibJ5_16302A` and `-C 750,0`. This closely matches the original R14 firmware family and demonstrates that the displayed **720 MHz ARM** and **750 startup argument** can coexist in one actual public boot trace. **Therefore neither value should be silently equated to this user's current RCC physical operating frequency**, and the startup CPU-info/timekeeping fields should be distinguished from genuine PLL readback.

- [Example Harman/J5 boot log, including all ARM/DSP/DDR frequencies](https://www.digital-eliteboard.com/threads/audi-mmi-mib2-mhi2-firmware-3634-3663-update-und-asi-apple-carplay-android-auto.480571/page-89)
- [Second Harman RCC boot trace/discussion](https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/discussions/218)
- [TI Automotive Infotainment Guide: DRA62x/DRA65x Jacinto 5 and their Cortex-A8/DSP/DDR architecture](https://de.farnell.com/wcsstore/ExtendedSitesCatalogAssetStore/cms/asset/images/europe/common/applications/automotive/pdf/ti-automotive-infotainment-guide.pdf)
- [QNX Jacinto5 ECO BSP lineage](https://community.qnx.com/sf/wiki/do/viewPage/projects.bsp/wiki/TiDra6xxDm811x?version=7). A matching BSP family is not sufficient to certify exact silicon grade, voltage or a speed ceiling.

## 3. RCC-specific feasibility, not an MMX TegraDiag port

The **RCC** is responsible for system/radio/low-level car interfaces, including diagnostics, timing-critical communications, audio/related DSP and watchdog/boot services. Thus extra CPU MHz would not automatically solve a multimedia CarPlay/VC-111 bottleneck, and an RCC restart could interrupt far more than visual frame presentation. It is separate from MMX/Tegra CPU, clock-controller, QNX startup and voltage/temperature measurement paths; the NVIDIA `/dev/nvclock` virtual devices are **NOT** an established RCC interface.

The already acquired original R14 RCC-side `Env` and `diagnosis` components contain board-voltage and mainboard/amplifier/FOT temperature reporting; this is not authenticated **Jacinto CPU-core VDD** telemetry. No validated register-level RCC voltage controller, active clock setter, runtime DVFS governor or safe live timebase retiming has been found. Underclocking/overclocking or reprogramming PLL/DSP/DDR/PMIC is **not** a next-step user test.

### An immediately worthwhile stock-only, read-only first measurement when convenient

Collect **on the RCC host itself**, as separately labeled output, if existing authorized read-only QNX access is available:
- `uname -a`; `pidin info`; `pidin syspage=cpuinfo`; `pidin syspage=qtime`: identify actual core count, QNX BSP build, **reported** CPU speed and installed system timebase.
- If already archived, capture original RCC IPL serial `IPL` and `CLK:` boot lines, motherboard/SKU/silicon-revision identifiers and the original startup `Command:` line; do not reboot merely to gather missing bootlogs.
- A small bounded read-only sample of `top`/`pidin` CPU/thread utilization and existing documented sensor getters, with Idle and normal-function context. Do not use arbitrary device/virtual-file writes or bring over the MMX TegraDiag getter paths.

**Interpretation guardrail:** QNX `cpuinfo.speed` can be a startup-declared rating, not independent voltage/PLL telemetry. The historical external IPL `720/600/400` and startup `-C 750,0` are different data channels. They cannot prove stock underclocking, available OC headroom, DSP/DDR PLL safety or that all involved clocks would track an ARM change.

## 4. Required offline prerequisites before judging RCC OC/UC viability

1. Obtain true silicon/board revision from existing live read-only ID or authenticated original board evidence; distinguish J5 vs J5eco and applicable TI datasheet/errata/approved OPP.
2. Recover exact original IPL's ARM/DSP/DDR PLL *read and initial write* data flow and clocksource/QNX timebase initialization for this specific original, **offline**, preserving branch and revision selection.
3. Identify actual *measured* core supply rail and temperature channels. Original `Env` mainboard/system voltage is not CPU VDD and generic MMX `1200` stub is irrelevant to RCC.
4. Establish the role of DSP, DDR and audio/MOST/radio/watchdog deadlines and baseline utilization: no benefit claim without a bottleneck measurement.
5. Separately confirm known-good RCC backup and recovery selection/behavior; never conflate RCC Emergency-IFS with MMX Recovery or assume either can unconditionally restore all failing early-boot paths.

**Current verdict:** **RCC independent CPU-clock research is technically well founded and ready for a read-only baseline**; the exact chip speed/actual stock clock, voltage envelope, PLL/QNX retiming and value of OC/UC remain OPEN. Prioritize a Jacinto5-specific *observer* rather than replicating the NVIDIA tuning tool or creating a persistent altered RCC image.
