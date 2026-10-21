# MU1440 R15: direct original MMX fs0 native partition / Primary-Stage-1 evidence (2026-10-12)

**Research-only read-only result, not a flashing/overclocking procedure.** Distinguish **MMX/Tegra** 64-MiB NOR from the independent **RCC** fs0 image examined in R14. The public report contains hashes, offsets and findings, no original NOR data or reconstructed/altered OEM image. Companion detailed upstream [Firmware Toolkit PR #8](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/8); [R14 RCC audit PR #7](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/7).

## 1. Source provenance correction

The newly user-uploaded 67,108,864-B MMX fs0 SHA-256 `4011a8b81bf3a785673d9e1868d270fd37c3c6daeb2c77f0d119e10e583f0094` is independently matched to **BACKUP-SNAPSHOT-06** in the existing R14 sanitized archive catalog, not the earlier requested BACKUP-SNAPSHOT-10 MMX hash `e9d65a0b18974054e119334e320ddc7963704830dedff4fbd957670e14ca7463`. Both records carry a MU1440 train label; neither substitutes for proving the *currently installed car's* raw flash bytes.

## 2. What is no longer just historical MMX NOR speculation

Original region `[0,0x40000)` contains **four byte-identical 64-KiB BCT copies** (content redundancy proven; BootROM integrity/acceptance not assessed). PT `[0x40000,0x60000)` contains **64 byte-identical 2-KiB PT blocks**, each directly decoded to 13 named, contiguous start/count/end entries using 0x800-byte logical address units. All 13 ranges span exactly 64 MiB. The native on-storage map is the historical G11 **Normal** variant, not H22:

| Real original PT entry | Start | End exclusive | Size |
|---|---:|---:|---:|
| BCT | `0x00000000` | `0x00040000` | 256 KiB |
| PT | `0x00040000` | `0x00060000` | 128 KiB |
| STAGE1_RECOVERY | `0x00060000` | `0x000A0000` | 256 KiB |
| STAGE2_RECOVERY | `0x000A0000` | `0x000E0000` | 256 KiB |
| STAGE1_PRIMARY | `0x000E0000` | `0x00120000` | 256 KiB |
| STAGE2_PRIMARY | `0x00120000` | `0x00160000` | 256 KiB |
| **KERNEL_RECOVERY** | **`0x00160000`** | **`0x00760000`** | **6 MiB** |
| **KERNEL_PRIMARY** | **`0x00760000`** | **`0x00A60000`** | **3 MiB** |
| MAIN_STAGE2 | `0x00A60000` | `0x03460000` | 42 MiB |
| SWDL | `0x03460000` | `0x03480000` | 128 KiB |
| SPLASH | `0x03480000` | `0x03600000` | 1.5 MiB |
| SYSTEM | `0x03600000` | `0x03800000` | 2 MiB |
| PERSIST | `0x03800000` | `0x04000000` | 8 MiB |

Original STAGE1_RECOVERY and STAGE1_PRIMARY **complete** 256-KiB regions match byte-for-byte; STAGE2_RECOVERY and STAGE2_PRIMARY are likewise identical. Their respective **kernel** images are NOT identical: Recovery is an independently complete 6-MiB `ANDROID!` container.

## 3. Definitive original update-member ↔ installed Primary provenance (THIS BACKUP)

Raw KERNEL_PRIMARY SHA-256 `65584560cb3c31abed1b2fadf33b45b0fbf6d4758346055867cf1339aac83a14`, starts `ANDROID!`. Compared against R14 privately archived OEM **variant-70** exact 3-MiB transport member (SHA-256 `511bdba0f12e8a7510930ca689f7a9020656c777b11301c7eb70176825f7af0a`), **only FOUR byte positions** across the entire 3 MiB differ: original relative offsets `0x1, 0x3, 0x5, 0x7`, the distinct outer magic. Normalize only OEM transport magic `41 FF 44 FF 4F FF 44 FF` into installed ASCII `ANDROID!` and all **3,145,728 bytes match** the physical PT-designated Primary. Original /50/ does not match. Installed zlib payload decodes to the full exact known /70/ original kernel, SHA-256 `f3e9098cd9eadd48cf65a9e1dc28481be4894b64c765956046abf286ea078465`, and the identical known 106,760-byte primary startup SHA-256 `9a7d54a69a5672cf13e532b262670b3ab4146d1e4d942b6cd2424a346a223b39`. Independent QNX startup and ImageFS additive sums both equal zero.

This converts [R13's packaging/NOR hypothesis](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md) from size correspondence alone into direct physical-original provenance in one archived source. It is NOT an accepted altered-image SWDL transaction or evidence a four-byte NOR edit is possible in a compressed kernel.

## 4. Solved second outer-header checksum at `0x7FC`

Original directly installed Primary AND Recovery each satisfy both:
- `LE32(image+0x264) == CRC32(image[0x800:0x800+kernel_size])` (Primary `0xD15EE9A7`, Recovery `0xA240F2F9`).
- **`LE32(image+0x7FC) == CRC32(image[0:0x7FC])`** using installed `ANDROID!` first-page magic (Primary `0x9A964B9D`, Recovery `0x6B7E72CC`).

The original OEM SWDL /50/ and /70/ 3-MiB members have **the CRC of their installed normalized `ANDROID!` header**, NOT a CRC over the raw `A FF D FF O FF D FF` transport-header bytes. The matching expected values after normalizing only the original eight magic bytes are /50/ `0x89513F41` and /70/ `0x9A964B9D`. This resolves one former R12–R14 blocker; the exact meanings of `0x260/0x400`, any additional authentication, and altered-image boot acceptance remain open.

Recovery cleanly decodes 5,572,424 compressed bytes to a different full **12,959,872-B QNX kernel**, with ImageFS 12,853,104 B, valid separate QNX additive sums, and distinct startup hash `94b75646b7266f2deb619d04de1cadbc956e475b3a729d1e0035c5fee86eb821`. There are 115 differing startup bytes relative to PRIMARY, which was not an exact Recovery code duplicate. MAIN_STAGE2 actually starts `0xA60000` with `LZOZ`, 2,097,152-B expanded block size and **37** contiguous declared nonzero compressed block lengths.

## 5. Effect on original overclock/boot research

**Resolved offline on THIS archived image:** physical Primary/Recovery boundaries from a *native* partition table, the exact installed /70/ mapping, both outer CRC fields, a complete independently parsed Recovery and redundant original BCT/PT and small loader areas. This supports the hypothesis that a 3-MiB logical Primary is a separate on-storage unit and reinforces why rewriting **all 64 MiB** could unnecessarily endanger BCT/PT and intact Recovery.

**Not yet resolved:** current car's unit-specific raw identity; actual bootloader authentication or a changed-image acceptance test; physical NOR erase/program block sizes; a verified selective SWDL/primary-write route and independent rollback/recovery; initial pre-QNX PLLX writer, CPU VDD voltage measurement/PMIC, safe runtime Global Timer/qtime retiming or any validated OC operating point. PT's logical 2-KiB block is not NOR physical erase geometry. No image has been altered, booted, flashed or tested on vehicle.

**Related:** [consolidated clock/power/timebase research](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md), [R12 first-stage source](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md), [R13 direct PLLX / qtime /2 ARM XREF](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md), [R13 OEM exact wrapper roundtrip](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md), [Toolkit R15 upstream details in PR #8](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/pull/8), [R14 acquisition Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41).
