# MIBR/3 — public, project-owned source-only reference

These are **actual source files**, not an illustration or an installer. They are provided under the repository's GPL-3.0-or-later source license (SPDX headers in C). The package is deliberately isolated from the target's OEM/J9/CarPlay runtime.

- `api_v3_contract.py`: bounded line framing, percent/UTF-8 encoding, validation, response construction and read-only supplied-snapshot projection. It performs **no** socket, QNX, disk, source-switch, vehicle-data or iAP2 operation.
- The mailbox and owner-lifecycle implementations are owned canonically by [`modules/broker/source/mibr-control`](../../../modules/broker/source/mibr-control/). This reference keeps its Python contract model and standalone route-interface headers; its host regression compiles and probes the canonical C implementations.

The mailbox is a component interface, **not an authenticated production service**, target installer, car access path, physically attested VC state or permission to start a second parity writer. A successful mailbox handoff means **accepted/pending**, never a proven visible-route change. Do not use its `qualified` flag without independently establishing exact source/session, active owner, AID display evidence and safe rollback.

Host checks (Python 3 and a C compiler; set `CC` when the compiler is not named `cc`):

```sh
python3 -B tests/test_public_mibr3.py
```

This is an independently scoped MIBR/3 protocol and owner-policy reference; shared C implementations live only in the Broker module. It does **not** claim to provide the newest integrated Java HMI, native persistent controller, original registry dependency, complete parity writer, KEY40 target binding or vehicle-data sender. See [public source coverage](../../../docs/status/PUBLISHED_SOURCE_COVERAGE.md) and [module architecture](../../../docs/architecture/MODULE_BOUNDARIES_AND_PORTABILITY.md).
