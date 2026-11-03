# Broker and input module

The broker's development source and runtime are now physically co-located in this module. The installed distribution layout and vehicle-qualification scope remain independent.

## Source and runtime

- [Native MIBR controller source](source/mibr-control/)
- [Controller runtime scripts](runtime/mibr-control/)
- [Canonical settings registry](../../settings/registry.json)
- [Native keypanel source](source/keypanel/)
- [Parity owner/session source](../../src/native/parity-session/)
- [Controller source/build guide](../../docs/build/MU1440_R57_SOURCE.md)

## Contracts and evidence

- [Runtime contracts](../../docs/architecture/RUNTIME_CONTRACT.md)
- [Native HMI and control plane](../../docs/architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md)
- [Published source coverage](../../docs/status/PUBLISHED_SOURCE_COVERAGE.md)
- [Vehicle test protocol](../../docs/testing/VEHICLE_TEST_PROTOCOL.md)
- [Key mapping evidence](../../docs/testing/MU1440_MFW_RAW_KEY_MAPPING.md)

Stored settings, accepted requests, applied actions, and visible vehicle effects are separate states. The latest controller safety correction is host-tested but not yet vehicle-qualified; input/action acceptance remains configuration-specific.
