# CarPlay and media module

This module owns the canonical CarPlay/video source and development runtime. The distribution's `common/carplay/` tree is generated separately; moving a source file here does not change its installed path or imply a new vehicle qualification.

## Source and runtime

- [GEN2 / Type-111 source](source/altscreen111-gen2/)
- [GEN2 source build and evidence](../../docs/build/INSTALLED_GEN2_SOURCE.md)
- [Direct-TS remux source](source/direct-ts-remux/)
- [Direct-TS parity source](source/direct-ts-parity/)
- [MOST transport writer](source/most-ts-writer/)
- [Optional vehicle-data/iAP2 adapter sources](source/vehicle-data/) (shared GEN2 build; host-tested source, no new Unit qualification)
- [Automatic direct runtime](runtime/auto-direct/)
- [Exclusive native display gate](source/isotx2-gate/)
- [Vehicle-tested artifact inventory](../../artifacts/mu1440/)

## Build, support, and evidence

- [Source coverage and limitations](../../docs/status/PUBLISHED_SOURCE_COVERAGE.md)
- [MU1440 R57 source build guide](../../docs/build/MU1440_R57_SOURCE.md)
- [Compatibility matrix](../../docs/testing/COMPATIBILITY_MATRIX.md)
- [Reference vehicle demonstration](../../docs/media/mu1440-stream111-poc-2026-09-29/README.md)

The demonstrated video path is tied to pinned MU1440 configurations. A vehicle-tested artifact or source build does not qualify a reorganized package, other firmware, or a current complete installer.
