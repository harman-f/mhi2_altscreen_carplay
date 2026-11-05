# MU1440 NVIDIA nvmemctrl — memory-controller error handler static audit (R6, 2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


> [!CAUTION]
> **RESEARCH ONLY / OFFLINE STATIC ANALYSIS.** No memory/PLL/CPU setting was changed. This report analyzes a private exact-target vendor executable but **does not distribute the executable or reconstructed firmware**. Do not stop, restart or patch this daemon in a running vehicle and do not experiment with hardware registers.

**Target:** Škoda/Harman \`MHI2_ER_SKG13_P4526_MU1440\`, QNX 6.5, Tegra T30. This report follows [R5: RAM_CODE strap and boot-memory/CPU-clock separation](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md), [R4: the libnvsku wrapper](MU1440_TEGRA_SKU_STATIC_AUDIT_R4_2026-10-11.md), and the [consolidated CPU/PLL/power/timebase audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).

## Executive finding: misleading name, different job

The on-unit \`nvmemctrl\` process (observed PID \`49167\`) is **predominantly a Tegra Memory Controller fault/error interrupt service and diagnostic**, *not* the sought runtime DRAM frequency governor or early SDRAM timing initializer. The 10.8-KB ARM program maps the Memory Controller registers, installs an IRQ handler, decodes error status/address/client and logs or acknowledges events. It contains **no identified RAM_CODE profile lookup, BCT SDRAM table, EMC timing-training algorithm, PLLM/EMC frequency-setting API, or DDR voltage policy**.

This distinction is important: it cannot resolve the earlier \`PLLM0=750000\` kHz and \`EMC current=750000\` kHz vs \`EMC driver maximum=625000\` kHz discrepancy, and it should not be called the active memory clock manager. The actual RAM training/initialization remains an early-boot/BCT and potentially separate BSP/clock-library question.

## 1. Provenance, identity, limitations

| Item | Result |
| --- | --- |
| Exact live path | \`/sbin/nvmemctrl\` (PID in captured session: \`49167\`) |
| Original backup file (private) | \`MU1440_nvmemctrl.stock\` |
| Length | **10,820 bytes** |
| SHA-256 | \`3e9a353ba936026bfa33b6b40af947e52095efb1694e3b983a5a48906f25fa16\` |
| Format | ELF32 little-endian ARM EABI5, stripped, dynamic QNX executable |
| Interpreter | \`/usr/lib/ldqnx.so.2\` |
| Dynamic NEEDED | Only \`libc.so.3\` |
| Linked entry / \`main\` | \`0x1009d8\` / \`0x100c00\` |
| Build note | \`NAME=nvmemctrl\`; \`DATE=2017-03-07PST-14:26:31\`; \`STATE=experimental\`; \`VERSION=qnx650\`; \`TAGID=17.45.06-8589238\` |

The vendor ELF is stripped and only has minimal original section metadata. Offline analysis inspected its original ELF program/dynamic tables and used a **temporary non-executable copy** with reconstructed section metadata for ARM disassembly. Addresses below refer to original linked virtual addresses. They are disassembly evidence, not debugger/runtime address guarantees. No private register dumps, serials or proprietary binary bytes are committed.

## 2. Imported functions establish the daemon's role

Relevant imported libc/QNX functions:

\`\`\`text
mmap_device_memory / munmap_device_memory
ThreadCtl / procmgr_daemon / signal
InterruptAttachEvent / InterruptWait / InterruptUnmask / InterruptDetach
pthread_create / pthread_join / pthread_setcanceltype
slogf / vslogf / fprintf / fwrite / perror / sleep
\`\`\`

The program does **not** dynamically import \`NvQryClockSet*\`, \`NvRmPmuSetVoltage\`, \`strtoul\`-based RAM_CODE selection or a visible vendor SDRAM training API. String inspection of this exact object found no literals for \`RAM_CODE\`, \`PLLM\`, \`PLLX\`, \`EMC\`, \`SDRAM\`, \`DDR\` or \`BCT\`. Absence of an imported function by itself would not disprove inlined hardware operations; the **control-flow and register-purpose evidence together** provide the stronger conclusion.

Specific in-binary strings include \`NvMemCtrlInit\`, \`MC_DECERR\`, \`MC_SECURITY_ERR\`, \`MC_SMMU_ERR\`, \`SECURITY_TRUSTZONE\`, \`SECURITY_CARVEOUT\`, \`Non-Secure\`, \`Read\`, \`Write\`, and more than 40 labels for the reporting device/client (display0/1 windows, \`gr2d\`, \`gr3d\`, \`host1x\`, \`vde\`, SATA, PCIe, etc.). These labels identify a failed memory **transaction initiator**, not different SDRAM chips or a performance profile.

## 3. Reconstructed control flow (key addresses)

| VA | Observation |
| --- | --- |
| \`0x100c00–0x100cdc\` | \`main\`: daemonization, signal setup, initialization, wait for stop and cleanup. |
| \`0x100d88–0x100ddf\` | \`mmap_device_memory\` with physical base **\`0x7000F000\`**, the Tegra Memory Controller register region. |
| \`0x100d00–0x100d1f\` | Inline memory-mapped register read helper. |
| \`0x100d20–0x100d3f\` | Inline memory-mapped register write helper. Writes associated with fault handler/IRQ setup and acknowledgment should not be described as memory timing programming. |
| \`0x100de0–0x100e53\` | Logging helper (syslog/stderr paths). |
| \`0x100ea4–0x100f43\` | \`NvMemCtrlInit\`-identified initialization: register mapping, IRQ registration, diagnostics on failure, initial register configuration. |
| \`0x100f44–0x1011d3\` | Worker: establishes interrupt/termination state; loops through \`InterruptWait\`, reads fault/status registers, decodes error context, logs, acknowledges and unmasks. |

Among observed register offsets used by the worker are \`0x00\` (interrupt status), \`0x08\` (error status) and \`0x0c\` (error address), consistent with the public Tegra30 MC error-handler definitions. It tests fault/status bits, derives a hardware client identifier from the status field, selects strings such as \`MC_DECERR\` and \`MC_SMMU_ERR\`, formats the offending address and permission/security context and clears/reenables the interrupt. Its initialization path **does make MMIO writes**, so saying the process is globally read-only would be false; the crucial distinction is that none of the analyzed routines implements a general DRAM frequency/timing configuration.

Independent source cross-check: [NVIDIA-authored older Linux Tegra30 MC driver](https://android.googlesource.com/kernel/common/+/3aebd34b1200a902a8662da8845824a02f00772e/drivers/memory/tegra30-mc.c) defines \`MC_INTSTATUS=0x0\`, \`MC_INTMASK=0x4\`, \`MC_ERR_STATUS=0x8\`, \`MC_ERR_ADR=0xc\`, names matching the binary and a similar ISR fault decoding flow. This is corroboration of register meaning **on the same SoC family**, not a claim that the QNX and Linux drivers have identical implementation.

## 4. Consequences for the RAM / overclock investigation

| Question | R6 conclusion |
| --- | --- |
| Does \`nvmemctrl\` select \`ram_code=2\` or read physical RAM straps? | No such flow identified. R5 located RAM_CODE in **\`devg-nvsku\`**, which reads bits [7:4] of the strap register at \`0x70000008\`. |
| Does it establish initial DRAM training or BCT SDRAM tables? | No such logic identified; this likely occurs before QNX userspace, exact target images pending. |
| Does it perform dynamic EMC DVFS or set PLLM? | No identifiable mechanism in this object; do not equate its process name with memory frequency management. |
| Does it modify hardware registers? | **Yes:** MC fault/status/interrupt path; do not run custom probing against it. |
| Does \`PLLM0=750\` and \`EMC getter=750\` prove stock RAM runs outside its 625-MHz policy limit? | **No.** Root cause unresolved; we need the original BCT/clock initialization and the exact getter/source semantics. |
| Could it explain arbitrary slowdown if MC/SMMU errors occur? | It can report such faults; **none was demonstrated in the supplied live snapshots**, and the presence of a handler is not evidence of a fault or cause of VC stutter. |

### Where RAM configuration likely actually belongs (not yet proven for this exact Harman boot image)

\`\`\`text
physical RAM_CODE = 2 (R5 confirmed)
        |
Tegra30 BootROM selects early boot memory parameters / BCT
        |
SDRAM initialization, selected EMC/MC timings and PLLM policy
        |
QNX startup / hardware configuration / devg-nvclock runtime getters
        |
nvmemctrl: MC error detection and reporting, not the startup timing engine
\`\`\`

NVIDIA's [cbootimage-configs project](https://github.com/NVIDIA/cbootimage-configs) documents Tegra BCT extraction as a way to recover device-specific \`SDRAM[]\`/device parameter entries; [\`bct_dump\` supports Tegra30](https://github.com/NVIDIA/cbootimage/blob/master/src/bct_dump.1.in). A **read-only extraction from a verified original image, offline**, is preferable to trial alterations. We have **not** identified the actual MU1440 BCT storage offset, security/boot layout or the \`ram_code=2\` profile yet. Do not blindly copy Linux block-device examples onto QNX or read an unspecified raw flash partition.

For CPU frequency separately, any future persistent configuration would need coordinated PLLX, approved voltage/OPP and correct QNX Global Timer calibration. R6 neither resolves this clocksource problem nor authorizes a live PLLX write.

## 5. Next research gates (in order)

1. Identify the exact Harman/Tegra early-boot firmware layout from an existing, trusted *offline* reference/flash image. Determine whether a BCT is present and where, without executing generic write/flash commands.
2. With that evidence, decode the original BCT using \`bct_dump\` and correlate \`SDRAM[2]\` to the observed RAM_CODE=2 **only after validating the table selector contract**. Record PLLM and SDRAM/EMC/MC timing parameters rather than assuming a headline frequency.
3. Independently reconstruct the QNX startup/BSP PLLX and Global Timer (450 MHz, interrupt 27). A possible boot-time coordinated CPU configuration is a *design direction*, not a tested modification.
4. Correlate stock runtime EMC getters with the recovered boot parameters; investigate which APIs provide \`get_device_clk_freq/EMC\` and \`get_max_device_clk_freq/EMC\`.
5. Keep \`mibr-tegradiag\` read-only and distinguish any MC error reports from ordinary CPU/thread load and Stream-111 frame timing.

## Live validation addendum — process/MMIO mapping (2026-10-11)

A subsequent exact-target read-only session corroborated the previously static findings:

```text
pidin ar | grep nvmemctrl
   49167 nvmemctrl

pidin -p 49167 mem
   49167   1 sbin/nvmemctrl   10r NANOSLEEP
   49167   2 sbin/nvmemctrl   10r INTR
            nvmemctrl          @  100000             8192  4096
            libc.so.3          @ 1000000             536K   12K
            /dev/mem           @28000000 (7000f000)        4096
```

Two live threads and the interrupt wait state independently match the static error/IRQ handler analysis; the 4,096-byte device-memory map at physical `0x7000F000` is the exact MC register base seen in disassembly. This is a **runtime corroboration of the fault-handler role**, not a claim to have decoded a live RAM timing table, and no MC error occurrence was observed by this output.

The same session's `ls -l /proc/boot` listed `startup.script` (4,828 bytes), `procnto-smp-instr` (663,552 bytes), `libc.so.3`, `libz.so.2` and symlinks, but no separately visible startup executable. The command `pidin syspage=asinfo` wrote a private SD diagnostic file; its **contents have not yet been reviewed**. Next inspect this file and privately copied `/proc/boot/startup.script` (with publication privacy review) to identify QNX driver order and boot/startup clues. Neither the file list nor the script alone establishes the location or structure of the exact original Tegra BCT.

## 6. Read-only reference capture (already vehicle-proven)

\`\`\`sh
pidin ar | grep nvmemctrl
ls -l /sbin/nvmemctrl
pidin syspage=qtime
cat /dev/nvclock/get_source_clk_freq/PLLM0; echo
cat /dev/nvclock/get_device_clk_freq/EMC; echo
cat /dev/nvclock/get_max_device_clk_freq/EMC; echo
\`\`\`

No need to restart \`nvmemctrl\`, map MC physical registers from a new live tool, change its IRQ mask, or modify RAM/CPU rates. Continue [the public research index](../README.md) for evidence-class boundaries and privacy requirements.
