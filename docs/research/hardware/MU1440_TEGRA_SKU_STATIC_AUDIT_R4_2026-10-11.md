# MU1440 Tegra T30 — SKU library static audit R4 (2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


**Classification:** exact-target static, read-only. No running device was modified, no vendor binary published, no CPU speed grade or overclock qualified.

## Provenance

- Private original: `/lib/libnvsku.so` (SD backup `MU1440_libnvsku.stock.so`), 8,192 bytes.
- SHA-256: `4758c10c3c8c37f87024682740b43022ad1327ca5a815a1e4299a36de0e2ca2c`.
- ELF: stripped, 32-bit little-endian ARM EABI5 shared library; build note `NAME=libnvsku.so`, `DATE=2017-03-07PST-14:26:31`, `STATE=experimental`, `VERSION=qnx650`, `TAGID=17.45.06-8589238`.
- PT_DYNAMIC: only `libc.so.3` NEEDED; imports `open64`, `read`, `close`, and `strtoul`.
- This analysis used the private original for inspection and a temporary copy with reconstructed ELF section metadata for ARM disassembly. The original was not rewritten or executed.

## Actual exported functions and exact-target call paths

| Export | Original VA | Approx. size | Reads | Behavior |
| --- | ---: | ---: | --- | --- |
| `is_base_board_e1888` | `0x260` | `0x90` | `/dev/nvsku/e1888` | Opens read-only; reads one byte; returns false for ASCII `0`, true for any other successfully read byte; defaults to false for open/read failure. |
| `get_board_rev` | `0x2f0` | `0x94` | `/dev/nvsku/rev` | Opens read-only, reads up to 9 bytes into zero-initialized local buffer, `strtoul(..., NULL, 10)`, closes. Open/read failure yields `-1`. |
| `get_board_sku` | `0x384` | `0x94` | `/dev/nvsku/sku` | Same decimal-value wrapper as above. |
| `get_board_proj` | `0x418` | `0x94` | `/dev/nvsku/project` | Same decimal-value wrapper as above. |

Original embedded path strings are at approx. `0x4ac` (`e1888`), `0x4c0` (`rev`), `0x4d0` (`sku`) and `0x4e0` (`project`); dynamic export names are in the ELF dynstr table. No code path in this tiny library reads `/dev/nvsku/prod_sku`, CPU speedo, fuse registers, PLLX, voltage rails or the PMIC. No extra NVIDIA dynamic library dependency is present.

**Interpretation:** This library does not determine the Tegra CPU's approved speed grade. It simply delegates to the separate running `devg-nvsku` QNX resource manager. A reported board `sku=0001` / `rev=900` must not be interpreted as decoded chip speedo, clock OPP, or confirmation that 1.3/1.4 GHz is approved. The `e1888` flag is a board identity test, not a fuse qualification. In the earlier exact-target `devg-nvpower` audit, its `get_board_sku`, `get_board_proj` and `get_board_rev` dependencies therefore carry these same limitations.

## Next discriminating evidence (read-only)

1. Locate and privately copy the *actual* `devg-nvsku` binary to inspect how the virtual files are populated and whether it references fuse/ODM/strap/product/board information. Do not publish proprietary bytes.
2. Enumerate `/dev/nvsku` names and permissions, and preserve the already observed output of known read getters; do not assume every apparent pseudo-file is a passive getter.
3. Trace Tegra fuse/speedo/PMIC and the Harman BSP/startup QNX Global Timer configuration separately. There is no evidence yet that `libnvsku` can answer either question.
4. Continue with `mibr-tegradiag` read-only; keep clock setter/voltage experiments disabled. A verified industrial fixed 900-MHz reference operating point and the generic 1.7-GHz PLL parameter are not silicon qualification evidence.

### Target-only safe discovery commands

```sh
ls -l /sbin/devg-nvsku /lib/libnvsku.so
ls -l /dev/nvsku
pidin ar | grep devg-nvsku
```

If `/sbin/devg-nvsku` exists, copy it *unchanged* to the SD test directory for offline upload; avoid process restart or probing setter nodes. The R4 result should be cited from the consolidated [MU1440 Tegra T30 audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).
