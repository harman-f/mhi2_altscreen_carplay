# MU1440 Tegra T30 — NVSKU RAM_CODE provenance and boot-vs-runtime clock configuration (R5, 2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


> [!CAUTION]
> **Exact-target static research / no memory or CPU overclock has been attempted.** This document is an offline audit of the privately supplied stock binary, not a deployable modification or a complete reconstruction of the Harman boot chain. Do not write to PLLX, PLLM, EMC, PMIC, RAM strap, BCT or boot storage on the strength of these observations.

**Reference:** `MHI2_ER_SKG13_P4526_MU1440`; QNX 6.5, Tegra T30. Preceding reports: [consolidated clock/power/timebase audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md) and [R4 libnvsku wrapper audit](MU1440_TEGRA_SKU_STATIC_AUDIT_R4_2026-10-11.md).

> [!IMPORTANT]
> **R6 follow-up:** The subsequently recovered original `/sbin/nvmemctrl` is an MC fault/IRQ reporting service, **not** the SDRAM timing initializer or EMC frequency governor. See the [exact-target R6 nvmemctrl audit](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md). R5's former proposal to inspect nvmemctrl was a research lead and is now resolved negatively. Continue with trusted original boot/BCT and QNX startup images instead. No overclock is validated.

## 1. Original binary and scope

- Private source: live `devg-nvsku`, backed up unchanged as `MU1440_devg-nvsku.stock`; proprietary original **not included** in the public repository.
- Original length: **12,765 bytes**; SHA-256 `ab75541cb624085bebc8368bb2169a16a33d47bc65e06d7bfe1fda8b716113d5`.
- Stripped ELF32 little-endian ARM EABI5; interpreter `/usr/lib/ldqnx.so.2`; `libc.so.3` dynamically needed. QNX build note: `NAME=devg-nvsku`, `VERSION=qnx650`, `DATE=2017-03-07PST-14:26:31`, `TAGID=17.45.06-8589238`.
- Offline disassembly used a temporary copy with reconstructed minimal ELF section headers (the original ELF was left untouched). ARM addresses below are original linked virtual addresses.

## 2. Where /dev/nvsku values actually come from

The resource manager exposes board/product metadata via `/dev/nvsku`. The compiled strings and main-path disassembly demonstrate QNX syspage/asinfo parsing with the names **`nvsku`, `nvprod`, `serial_info`, `is_e1888`** and creation of the pseudo-device entries:

```text
bom  project  sku  rev  rev_uint8  serial_num  prod_sku  sku_ver  e1888  ram_code
```

Those are metadata identifiers, *not* an automatically decoded silicon performance-grade table. In particular `sku=0001` and `rev=900` do not assert an approved CPU OPP or industrial silicon bin. R4 showed `libnvsku.so` exports only four libc-based wrappers that read `/dev/nvsku/e1888`, `rev`, `sku`, and `project`; the actual producer is this daemon.

### 2.1 RAM_CODE is different: directly read from hardware strap

At **`0x1014e0–0x101534`** the binary makes a `mmap_device_memory` call for **four bytes at physical `0x70000008`** and closes the mapping via `munmap_device_memory`. It then loads the register word and executes:

```text
0x10150c  ldr   r5, [r0]
0x101510  ubfx  r5, r5, #4, #4
```

Thus the published `ram_code` is **bits [7:4] of the boot strapping register**; this matches NVIDIA Tegra APBMISC/PMC strapping conventions in Linux (`0x70000008`, `RAM_CODE_SHIFT=4`). It is a **selection identifier**, not the current RAM frequency and not a setter. The previously read `ram_code=2` denotes hardware strap profile number 2; the *actual* associated SDRAM timing block has yet to be extracted from the reference boot images.

External cross-references:
- [Tegra30 APBMISC mapping (Linux DTS)](https://code.googlesource.com/linux/torvalds/linux/+/3c8f504b3a486e4e984ac8dc619eba3afa24cec4/arch/arm/boot/dts/tegra30.dtsi) lists the strapping options register at `0x70000008`;
- [Linux Tegra RAM_CODE reader](https://android.googlesource.com/kernel/common/+/d65be1c67eff4b6b3856b54eaaf64e28ee51fb85/drivers/soc/tegra/fuse/tegra-apbmisc.c) defines the shift and relevant masks.

**What this code does not do:** It contains no SPD/DDR timing table, does not set PLLM0, does not train memory, and is not evidence that RAM timings are dynamically governed by this daemon.

## 3. Boot chronology: RAM and CPU changes are separate questions

```text
physical RAM_CODE strapping (code 2 on observed unit)
   |
Tegra BootROM / early boot memory selection [expected T30 mechanism;
exact Harman boot image and BCT are not yet recovered]
   |
SDRAM/EMC/MC initialization with selected boot parameters
   |
bootloader / QNX startup: clocks, timers, other platform setup
   |
QNX kernel: qtime / global timer, devg-nvclock, nvmemctrl, device policy
   |
normal CarPlay and optional Virtual Cockpit Stream 111 runtime
```

A Tegra30 **Boot Configuration Table (BCT)** can contain multiple `SDRAM[n]` entries including PLLM, MC and EMC configuration. The hardware RAM_CODE acts as an early memory-configuration selector in the Tegra family. See [Tegra30 BCT example and `bct_dump` output](https://github.com/tofurky/tegra30_debrick/blob/master/README.md). This is a **generic Tegra30 mechanism**: the exact location, selection policy, authentication and use of BCT in the MU1440/Harman boot chain are **not yet proven**. Extract the original boot/BCT evidence offline before assigning physical timings to `ram_code=2`.

**Existing live inconsistency is still unresolved:** `get_source_clk_freq/PLLM0=750000` kHz, `get_device_clk_freq/EMC=750000` kHz, but `get_max_device_clk_freq/EMC=625000` kHz. A source PLL, an actual EMC module clock and a driver policy cap can describe different concepts. This is *not* proof of RAM overclocking. Do not change RAM/EMC rates without the matching timing and voltage/refresh transition design.

### Boot-time versus live modification — decision matrix

| Subject | During early boot | During QNX runtime | Project decision |
| --- | --- | --- | --- |
| **DRAM selection / training / base timings** | BootROM/BCT/bootloader stage, before normal DRAM-dependent software | Unsafe to change as if it were a simple scalar; live DVFS requires matching multiple EMC/MC timings, refresh, DLL/calibration, voltage and transition order | **Trace and document stock BCT first. No RAM OC or strap/BCT modification.** |
| **RAM/EMC frequency policy** | Initial PLLM/EMC clock and selected timings | May be controlled by platform-specific `nvmemctrl` and clock APIs, contract not established on this firmware | Recover `nvmemctrl` implementation and exact configured limits. |
| **CPU PLLX0** | Bootloader/QNX startup can establish nominal clock before timer calibration | The existing `devg-nvclock` API can reach hardware PLL configuration, but voltage and timebase coordination are unproven | Separate read-only tool first; do not assume boot or live writes safe. |
| **QNX system timebase** | Kernel startup records `cycles_per_sec=450 MHz`, `intr=27` | If the Global Timer rate follows PLLX while QNX's conversion stays constant, time-based scheduling/media timestamps may be wrong | Confirm startup clocksource and any atomic retiming mechanism before live PLLX test. |

**Longer-term engineering implication:** Once an operating point is independently qualified, a **coordinated boot/BSP profile** could be cleaner for a permanent CPU configuration than writing a new value blindly after every boot: CPU clock, voltage/OPP and QNX timer calibration can be established coherently before normal workloads. However, modifying the boot path has a greater recovery/brick risk and is **not** the first test. A temporary live test would only be considered *after* clocksource, DVFS and independent hardware recovery are solved. A userspace rollback daemon is insufficient if kernel/CPU timing is already broken.

## 4. Specific next evidence and read-only collection

1. **Completed in R6:** the exact `/sbin/nvmemctrl` executable was collected and audited; it implements MC error/IRQ handling, **not** the RAM timing/clock control path. See [R6](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md).
2. Identify the exact MU1440 early boot image and **offline** parse original BCT/SDRAM entries where available; correlate the RAM_CODE=2 selector to an actual profile, and check PLLM/EMC getter discrepancy.
3. Locate the QNX startup/BSP and inspect Global Timer / PLLX handling; investigate speedo/fuse independently of NVSKU board metadata.
4. Implement a read-only `mibr-tegradiag`; avoid adding persistent write load to active 111 frame-pacing tests.

**Suggested next vehicle command (enumeration/copy only, no driver restart or register writes):**

```sh
echo "=== MEMORY CONTROLLER PROCESS ==="
pidin ar | grep nvmemctrl
echo "=== MEMORY CONTROLLER BINARY PATHS ==="
for p in /sbin/nvmemctrl /bin/nvmemctrl /proc/boot/nvmemctrl /mnt/app/armle/usr/sbin/nvmemctrl; do if [ -f "$p" ]; then ls -l "$p"; fi; done
echo "=== NVSKU NODES ==="
ls -l /dev/nvsku
echo "=== BOOT STORAGE LAYOUT (NAMES ONLY) ==="
ls -l /dev | grep -E 'sd|mmc|spi'
```

An earlier live process listing contained `nvmemctrl`, so this is a targeted next file, not speculative deployment. Preserve privacy: never publish serial-number contents, vendor boot binaries, raw captures or personal paths.

**Conclusion:** R5 proves the physical source of `ram_code`; it does not yet find the MU1440 SDRAM timing table. The next investigation is **the verified original early boot/BCT/SDRAM image**, not `nvmemctrl` (ruled out as the clock/timing governor by R6); CPU overclocking needs a *separate* PLLX/PMIC/QNX-clocksource validation route.
