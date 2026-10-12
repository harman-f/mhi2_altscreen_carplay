# MU1440 QNX shell / command compatibility

Target: `MHI2_ER_SKG13_P4526_MU1440`  
Context: direct SSH / MMX QNX shell

This is the **canonical mandatory preflight contract for ALL on-unit QNX shell material**, including
MMX and RCC runtime, developer deployment, ad-hoc read-only diagnosis, keypanel probes, boot/clock
inventory, one-off shell snippets and **ZIPs prepared outside this repository**. It exists because
desktop Linux habits are not a safe compatibility model for the unit.

Read together with [root AGENTS.md](../../AGENTS.md) and invoke
`python3 tools/check_mu1440_target_shell.py --self-test --check <every-target-script>`
on the HOST **before** a target-side copy/test. The checker does not establish real hardware support:
the exact board must subsequently confirm each unproven command/option and the output. The
repository CI previously scanned only `deployment/mu1440` and `runtime`; a private R17.1 diagnostic
bundle bypassed that scan, despite this file documenting absent external `printf`.

## Operator command rule

For direct SSH copy/paste, use **one logical command per paste**.

Avoid interactive multi-line constructs such as multi-line `awk` programs, shell functions or
unfinished quotes. An incomplete paste can leave the QNX shell at the continuation prompt `>`.
Recover with Ctrl+C before entering another command.

Prepared script files may contain multi-line shell/awk programs; that is a different execution path
and several such exact programs have already been vehicle-tested.

## Confirmed exact-target limitations

### external `printf` — hard target prohibition

**VEHICLE-PROVEN ABSENT on the MMX; never assume a shell built-in will rescue it.**
Not available in the tested direct runtime PATH.

Observed:

```text
./gen2_nav_config.sh[459]: printf: cannot execute - No such file or directory
```

Runtime scripts use `echo` for the required simple line writes instead. The same failure reoccurred in the separately distributed
R17.1 MMX inventory (2026-10-12): `mibr-mmx-inventory-r17.ksh[16..31]: printf:
cannot execute - No such file or directory`. Audit showed that **all three** R17.1 target
scripts (MMX inventory, TegraDiag recorder, RCC baseline) used `printf`. Their Linux
mock/syntax checks had passed because they did not model this command restriction.
The R17.2 replacement uses simple `echo` for simple lines and keeps machine-readable
record delimiters; never reuse the superseded R17/R17.1 target scripts.

### stock `sha256sum`

Do not assume it exists.

The guarded public developer package carries its own reproducibly built QNX ARMv7
`payload/sha256sum` and uses that exact helper by default.

### `sed` / `tr`

Do not make either a vehicle runtime dependency. `sed` is missing on some older firmware trains, so the stable deployment removed its only required use in favor of stock `awk`. Earlier live-monitor work also had to remove `tr`.

### R17.2 direct-MMX live evidence: `date` is not executable (2026-10-12)

The actual R17.2 MMX inventory ran to `# FINISH status=COMPLETED`, but
the optional timestamp section logged `date: cannot execute - No such file or
directory` and `# END timestamp exit_code=126`. The TegraDiag recorder
similarly produced valid numeric samples with `wall_time=NA`. **Do not make
`date` (even without GNU options) a mandatory MMX diagnostic dependency.**
Use sample ordinal and QNX syspage/qtime snapshots instead; a matching `RCC`
command still requires independent RCC-side evidence.

A second exact-target finding: `cat /dev/nvtmon/current` and
`cat /dev/nvtmon/current_local` return bare numeric text without final newline
(in this run `033` and `027`). The R17.2 shell collector concatenated
`# END ...` directly onto those values. A target script must add an explicit
plain `echo` separator **after** each command before the `# END` delimiter;
a host parser must include no-trailing-newline device fixtures. The real samples
remain usable; R17.2 host inventory parser's 2 section-boundary warnings reflect
output framing, not a failed sensor getter. Never turn an optional section
failure into an unconditional complete-success claim.

### GNU `date` behavior

Do not assume GNU formatting/options. Runtime code uses the known RCC date path only as a best-effort
timestamp source and has a fallback.

### grep alternation

Do not rely on desktop BRE alternation such as:

```text
grep 'A\|B'
```

Use separate fixed-string checks where correctness matters.

## `awk`: important distinction

`awk` is **not banned**.

The exact MU1440 has successfully executed the project’s scripted `awk` transformations in the
vehicle-proven gate/CarPlay tooling, and `gen2_nav_config.sh` used its small status parsers during
the successful live composition tests.

What is not safe is treating an interactive multi-line `awk '...'` paste as an operator-friendly
command. The shell/paste failure that motivated this document happened in that interactive form.

The developer installer now checks that `awk` exists **before persistent mutation**.

## Proven direct-shell patterns

Examples repeatedly used on the reference vehicle:

```sh
cd /net/mmx/fs/sda0/esd/carplay-test
cp source destination
mv source destination
rm -f file
touch file
cat file
grep -n -F 'literal' file
grep '^prefix=' file
pidin fds 2>/dev/null | grep 'isoTX2'
mount -uw /net/mmx/fs/sda0/
mount -ur /net/mmx/fs/sda0/
mount -uw /mnt/app
mount -ur /mnt/app
sync
sleep 1
```

QNX `on -d -f mmx` is vehicle-proven inside the audited Auto-Direct scripts.

## SD and persistent mount state

Readable is not writable.

The SD card may return read-only after reboot. Persistent application/system filesystems are also
normally read-only. Every mutator must remount the filesystem it owns and restore the expected
read-only state after the write.

Do not make a previous menu action or manual remount an implicit prerequisite.

## Standalone developer-package dependency model

The prepared SD package is now independent of an existing M.I.B. card layout:

- no `config/BASICS` / GLOBALS bootstrap;
- no `apps/mounts` helper;
- no `/apps/sbin/sha256sum` fallback;
- no firmware/M.I.B. `tee` dependency; the package carries its own QNX ARMv7 `payload/tee`.

The project-supplied command-line compatibility binaries required by the deployment are `payload/sha256sum` and `payload/tee`. The native project payload also contains the feature binaries
`libaltscreen111.so`, `direct-ts-remux` and `libmibr_isotx2_gate.so`, but these are functional
components rather than replacements for missing shell utilities.

Mandatory firmware/QNX commands used by the install/runtime path are fail-closed in the top-level
preflight: `mount cp mv chmod sync mkdir rm touch sleep grep awk wc cat pidin on slay`, plus
`/bin/sh`, `/bin/ksh` and `/eso/bin/apps/dmdt`.

Some diagnostic-only paths also try tools such as `tail`, `netstat`, `ls`, `uname`, `use` or
`strings`. Those calls are optional/fallback diagnostics and are not installation prerequisites.

## Developer-package preflight

Before changing persistent files, `deployment/mu1440/install.sh --check` validates:

- bundled SHA-256 helper;
- exact MU1440 `libairplay.so` hash;
- exact published GEN2/remux/gate hashes;
- required runtime files;
- the exact command set used by the current install/runtime;
- inventory/archive of conflicting or foreign Java bootclasspath state before any replacement;
- DisplayManager gate patchability;
- exact NavIgnore presence/hash, either from `payload/` or an already-installed target copy.

Unknown state is fail-closed.

## Regression rule

A runtime/deployment shell change should not introduce:

- external `printf`;
- bare dependency on firmware `sha256sum` or `tee`;
- a dependency on M.I.B. `config/BASICS`, `apps/mounts` or `/apps/sbin`;
- an interactive multi-line patch procedure as the normal install path;
- a persistent mutation before tool/hash/target preflight;
- an assumption that a readable SD or persistent filesystem is writable.

The public CI checks the first deployment-level regressions automatically.


## Contract for every new MMX/RCC diagnostic handoff — hard gate (2026-10-12)

**Why a repeated regression occurred:** the existing publication CI already prohibits
`printf` in the committed `deployment/mu1440` and `runtime` directories, but our
standalone source ZIP was built outside those locations. Linux mock tests also used a
shell with its own `printf` builtin. Passing a syntax check or mock says **HOST-ONLY**,
never **VEHICLE-PROVEN** command availability.

Before providing any copyable QNX command or downloadable diagnostic ZIP:

1. Declare **MMX or RCC**, exact firmware/board and evidence grade. Do not transfer an MMX
   command/device path to RCC by inference. On RCC, stock `pidin`, `ls`, `date`, and
   `uname` still need their own target validation; do not claim proven until observed there.
2. Inventory **all** executable names, shell builtins, option/format assumptions and
   `/dev` getter paths used in **every** delivered `.sh`/`.ksh`, not just the entrypoint.
   Use only exact-board tested endpoints; treat each new dependency as unproven.
3. For an external handoff ZIP, extract it on the PC and run the project's host checker
   against all target scripts. Run its negative/self-test; inspect shell source manually
   for dynamically assembled commands. A host `bash -n` is additional syntax verification,
   NOT a capability test. When a command cannot be established, remove it or make it an
   explicit failure/optional result rather than guessing a Linux replacement.
4. **Forbidden as unbundled assumptions:** external `printf`; `sed`, `tr`; stock
   `sha256sum` or `tee`; GNU-only `date`, `grep` alternation `A\\|B`, and GNU option
   extensions. The last four points may be used only with documented exact-board
   confirmation or with the intended explicitly verified compatible bundled helper.
   Shell `echo` with uncomplicated single-line text is proven on MMX. Do not rely on
   `echo -n` or portable backslash-escape interpretation.
5. Use a **new user-chosen writable diagnostics path**. Scripts emit stdout by default;
   caller redirects to a new log. Capture stderr/exit codes and preserve partial logs.
   No implicit remount or write to a production flash/application partition for a
   read-only collector.
6. Maintain per-artifact evidence: files/commands scanned, mock negative fixture,
   syntax result, parser regression result, SHA-256 manifest, exact tested hardware,
   errors, and outstanding NOT TESTED gates. When a real unit rejects a command,
   update this canonical record and its guard *before* producing the replacement.

**CI scope:** GitHub scans committed vehicle runtime/deployment code; it cannot
automatically inspect private archives attached to conversations. For these, the
host checker is a mandatory explicit packaging step. This distinction must be
disclosed rather than calling a Linux-only shell simulation “QNX-validated”.
