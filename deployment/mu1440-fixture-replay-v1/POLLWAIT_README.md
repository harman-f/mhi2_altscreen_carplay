# MU1440 POLLOUT / EAGAIN prototype – standalone paired toolkit

**Research-only. Not vehicle-qualified.** Branch `work/mu1440-eagain-poll-proto-v1`, draft PR #31. This toolkit is independent of the vehicle-tested `clockdiag-v1` SD directory and its old backup. No autostart, no base GEN2 or native MOST guard modification.

## Complete `pollwait-v1/` folder

- `direct-ts-parity` – QNX 6.5 ARMv7 writer with opt-in `poll(POLLOUT)` EAGAIN wakeup and per-session safe legacy fallback
- `parity-session` – strictly matched QNX ARMv7 owner built from the same CI run
- `PAIR_SHA256SUMS.txt` – exact binary hashes
- `MU1440_POLL_SWAP.sh` – strict offline preflight, paired install, paired hash verify, status, stop and rollback to the original exact pair
- `MU1440_POLL_LIVE.sh` – 150-second opt-in/legacy live capture; source-side measurements and final status
- `MU1440_POLL_FIXTURE.sh` – bounded fixture helper; never enables experimental poll in fixture mode
- `POLLWAIT_README.md` – this file

All 7 files are staged by CI. `MU1440_POLL_SWAP.sh` receives the new pair's actual hashes during CI packaging, not source placeholders.

## Strictly isolated paths

- SD: `/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/pollwait-v1`
- Installed original pair: `/mnt/app/root/altscreen-u2/bin/{direct-ts-parity,parity-session}`
- Independent backup: `/mnt/app/root/mibr-pollwait-v1-backup`
- Logs: `/net/mmx/fs/sda0/esd/carplay-test/logs/parity-drive/pollwait-live-*`

The preflight only accepts the known-good CI314 clockdiag pair (bridge SHA256 `74c39c205bdab2f5e894cf35e644bf7d9fe9c9b46dc71a27e26bb5c2b237f3e2`, owner SHA256 `c513ca1f7fb52df2d6ebb4e65b7bddc7b0aa3c1e455a2d1d614c63972794e370`) or the pre-existing CI295/CI305 baseline, and refuses unknown mixed pairs. It requires idle native gate, no active owner/bridge/supervisor, persistent supervisor disabled, and intact paired hashes. The original clockdiag backup and SD binaries are not overwritten. The pollwait backup is also immutable once its hash manifest is committed: a repeat install checks the stored pair, and incomplete/orphaned backup files fail closed. Recovery stages and hashes both binaries before rename; the two filesystem renames cannot be atomic together. A power loss between renames can leave a mixed pair. In that case, **do not start CarPlay**; inspect actual hashes and perform operator-controlled recovery from the preserved backup with native gate and owner idle. This is not a power-loss-atomic update mechanism.

## Research-only commands – execute **only after explicit vehicle release**

Vehicle parked, gate in stock, SD writable, exact package from a fully green QNX CI run. Do not transfer single binaries independently. Stop if any check fails.

```sh
D=/net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/pollwait-v1
/bin/ksh -n "$D/MU1440_POLL_SWAP.sh"
/bin/ksh -n "$D/MU1440_POLL_LIVE.sh"
/bin/ksh -n "$D/MU1440_POLL_FIXTURE.sh"
cd "$D"
cat PAIR_SHA256SUMS.txt
/mnt/app/root/altscreen-u2/bin/sha256sum "$D/direct-ts-parity"
/mnt/app/root/altscreen-u2/bin/sha256sum "$D/parity-session"
/bin/ksh "$D/MU1440_POLL_SWAP.sh" status
/bin/ksh "$D/MU1440_POLL_SWAP.sh" install
/bin/ksh "$D/MU1440_POLL_SWAP.sh" verify
```

Legacy reference (default): `/bin/ksh "$D/MU1440_POLL_LIVE.sh" preflight` followed by `/bin/ksh "$D/MU1440_POLL_SWAP.sh" live`.

To request experimental notifier: `MIBR_PARITY_EAGAIN_WAIT=poll /bin/ksh "$D/MU1440_POLL_SWAP.sh" live`, after checking `preflight`. The QNX native writer reports `PARITY_BACKPRESSURE wait=poll_opt_in` in `session.log`; status contains `eagain_wait` and `writer_poll_*`. Environment is passed to the session shell and native writer; confirm the runtime log before interpreting any A/B results. On `poll` notifiers that are missing, invalid or misleading, the writer disables the experiment and falls back to the legacy 1-ms-request sleep for the session. Existing 500-ms write deadline, 12032-byte full-block fail-closed acceptance, PCR/PTS and native gate are unchanged.

After the owner has ended and stock gate/route are independently verified:

```sh
/bin/ksh "$D/MU1440_POLL_SWAP.sh" restore
/bin/ksh /net/mmx/fs/sda0/esd/carplay-test/omonob-clock-test/clockdiag-v1/MU1440_CLOCKDIAG_SWAP.sh verify
```

Expected restored pair is exactly the one backed up before the poll experiment. The second verify line applies if CI314 clockdiag was installed initially. If rollback fails, do not start new sessions; diagnose owner/gate and hashes first.

## What CI does *not* prove

A green host test + QNX cross-compilation does not prove that the MU1440 `/dev/mlb/isoTX2` QNX resource manager implements meaningful writable notification, that a successful write equals actual physical MOST drain, or that `poll()` improves cockpit decoder cadence. The ~-0.44% acceptance-clock-model discrepancy is observational, not an automatic reason to change PCR. This candidate is for review/qualification, not immediate unassisted field use.
