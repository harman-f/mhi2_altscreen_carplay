# MU1440 parity orchestration

The current supervisor is R49. It invokes the single native R50 owner, retries same-stream reopening with cooldown and bounded burst/backoff, rejects concurrent supervisors, and leaves bridge identity, writer exclusion and stock restoration with the native owner. It is not an additional ownership service.

The installed supervisor source SHA-256 is `5f4eb6e5f81dbb9cfc2b396cf0b8c2138ac90957b9156f50976bf3fcb628dde3`. Public source comments have been curated, so the script's byte hash differs while executable behavior is retained. It preserves until-stop operation, finite diagnostic override, temporary/persistent diagnostic selection and optional SD logging. No new defaults or controls are introduced by this publication.

## Command dependencies

The scripts target the direct MMX QNX namespace. Shell syntax/builtins include `echo`, `read`, `test`, `trap` and arithmetic. Runtime commands include `cat`, `grep`, `awk`, `sleep`, `kill`, `pidin`, `rm`, `cp`, `mv`, `chmod`, `mkdir`, `touch`, `mount`, `sync` and the native settings/owner/bridge programs. Enabling the persistent boot hook additionally requires the exact OEM `lsd.sh` preimage and a separately qualified recovery procedure. The optional RCC date path has a fallback and is not a required MMX timestamp command. SD evidence uses the installed M.I.B. mount bootstrap and a real write test; projection can continue with SD diagnostics disabled.

All target-critical volatile state uses flat `/tmp` files. These are installed-layout sources, not relocatable SD package launchers. The helper scripts describe the reference layout; this source publication does not authorize or package their installation. Static checks pass the [QNX shell contract](../../docs/testing/MU1440_QNX_SHELL_COMPATIBILITY.md); host shell syntax does not prove target command availability or complete vehicle acceptance.
