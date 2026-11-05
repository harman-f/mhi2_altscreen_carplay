# MU1440 R9 — exact QNX clock_init handoff and Stage-2 IFS reservation (2026-10-11)

> **Research status · 2026-11-05:** **HISTORICAL HARDWARE RESEARCH.** Original static or measured evidence only; not an instruction to change clocks, voltage, boot or flash. [Topic index](README.md) · [Current feature evidence](../../status/FEATURE_STATUS.md).


> [!CAUTION]
> **Research only.** Exact-target offline review of the private stock text file `/usr/sbin/startup.sh` (3,184 bytes; SHA-256 `941734dee66b7dd08d92ab428693da8045ed2715188524465a328d6aeebb187d`). Original firmware files are not published. Do not run `clock_init` manually, restart clock/power drivers, modify boot storage, or write PLL/EMC/PMU registers.

**Target:** `MHI2_ER_SKG13_P4526_MU1440`, QNX 6.5, NVIDIA Tegra T30. Related: [R5 RAM_CODE strap](MU1440_TEGRA_RAM_CODE_BOOT_MEMORY_CLOCK_AUDIT_R5_2026-10-11.md), [R6 nvmemctrl MC IRQ handler](MU1440_NVMEMCTRL_MC_ERROR_HANDLER_AUDIT_R6_2026-10-11.md), [R7 ASINFO](MU1440_QNX_ASINFO_BOOT_MEMORY_LAYOUT_AUDIT_R7_2026-10-11.md), [R8 initial binary QNX startup script](MU1440_QNX_STARTUP_SCRIPT_PMU_HANDOFF_AUDIT_R8_2026-10-11.md), [consolidated Tegra clock/timebase audit](MU1440_TEGRA_T30_CPU_CLOCK_POWER_TIMEBASE_AUDIT_2026-10-11.md).

> [!IMPORTANT]
> **R10 follow-up:** The recovered exact `clock_init` binary is now statically audited: [R10](MU1440_CLOCK_INIT_STATIC_AND_IFSLOADER_AUDIT_R10_2026-10-11.md). It does configure clocks, but its two byte-identical named POR PLL tables contain PLLC0/PLLC1/PLLM1/PLLA1/PLLA0, **not PLLX0 or PLLM0**. Additionally, a separately supplied live `ifsloader` report confirms that the 84-MiB `-r` *reservation* corresponds to a **74-MiB actual mounted Stage-2 IFS**, leaving a 10-MiB difference of unverified purpose. Do not manually re-run `clock_init` or `ifsloader` on a running unit.

## 1. New concrete lead: `clock_init`

Lines 11–22 of the recovered plain-text `/usr/sbin/startup.sh` explicitly launch the MC error/IRQ handler, clock resource manager and NVOS before the clock initializer:

```sh
## Launch nvmemctrl: MC Error interrupt handler
nvmemctrl
info "MMX BENCH_Startup static splash"
devg-nvclock -v 1
NVOS_INTERRUPT_PRI=21 devg-nvos &
waitforpoll /dev/nvos 10 20
waitforpoll /dev/nvclock 10 20
clock_init
```

**This is the first exact-target explicit post-kernel clock initialization entrypoint identified.** It is the highest-priority binary for the next offline analysis. The source proves **invocation ordering**, not yet the identity of the program's programmed PLLs, whether it itself sets 900 MHz, whether voltage tracks a PLLX change, or whether QNX qtime is retimed. A live repeat invocation is *not* an acceptable experiment.

The next commands read `/dev/nvsku/project` and `/dev/nvsku/rev` for board/revision-dependent display and later flash-driver branches, not a proven decoded Tegra CPU speedo/fuse or OPP selector. A HighScale-only conditional checks the MCM daisy-chain GPIO and reports suspected T30 VCM solder/PCB connection faults, but **this is a hardware integrity warning branch, not a clock qualification routine**.

## 2. Full second-stage ordering from exact source

| Script order | Action | Interpretation |
| ---: | --- | --- |
| 1 | `random -pt`, `mqueue`, background `ooc-starter.sh` | Early facilities |
| 2 | `nvmemctrl` | R6 confirmed: MC fault IRQ diagnostics |
| 3 | `devg-nvclock -v 1`; background `devg-nvos`; wait for both virtual devices | Required driver APIs |
| 4 | **`clock_init`** | New offline investigation target |
| 5 | Board project/revision reads and integrity/display conditions | Not confirmed silicon speed grade |
| 6 | `display-init-nvidia-tegra2-mmx`, `pipe`, `devg-nvrm`, wait for display controller | Display services |
| 7 | Read `/dev/nvpower/init_lp_state`, launch display starter; I2S/I2C1, early RVC and PCI starters | Peripherals/power handoff |
| 8 | Stage-2 `ifsloader` | See exact reserve match below |
| 9 | `devf-generic-tegra2` NOR flash driver; `mount -ur /mnt/system` | Storage-specific settings, not SDRAM frequency |
| 10 | `tinit &`; `sh /etc/boot/boot.sh` | Remaining application boot chain |

Some steps fork into background; this table is source invocation order, not independently timed completion order.

## 3. R7 84-MiB ASINFO gap now exactly matches R9 Stage-2 loader

The exact original script (line 90) contains:

```sh
ifsloader -r 0x92000000,0x05400000,1 -a 10878976 -m / -v -d /mnt/app/img_restore/main_stage2.ifs.lzo
```

R7's missing-`sysram` window was `0x92000000–0x973FFFFF`. The R9 `-r` region starts at **`0x92000000`** and has **`0x05400000 = 88,080,384 bytes = 84 MiB`** length, hence last byte **`0x973FFFFF`**. This is a strong exact-byte correlation between the QNX map reservation and the Stage-2 IFS load. The `-a 10878976` argument equals `0x00A60000`, but its precise loader semantics were not separately verified.

The `main_stage2.ifs.lzo` file is a later QNX image source **after RAM initialization**. It must not be confused with the earlier Tegra Boot Configuration Table (BCT) or with SDRAM training. R7's `imagefs`/`bootram` aliases also refer to one and the same early QNX region, not two allocations.

## 4. Other clock-looking values are not CPU or DRAM rates

The script's `DEVF_TEGRA_ARGS` includes a `-s0x48000000,64M` argument passed to `devf-generic-tegra2`: this belongs to the NOR-flash driver. Likewise R8's `inpclk=102000000` belongs to the mNAND driver. None of these establishes the CPU PLLX/SDRAM EMC frequency. The reviewed script contains no literal direct `PLLX0=900000`, `PLLM0=750000`, RAM_CODE=2 timing profile or `qtime=450 MHz` configuration.

## 5. Immediate next step: private exact clock_init binary

Run the following **existence/listing only**, then copy the one existing binary unchanged to SD. No invocation or driver restart:

```sh
echo "=== CLOCK_INIT PATHS ==="
echo "$PATH"
for p in /sbin/clock_init /bin/clock_init /usr/sbin/clock_init /usr/bin/clock_init /proc/boot/clock_init /mnt/app/armle/usr/bin/clock_init /mnt/app/armle/usr/sbin/clock_init; do if [ -f "$p" ]; then ls -l "$p"; fi; done
echo "=== END ==="
```

Offline questions: does `clock_init` invoke NVIDIA PLL/EMC getters or setters; which frequencies/board profile are encoded; is 900 MHz selected there or inherited; how the 750/625-MHz EMC mismatch arises; any voltage/PMIC coupling; any QNX clocksource/qtime coordination? A lack of symbol names alone would not prove safe retiming. A separately verified original early QNX startup/BSP and Tegra BCT remain required for initial DDR, CPU and Global Timer calibration.

**No clock, voltage, RAM or flash change is currently proposed.**
