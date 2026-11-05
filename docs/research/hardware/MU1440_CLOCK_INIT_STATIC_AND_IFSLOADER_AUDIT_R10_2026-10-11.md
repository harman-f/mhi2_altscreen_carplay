# MU1440 \`clock_init\` exact-target static audit and Stage-2 IFS runtime correction — R10 (2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


> [!CAUTION]
> **RESEARCH ONLY.** Original proprietary binary remains private, and no clock/voltage/DRAM/flash change is provided or authorized. Never manually re-run \`clock_init\` (boot-time hardware initializer) or \`ifsloader\` (can remount the live root IFS). This is static/offline analysis plus a user-provided **already executed** IFS loader observation.

Target: \`MHI2_ER_SKG13_P4526_MU1440\`, Tegra T30, QNX 6.5. Refer to [R9 startup.sh and Stage-2 reserve](MU1440_QNX_CLOCK_INIT_STAGE2_IFS_AUDIT_R9_2026-10-11.md), [R8 first-stage script](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md), [R7 ASINFO](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md), [R5 RAM_CODE](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md), and [consolidated clock/power/timebase](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).

> [!IMPORTANT]
> **R11 follow-up:** The exact front `libnvclockapi.so` was recovered and [traced end-to-end](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md) through `/dev/nvclock` to the matching implementation. The backend has five separate special-clock write handlers (`SCLK`, `CCLK`, `HCLK`, `PCLK`, `EMC`); the stock `clock_init` default directly names **only SCLK/HCLK/PCLK**. Backend CCLK/EMC capability is not proof of a default stock invocation. The origin of initial PLLX0=900 MHz and QNX qtime=450 MHz remains unresolved. No live write test is approved.

## 1. Input/provenance

| Exact property | Value |
| --- | --- |
| Private live executable | \`clock_init\` invoked without CLI flags from \`/usr/sbin/startup.sh\` immediately after \`devg-nvclock -v 1\`, \`devg-nvos\`, \`waitforpoll /dev/nvos\`, \`waitforpoll /dev/nvclock\` |
| Original uploaded backup | \`MU1440_clock_init.stock\` |
| Bytes | **12,894** |
| SHA-256 | \`14f98073333c0ee6200384ae54f10e883213183ecf55a4c59bb27c0257439cda\` |
| ELF | Stripped ELF32 little-endian ARM EABI5, linked for QNX; interpreter \`/usr/lib/ldqnx.so.2\`; \`main=0x100c18\` (dynsym), entry \`0x100a14\` |
| Needed shared libraries | **\`libnvclockapi.so\`, \`libnvsku.so\`, \`libc.so.3\`** |
| Build note | \`NAME=clock_init\`, \`DATE=2017-03-07PST-14:26:31\`, \`VERSION=qnx650\`, \`TAGID=17.45.06-8589238\` |
| Method | Preserved the stock ELF unchanged and rebuilt only minimal **temporary offline disassembly metadata** for ARM instruction inspection. Addresses herein are original linked addresses, not necessarily live load addresses. |

This is positively **a clock-setting executable**, not only a clock getter, as evidenced by calls imported from \`libnvclockapi.so\` and its table-driven control path.

### 1.1 Exact imported clock and board APIs

\`\`\`text
NvClockCarRegRead
NvClockCarRegWrite
NvClockSetVerboseLevel / NvClockGetVerboseLevel
NvClockConfigureSpecialModuleClock
NvClockDeviceResetControl
NvClockConfigurePLLClock
NvClockConfigurePeripheralClock
get_board_sku
get_board_proj
\`\`\`

No imported QNX qtime retiming or PMU voltage function was identified in this object. This **does not prove** that the imported clock library or BSP cannot perform indirect clocksource or voltage side effects.

## 2. Main control flow and default startup path

The binary contains an internal getopt string \`v:iarsh\` and embedded help/options:

| Flag | Meaning (stock help) | Default without CLI flags |
| --- | --- | --- |
| \`-a\` | Initialize **all** peripheral/module clocks | Disabled |
| \`-i\` | Ignore programming power-on-reset (POR) clock settings | **POR programming enabled** |
| \`-r\` | Bring all modules out of reset | Disabled |
| \`-s\` | Ignore programming special module clocks | **Special module programming enabled** |
| \`-v\` | Clock verbose level | 0 |
| \`-h\` | Help | N/A |

**Do not execute this program with these options to test anything:** even its stock no-flag path writes hardware clock settings. The text help describes the special-clock group as \`SCLK/CCLK/HCLK/PCLK/EMC\`, but the exact main routine (approx. \`0x100ed8–0x100f20\`) contains **three direct calls** to \`NvClockConfigureSpecialModuleClock\` with name pointers corresponding to **SCLK, HCLK and PCLK**. Possible internal relationships or secondary configuration of CCLK/EMC require examining \`libnvclockapi.so\`; one should not declare this binary has independently initialized CCLK/EMC merely because the usage text mentions them.

The main routine (\`0x100c18–0x100fa3\`) first calls \`get_board_sku\` at \`0x100c2c\` and \`get_board_proj\` at \`0x100c38\`. The disassembly includes project validation for \`61858\` or \`61852/61853\` and accepts board SKU values \`1\`, \`2\`, \`5\`, \`8\`; table selection groups SKUs \`2/8\` together and \`1/5\` together. **The observed MU1440 board SKU 0001 takes the profile exported as \`Sku5\`; it is a code-path/table label, not a direct numerical equivalence or silicon speed-grade assertion.** No \`ram_code=2\` SDRAM timing selector is implemented in this binary.

The default path (no \`-i\`) iterates the selected five POR PLL entries and invokes \`NvClockConfigurePLLClock\` for recognized entries; the default special-clock path performs the named \`SCLK/HCLK/PCLK\` configuration, after which optional \`-a\` would allow all table-based peripheral-clock configuration. The optional \`-r\` branch executes a series of CAR clock/reset register calls (approx. \`0x100fa4–0x1010c7\`); this is a **register-writing** path and not a safe diagnostic mode.

## 3. Exact SKU PLL tables, and the important negative finding

Original dynamic symbols locate two separate **300-byte / five-entry** arrays:

| Export | VA | Entry count |
| --- | ---: | ---: |
| \`Sku2_PORPllClocks\` | \`0x102568\` | 5 × 60 bytes |
| \`Sku5_PORPllClocks\` | \`0x102694\` | 5 × 60 bytes |

**The two arrays are byte-identical**, independently compared across all 300 original bytes. In both, the five explicitly named entries in order are:

\`\`\`text
PLLC0
PLLC1
PLLM1
PLLA1
PLLA0
\`\`\`

There is **no explicit named \`PLLX0\` or \`PLLM0\` record** in either POR PLL table. The entries contain other numeric fields (e.g. \`PLLC0\` has \`484\`, \`PLLA1\` has \`294\`), but **their unit/field semantics cannot be safely inferred from their magnitude alone without the matching API structure definition**. Do not label them proven effective MHz settings merely from table bytes.

The separately exported peripheral arrays are **different**:

| Export | VA | Entries | Distinguishing evidence |
| --- | ---: | ---: | --- |
| \`Sku2_PeripheralClocks\` | \`0x1027c0\` | 16 × 56 bytes | I²C1–4/DVC, SDMMC1–4, SATA/SATA_OOB, UART A–E; no SBC1 entry |
| \`Sku5_PeripheralClocks\` | \`0x102b40\` | 17 × 56 bytes | Includes **SBC1**, and I2C4 table-field difference, plus shared devices |

Thus the exact profile difference in this binary is peripheral-related, **not an alternate CPU PLLX0 or primary SDRAM PLLM0 frequency table**. This does not exclude an indirect CCLK/EMC change inside the imported \`libnvclockapi.so\` or another boot component.

### Current CPU and RAM clock conclusions

- \`PLLX0=900000\` kHz, \`qtime.CPS=450000000\` and \`intr=27\` were independently measured in earlier live captures; R10 finds **no direct PLLX0 setter/table in this \`clock_init\`**. The original QNX startup/BSP or earlier Tegra stage becomes a stronger next source-of-900-MHz candidate.
- The reported \`PLLM0=750000\` kHz, \`EMC=750000\` kHz and driver \`EMC max=625000\` kHz discrepancy **remains unresolved**. R10's named POR PLL table does contain **PLLM1**, not PLLM0; do not conflate either with the physical RAM data-clock or DDR transfers.
- No direct QNX \`qtime\` recalibration, Global Timer interrupt 27 management or PMIC CPU voltage adjustment appears in the analyzed executable's imports/control path. That is **not** a conclusive assurance that a hardware PLL write would be safe.

## 4. New live ifsloader observation corrects R9's reserved-vs-mounted size

The user manually invoked the exact stock \`ifsloader\` command copied from \`startup.sh\` and supplied its output. **Do not repeat this on an already running unit:** it actively mounts an IFS on \`/\`; although the submitted execution reported success, repeating startup loaders can affect a mounted live system. R10 records the result only; it does not endorse that action.

Observed log facts:

\`\`\`text
IFS Loader (Build Feb 25 2019)
IFSLOADER: found lzo1z header
IFSLOADER: found 37 blocks
IFSLOADER: mem da: phys 0x92000000 virt 0x28100000
IFSLOADER: mount point '/' mount param 'offset=0x92000000,size=0x4a00000'
IFSLOADER: Image mounted successfully.
IFSLOADER: Image size: 77594624 bytes
IFSLOADER: Transfer time: 2.017000 s
IFSLOADER: Transfer speed: 36.688151 MB/s
\`\`\`

**Exact size reconciliation:**

| Property | Bytes | MiB | Address mapping |
| --- | ---: | ---: | --- |
| R9 loader \`-r\` reservation | \`0x05400000 = 88,080,384\` | **84** | \`0x92000000–0x973FFFFF\` |
| Actual mounted IFS per runtime output | \`0x04A00000 = 77,594,624\` | **74** | \`0x92000000–0x969FFFFF\` assuming contiguous offset/size |
| Difference between reserved window and mounted IFS | \`0x00A00000 = 10,485,760\` | **10** | Mount occupies only part of reserved space |
| Other original CLI argument \`-a 10878976\` | \`0x00A60000\` | **10.375** | Precise option semantics not independently confirmed |

The exact 84-MiB reserve continues to match the earlier R7 ASINFO non-\`sysram\` interval **on the byte**. R9 must **not** imply all 84 MiB are mounted filesystem contents. The actual mounted image is 74 MiB; the remaining 10-MiB difference is not thereby proven to be free/unused or to serve any specifically named buffer. 37 LZO blocks and 2.017 s transfer are the loader's own reported run, not CPU/EMC frequency measurements.

## 5. Next discriminating work — do not re-run boot initializers

1. **Review the exact previously archived \`libnvclockapi_impl.so\`** against these \`clock_init\` call signatures, specifically \`NvClockConfigurePLLClock\` and \`NvClockConfigureSpecialModuleClock\`, their type-2 table structure, and indirect CCLK/EMC/CPU effects. If a thin \`libnvclockapi.so\` front library is distinct, obtain it privately for exact-symbol/call-chain matching.
2. Locate a trusted exact original QNX boot image/startup binary **offline** and determine the actual setup of PLLX0=900 MHz, ARM Global Timer/qtime.CPS=450 MHz, and chip OPP/PMIC rail. Do not assume \`clock_init\` initializes these just because its name suggests so.
3. Separately identify the original Tegra30 BCT \`SDRAM[n]\` profile selected by hardware RAM_CODE=2; R10 does not contain RAM training or SDRAM timing tables.
4. Continue non-writing \`mibr-tegradiag\` baseline instrumentation. Avoid manual invocation of production clock/image/memory initializers on the live car.

**Research result:** We have identified the real stock post-kernel clock-initializer, its two SKU-related configuration families, and the exact absence of a *direct named* PLLX0 or PLLM0 POR table entry. The initial CPU clock/timebase remains a distinct earlier-boot investigation. No tested overclock or deployable clock patch exists.
