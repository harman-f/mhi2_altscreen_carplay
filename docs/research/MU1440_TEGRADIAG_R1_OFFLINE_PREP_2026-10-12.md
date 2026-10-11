# MU1440 TegraDiag R1 — offline-prepared, stock-only evidence logger (2026-10-12)

**Target:** `MHI2_ER_SKG13_P4526_MU1440` / Tegra T30 / QNX 6.5. This note preserves the provenance/status of a separately delivered **private ChatGPT-session source kit**, rather than committing a generated file that has not been run on the hardware. **NO** target clock, power, PMIC, voltage, NOR, qtime or firmware writes; no stress/load generator.

Start with the [consolidated CPU/power/clock/timebase research overview](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md). Its source lineage is [R11 original runtime clock API](MU1440_NVCLOCKAPI_FRONT_BACKEND_SPECIAL_CLOCK_AUDIT_R11_2026-10-11.md), [R12 first-stage OEM source](MU1440_BOOT_CHAIN_FIRST_STAGE_SOURCE_AUDIT_R12_2026-10-11.md), [R13 direct PLLX getter and QNX initial qtime/2](MU1440_FIRST_STAGE_CPU_CLOCK_QTIME_XREF_AUDIT_R13_2026-10-11.md), [original Stage-1 wrapper/flash boundaries](MU1440_STAGE1_OEM_WRAPPER_ROUNDTRIP_AND_NOR_BOUNDARIES_2026-10-11.md), and [R14 source-only Codex handoff, Issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41).

## What actually exists in the private R1 kit

| Item | Action | Verification |
| --- | --- | --- |
| `mibr-tegradiag-r1.ksh` | Host-authored bounded stock QNX script, 1–60 samples (15 default), 2-second **pause between** readings (not a precise sampling period), stdout CSV+commented qtime snapshots | `sh -n` PASS; mock command run PASS; **real QNX ksh/unit NOT YET TESTED** |
| `tegradiag_analyze.py` | Offline Python-standard-library R0/R1 log parser; 1–3 labeled log comparison with input SHA-256 provenance, missing/truncation/unstable readback warnings; JSON+Markdown output into fresh directory | Nine Python 3.13 unit tests PASS; 3 synthetic labeled test logs PASS |
| `README.md`, `TOMORROW_TEST_PLAN.md` | Operating boundaries, input/output syntax, acceptance checklist | Reviewed offline; instructions do not call setter or performance controls |
| `tests/`, `examples/SYNTHETIC_*`, `SHA256SUMS` | Mock fixture, parser regression and example output | Synthetic data explicitly NOT genuine vehicle readings |

Private delivered archive basename `MU1440_TEGRA_R1_OFFLINE_KIT.zip`; **17,475 bytes**, SHA-256 `37af17f14d1227befd1f3990a3b8f66144c4e63cf495c57aaae032692c8e42c0`. Archive fresh-open, testzip and each internal SHA256SUMS entry passed. This public note intentionally does not distribute actual firmware/board bytes or claim that a private chat-session download link is a durable GitHub asset. The complete kit is separately attached in the conversation.

## Strict interface boundary

Production logger contains only these fixed, previously observed *read-only* target paths: `/dev/nvclock/get_source_clk_freq/PLLX0`, `/dev/nvclock/get_pll_status/PLLX0`, `/dev/nvtmon/current`, `/dev/nvtmon/current_local`, and `/dev/nvclock/get_device_clk_freq/{G3D,VDE,HOST1X,EMC}`, together with `pidin syspage=qtime` snapshots. The script accepts only sample count; user cannot supply arbitrary virtual-device paths. No clock setter, load generator, driver restart, I2C/PMIC access or auto-fallback is present.

CSV schema (exact order):

```text
sample,wall_time,PLLX0_kHz,PLLX0_status,CPU_temperature_C,local_temperature_C,G3D_kHz,VDE_kHz,HOST1X_kHz,EMC_kHz,VDD_CPU_mV
```

Unknown/failed getters return `NA`. `VDD_CPU_mV` is always `UNAVAILABLE`: the exact original generic `NvRmPmuGetVoltage`'s `1200` is a **hardcoded stub constant**, NOT an independently measured CPU rail voltage. No stress safety or thermal limit is inferred from a brief stock log. Original R13 proves the initial qtime rate calculation, not dynamic timebase recalibration during a PLL change.

## Optional next stationary, stock-only session

When the vehicle is available, first review the local script, copy it only into an already writable diagnostics/SD directory and invoke it with `/bin/ksh` while deliberately saving stdout to a NEW chosen filename (not a stock path). Three *separately labeled* sessions: Idle, CarPlay main only, and CP+VC111 only when a real 111 video stream is visibly active. Do not run while driving; recording is voluntary and can wait for convenient weather. The host analyzer can compare these three captures later; its simulated outputs are not a vehicle validation.

## Remaining gates

The [R14 issue #41](https://github.com/harman-f/mhi2_altscreen_carplay/issues/41) collects original variant-/70/ wrapper and archival backup provenance, exact-device flash/Recovery evidence where independently grounded, and any genuine **read-only** CPU rail measurement source. The known original /50/ OEM-exact wrapper roundtrip is documented in the [merged Toolkit guide](https://github.com/harman-f/MHI2-MHI2Q-MH2P-Firmware-Toolkit/blob/main/docs/MU1440_STAGE1_OEM_OFFLINE_ROUNDTRIP.md), but does not establish device acceptance, a safe full- or partial-NOR flash, or a validated CPU overclock. R1 is a useful baseline instrument, not an experimental clock-control agent.
