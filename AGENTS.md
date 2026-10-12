# AGENTS.md — mandatory instructions for contributors and AI agents

**Read before proposing, writing, reviewing or packaging ANY on-unit QNX shell command,
script, diagnostic ZIP, test script or deployment** for the MU1440, even when that
artifact is generated outside this repository or shared only in a chat.

1. Read [the canonical, vehicle-evidenced QNX shell/command compatibility contract](docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md) **first**. This is the source of truth for command availability, interactive SSH quirks and evidence scope. Reuse its tested patterns; do not rediscover the same limitations with a Linux-only test.
2. **Do not invoke external `printf` on the target.** Its absence is VEHICLE-PROVEN, repeatedly (including R17.1 MMX inventory). A passing Linux `bash -n`, `ksh -n` or mock PATH does NOT prove target command availability: the host shell may have a `printf` builtin. Use simple `echo` for simple constant/variable-prefixed lines; if exact formatting is needed, use a separately target-verified capability or stop.
3. Do not assume bare stock `sha256sum` or `tee`, `sed`, `tr`, GNU `date` options, GNU tools/flags, `grep 'A\\|B'` alternation, or M.I.B. `apps/sbin` or `config/BASICS` layouts. Only invoke a bundled hash/tee helper with a verified explicit executable path. Scripted `awk` is permitted **when the exact program/host environment was validated**; multi-line interactive copy/paste is not.
4. **MMX and RCC are independent QNX boards.** An MMX `/dev/nvclock`, sensor getter, mount path, command or observed startup frequency is NOT evidence that the same interface exists on RCC. Keep their scripts, evidence labels and logs separate. Unknown endpoint means inventory first, not guessed `cat`/writes.
**Further live R17.2 evidence:** `date` failed with exit code 126 on the MMX
even though the inventory/clock reads completed. Do not require it for target
timestamps; `wall_time=NA` is an honest result. The two stock `nvtmon` raw
text getters can omit a final newline, so always frame a section end with
a deliberate plain `echo` separator and test a no-newline mock. RCC evidence
must be measured independently.

5. **Every command is a dependency.** Before handing over a target script (including private one-off ZIPs), write its command/option/read-path inventory, check it against the canonical contract, and run the repository host-side static gate on **every** target `.sh`/`.ksh` file:
   `python3 tools/check_mu1440_target_shell.py --self-test --check path/to/each-target-script.ksh`
   The gate is necessary, not sufficient; unavailable commands that it cannot recognize must still be checked explicitly. Include a negative fixture that would reproduce the bug; do not mark the artifact vehicle-tested until real QNX output is captured.
6. Keep read-only data collection bounded, with fixed known GETTER paths and stdout output; never silently remount, modify clocks, QNX qtime, CPU voltage/PMIC, NOR, bootloader, driver state, or production app settings. User chooses a previously validated writable output directory and new filenames. Unknown/error output is preserved, not overwritten with an invented PASS.
7. For direct SSH operator instructions, give **one complete logical command per paste**; no live multiline `awk`, unfinished quotation or mixed-shell assumptions. For errors, preserve stdout and stderr, inspect the partial log, correct off-unit and repackage. Do not test a risky fallback interactively.
8. Check the [publication integrity workflow](.github/workflows/publication-audit.yml) and add static guards/tests for new target scripts. **Do not limit compatibility tests to `deployment/mu1440` and `runtime` and then treat standalone diagnosis artifacts as tested**. When a source ZIP is prepared outside Git, run the checker explicitly against its extracted target scripts, and report that it was not covered by GitHub CI unless actually committed/tested there.

Evidence labels: **VEHICLE-PROVEN MMX**, **VEHICLE-PROVEN RCC**, **STOCK-FIRMWARE STATIC**,
**HOST-ONLY TEST / MOCK**, and **NOT TESTED** must not be conflated. The detailed compatibility
document and source-specific reports contain dates and applicability; this root file exists to
make their preflight impossible to miss.

For firmware extraction tooling (run on a workstation, NOT QNX) use that project's
own agent and tool documentation instead of transplanting target-shell constraints.
