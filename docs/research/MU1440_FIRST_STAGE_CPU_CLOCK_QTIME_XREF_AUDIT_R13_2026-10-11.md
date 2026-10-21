# MU1440 R13 — exact QNX First-Stage CPU-clock / Global-Timer qtime XREF audit (2026-10-11)

> [!CAUTION]
> **OFFLINE STATIC RESEARCH ONLY.** No OEM startup bytes, complete disassembly, BCT, firmware image or locally identifying paths are published. This does not authorize a PLL, PMIC, EMC, qtime or flash change, a manual boot-initializer rerun, or any live overclock. The absence of a demonstrated runtime retiming path is **not** a proof that no such code exists anywhere.

**Provenance:** [Issue #39](https://github.com/harman-f/mhi2_altscreen_carplay/issues/39); data acquisition by Codex/Luna, technical binary/XREF interpretation by ChatGPT. This R13 report follows the now-merged [R12 PR #38](https://github.com/harman-f/mhi2_altscreen_carplay/pull/38), which corrected its QNX-header P2 finding. Related previous analyses: [R7](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md), [R10](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md), [R11](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md), [R12](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md).

**Research navigation:** Start at the [consolidated Tegra CPU/clock/power/timebase overview](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md). [R12](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md) identifies the exact OEM startup; **this R13** resolves the initial PLLX read and qtime /2 instructions; [the packaging/NOR companion](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md) and [the merged Toolkit's step-by-step OEM guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md) establish offline 3-MiB roundtrip only. The separate [R14 source inventory issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41) requests original /70/ wrapper, archived backup provenance and a genuine read-only CPU voltage measurement source. Neither recovery nor live CPU tuning is certified by these sources.

## 1. Independently verified private input and bounded method

The private, directly user-uploaded `MU1440_R13_CHATGPT_HANDOFF.zip` is **3,159,647 bytes**, SHA-256 `03984ddc2b7084475cd901ea87dc4ea3551e7ef173167933922c1e3393d29aa0`. A fresh offline ZIP integrity test and all **11** internal `SHA256SUMS` file checks passed. The reconstructed kernel and startup slice match the exact original variant-70 handoff:

| File / region | Exact length | SHA-256 |
| --- | ---: | --- |
| Decoded variant-70 Stage-1 kernel | 6,841,260 | `f3e9098cd9eadd48cf65a9e1dc28481be4894b64c765956046abf286ea078465` |
| Startup region `kernel[0x8:0x1A110]` | 106,760 | `9a7d54a69a5672cf13e532b262670b3ab4146d1e4d942b6cd2424a346a223b39` |

The QNX header is **256 bytes** starting at kernel offset `0x8`. Header-declared `startup_vaddr=0x80A06B40`, `image_paddr=0x80A00808`, `paddr_bias=0`, hence the header entry is startup-relative `0x6338` / kernel-file offset `0x6340`. At the mapped entry, independently decoded ARM instructions prepare CPSR/CP15/cache/TLB and the stack before directly calling the boot-main path at `0x80A048BC`. **Do not treat the whole 106,760-byte startup as ARM code:** it includes header, data, literals, branch tables and possible trailer. R12's variant-50/70 byte-identical startup finding is retained.

Method: a synthetic **analyst-only ELF section wrapper** was constructed from the unchanged original decoded kernel, mapping kernel-file offset `x` to `0x80A00800+x` (the image's identity address map with the eight-byte preamble). LLVM ARMv7 disassembly, byte-level confirmation of each reported instruction, PC-relative literal resolution and direct branch/XREF checks were conducted on the private copies. The wrapper is NOT an original OEM ELF and does NOT establish every internal code/data boundary. There was no firmware execution and no use of live setter APIs.

## 2. Verified startup call chain (direct instruction evidence)

| VA (kernel-file offset) | Exact observation | Strength |
| --- | --- | --- |
| `0x80A06B40` (`0x6340`) | Header-declared ARM entry; directly calls `0x80A048BC` at `0x80A06B78` | DIRECT |
| `0x80A049B8` (`0x41B8`) | Boot-main dispatch invokes `0x80A03668` | DIRECT |
| `0x80A03784` (`0x2F84`) | Early boot flow invokes clock-state initialization `0x80A0463C` (another conditional call at `0x80A03900`) | DIRECT |
| `0x80A037D0` (`0x2FD0`) | Later boot path calls qtime/timer setup `0x80A033EC` | DIRECT |
| `0x80A033F8` (`0x2BF8`) | qtime setup calls active CPU-clock-source frequency getter `0x80A04044` | DIRECT |

These edges are actual decoded ARM branches, not ASCII-marker or symbol-name guesses.

## 3. Actual hardware PLLX read and CPU source selector

At `0x80A0463C`, startup requests an MMIO mapping of **physical `0x60006000`**, Tegra30's Clock and Reset Controller (CAR), via its platform mapper. In the function's established CAR-base register (`r5`):

- `0x80A0472C–0x80A04738`: reads `[CAR+0xE0]` and calls the local PLL-frequency decoding helper `0x80A03EB8` with the already determined input frequency; the decoded rate is stored at `[internal_clock_state+0x58]`. This is **a hardware register READ plus internal RAM write**, **not** a direct PLLX0 register write.
- The decode helper tests the PLL-enable bit and derives the frequency from the PLL divider/multiplier fields (its exact observed instructions extract low five bits, `[17:8]` and `[22:20]`). Do not claim original `M/N/P` values from the offline binary because the *live CAR register value* is not part of this handoff.
- `0x80A04044` reads `[CAR+0x20]`, decodes the CPU burst-policy/source selection, and dispatches through a bounded source jump table. **Selector 8** reaches `0x80A040C4`, which returns `[internal_clock_state+0x58]` — the earlier calculated PLLX rate.

Independent Tegra30 register definitions confirm `CAR+0x20=CCLK_BURST_POLICY`, `CAR+0xE0=PLLX_BASE`, and the PLLX CPU-source selector value **8**:

- [Linux Tegra30 CAR implementation, register defines and source selection](https://git.ti.com/cgit/ti-linux-kernel/ti-linux-kernel-next/tree/drivers/clk/tegra/clk-tegra30.c?id=7396ff8c77fba1ddda2fc8bcb61c81a3ea4874f9).
- [Independent Tegra30 clock implementation / CPU resume policy](https://android.googlesource.com/kernel/common/+/358feceebbf68f33c44c6650d14455389e65282d/drivers/clk/tegra/clk-tegra30.c).

**Conclusion, carefully scoped:** the original Stage-1 startup **reads and interprets an existing PLLX_BASE setting**; the decoded clock-state initializer does not itself write `CAR+0xE0` in the traced function. That is substantially stronger than R12's string-only markers. The precise *original writer/boot stage*, active numeric `PLLX_BASE` word and exact stock selected `CCLK_BURST_POLICY` word are **not contained in this input**. Earlier Tegra boot/BCT/bootloader remains the principal hypothesis, not a proven origin. Do not claim no other code anywhere can change PLLX.

## 4. Direct proof of QNX qtime's half-CPU-clock assumption

The recovered `0x80A033EC` early qtime initialization contains a direct, short and consequential operation chain:

| Instruction location | Behavior |
| --- | --- |
| `0x80A033F0` | Obtains/initializes the QNX timekeeping structure via `0x80A04D14` |
| `0x80A033F8` | Reads the current active CPU clock-source rate via `0x80A04044` |
| `0x80A03414` | Retains the whole source-clock frequency in an internal global |
| **`0x80A03418`** | **`r5 = r0 >> 1`**: explicit division by two |
| `0x80A03430–0x80A03434` | Writes literal **27** to the timekeeping structure's timer-interrupt field |
| `0x80A03450` | Passes the timekeeping structure and half-rate to further qtime conversion initialization |
| **`0x80A03458`** | **Stores the half-rate in the timekeeping structure's frequency field** |

The actual stock live baseline recorded in previous independent captures is `PLLX0=900,000 kHz`, `qtime.CPS=450,000,000`, interrupt `27`. **The exact startup now explains the numeric /2 relationship by decoded instructions, not by coincidence.** For the CPU source-selector-8 (PLLX) route, the qtime startup rate is explicitly `PLLX-rate / 2`.

This **does not establish the identity or source of the original 900-MHz PLLX register write**, nor validate the live policy bits independently: those would require a stock live read-only CAR snapshot or authenticated pre-QNX boot evidence, which was not included and is not requested here.

## 5. Global Timer evidence, with the necessary pointer/fixup qualification

The startup has timer-support code matching the Cortex-A9 global timer register shape:

- An original timer-read template at `0x80A0149C` accesses a lower/upper 64-bit counter at template-base offsets `0x200` and `0x204` with a high-low-high consistency sequence.
- Additional template functions around `0x80A018BC–0x80A01968` use counter/control/interrupt/comparator offsets corresponding to Cortex-A9 Global Timer counter, control, interrupt status and comparator.
- In the original storage some code templates use an intentionally invalid `0xFFFFFFFF` base placeholder and are subject to later relocation/patching. **The existence of the template does not by itself prove the final runtime mapping or that every template is the live-selected clocksource.** The direct qtime setup's interrupt-27 selection, frequency division and ARM architectural mapping materially strengthen the Global Timer interpretation.

The [ARM Cortex-A9 MPCore TRM DDI0407I](https://e2e.ti.com/cfs-file/__key/communityserver-discussions-components-files/791/DDI0407I_5F00_cortex_5F00_a9_5F00_mpcore_5F00_r4p1_5F00_trm.pdf) documents the global timer at `PERIPH_BASE+0x200`, an interrupt ID **27**, and clocking from **PERIPHCLK**, with counter/control/status/comparator offsets. Tegra30 DTS references the distinct per-core watchdog/private timer at `0x50040600`: do not confuse that `+0x600` block with the global timer.

**Bounded judgment:** global-timer coupling is now strongly supported by the original timer templates, explicit `qtime` source `>>1` and interrupt 27, but the complete template relocation and runtime counter-route XREF still merits a final independent mapping audit.

## 6. The operating-point / timer safety consequence

If a future operation changes the effective CPU clock / PERIPHCLK while QNX continues to use the **boot-time fixed** half-rate as its cycles-per-second calibration, system timing, timeouts, performance measurements and Stream111 pacing **could become incorrect**. The current first-stage trace demonstrates an initialization, not an established automatic runtime-safe recalibration. Do **not** infer that there is no retiming implementation anywhere, or that `NvClockSetPLL...` would handle QNX qtime, PMIC voltage and media timestamps atomically.

No silicon speed grade, approved CPU OPP/voltage envelope, regulator coordination, dynamic clocksource migration, live PLLX register word or RAM/BCT SDRAM profile has been established. No 1.3/1.4-GHz qualification follows from this audit.

## 7. Evidence/decision matrix and next precise data gate

| Claim | Status | Remaining input |
| --- | --- | --- |
| Exact startup source and entry header | DIRECT, cross-validated | None for this source |
| Stage-1 reads `PLLX_BASE` and decodes it into a CPU-rate table | DIRECT | Live register word only to calculate exact numerical fields |
| CCLK selector 8 returns that PLLX-derived internal rate | DIRECT, architecture cross-check | Actual stock burst-policy word to prove selected runtime branch independently |
| qtime startup sets `rate = current-CPU-source-rate >> 1` and `intr=27` | **DIRECT** | None for the instruction sequence |
| Global Timer is the counter source | STRONGLY SUPPORTED, pending template/runtime relocation audit | Final fixup/descriptor mapping; stock counter source if available read-only |
| Startup itself sets PLLX0 to 900 MHz | **NOT DEMONSTRATED** in the traced initializer; it reads existing register | Original earlier Tegra boot/BCT/bootloader or an evidenced alternative writer |
| Runtime PLLX write is safe for qtime/PMIC | **UNKNOWN / NOT APPROVED** | Comprehensive timer-retiming path and genuine silicon/voltage/OPP evidence |
| `RAM_CODE=2` selects `SDRAM[2]` | **UNKNOWN**: no validated BCT | Authenticated original Tegra30 BCT; separate research thread |

A reasonable next **data-only** Codex request, if truly needed later, is to locate existing stock read-only CPU burst/PLLX register snapshots in archived original logs — **not** to execute any clock setter or to start vehicle tests. A separate authenticated boot/BCT source is required to settle the original PLLX programming and RAM strap mapping.

**Result:** R13 establishes the stock MU1440's CPU-rate-to-qtime **/2** dependence in the original first-stage ARM code, and that the tracked CAR initialization **reads** an already configured PLLX register rather than explicitly programming 900 MHz itself. Clock-change implementation remains out of scope.

**Later source-specific R15 correction (2026-10-12):** [Direct native MMX fs0 PT and installed Stage-1 audit](MU1440_MMX_FS0_NATIVE_PT_AND_STAGE1_HEADER_CRC_R15_2026-10-12.md) confirms the historical 3-MiB KERNEL_PRIMARY and 6-MiB KERNEL_RECOVERY are **separate original native named partitions in BACKUP-SNAPSHOT-06**. The *entire* installed Primary matches the authenticated OEM /70/ transport module after only four outer-magic byte differences, and formerly unknown header 0x7FC is an independently verified CRC32 of the normalized installed ANDROID! first 0x7FC header bytes. This substantially closes offline original-format mapping; it does NOT establish modified-image boot acceptance, current live-unit provenance, physical erase geometry, voltage or safe PLLX/qtime handling. Earlier R13 claims below are retained as historical findings and should be read with this supplement.

## 8. Follow-up: authenticated OEM /50/ wrapper roundtrip and packaging/NOR boundaries (2026-10-11)

The **original OEM `mifs-stage1.img` variant-50** was subsequently provided separately and revalidated against R12: **3,145,728 bytes, SHA-256 `694c707035fea415842d222f2993e90aad69ca539c1b3608631bd8182ceffc6c`**. It decoded to a different full variant-50 kernel (**6,841,260 bytes; SHA-256 `2dc088bb719fcb42ec0f12260f1f3a451bd328bbf0cecdec3647f5f07cb703ba`**) but the original first-stage startup was **byte-identical** to the variant-70 R13 source (`9a7d54a69a5672cf13e532b262670b3ab4146d1e4d942b6cd2424a346a223b39`). The R13 CPU/qtime instruction paths and source identity therefore remain applicable to this *common* startup. ImageFS and entire variant-50/70 kernels are NOT interchangeable.

**New exact offline wrapper facts:** OEM Stage-1 is a fixed **3-MiB** custom Android-style module with an original **0x800-byte** extended header/page, `kernel_size=2,984,374` at outer `0x8`, zlib stream starting at outer `0x800`, and **verified compressed-stream CRC32 `0xFA04A09A` at outer `0x264`**. The meaning/integrity policy of extra fields `0x260/0x400/0x7FC` remains unproven. Python 3.13.5 / zlib 1.3.1 `zlib.compress(unchanged_variant50_kernel, 9)` produced **the exact original compressed bytes**; rebuilding with the untouched OEM first page and original zero/`0xFF` fill produced the entire original 3-MiB image **byte-for-byte**, same original SHA-256. This goes beyond a decoded-filesystem match. A single harmless *diagnostic ASCII byte* change was separately tested offline: with the inner QNX startup checksum and observed outer length/CRC repaired, a fresh re-decode recovered only the intended ASCII/checksum difference and unchanged ImageFS. The modified fixture remained private and was **not booted, flashed or OEM acceptance-validated**.

Full separate, sanitized [R13 packaging, module map and NOR-boundary research](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md) gives the step-by-step evidence ladder and crosslinks to the [exact Firmware Toolkit Stage-1 step-by-step guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md). Toolkit's `main` is PR-protected; the documentation was committed to a named branch and then merged into `main` via [Toolkit PR #6](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/6).

**Do not conflate three claims:** (1) **offline original/benign modified wrapper reconstruction** is now demonstrated; (2) SWDL metadata/variant handling is a separate layer whose helpers do not establish authenticated acceptance of a modified boot image; (3) **actual NOR updating** is a separate device-specific question. Historical G11 MMX NOR maps contain a 3-MiB `KERNEL_PRIMARY=[0x00760000,0x00A60000)`, matching the logical wrapper size, but this layout has not been verified against this particular MU1440 NOR/PT. A full 64-MiB NOR flash has **not** been established as required, nor has a 3-MiB module-only installer been established safe/accepted. Compressed data means a few altered startup bytes may affect multiple stored sectors. None of this identifies the original PLLX writer, validates an early PLLX write, guarantees timebase/PMIC coordination or authorizes any overclock.
