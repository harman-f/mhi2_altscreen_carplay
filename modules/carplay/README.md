# CarPlay and media module

The canonical project-owned media source and runtime inputs are physically co-located in this module. Source relocation does not change the package's installed paths or qualify any firmware/vehicle target.

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
