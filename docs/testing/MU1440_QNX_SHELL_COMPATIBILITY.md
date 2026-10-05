# MU1440 QNX shell / command compatibility

Target: `MHI2_ER_SKG13_P4526_MU1440`  
Context: direct SSH / MMX QNX shell

This file records exact-target command constraints that matter to this repository's developer
deployment. It exists because desktop Linux habits are not a safe compatibility model for the unit.

## Operator command rule

For direct SSH copy/paste, use **one logical command per paste**.

Avoid interactive multi-line constructs such as multi-line `awk` programs, shell functions or
unfinished quotes. An incomplete paste can leave the QNX shell at the continuation prompt `>`.
Recover with Ctrl+C before entering another command.

Prepared script files may contain multi-line shell/awk programs; that is a different execution path
and several such exact programs have already been vehicle-tested.

## Confirmed exact-target limitations

### external `printf`

Not available in the tested direct runtime PATH.

Observed:

```text
./gen2_nav_config.sh[459]: printf: cannot execute - No such file or directory
```

Runtime scripts use `echo` for the required simple line writes instead.

### stock `sha256sum`

Do not assume it exists.

The guarded public developer package carries its own reproducibly built QNX ARMv7
`payload/sha256sum` and uses that exact helper by default.

### `sed` / `tr`

Do not make either a vehicle runtime dependency. `sed` is missing on some older firmware trains, so the stable deployment removed its only required use in favor of stock `awk`. Earlier live-monitor work also had to remove `tr`.

### GNU `date` behavior

Do not assume GNU formatting/options. Runtime code uses the known RCC date path only as a best-effort
timestamp source and has a fallback.

### grep alternation

Do not rely on desktop BRE alternation such as:

```text
grep 'A\|B'
```

Use separate fixed-string checks where correctness matters.

## `/tmp` / `/dev/shmem` semantics on MU1440

Vehicle-confirmed on the reference `MHI2_ER_SKG13_P4526_MU1440` target on 2026-10-05:

```text
/tmp -> /dev/shmem
```

The same test file addressed through `/tmp` and `/dev/shmem` reported the same inode, so
`/tmp` must be treated as the QNX shared-memory filesystem on this target, not as a normal
disk-backed Unix `/tmp`.

### What is confirmed to work

A native QNX ARMv7 vehicle probe on 2026-10-05 measured the actual syscall behavior below
`/tmp -> /dev/shmem`:

```text
open_excl_create rc=3 errno=0 strerror=OK
open_excl_collision rc=-1 errno=17 strerror=File exists
write rc=17 errno=0 strerror=OK
fcntl_F_SETLK rc=-1 errno=89 strerror=Function not implemented
fsync rc=-1 errno=89 strerror=Function not implemented
close_write_fd rc=0 errno=0 strerror=OK
rename rc=-1 errno=18 strerror=Improper link
open_readback rc=-1 errno=2 strerror=No such file or directory
unlink_final rc=-1 errno=2 strerror=No such file or directory
```

This directly qualifies atomic flat lock creation with `O_CREAT|O_EXCL`, ordinary writes and
close. A separate direct-write vehicle check also confirmed that shell redirection truncates an
existing flat `/tmp` file correctly: after writing a longer value, `echo X > file` left a
2-byte file containing only `X\n`.

The native gate status publisher independently confirms flat create/truncate/write/close behavior
for `/tmp/mibr-alt111-native-gate.status`.

### Native `rename()` is not available inside `/tmp -> /dev/shmem`

The same native probe proved that `rename(old, new)` fails reproducibly with:

```text
errno=18 strerror=Improper link
```

This is the concrete cause of the first live `dual-temp` failure:

```text
result=APPLY_FAILED journal
```

The earlier shell test using `mv old new` returned success, but that must not be interpreted as
native-`rename()` support. The shell utility can fall back to copy+unlink when `rename()` fails.
For native settings transactions on this target, temp-file-plus-rename is therefore invalid.

### `fsync()` on volatile shared-memory files

The target-native probe also measured:

```text
fsync rc=-1 errno=89 strerror=Function not implemented
```

The settings layer already tolerated `ENOSYS` for volatile `/dev/shmem` files, so `fsync()`
was **not** the journal failure. A short-lived hypothesis that `EINVAL` might be the vehicle
failure was disproved by the native probe and must not be used as target evidence.

The current target contract is therefore narrow: tolerate the vehicle-proven `ENOSYS` result for
volatile settings files, keep every other `fsync()` error fail-closed, and do not generalize this
exception to persistent filesystems.

### Transaction design without `rename()`

The replacement transaction design uses only target-proven flat-file primitives:

- `O_CREAT|O_EXCL` for the settings lock and one-shot transaction markers;
- direct truncate/write for backups and active temporary settings files;
- `unlink()` for marker cleanup;
- no native `rename()` below `/tmp`.

Crash recovery uses two flat markers. New transactions write a `schema=2` journal completely
first. Then `mibr-alt111-settings.journal-armed` is created exclusively. Active settings may only
be rewritten after the armed marker exists.

This yields three recoverable schema-2 states:

- journal without armed: transaction died before active mutation; discard the unarmed journal;
- journal plus armed: active mutation may have started; restore every affected group from validated backups;
- armed without journal: journal removal already crossed the commit point; only remove the stale armed marker.

Upgrade compatibility is intentionally fail-safe. The previous rename-based implementation wrote
`schema=1` journals and had no armed marker. A schema-1 journal without armed therefore **cannot**
be treated as pre-mutation; it follows the legacy validated-backup rollback path. This prevents an
upgrade from discarding recovery state left by an older binary.

This preserves explicit crash recovery without relying on filesystem semantics the MU1440 target
does not provide.

### What must not be assumed

Do **not** use POSIX advisory record locking on a file below `/tmp` as a MU1440 synchronization
primitive.

The first target implementation of the settings layer created
`/tmp/mibr-alt111-settings.lock` and then used `fcntl(F_SETLK)`. The lock file itself was created
successfully, but even a read-only settings query failed reproducibly with:

```text
result=BUSY settings_lock
```

No settings journal and no rollback barrier were present. The failure reproduced for both a settings
read and the `dual-temp` write path. Because the settings implementation mapped any
`F_SETLK`/related lock setup failure to the same result, this exposed an invalid Linux-style
assumption in the target settings layer rather than evidence of a real competing writer.

Also do **not** make directory creation below `/tmp` a required synchronization primitive on this
target. Vehicle testing found that `mkdir` is not a usable replacement there. Keep volatile target
state flat unless a directory operation has been independently demonstrated on the exact firmware.

### Current synchronization rule

Cross-process settings synchronization must therefore avoid both:

- `fcntl(F_SETLK)` / POSIX record locking on `/tmp`;
- directory-lock schemes below `/tmp`.

The current replacement uses an atomic flat lock-file create with
`open(..., O_CREAT|O_EXCL, 0600)` on a new `mibr-alt111-settings.lock-v2` path. This
exclusive-create behavior is now vehicle-qualified on the reference MU1440. The file records the
owner PID. A pre-existing V2 lock is reclaimed only when `kill(pid, 0)` proves the recorded owner is
gone with `ESRCH`; success, `EPERM`, malformed/empty owner data and all other errors remain
fail-closed. This is required so a process killed in the middle of a settings transaction does not
permanently block the explicit journal-reconciliation path.

The old `mibr-alt111-settings.lock` file may remain present from the record-lock implementation.
Its mere existence is not proof that a process owns a lock and it must not be used as a stale-lock
heuristic.

### Portability implication

Code shared between Linux host tests and QNX target runtime must not infer ordinary filesystem
locking semantics from the pathname `/tmp`. Target synchronization primitives need an explicit
MU1440 qualification step, and failure paths should identify the primitive that failed rather than
collapsing unrelated `fstat`, descriptor-flag and lock failures into a generic `BUSY` result.

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
