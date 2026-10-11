# MU1440 R11: clock API front-to-backend and special-clock audit (2026-10-11)

> [!CAUTION]
> Research only. All analyses are offline on private exact-target stock binaries. Do not manually rerun clock_init or ifsloader, restart clock drivers, or write PLL/EMC/PMIC/CAR controls. No vendor executable is published and no overclock is validated.

Target: MHI2_ER_SKG13_P4526_MU1440, QNX 6.5, Tegra T30. Earlier context: [R10](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md), [R9](MU1440_QNX_CLOCK_INIT_STAGE2_IFS_AUDIT_R9_2026-10-11.md), [consolidated clock audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).

**Read next:** [consolidated clock/overclock navigation](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md) → [R12 original first-stage source](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md) → [R13 first-stage PLLX read and qtime /2 proof](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md) → [OEM Stage-1 roundtrip, SWDL/NOR boundaries](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md). This R11 audit is **the later running-system clock-API route**; it must not be confused with the earlier ARM QNX startup itself. For outstanding original voltage/backup data see [R14 Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41).

## 1. Matching private binary fingerprints

| Binary | Bytes | SHA-256 |
| --- | ---: | --- |
| MU1440_clock_init.stock | 12,894 | 14f98073333c0ee6200384ae54f10e883213183ecf55a4c59bb27c0257439cda |
| MU1440_libnvclockapi.stock.so (new) | 24,576 | 49338b81c767ace5ced3be5581f885707be0ba0db2fd525039abacf6481353df |
| MU1440_devg-nvclock.stock | 27,380 | 8c9296f0feecb500dc5864a90731ab0c8c7bed1c46bbcc4b1a31485edcfdc197 |
| MU1440_libnvclockapi_impl.stock.so | 81,920 | ad4a1e25559b1d9527d8c6491bc7ebecf7a98a1d0a6d3d79859b0be487731db0 |

New file is stripped ARM ELF32 little-endian EABI5, SONAME libnvclockapi.so, QNX build 2017-03-07; DT_NEEDED only libc.so.3. Its imports include open64, fcntl, devctl, close, pthread_mutex_lock/unlock and formatting/logging functions. It has NO direct DT_NEEDED dependency on libnvclockapi_impl.so, NO imported PMIC/voltage function and NO identified imported QNX qtime recalibration function. Temporary offline ELF section metadata was created for disassembly; originals were left untouched.

## 2. Exact software path and the node dispatch table

Stock /usr/sbin/startup.sh launches devg-nvclock -v 1 and devg-nvos, waits for their QNX device nodes, then calls clock_init without options. The complete path is:

    clock_init -> libnvclockapi.so -> /dev/nvclock/... -> devg-nvclock -> libnvclockapi_impl.so -> Tegra CAR/PLL/module registers

The front library uses a 20-byte-entry descriptor table at virtual address 0x4cb8, with lazy device open and devctl request dispatch in its shared helper at 0x0f80. This is an operational resource-manager proxy, NOT a local state-only wrapper. Indexes below are static audit IDs, not suggestions for live commands.

| Internal table index | Observed device node |
| ---: | --- |
| 2 | /dev/nvclock/get_source_clk_freq/NULL |
| 3 | /dev/nvclock/get_device_clk_freq/NULL |
| 4 | /dev/nvclock/get_max_device_clk_freq/NULL |
| 15 | /dev/nvclock/set_device_frequency/NULL |
| 16 | /dev/nvclock/set_max_device_frequency/NULL |
| 17 | /dev/nvclock/change_pll_param/NULL |
| 21 | /dev/nvclock/set_pll_frequency/NULL |
| 22 | /dev/nvclock/set_max_pll_frequency/NULL |
| 23 | /dev/nvclock/set_special_device_clock/NULL |
| 43 | /dev/nvclock/impl_lib_api_wrapper/configure_peripheral_clock |
| 44 | /dev/nvclock/impl_lib_api_wrapper/configure_pll_clock |

Here NULL is the stock string placeholder for the requested clock/device name. The original NvClockConfigureSpecialModuleClock front export at VA 0x2124 sends the chosen name plus three numeric arguments (format: %u %u %u) via index 23. The front NvClockConfigurePLLClock export at VA 0x1500 passes a 60-byte configuration record to the configure_pll_clock endpoint, consistent with the original clock_init 5-by-60-byte POR tables. These calls can lead to actual hardware writes through the resource manager.

## 3. What is supported by the backend versus invoked at stock startup

The exact original libnvclockapi_impl.so exports NvQryClockConfigureSpecialModuleClock at VA 0x3be8 (536 bytes). ARM disassembly and its five-entry eight-byte name/type table at 0x12be0–0x12c07 prove these distinct cases:

| Type | Name | Implementation evidence |
| ---: | --- | --- |
| 0 | SCLK | 0x3c84 branch; CAR register helper calls for offsets 0x28, 0x2c |
| 1 | CCLK | 0x3d74 branch; CAR register helper calls for offsets 0x20, 0x24 |
| 2 | HCLK | 0x3d48 branch; register 0x30 read/modify/write, separate bit-field |
| 3 | PCLK | 0x3d1c branch; register 0x30 read/modify/write, another bit-field |
| 4 | EMC | 0x3ce8 branch; register 0x19c read/modify/write |

CAUTION: The exact stock clock_init default direct calls name SCLK, HCLK and PCLK only; it does not directly call the named CCLK and EMC special handlers in the decoded standard path. The binary's general -s help mentions all five clock names, but that documents backend capability, not proof of a stock invocation. Indirect/shared-parent effects through SCLK cannot be categorically excluded by string search alone.

R10 separately demonstrated byte-identical Sku2_PORPllClocks and Sku5_PORPllClocks arrays (five records, 300 bytes each), explicitly naming PLLC0, PLLC1, PLLM1, PLLA1 and PLLA0, with NO directly named PLLX0 or PLLM0 entry. Board SKU=0001 selects the internal Sku5-family branch: this table label is not silicon speed grade. The different profile's peripheral clocks do not establish a different CPU OPP.

## 4. Current decision and open gates

| Question | Evidence-bounded conclusion |
| --- | --- |
| Do the stock front API and clock_init have actual clock-write capability? | Yes, through the exact QNX daemon/backend |
| Does the backend implement CCLK and EMC write handlers? | Yes, in separate CAR-register branches |
| Are these two handlers directly named in the stock clock_init default special-clock calls? | No |
| Does this show who established stock PLLX0=900 MHz? | No; QNX startup/BSP/earlier boot or indirect path remains open |
| Does this explain PLLM0=750 / EMC getter=750 / maximum=625 MHz? | No; recover BCT/SDRAM timing and exact getter semantics |
| Does it establish PMIC-voltage DVFS or recalibration of QNX qtime.CPS=450 MHz at interrupt 27? | No |

Next, acquire the trusted original early QNX startup/BSP image OFFLINE and analyze its clocksource/PLLX initial setup, independently identify original Tegra BCT SDRAM[RAM_CODE=2], and only then judge which operating-point hypothesis to test. Continue read-only telemetry. Do not manually rerun ifsloader: an earlier live invocation remounted the 74-MiB Stage-2 image within an 84-MiB reserved region.

Bottom line: R11 closes the front-to-backend control graph, and makes an essential distinction between possible backend CCLK/EMC programming and what the exact MU1440 clock_init default path actually requests. This is neither a safe-clock qualification nor a deployable patch.
