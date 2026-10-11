# MU1440 NVIDIA Tegra 3 T30: CPU clock, QNX timebase, power management and Stream-111 load — research audit (2026-10-11)

> [!CAUTION]
> **RESEARCH ONLY — no clock-changing payload, installer, tuning recommendation, or validated overclock.**
> This report records read-only measurements of one exact Škoda/Harman MU1440 vehicle, independent external platform specifications, and offline static analysis of matching firmware components. Do not write to `/dev/nvclock/*set*`, `*change*`, clock/reset (CAR) register interfaces, PMU/I²C or `/dev/nvpower` on the strength of these findings. A successfully accepted PLL setting would not prove an approved silicon operating point, voltage margin, a valid QNX clocksource or recovery after a hang.

**Exact reference:** `MHI2_ER_SKG13_P4526_MU1440`; QNX Neutrino 6.5.0; NVIDIA Tegra T30 (`nVidia_Tegra2(T30)_Boards armle` BSP identification); four online Cortex-A9 cores; direct CarPlay Type-111 -> H.264 -> MPEG-TS -> MOST150 -> AID10-class Virtual Cockpit. **Status:** exact-target live/read-only + exact-target offline binary analysis + comparison literature + explicitly marked hypotheses. No overclock was attempted.

### R15 follow-up to the original clock/boot/packaging research (2026-10-12)

[Direct native original MMX fs0 /70/ Stage-1 and PT audit](MU1440_MMX_FS0_NATIVE_PT_AND_STAGE1_HEADER_CRC_R15_2026-10-12.md) **supersedes** the earlier historical-only Primary/Recovery geometry and the previously unknown outer header field at 0x7FC: exact original archived BACKUP-SNAPSHOT-06 PT directly establishes KERNEL_PRIMARY (3 MiB), separate KERNEL_RECOVERY (6 MiB), and the whole installed Primary equals the original /70/ SWDL module after only four transport-magic bytes differ. The installed 0x7FC word is directly CRC32(first 0x7FC bytes of ANDROID! header), confirmed on two installed kernels and both original OEM update headers after magic normalization. A separate original Recovery QNX kernel passes format/checksum checks. **This does not** identify the *current* vehicle's live NOR contents, authenticate a changed boot image, validate physical flash erase geometry, prove a recovery fallback, or solve safe live CPU voltage/qtime retiming. See [Toolkit source-detail PR #8](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/8).

**Independent domain:** [R16 RCC Jacinto-5 / Cortex-A8 clock baseline](MU1440_RCC_JACINTO5_CLOCK_BASELINE_R16_2026-10-12.md) now verifies from the private original RCC raw image that this board has its own J5 ARM/DSP/DDR clock chain, unrelated to MMX/Tegra `/dev/nvclock` telemetry. External matching-family bootlogs show `CLK: 720/600/400 MHz (ARM/DSP/DDR)` alongside startup `-C 750,0`; neither establishes a live reading or OC/underclock headroom on the current car. A separate RCC stock-only observer is the next evidence gate, not a port of the MMX tuner.

## Navigation and subsequent exact-target findings (R4–R14)

**Start here for the CPU/overclocking research.** Sections below preserve the original R0–R3 live/static evidence as recorded on 2026-10-11. The *later* source-specific studies extend it; a previously open question is not still open if a linked later audit has closed that particular point. Evidence labels remain distinct: stock vehicle-readout, original-binary/static, offline wrapper roundtrip, and NOT validated on a modified boot or live overclock.

| If you need to understand... | Read this exact source | Relation to this overview |
| --- | --- | --- |
| Measured stock 900 MHz, driver getters, 450-MHz qtime, temperature, generic NVIDIA parameter ceilings and CarPlay/VC load | **This consolidated R0–R3 report** | Original system baseline; 1.7-GHz library value is not a qualified operating point |
| Board SKU/RAM strap and why `RAM_CODE=2` is not a known BCT SDRAM profile | [R4 SKU](MU1440_TEGRA_SKU_STATIC_AUDIT_R4_2026-10-11.md), [R5 RAM_CODE](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md), [R6 memory-controller audit](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md) | Defines early boot/voltage/SDRAM uncertainty |
| Original RAM map, startup-script/PMU handoff and later `clock_init` chronology | [R7 memory map](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md), [R8 script](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md), [R9 handoff](MU1440_QNX_CLOCK_INIT_STAGE2_IFS_AUDIT_R9_2026-10-11.md) | Distinguishes first-stage startup, QNX script, post-kernel clock initialization |
| Exact post-kernel clock tables and the route from front API through daemon to Tegra clock backend | [R10 clock_init](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md), [R11 front/backend](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md) | Confirms real clock-control capability but not safe live CPU/voltage retiming |
| Location/provenance of the OEM first-stage startup and the absence of a validated original BCT | [R12 source audit](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md) ([PR #38](https://github.com/harman-f/mhi2_altscreen_carplay/pull/38)) | Exact original 50/70 106,760-byte common startup; BCT remains open |
| **Exact first-stage ARM instruction paths: PLLX read, CCLK selector and initial qtime = selected source / 2** | **[R13 ARM/XREF audit](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md)** ([PR #40](https://github.com/harman-f/mhi2_altscreen_carplay/pull/40)) | Directly resolves the original qtime *initialization* dependency; dynamic recalibration, original pre-startup PLLX writer and electrical safety remain open |
| Original **3-MiB Stage-1 wrapper**: formats, CRC, exact byte-identical original repack and inert one-byte offline test | [R13 packaging/NOR companion](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md) → [detailed Firmware Toolkit procedure on `main`](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) ([Toolkit PR #6 merged](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/6)) | Proves **offline reconstruction**, NOT modified image boot/SWDL acceptance or a required full-64-MiB flash |
| **Already prepared read-only stock logger and desktop comparison** (not yet target-run) | [TegraDiag R1 offline readiness / nine-test validation](MU1440_TEGRADIAG_R1_OFFLINE_PREP_2026-10-12.md) | A local script, parser, mock data and private kit exist; **not** a live overclock or voltage instrument |
| Existing private original Stage-1 variants, archived NOR provenance and **actual read-only CPU voltage source** still to collect | [R14 Codex data-only handoff, Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41) | Open collection task, **not** a completed NOR map, verified recovery, or CPU mV measurement |

**Recommended reading order:** current report → R10/R11 (runtime setter) → R12 (exact OEM startup) → R13 (instruction-level initial clock/timebase) → Stage-1 packing/NOR companion and Toolkit guide → R14 data handoff. The runtime setting and permanent boot-image approaches are different hypotheses; no modified image or overclock has been approved for vehicle use.

## 0. Read this first — what is actually proven

| Statement | Evidence class | Interpretation |
| --- | --- | --- |
| All four reported cores operate at **900 MHz** | **VEHICLE-PROVEN read-only**: `pidin info`, `pidin syspage=cpuinfo`, live `PLLX0=900000` kHz | This is not merely a label in firmware metadata. It is corroborated by the NVIDIA runtime clock getter. |
| The CPU-PLL exposes read and write namespaces, including `PLLX0` | **VEHICLE-PROVEN device enumeration** | Existence is not proof that arbitrary values are allowed/safe. No write was made. |
| The implementation library has a **1,700,000,000 Hz PLLX parameter value** | **EXACT-TARGET STATIC** | Generic software PLL parameter/ceiling; **not a verified chip rating, four-core OPP or approved overclock**. |
| Industrial-temperature T30 documentation describes a fixed NVIDIA-supported **900 MHz** CPU point | **EXTERNAL REFERENCE** (Toradex) | Consistent with, but does not alone identify, this particular Harman board's exact silicon grade. |
| **1.4 GHz** exists for certain *non-IT T30* configurations | **EXTERNAL REFERENCE** (Toradex) | Single-core maximum; non-IT quad-core peak is generally **1.3 GHz**, time/temperature limited. The MU1440 is **not thereby entitled to 1.4 GHz**. |
| QNX `qtime.cycles_per_sec=450,000,000` and `intr=27` | **VEHICLE-PROVEN read-only** | Strongly implicates ARM Cortex-A9 Global Timer clocked at a value coincident with `PLLX0/2`. Exact Harman clock-source/BSP behavior requires verification. |
| Voltage rises automatically on a `PLLX0` change | **UNPROVEN** | Cannot infer this from a clock setter, a live power daemon, or stubbed generic RM exports. |
| CPU saturation explains slight VC stutter | **NOT SHOWN** | Measured whole-system load was 35.9–42.2% with VC; individual realtime deadlines, media timestamps, MOST pacing, I/O jitter remain separate questions. |

This document intentionally distinguishes **measured 900 MHz**, **industrial nominal 900 MHz**, **non-industrial 1.4/1.3 GHz examples**, and **1.7 GHz in a generic library parameter block**. These four numbers must never be presented as interchangeable.

## 1. Provenance and publication boundary

### 1.1 Exact firmware and live command evidence

`uname -a` identified a QNX 6.5 Tegra T30 BSP (`nVidia_Tegra2(T30)_Boards`, `armle`). `pidin info` repeatedly reported:

```text
Processor1: Cortex A9 MPCore 900MHz FPU
Processor2: Cortex A9 MPCore 900MHz FPU
Processor3: Cortex A9 MPCore 900MHz FPU
Processor4: Cortex A9 MPCore 900MHz FPU
```

`pidin syspage=cpuinfo` independently reported `spd:900` for each processor. The hardware-facing virtual device returned:

```text
cat /dev/nvclock/get_source_clk_freq/PLLX0
900000
```

The latter is in kHz (900 MHz); `get_pll_status/PLLX0` returned `1`. No frequency-changing command was executed in this research sequence. The live processes included `devg-nvsku`, `devg-nvpower`, `devg-nvclock -v 1`, `devg-nvrm`, `devg-nvtmon`, `nvmemctrl`, `devg-nvcapture` and other stock services.

### 1.2 Private, matching original binaries — identifiers only

The following proprietary Harman/NVIDIA binary **bytes are not published**. Analysis used private originals copied read-only from the live reference unit to SD, then independently compared by SHA-256. Reuploaded clock copies were byte-identical.

| Original target path | Size (bytes) | SHA-256 |
| --- | ---: | --- |
| `/sbin/devg-nvclock` | 27,380 | `8c9296f0feecb500dc5864a90731ab0c8c7bed1c46bbcc4b1a31485edcfdc197` |
| `/lib/libnvclockapi_impl.so` | 81,920 | `ad4a1e25559b1d9527d8c6491bc7ebecf7a98a1d0a6d3d79859b0be487731db0` |
| `/sbin/devg-nvpower` | 28,389 | `ec8eb075996980aa591a13299d1150912b2279613bb4ed1136cf6d4e29fee460` |
| `/lib/libnvrm.so` | 53,248 | `357e1bf056f16af0205036da33c8c2c5a2d2d5a182c44515c876ba89b6bb0887` |

All four supplied objects are stripped, dynamic ARM32 ELF / QNX-compatible images. `/lib/libnvsku.so` exists (8,192 bytes) but has **not** been collected/analyzed in this round. Do not imply otherwise. Archive dates of 1980 on SD are filesystem timestamp artifacts, not proof of different binary content.

## 2. Tegra T30: industrial vs other speed grades

**SoC family:** NVIDIA Tegra 3 / T30, four primary Cortex-A9 CPUs in the live QNX configuration. Tegra 3 product descriptions often also refer to an auxiliary low-power companion/shadow core; its presence in marketing does not mean `pidin` exposes five symmetric online application CPUs. QNX reports four here.

**Critical differentiation from documented third-party T30 modules, not identification of the Harman board:**

| External product/specification | CPU operating point | How it may be used here |
| --- | --- | --- |
| NVIDIA-supported industrial-temperature T30 according to Toradex platform note | Fixed **900 MHz** for primary CPU cores; slow/fast process examples use different CPU voltages; GPU 484 MHz, DDR 625 MHz | A credible explanation of the observed 900/484 pattern. Exact MU1440 chip grade, fuses, voltage and temperature qualification are still open. |
| Toradex non-IT Apalis/Colibri T30 | Up to **1.4 GHz single-core**, **1.3 GHz peak quad-core**, with time/temperature restrictions | A different graded/module/BSP configuration, not a guaranteed MU1440 four-core speed. |
| Toradex IT Linux implementation examples | Product/BSP-specific limits may differ (e.g. Colibri T30 IT 1.0 GHz in Toradex DVFS documentation) | Emphasizes that vendor-approved OPP and board policy matter. Does not override the fixed NVIDIA industrial point above. |
| MU1440 software `PLLX0` parameter block | 1.7 GHz value | A generic frequency parameter, not electrical/thermal/silicon validation. |

Sources: [Toradex T30 temperature / industrial operating points](https://developer.toradex.com/windows-ce/knowledge-base/apaliscolibri-t30-temperature-monitoring/); [Toradex CPU Frequency and DVFS](https://developer.toradex.com/software/linux-resources/linux-features/cpu-frequency-and-dvfs-linux/); [Apalis T30 datasheet](https://docs.toradex.com/101024-apalis-t30-datasheet.pdf).

Toradex's industrial reference explicitly lists CPU 900 MHz; example industrial `VDD_CPU` values **1.007 V (slow)** and **0.916 V (fast)**, `VDD_CORE` 1.25 V, GPU 484 MHz and RAM 625 MHz. **Those voltages are not measurements on the Harman unit; do not apply them as settings.** No physical silicon part marking, speedo/fuse classification, PMIC rail measurement or automotive-specific OPP authorization has yet been obtained. The observed `sku=0001` / board metadata alone do not conclusively decode industrial grade. In particular: "**T30 can do 1.4 GHz**" is an incomplete specification and "**this unit should run at 1.4 GHz**" is unsupported.

## 3. Exact-target runtime clock inventory (read-only)

The filesystem under `/dev/nvclock` is a QNX virtual resource-manager API, *not* ordinary files or sysfs. Node names are method-like, and a filesystem permission bit alone does not establish safe API semantics. Snapshot values:

| Getter | Live output | Meaning / caveat |
| --- | ---: | --- |
| `get_source_clk_freq/PLLX0` | `900000` kHz | Actual driver CPU PLL readback |
| `get_pll_status/PLLX0` | `1` | Reported PLL status; exact enum not reconstructed |
| `get_device_clk_freq/G3D` | `484000` kHz | Configured GPU clock, **not utilization** |
| `get_device_clk_freq/G3D2` | `484000` kHz | Configured GPU clock, not utilization |
| `get_device_clk_freq/VDE` | `484000` kHz | Video decode clock, not decoder busy time |
| `get_device_clk_freq/MPE` | `484000` kHz | Multimedia clock |
| `get_device_clk_freq/G2D` | `484000` kHz | 2D clock |
| `get_device_clk_freq/HOST1X` | `242000` kHz | Host/display-related clock |
| `get_source_clk_freq/PLLM0` | `750000` kHz | Reported memory-source PLL |
| `get_source_clk_freq/PLLM1` | `375000` kHz | PLLM output |
| `get_device_clk_freq/EMC` | `750000` kHz | Reported EMC device getter |
| `get_max_device_clk_freq/EMC` | `625000` kHz | **Inconsistent with 750000 current getter**; unresolved |
| `get_max_device_clk_freq/G3D/G3D2/VDE/MPE` | `484000` kHz | Driver-reported limits |
| `get_max_device_clk_freq/HOST1X` | `242000` kHz | Driver-reported limit |
| `/dev/nvtmon/current` | `046` then `053` then `054` | Samples in °C; not a calibrated thermal soak test |
| `/dev/nvtmon/current_local` | `041` | Local sensor sample from earlier snapshot |
| `/dev/nvtmon/status` | `0` | Exact meaning not verified |

One must **not** call the 750 MHz EMC readback a proven RAM overclock. In particular the driver can expose PLL outputs, module clock policy and memory timing through different mechanisms; current-vs-max discrepancy requires BCT, descriptor and `nvmemctrl` investigation. Likewise 484 MHz GPU readback is not a claim of maximum GPU **load**.

Four short repeated samples with normal CarPlay showed unchanged `PLLX0=900000`, `PLLM0=750000`, `G3D=484000`, `VDE=484000` and `EMC=750000` at `053` °C. A later CP+VC reading showed `054` °C, with `pidin info` and PLLX getter still at 900 MHz. No frequency drop was observed in these samples; this does **not** establish long-duration thermal stability or overclocking headroom.

### 3.1 Discovery of setter nodes (enumeration, never execution)

The device tree exposes `set_pll_frequency/PLLX0`, `set_max_pll_frequency/PLLX0` and `change_pll_param/PLLX0`, as well as corresponding entries for many PLLs and per-device setters such as `set_device_frequency/G3D` and `set_device_frequency/EMC`. `change_pll_out_param` has no observed PLLX0 node. The actual read-only enumeration used:

```sh
for x in set_pll_frequency set_max_pll_frequency change_pll_param change_pll_out_param set_device_frequency set_max_device_frequency; do echo "=== $x ==="; ls -l /dev/nvclock/$x; done
```

**Do not issue writes**, including an apparently harmless write of the current 900 MHz value or to `set_max_*`. The latter is proven by static control flow to reach hardware-affecting code. No supported user-facing setter syntax, units, or voltage contract has been validated.

## 4. Static reverse engineering: `devg-nvclock` wrapper

The 27,380-byte daemon is a QNX Resource Manager that exposes the `/dev/nvclock` virtual namespace. It imports hardware API entry points implemented in `libnvclockapi_impl.so`, including:

- `NvQryClockGetSourceClockFreq` / `NvQryClockGetDeviceClockFreq`;
- `NvQryClockSetPLLClockSrcFreq` and `NvQryClockSetMaxPLLClockSrcFreq`;
- `NvQryClockConfigurePLL`;
- `NvQryClockCarRegRead` / `NvQryClockCarRegWrite` (potentially direct register access).

**Offline ARM disassembly anchors** (addresses refer to the original matched ELF; a relocated/runtime address can differ):

| Wrapper address | Observed action |
| --- | --- |
| `0x102b54–0x102bb4` | Write handler tokenizes numeric input via `strtol`/`strtoul` and invokes `NvQryClockSetPLLClockSrcFreq`. Full argument/units contract still open. |
| `0x102b48–0x102b50` | Invokes `NvQryClockSetMaxPLLClockSrcFreq`. |
| `0x102bcc–0x102cbc` | `NvQryClockConfigurePLL` write variants. |
| `0x1031c0–0x1031c8` | Source-frequency read dispatch. |
| `0x1031a8–0x1031bc` | Device current and maximum getter dispatch are distinct. |
| `0x1031cc–0x1031d8` | `clock_tree` getter invokes `NvQryClockPrintDeviceClockTree` and returns a numeric response. |
| `0x1030ec–0x103174` | Common read response formats a short numeric buffer. |

On this unit `cat /dev/nvclock/clock_tree` displayed `0`; an output file contained 10 bytes. The wrapper suggests this is the print routine's return value rather than a serialized clock tree. The target shell lacks the usual Linux conveniences `od`, `hexdump`, `xxd`, `hd` and `busybox`; do not require them in vehicle-only diagnostics.

**Later implementation trace:** [R11](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md) independently follows the exact `clock_init → libnvclockapi.so → /dev/nvclock → devg-nvclock → libnvclockapi_impl.so` front-to-backend route and separates the default stock SCLK/HCLK/PCLK calls from possible CCLK/EMC backend handlers. [R10](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md) documents the original default clock table. These facts establish write-capable code paths, not an approved CPU tuning or automatic voltage/qtime adjustment.

## 5. Static reverse engineering: `libnvclockapi_impl.so`

The 81,920-byte implementation library contains a concrete, hardware-affecting PLL control path. Key exported routines:

| Export | Virtual address | Approx. size |
| --- | ---: | ---: |
| `NvQryClockCarRegRead` | `0x35c0` | direct CAR accessor |
| `NvQryClockCarRegWrite` | `0x35e4` | direct CAR accessor |
| `NvQryClockGetMaxDeviceClockFreq` | `0x5138` | `0xe8` |
| `NvQryClockInitClockModule` | `0x7338` | `0x698` |
| `NvQryClockGetSourceClockFreq` | `0x79d0` | `0x120` |
| Internal PLL configurator | `0x8128` | multiple branches |
| `NvQryClockSetMaxPLLClockSrcFreq` | `0x88b0` | `0x30c` |
| `NvQryClockSetPLLClockSrcFreq` | `0x8bbc` | `0x330` |
| `NvQryClockConfigurePLL` | `0x8eec` | `0x35c` |
| `NvQryClockGetDeviceClockFreq` | `0x94dc` | `0x11c` |
| `NvQryClockSetMaxDeviceClockFreq` | `0xa6a8` | `0x3b8` |
| `NvQryClockSetDeviceClockFreq` | `0xaa60` | `0x3ac` |

### 5.1 PLLX descriptor and 1.7-GHz interpretation

The `PLLX0` source descriptor is at virtual `0x12560` (ELF file offset `0x11560`), name pointer `0x0000daf0`. Descriptor flags at `+0x18` are `0x00040040`. Its PLL parameter-block pointer at `+0x7c` resolves to virtual `0x139c8` (file `0x129c8`). First and seventh 32-bit words in that block both encode `1,700,000,000`; subsequent observed entries include `2,000,000`, `31,000,000`, `1,000,000`, `6,000,000`, `20,000,000` and `300`. Full struct semantics are not fully reconstructed.

The internal configurator dereferences the per-source parameter block; one branch directly compares a requested frequency against its first word. Thus there is a substantive software parameter/constraint, **not** evidence that an IT-grade component is approved for 1.7 GHz or that the voltage automatically follows. A search for the simple literal 900,000,000 Hz in this library did not find it; its source could instead be boot-time initialization, module/board configuration, fuse/OPP policy, or computed logic.

### 5.2 Why the live setter is not a harmless experiment

`NvQryClockSetPLLClockSrcFreq` (`0x8bbc–0x8eeb`) validates source/request parameters, looks up the descriptor, checks flags, enumerates dependent active clocks, temporarily saves/reconfigures consumer source/divider information, enters the internal PLL configurator (`0x8128`), and restores affected consumers. This is a real clock-tree reconfiguration path.

`NvQryClockSetMaxPLLClockSrcFreq` (`0x88b0–0x8bbb`) **also** reaches the same internal configurator. It is not an isolated software setting. The generic implementation is considerably more sophisticated than a naïve direct CAR register write, but external timing/voltage guarantees are not demonstrated.

**Follow-up provenance:** [R8](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md) documents the original early `/dev/i2c5` handoff, and [R14 Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41) requests only already available original sources for a genuine *read-only* VDD_CPU measurement. The generic compiled `1200` return remains a stub constant, **not** measured voltage. No over-/undervolting path has been validated.

## 6. Power management: daemon versus stubbed Resource Manager

`/sbin/devg-nvpower` (28,389 bytes) runs with no additional visible command-line arguments; a `pidin -p <pid> mem` snapshot had one thread and listed `libnvsku.so`, `libc.so.3` and `libm.so.2`, **not** `libnvclockapi_impl.so` or `libnvrm.so`. Static strings/control flow expose an I²C-facing PMU facility (binary defaults refer to `/dev/i2c5` and slave `0x5a`, not yet verified as the active board PMIC) and a configurable, optional `nvpm` CPU-management path referencing `/dev/nvt3pwr`.

Live `/dev/nvpower` enumeration:

| Node | Permissions in snapshot | Caution |
| --- | --- | --- |
| `init_lp_state` | read-only | Low-power state result |
| `lp_mode` | read-only | Low-power mode |
| `nvpm` | read/write | Not evidence that optional NVPM controller is running |
| `sata_pcie` | read/write | Potential hardware effects |

`/dev/nvt3pwr` **does not exist** on this running reference unit. Together with the bare daemon command and one-thread snapshot, this argues against the optional NVPM CPU-control mode being active; it does not prove no separate board-specific voltage path exists. Unknown RW pseudo-nodes must not be probed by trial writes or assumed passive reads.

`/lib/libnvrm.so` (53,248 bytes) exports many generic NVIDIA names, but **this exact compiled image** contains substantial stubs:

| Symbol | Address | Static behavior |
| --- | ---: | --- |
| `NvRmPmuSetVoltage` | `0x81c4` | Tiny stub; no evident device/I²C access |
| `NvRmPmuGetVoltage` | `0x81d4` | Returns hard-coded **1200** through output pointer — **NOT a measured live CPU voltage** |
| `NvRmPmuGetCapabilities` | `0x81e4` | Fixed parameter structure |
| `NvRmDfsSetCpuEnvelope` | `0x8284` | Constant return |
| `NvRmDfsSetTarget` | `0x828c` | Constant return |
| `NvRmDfsSetState` | `0x829c` | Constant return |
| `NvRmDfsGetClockUtilization` | `0x82a4` | Constant return |

Do not describe the mere existence of `NvRmPmu*` or `NvRmDfs*` exports as validated DVFS on this QNX image. In particular, the `1200` constant must never be promoted to an actual measured CPU voltage.

**Subsequent instruction-level resolution of initial setup (R13):** [the exact original first-stage ARM/XREF audit](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md) directly traces `CAR+0xE0` PLLX read, `CAR+0x20` CCLK source selection and `qtime.cycles_per_sec = selected CPU source rate >> 1` with interrupt 27 during **boot initialization**. The stronger R13 result supersedes any implication below that the /2 dependency is based on numerical coincidence alone. **It does not demonstrate atomic dynamic timer recalibration after a live PLL change**, nor the early writer responsible for initial PLLX=900 MHz. See also [R12 OEM source provenance](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md).

## 7. The most important blocker: QNX `ClockCycles()` / A9 Global Timer

`pidin syspage=qtime` reported:

```text
Section:qtime offset:0x00000158 size:0x00000060
boot:00000000 CPS:000000001ad27480 rate/scale:2222222222/-18 intr:27
flags:00000003 load:450000 epoch:1970 rr_mul:0 adj count/inc:0/0
```

`0x1ad27480` is **450,000,000 cycles/second**, exactly `900 MHz / 2`. The ARM Cortex-A9 MPCore TRM documents the **Global Timer** (counter clocked by PERIPHCLK) as banked interrupt **ID27**, whereas the Private Timer uses **ID29**. This congruence of independent observations is strong evidence that the active QNX timebase uses the A9 Global Timer. What remains unverified is the precise Tegra/Harman `PERIPHCLK` mux/divider and whether QNX startup/kernel coordinates a runtime PLLX change.

Sources: [ARM Cortex-A9 MPCore TRM](https://developer.arm.com/documentation/ddi0407/h/); [QNX 6.5 ClockCycles reference](https://qnx.com/developers/docs/6.5.0SP1.update/com.qnx.doc.neutrino_lib_ref/c/clockcycles.html); [example A9 Global Timer clocking in Xilinx BSP](https://github.com/Xilinx/embeddedsw/blob/master/lib/bsp/standalone/src/arm/cortexa9/xtime_l.h) (**other SoC, illustrative only**).

**Conditional failure model (NOT an observed test):** If a 900 -> 1200 MHz CPU switch also drives Global Timer 450 -> 600 MHz while `qtime.cycles_per_sec` remains at 450 MHz, `ClockCycles()`-based durations would be scaled by `600 / 450 = 4/3`. Thread deadlines, sleep/timers, system clock accounting and source/media time conversions could become incorrect even if the processor initially runs. Whether and how these exact QNX/Harman paths adapt is unknown. An in-process rollback watchdog cannot be relied on after a CPU/clocksource/kernel hang.

A stock-only monitoring tool can verify clocksource consistency without changing clocks, but **must not claim to establish dynamic-change safety by observing the stock value**. Offline BSP/startup inspection and independent recovery design remain required.

## 8. CarPlay/VC workload evidence — three distinct states

Same 900-MHz reference unit, `top` percentage of *total four-core capacity*, human-observed workload. These are snapshots, **not controlled frame-to-frame profiling or proof of monotonically increasing demand**:

| State | User | Kernel | Total busy | Available RAM | Processes / threads |
| --- | ---: | ---: | ---: | ---: | ---: |
| A. Stock, no CarPlay | 7.5% | 1.6% | **9.1%** | 769 MB | 131 / 2193 |
| B. Normal CarPlay, **main display only** | 14.2% | 6.3% | **20.5%** | 721 MB | 131 / 2260 |
| C1. Normal CarPlay **plus active Stream 111 to VC** | 26.8% | 9.1% | **35.9%** | 717 MB | 140 / 2268 |
| C2. Still CP + Stream 111 | 31.1% | 8.8% | **39.9%** | 717 MB | 140 / 2268 |
| C3. Still CP + Stream 111 | 26.2% | 16.0% | **42.2%** | 717 MB | 139 / 2268 |

Interpreting B versus A: +11.4 percentage points from normal CarPlay in these snapshots. C1 versus B: +15.4 points for the combined added VC workload. C3 versus B: +21.7 points; do not present variation between C1–C3 as a time-trend or as the isolated remuxer cost. The last reading had core idles of 54.7%, 58.7%, 58.5%, 58.7%. Another C2 read had 57.2%, 60.0%, 60.8%, 61.5%. There was substantial total/core idle in sampled intervals.

C3's **16.0% kernel** share warrants attention; thread samples showed `dio_manager`, `io-pkt-v6-hc`, `devp-iso-mmx-mib2`, `devb-mmcsd-tegra3-devlite` among busy threads. Per-thread `top` entries cannot be summed indiscriminately into per-process totals. SD-driver activity could be storage/diagnostic logging, but **causal attribution remains open**.

**Observed UX:** with CP + VC 111, the map displayed *slight stutter/uneven frame cadence*. No observation proves that global CPU saturation is responsible. Check source AU arrival spacing, original source timestamps, H.264/IDR, PTS/PCR, remux queue/underflow, exact 12,032-byte MOST writes and display pacing. For the existing pre-TS direct path, see [direct Stream-111 frame-rate evidence](../findings/DIRECT_STREAM_FRAME_RATE_2026-09-27.md): 16,524 decodable source frames / 593 s = 27.865 fps, 0 reported capture drops in a distinct earlier run. That is **not** a guarantee of actual panel presentation cadence.

### 8.1 Important correction: `MIBR-Most20FPS.jar` is NOT a CarPlay Stream-111 20-fps limiter

A runtime J9 classpath listed `MIBR-Most20FPS.jar`. This patch is **project-owned / split from the pinned `jilleb/mib2-toolbox` prior art** and acts on the **native navigation/stock DisplayManager MOST producer**, not the CarPlay source or direct Type-111 pacing. It retains only `de/vw/mib/asl/internal/mostkombi/streamsink/usecases/ChangeDataRateSequence.class`, and is separate from `MIBR-NavIgnore.jar`. The repository already documents exact vehicle capture: stock native output at **10 fps / ~100 ms**, patched native output **20 fps / ~50 ms** at 1010×376, retaining five-frame GOP. See [Most20FPS provenance and validation](../../THIRD_PARTY/Most20FPS/README.md) and [advanced runtime switches](../architecture/ADVANCED_RUNTIME_SWITCHES.md).

CarPlay's own `GEN2`-negotiated maxFPS, source timestamp, optional direct-output pacer and keyframe-recovery policy are **separate mechanisms**. Do not attribute CP+111 judder or an imagined 20-fps cap to that JAR on the basis of the bootclasspath alone. The native owner may still matter indirectly to payload arbitration (e.g. STOCK vs DIRECT gate), and that must be measured rather than assumed.

## 9. What native QNX diagnostics already provide

| Available on target | Use |
| --- | --- |
| `pidin info`, `pidin syspage=cpuinfo`, `pidin syspage=qtime` | Core identity, reported clocks, kernel timebase |
| `top`, `hogs`, `pidin` | Aggregate/core load and thread/process snapshots |
| `/dev/nvclock/get_*` | PLL/module frequency, status, driver limit readback |
| `/dev/nvtmon/current` / `current_local` | Temperature snapshots |
| `/dev/nvsku` | Board/SKU fields, pending complete interpretation |
| `/sbin/tracelogger` | Potential QNX event trace capture; availability of a compatible trace decoder still to be validated |
| Existing project parity/remux telemetry | AU counts, IDR behavior, queue, MOST transport and scheduling evidence |

In the tested shell `traceprinter`, `qcc`, `od`, `hexdump`, `xxd`, `hd` and `busybox` were unavailable. Modern Linux `nvidia-smi`, `tegrastats`, Linux cpufreq/governors and Jetson tooling are **not QNX 6.5 / Tegra T30 drop-in tools**. Porting a broad monitoring suite is unnecessary before exploiting existing read getters. The size-limited clock-tree virtual response yielding `0` is explained by the QNX wrapper (see `4), not evidence that the tree itself has no content.

**Later handoff status:** A small private `mibr-tegradiag-r0.ksh` read-only shell prototype has been syntax-checked and simulated offline but **has not been run or validated on the Unit**; the proposed native QNX ARMLE implementation below is still a proposal. Voltage remains `UNAVAILABLE` until independently measured. R14's [original-data collection issue](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41) is separate from instrument development.

### Later offline tool handoff (2026-10-12): stock-only R1 ready for first target check

A separately delivered, private [**TegraDiag R1 offline-preparation / QA note**](MU1440_TEGRADIAG_R1_OFFLINE_PREP_2026-10-12.md) now documents an actual source kit: bounded `/bin/ksh` fixed-getter script, matching offline Python analyzer for up to three labeled logs (Idle, CarPlay main, CP+active VC111), nine green parser regression tests, and synthetic mock traces. Original R0 below remains a *proposed native QNX ARMLE reader*, not a built/tested target binary. R1 passed local shell syntax and mock test, **not** a real unit run. It contains no stress workload, clock setter or genuine VDD_CPU getter; voltage remains `UNAVAILABLE`. Its private archive hash/provenance and tomorrow's optional stationary collection checklist are in the linked note.

## 10. Proposed research-only tooling

### `mibr-tegradiag` R0 (safe, not yet implemented or vehicle-tested)

Small native QNX ARMLE reader; verify exact firmware/stock hashes and gather coordinated timestamps, `PLLX0`, GPU/VDE/HOST1X/EMC, temperature, `qtime` and optional aggregate CPU/thread snapshots. Sample into a bounded in-memory ring buffer; export CSV/JSON only at end to avoid polluting a frame-pacing experiment with sustained SD writes. Label all clock values as **getter/driver-reported**, not device utilization. Avoid reading unknown command-like virtual nodes.

Suggested CLI *concept*, not existing commands:

```text
mibr-tegradiag info
mibr-tegradiag clocks
mibr-tegradiag thermal
mibr-tegradiag monitor --seconds 60
mibr-tegradiag export
```

### `mibr-tegraclock` R0 (read-only capability audit, not yet implemented)

`status`, `capabilities` and `verify` only. No ``echo value > setter`` examples or write-enabled payload should be distributed. Separate entirely from Stream-111 runtime so it cannot silently affect normal CarPlay or the stock multimedia firmware.

**Current follow-up gates:** R12 establishes exact first-stage source, R13 directly establishes the **initial** CPU-to-qtime /2 path, and the original /50/ 3-MiB wrapper has passed an [exact byte-identical offline roundtrip](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md). Remaining gates are the original pre-startup PLLX writer, dynamic timebase/clocksource behavior, actual read-only VDD_CPU source, unknown wrapper integrity fields, exact-unit NOR/recovery mapping and modified-image acceptance. Existing backups and variant-/70/ validation are delegated as **data collection only** in [R14 Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41). Do not infer physical flash safety from a successful host-side unpack/repack.

## 11. Next gates, explicitly ordered

1. **Board identification:** collect and statically inspect the still-missing `/lib/libnvsku.so`; establish chip part marking/speedo/fuse data and board-specific PMIC/voltage rail, not just `sku=0001`. Keep private original binaries out of the public repository.
2. **BSP/clocksource:** identify Harman QNX startup timer source, `PERIPHCLK`/PLLX relation, timing calibration/interrupt behavior and whether any atomic clocksource-rate update exists. A default 450-MHz `qtime` value alone does not prove safe live adjustment.
3. **Electrical constraints:** identify exact silicon grade, voltage rail and temperature qualification, supplier-approved four-core OPP, thermal/power budget and independent board recovery after a kernel hang. Generic PLL max and Toradex's different modules do not substitute for these.
4. **Setter contract:** fully recover the parameter/units/flags of daemon `set_pll_frequency`, `set_max_pll_frequency` and any dependency/race/rollback behavior **offline**. Even a same-frequency setter write can be hardware-active.
5. **Performance causality first:** repeat B -> C -> B under matched map activity; correlate source AU timestamps and IDRs to post-remux MPEG-TS PCR/PTS, writer latency, MOST queue, per-thread CPU and disk logging. Compare optional diagnostic logging on/off without modifying native-nav FPS policy or mixing native/custom `isoTX2` writes.
6. **Only after all earlier gates:** consider a separately reviewed, explicitly reversible experimental clock plan with an *independent hardware recovery* path. No particular MHz setting, voltage, write procedure or production-default change is proposed by this research.

### Decision as of 2026-10-11

**Build the reader first; do not overclock the vehicle.** We have proven a nominal 900-MHz four-core operating point, a real QNX/NVIDIA clock-control implementation, a plausible industrial-grade explanation, and a strong kernel-clocksource safety concern. None of these establishes that the specific MU1440 CPU "should run" at 1.4 GHz. For the present slight VC jitter, source/transport/presentation timing deserves priority over additional nominal MHz.

## 12. Reproducibility: minimal read-only command inventory

Run only on an already accessible exact target. These commands do not restart drivers or change clock/power states:

```sh
uname -a
pidin info
pidin syspage=cpuinfo
pidin syspage=qtime
cat /dev/nvclock/get_source_clk_freq/PLLX0; echo
cat /dev/nvclock/get_device_clk_freq/G3D; echo
cat /dev/nvclock/get_device_clk_freq/VDE; echo
cat /dev/nvclock/get_device_clk_freq/EMC; echo
cat /dev/nvclock/get_max_device_clk_freq/EMC; echo
cat /dev/nvtmon/current; echo
ls -l /dev/nvpower
ls -l /dev/nvt3pwr
top
```

Take matched A (idle), B (main-display CarPlay only), C (CP+live VC 111) snapshots and record actual map motion/visible stutter. Do not assume `VC_R2_STATE=PATCHED_ON_DISK` or presence of an HMI tracer in J9 proves the live Stream-111 receiver is active; verify the real VC presentation/session.

## 13. References / adjacent project research

**External:** [Toradex industrial CPU/GPU/memory and voltage points](https://developer.toradex.com/windows-ce/knowledge-base/apaliscolibri-t30-temperature-monitoring/); [Toradex T30 per-core DVFS limits](https://developer.toradex.com/software/linux-resources/linux-features/cpu-frequency-and-dvfs-linux/); [Toradex Apalis T30 datasheet](https://docs.toradex.com/101024-apalis-t30-datasheet.pdf); [ARM Cortex-A9 MPCore TRM](https://developer.arm.com/documentation/ddi0407/h/); [QNX ClockCycles](https://qnx.com/developers/docs/6.5.0SP1.update/com.qnx.doc.neutrino_lib_ref/c/clockcycles.html). External module specs illustrate **other products**, not exact MU1440 approval.

**Project / follow-ups:** [research index](README.md); [R12 OEM first-stage source](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md); [R13 original ARM PLLX/qtime](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md); [R13 exact Stage-1 packaging/NOR audit](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md); [Toolkit OEM repack guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md); [R14 Codex source inventory issue](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41); [firmware profile map](MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md); [direct VC video path](../architecture/DIRECT_VC_VIDEO_PATH.md); [source frame-rate evidence](../findings/DIRECT_STREAM_FRAME_RATE_2026-09-27.md); [runtime/FPS controls](../architecture/ADVANCED_RUNTIME_SWITCHES.md); [native Most20FPS provenance](../../THIRD_PARTY/Most20FPS/README.md); [publication privacy](../PUBLICATION_PRIVACY.md).

**Audit lineage integrated here:** R0: daemon method mapping and stock getters; R1: exact clock library, PLLX parameter/configuration; R2: power daemon, libnvrm PMU/DFS stubs; R3: on-unit power-node and Global Timer/qtime read-only preflight. This consolidated report is the public handoff; no original vendor binaries or identifying local capture media are included.
