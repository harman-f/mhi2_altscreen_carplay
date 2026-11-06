# MU1440 QNX ASINFO and boot-memory layout audit — R7 (2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


> [!CAUTION]
> **Read-only exact-target runtime observation, not a BCT extraction or bootloader modification.** The source is a privately captured \`pidin syspage=asinfo\` text listing on \`MHI2_ER_SKG13_P4526_MU1440\`, QNX 6.5, four Cortex-A9 cores. Public tables below omit private contents of the metadata regions, including any serial/product values. No MMIO or flash reads/writes were made in this step.

See [R5: RAM_CODE hardware strap and boot-memory distinction](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md), [R6: nvmemctrl MC error handler](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md), and the [consolidated clock/timebase audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).

## 1. Exact ASINFO input

\`\`\`text
Header size=0x0000009c, Total Size=0x000010a8, #Cpu=4, Type=4
Section:asinfo offset:0x00000ac8 size:0x00000300
\`\`\`

Ranges below are inclusive; sizes are calculated as \`end - start + 1\`, not inferred from QNX allocation statistics:

| ASINFO tag | Inclusive range | Calculated span |
| --- | --- | ---: |
| \`/memory/below4G/ram\` | \`0x80000000–0xFFEFFFFF\` | **2,047 MiB** |
| \`/memory/1to1\` | \`0x80000000–0x8FFFFFFF\` | 256 MiB |
| \`/memory/below4G/ram/dma\` | \`0x90000000–0x91FFFFFF\` | 32 MiB |
| \`/memory/startup\` | \`0x80A00808–0x80A1A90F\` | **106,760 B** / 104.26 KiB |
| \`/memory/imagefs\` | \`0x80A1A910–0x81086BAB\` | **6,734,492 B** / 6.42 MiB |
| \`/memory/bootram\` | \`0x80A1A910–0x81086BAB\` | Exactly the same inclusive region as \`imagefs\` |
| \`/virtual/vboot\` | \`0xFE01D000–0xFE0BDE6C\` | 659,053 B / 643.61 KiB (**virtual address space**, not evidence of flash/BCT location) |

The RAM span is a **QNX ASINFO declaration**, not proof of available free RAM or an independently measured SDRAM bus frequency. The physical range nominally reaches a 2-GiB address window minus its top 1 MiB. The \`1to1\` and \`dma\` descriptors are *subregions* of the declared RAM, not quantities to add to 2,047 MiB. Likewise, imagefs/bootram overlap exactly and are **not two separate memory allocations**.

Additional published \`sysram\` intervals are \`0x80000000–0x80007FFF\`, \`0x8001D000–0x8001DFFF\`, \`0x8002B000–0x80A00807\`, \`0x81086BAC–0x8FFFFFFF\`, and \`0x97400000–0xFFEFFFFF\`. Between the 32-MiB DMA descriptor's end (\`0x91FFFFFF\`) and last sysram start (\`0x97400000\`), a distinct \`0x92000000–0x973FFFFF\` 84-MiB interval is not labeled \`sysram\` in this capture. **Do not assign a specific hardware consumer or assume it is free/reserved solely from this listing**.

### Why the \`startup\`/imagefs distinction matters

The QNX startup region is \`0x80A00808–0x80A1A90F\`; the image filesystem begins immediately at the next physical byte \`0x80A1A910\`. The output is consistent with a QNX boot-image layout already positioned in initialized DRAM. It does **not** identify the original *flash offset*, the Tegra Boot Configuration Table, how BootROM selected \`SDRAM[n]\`, or the compiled QNX startup code path that configured the CPU clock/Global Timer. The running \`/proc/boot\` listing contained \`startup.script\` and \`procnto-smp-instr\`, but not an independently listed standalone startup executable; a separate file in that pseudo-filesystem is not required for the startup code to have run.

The address \`/virtual/vboot\` is a VIRTUAL descriptor. In particular, its numeric proximity to high physical addresses must **not** be interpreted as a ROM/flash/BCT address.

## 2. SKU and early startup data are already present in ASINFO

These named entries lie inside the physical \`startup\` range:

| Entry | Inclusive physical range | Bytes | Interpretation |
| --- | --- | ---: | --- |
| \`/memory/bootprofiler\` | \`0x80A19F48–0x80A19FEB\` | 164 | Early-boot profiling metadata |
| \`/memory/nvsku\` | \`0x80A19F00–0x80A19F22\` | 35 | Board SKU information block |
| \`/memory/ramsize\` | \`0x80A19F24–0x80A19F34\` | 17 | Information-block length, **not decoded RAM-capacity value** |
| \`/memory/cust_info\` | \`0x80A1A34C–0x80A1A44C\` | 257 | Customer metadata; contents private |
| \`/memory/nvprod\` | \`0x80A1A47C–0x80A1A4A2\` | 39 | Product metadata; contents private |
| \`/memory/is_e1888\` | \`0x80A1A4A8–0x80A1A4B3\` | 12 | Board-identification flag block |

The private ASINFO capture also names \`serial_info\` and \`lp\`; their contents must not be copied to public logs. R4/R5 had already demonstrated that \`libnvsku.so\` is a file-reader wrapper and \`devg-nvsku\` populates the QNX device interface from the syspage/board information plus hardware RAM_CODE strap bits. **ASINFO does not contain the RAM_CODE numeric value itself in this displayed metadata listing, and \`ramsize\` is not an SDRAM timing table.** The earlier \`ram_code=2\` comes from a different live device observation and the R5 readout path.

## 3. Independent live confirmation of nvmemctrl R6

The same session included:

\`\`\`text
49167 1 sbin/nvmemctrl 10r NANOSLEEP
49167 2 sbin/nvmemctrl 10r INTR
nvmemctrl @100000 8192 4096
libc.so.3 @1000000 536K 12K
/dev/mem @28000000 (7000f000) 4096
\`\`\`

This directly corroborates the earlier R6 ARM-disassembly result: one interrupt-waiting thread and a 4-KiB mapping of physical MC MMIO base \`0x7000F000\`. \`nvmemctrl\` is a controller-fault/interrupt handler, **not** the RAM/EMC timing governor. No actual MC error event, RAM overclock, fuse speed grade or CPU voltage was established by this process listing.

## 4. Interpretation for the CPU/RAM clock investigation

| Hypothesis / question | Current answer |
| --- | --- |
| Does this ASINFO prove the unit's physical RAM layout? | Provides the QNX-declared address ranges; exact SPD/chip density and selected SDRAM timing profile still unverified. |
| Does it prove where the Tegra BCT is stored? | **No.** QNX \`startup\` and \`imagefs\` reside in RAM after early memory initialization. |
| Does \`/memory/ramsize\` reveal a frequency or timing profile? | **No.** It is a tagged information region. |
| Does it support R5's SKU data source? | **Yes:** \`nvsku\`, \`nvprod\`, \`is_e1888\` and related metadata are mapped into the QNX startup/syspage-accessible information. |
| Does \`/virtual/vboot\` locate the original bootloader? | **No.** Virtual mapping only; must inspect actual image provenance instead. |
| Does it explain \`PLLM0=750 MHz / EMC current=750 MHz / EMC max=625 MHz\`? | **No**; distinguish PLL output, clock getter and driver policy from actual memory timing. |
| Does it resolve whether \`PLLX0=900 MHz\` can be changed without invalidating QNX \`qtime.CPS=450 MHz\` / interrupt 27? | **No**; requires actual startup/BSP and clocksource analysis. |

## 5. Next exact-target, non-invasive evidence

The known \`/proc/boot\` listing showed:

\`\`\`text
startup.script       4828 bytes
procnto-smp-instr  663552 bytes
libc.so.3         560715 bytes
libz.so.2          79938 bytes
\`\`\`

**Next upload:** exact private copy of \`/proc/boot/startup.script\`; no live edits or execution. Inspect command order and actual arguments of clock/power/SKU/MC initialization and any boot-image references. It may not contain early CPU/DDR initialization if those occur before the script. Do a privacy review before quoting any embedded private paths, credentials, product serials or customer info.

\`\`\`sh
cp /proc/boot/startup.script /net/mmx/fs/sda0/esd/carplay-test/MU1440_startup.script.stock && sync && ls -l /net/mmx/fs/sda0/esd/carplay-test/MU1440_startup.script.stock
\`\`\`

Separately acquire a trusted original MU1440 **offline firmware/boot image** and identify its real QNX image header/startup and Tegra30 BootROM/BCT structure by signature/metadata, not a guessed raw partition offset. A QNX startup-script review alone does not provide BCT/SDRAM[n] selection or clocksource retiming proof.

## 6. Evidence provenance and privacy

- Live user-provided source: \`MU1440_BOOT_ASINFO_R6.txt\` (\`pidin syspage=asinfo\`), analyzed offline.
- Live \`pidin -p 49167 mem\` supplied with that capture.
- Original raw ASUS (?) **No**: this is a Harman MU1440 QNX \`asinfo\` snapshot, *not* a boot image, flash dump or hardware register dump.
- No original proprietary binaries, metadata contents or private vehicle identifiers included in this public note.
