# Type-111 firewall: additive installer step and rollback contract

**Status: design contract; not yet implemented in the public installer.**
Target for the initial qualification: exact Skoda MU1440/P4526. The firewall
is one normal install substep, like a change to an OEM JSON or launcher file;
it is **not** a separate major research/rollout project.

## Expected outcome

Ensure the currently configured/advertised CarPlay Type-111 TCP port (typically
**6031**) is permitted inbound on the **carplay0** interface in every existing
PF profile that the target firmware can load. A file's hash need not match
stock or a known reference to be safely updated. Preserve SSH port 22 and
any other third-party rules.

Two *reference*, not mandatory replacement, states exist:

- **OEM_STOCK:** bytes from independently verified exact target firmware
  (variants 50/70 may be compared as reference).
- **MIBR_TARGET:** the four saved files from the 2026-10-25 owner-unit
  snapshot, which represent the owner's *desired working policy*, not an
  exact-format requirement for every other firmware or installation.

Known MIBR_TARGET SHA-256 from K5:

| Profile | SHA-256 |
| --- | --- |
| pf.conf | 029079e992dd12a6e3c242b90b6bb6293f3e9d93d5ef87481c8c2f0d196aa031 |
| pf.ecm0.conf | e1f2125bdf3a31516890293ef31e78de098b82b88a6d6b7a47b70486ede99cb2 |
| pf.mlan0.conf | c6b01dcb72a7a33f0fbf95c6bc6710483676e12fdb8b63167f78da77a50a12ba |
| pf.ppp0.conf | 9df94378fe607ac1fad241d2d0eac913eeafe5e4c567833ffed95f66ae82e7ab |

The exact mounted source and loaded /etc profile are target-specific.
Do not invent missing profiles: enumerate relevant existing pf*.conf files
and inspect startup/reload logic as part of ordinary installer preflight.

## Minimal algorithm (integrated into the ordinary installer)

1. **CHECK (read-only):** inspect actual existing profiles, their hashes,
   the effective TCP allowlist on carplay0, and the configured Type-111 port.
   If the port is already allowed by a direct member or range and rule order
   is correct, report ALREADY_ALLOWED and perform **no write**. A textual
   occurrence of 6031 in an unrelated rule is not proof of access.
2. **PREPARE:** for every existing relevant profile missing the permit, alter
   **only** its existing carplay0 inbound TCP allowlist. Example: change one
   member 6030 to 6030:6031, or add 6031 to the same brace list. Preserve
   every other port, rule, comment, SSH exception, LF/CRLF, mode and owner.
   An existing 6030:6032 or 6030:6033 already includes 6031: skip it.
3. **BACK UP:** create a byte-exact backup of the **actual existing file**,
   whatever its SHA-256. Record preimage and proposed SHA-256, ownership,
   path and transaction ID. Build the new file in same-filesystem staging.
   Recheck that the live preimage still has the expected hash before rename.
4. **VALIDATE + APPLY:** independently check each candidate's only-intended
   delta and syntax (use target-confirmed pfctl -nf when supported). Write
   only changed files with guarded replacement, verify read-back and record
   them in the **normal installer recovery journal**, not a standalone
   firewall subsystem. Restore the preimages on failure if still owned.
   A normal installer --apply authorizes this known-safe additive step;
   no extra --apply-firewall switch should be required.
5. **VERIFY:** distinguish (a) stored rule, (b) effective loaded pfctl rules,
   (c) listener, (d) iPhone connection, and (e) Type-111 frames. Staging
   success proves only (a). A later supervised, separately authorized
   postboot/network-profile test is required for (b)-(e).
6. **ROLL BACK/UNINSTALL:** restore a saved original only if the current file
   still matches *this installer's* recorded postimage, or safely remove its
   uniquely identified unchanged rule. If later external edits exist, preserve
   them and report a conflict instead of wiping the file.

Never flush or reload PF in an unattended install, disable PF, kill SSH/inetd,
reset network interfaces, reboot, open broad inbound access or expose
127.0.0.1:19820 outside loopback.

### Unrecognized layout

An unknown full-file SHA-256 is not a blocker if the structural
carplay0 TCP allowlist is recognized and can be edited safely. Only if the
policy cannot be located, an earlier block overrides the permit, syntax
cannot be validated, or the profile loader/mount path is uncertain, leave
that profile unchanged and report FIREWALL_REVIEW_REQUIRED. Continue
independent installer steps where safe; do **not** claim that Type-111
network access is ready. Optionally propose an explicit owner-approved,
exact-target full-file replacement as fallback with byte-exact backup;
this is **not** the default and cannot be silently applied across brands.

### Existing SSH installation precedent

Source: https://github.com/Mr-MIBonk/M.I.B._More-Incredible-Bash/blob/main/mod/sshd/scripts/sshd_install.sh

The published More Incredible Bash SSH installer changes PF files as an
ordinary installation step: creates .bu backups for pf*.conf when absent,
then **copies .bu over the currently installed file on every execution**;
it inserts port 22 rules for interfaces present in the file and calls
pfctl -F all -f on pf.mlan0.conf, then restarts inetd.

**Do not copy its reset/reload behavior.** Reinstalling SSH with that
historical script can remove an existing 6031 allowance if the old .bu
snapshot predates it. This is why our step patches the *currently found*
rules, is idempotent, preserves SSH ports, and rechecks after third-party
changes. This is a source-code observation, not proof that the same
script actually ran on the owner's vehicle.

A similar in-place allowlist expansion is described in:
https://github.com/maxim-smirnov/mhi2-carplay-cluster/blob/main/docs/build-and-deploy/DEPLOY_AND_RELEASE.md
This is precedent, not a verified reusable binary or installer.

## API and acceptance

Use the existing installer's ordinary check/plan/apply/status/uninstall and
backup mechanisms. An optional firewall subcommand may expose the same
read-only evidence, but must not create a second configuration database or
installer state machine.

Host tests cover: stock 6030, existing 6031, 6030:6031 and 6030:6032
ranges; spaces and LF/CRLF; an unrelated SSH port-22 addition and other
foreign rules; multiple PF profiles and interface switches; an earlier
block quick; unchanged second install; stale preimage/hash; invalid syntax;
failure mid-install; exact restoration and conflicting third-party edits.
Explicitly simulate SSH-then-MIBR and MIBR-then-SSH-reinstall (the latter
must detect and repair a missing 6031 permission on the next install/check).

The original Type-111 stream may only be called firewall-ready after
the effective PF policy was independently verified. This does not
turn PF into a separate release pipeline or require exact whole-file
stock/MIBR_TARGET equality on other units.
