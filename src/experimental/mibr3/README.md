# MIBR/3 — public, project-owned source-only reference

These are **actual source files**, not an illustration or an installer. They are provided under the repository's GPL-3.0-or-later source license (SPDX headers in C). The package is deliberately isolated from the target's OEM/J9/CarPlay runtime.

- `api_v3_contract.py`: bounded line framing, percent/UTF-8 encoding, validation, response construction and read-only supplied-snapshot projection. It performs **no** socket, QNX, disk, source-switch, vehicle-data or iAP2 operation.
- `mibr_v3_parity_mailbox.c/.h`: a bounded, single-request file handoff to an **already qualified existing owner**, with no-replace atomic publication and an uncertainty return that forbids blind retries.
- `mibr_v3_parity_mailbox_probe.c`: host test of rejects, START/STOP, existing owner request and competing publishers.

The mailbox is a component interface, **not an authenticated production service**, target installer, car access path, physically attested VC state or permission to start a second parity writer. A successful mailbox handoff means **accepted/pending**, never a proven visible-route change. Do not use its `qualified` flag without independently establishing exact source/session, active owner, AID display evidence and safe rollback.

Host checks (Python 3 and a POSIX C compiler):

```sh
python3 -B tests/test_public_mibr3.py
```

This is only the first independently publishable MIBR/3 source slice; it does **not** claim to provide the newest integrated Java HMI, native persistent controller, original registry dependency, complete parity writer, KEY40 target binding or vehicle-data sender. See [public source coverage](../../../docs/status/PUBLISHED_SOURCE_COVERAGE.md) and [module architecture](../../../docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md).
