# MU1440 QNX boot startup script / PMU handoff audit — R8 (2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


> [!CAUTION]
> **Read-only research, not a startup-script replacement, boot patch or overclocking recipe.** This note reconstructs command records from one privately backed-up exact-target QNX boot script. The original proprietary 4,828-byte payload is not published. It does **not** contain the preceding Tegra BootROM/BCT or the entire subsequently invoked shell startup chain. No binary was executed, rewritten or installed.

**Exact target:** \`MHI2_ER_SKG13_P4526_MU1440\` / QNX 6.5 / Tegra T30. Context: [R7 ASINFO / boot memory](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md), [R6 memory controller error-handler](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md), [R5 RAM_CODE/early SDRAM hypothesis](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md), [CPU/PLL/power/timebase audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).

## 1. Exact evidence and file format

| Property | Value |
| --- | --- |
| Original running path | \`/proc/boot/startup.script\` |
| Private backup name | \`MU1440_startup.script.stock\` |
| Size | **4,828 bytes** (matching live \`/proc/boot\` listing) |
| SHA-256 | \`055fda81956df20d0a9b00e90a5590d9b85cec4c40d5579b68d10f5a74b84e20\` |
| File type | **QNX binary-encoded buildfile startup script**, not a plain textual \`ksh\` script |
| Method | Offline byte/token inspection of original, preserving embedded NUL-delimited process command/argv/environment fields and nontext record headers |

Do not feed this binary to \`ksh\` or mistake its visible strings for a complete plaintext shell script. Process entries contain repeated baseline environment strings (\`OEM=SK\`, \`REGION=ER\`, \`HMI_TYPE=G13\`, \`CHIP_VENDOR=NVIDIA\`, \`BUILD_MODE=production\`, etc.); those constants are build context rather than CPU frequency or decoded fuse speed grade. This public report deliberately excludes private customer/product values.

## 2. Actual embedded launch/order records

The following is a **human-readable reconstruction of records encoded in this original startup.script**. Individual QNX control/wait/link record encodings are not presented as independently fully decoded executable syntax. Sequence is meaningful; completion/scheduling semantics of all asynchronously started children have not been fully reconstructed.

| Record order | Encoded operation / argument(s) | Verified significance |
| ---: | --- | --- |
| 1 | \`devc-ser8250-tegra2 -e -t12 -T12 -F -S -b115200 -M -c408000000 0x70006300^2,122\` | Initial serial-device/console driver entry |
| 2 | \`/dev/ser1\` device/control references | Console-related script metadata |
| 3 | \`slogger -s 1024k\` | QNX system logging |
| 4 | \`info "Using mnand driver options inpclk=102000000"\` | Explicit mNAND clock-input configuration message |
| 5 | \`ksh /usr/sbin/mnand-starter.sh\` with \`MNAND_EXTRA_OPTS=rfsh=60,inpclk=102000000\` | Delegates mNAND driver startup to separate shell script |
| 6 | \`info "MMX BENCH_Startup procnto up"\` | Marker emitted in a running QNX/procnto startup context |
| 7 | \`devg-nvsku\` (no visible CLI arguments) | Board/product info resource manager |
| 8 | \`echo "Starting i2c interface for PMU"\` | Explicit power-management handoff message |
| 9 | \`i2c-tegra2 -c5 -f12000000 --u5\` | Launches Tegra I²C controller 5; **do not infer CPU or DRAM MHz from \`-f\`** |
| 10 | \`/dev/i2c5\` device/readiness control reference | PMU I²C device must be provided on this startup path |
| 11 | \`echo "Starting devg-nvpower"\` | Explicit transition into the power driver |
| 12 | \`devg-nvpower\` (no visible CLI arguments) | Power/PMU resource manager |
| 13 | \`devg-nvgpio\` (no visible CLI arguments) | NVIDIA GPIO manager |
| 14 | \`ksh /usr/sbin/startup.sh\` | Delegates to the next-stage shell startup; **its content is not in the submitted backup** |

**Most important new corroboration:** \`i2c-tegra2\` and a \`/dev/i2c5\` readiness reference precede \`devg-nvpower\`. This is consistent with the separately audited power daemon's \`/dev/i2c5\` PMU handling. R2's device reference is therefore not merely an unused arbitrary library string, although exact live PMIC identity, CPU voltage rail and DVFS behavior are **still unverified**.

### mNAND is not SDRAM

\`MNAND_EXTRA_OPTS=rfsh=60,inpclk=102000000\` and the associated \`info\` line concern **mNAND-driver input clock configuration**. The \`102000000\` literal must not be described as Tegra SDRAM/EMC rate, nor as CPU PLLX. The \`-f12000000\` switch belongs to \`i2c-tegra2\` in this command; its exact driver-specific units should be verified against that driver if needed and must not be used as CPU/DRAM evidence.

## 3. What is conspicuously not established here

- The binary contains **no plain string references** to \`PLLX\`, \`PLLM\`, \`EMC\`, or simple \`900000\`, \`750000\` or \`450000\` clock values, and no direct \`devg-nvclock\` or \`nvmemctrl\` launch record in this stage. This is a bounded finding **about this 4,828-byte script**, not proof those clock values are absent from the whole firmware.
- SDRAM initialization must be sufficiently complete before the observed QNX startup script is executing and before \`/memory/startup\` and \`/memory/imagefs\` are serving the running system. **The exact MU1440 BCT, RAM_CODE=2 selected timing profile and boot-image/flash location remain unidentified.**
- The QNX \`qtime.CPS=450 MHz\` and interrupt 27 were previously read from the running system. The startup script is not the actual QNX startup CPU/Global Timer implementation. A \`procnto up\` marker is not a disassembly of that implementation and does not establish whether later dynamic CPU PLLX retiming is coordinated.
- The fact that \`devg-nvpower\` runs after I²C 5 is **not evidence of automatic CPU voltage tracking** when a clock setter is called; R2 found dummy/stubbed generic PMU/DFS methods in the exact \`libnvrm.so\`.

## 4. Chain so far and immediate discriminating target

\`\`\`text
physical RAM_CODE = 2 (R5: strap field)
  -> early Tegra boot / original BCT / SDRAM initialization [MU1440 BCT not yet recovered]
  -> QNX startup and original QNX boot image [actual startup binary not yet recovered]
  -> QNX boot script: /proc/boot/startup.script (THIS R8)
       console + slogger
       mNAND startup handoff -> /usr/sbin/mnand-starter.sh
       devg-nvsku
       i2c-tegra2 controller 5 -> /dev/i2c5
       devg-nvpower -> devg-nvgpio
       -> ksh /usr/sbin/startup.sh  [NEXT FILE]
  -> remaining production processes (need exact follow-on script to map nvclock, nvmemctrl, multimedia)
\`\`\`

**Next exact-target, read-only backup:** \`/usr/sbin/startup.sh\` (first verify the file exists and size); optionally separately collect \`/usr/sbin/mnand-starter.sh\` if storage/boot-source context is required. These are private original source artifacts; check for unique identifiers, passwords or sensitive configuration before public excerpts. A successful discovery of \`devg-nvclock\` in the second stage would establish *start ordering*, not by itself prove it first set PLLX0=900 MHz.

Suggested vehicle commands (copy only; do not execute an uploaded script, restart any daemon or alter clocks):

\`\`\`sh
echo "=== NEXT-STAGE SCRIPTS ==="
ls -l /usr/sbin/startup.sh /usr/sbin/mnand-starter.sh
echo "=== BACKUP ONLY IF PRESENT ==="
if [ -f /usr/sbin/startup.sh ]; then cp /usr/sbin/startup.sh /net/mmx/fs/sda0/esd/carplay-test/MU1440_usr_sbin_startup.stock.sh && sync && ls -l /net/mmx/fs/sda0/esd/carplay-test/MU1440_usr_sbin_startup.stock.sh; fi
\`\`\`

Following the next-stage audit, prioritize independently locating the trusted original QNX boot image/startup code and early Tegra BCT. Do **not** assume \`/proc/boot/startup.script\`, \`/virtual/vboot\` or a guessed flash offset is the location of the pre-DRAM Boot Configuration Table.

## 5. Research decision

The new fact is an explicit **PMU I²C5-before-power-daemon handoff** and a clean boundary to \`/usr/sbin/startup.sh\`. It does **not** relax the existing CPU-clock safety gates: approved speed grade/OPP and live VDD measurement, exact QNX Global Timer source/coupling, safe update of any timebase scale, and independent hardware recovery. No CPU or RAM overclock has been tried.
