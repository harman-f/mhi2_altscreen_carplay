# CarPlay and media module

This page maps the existing CarPlay/video implementation. The repository has not yet been moved into the package's proposed `common/carplay/` tree; the paths below remain canonical.

## Source and runtime

- [GEN2 / Type-111 source](../../src/native/altscreen111-gen2/)
- [GEN2 source build and evidence](../../docs/build/INSTALLED_GEN2_SOURCE.md)
- [Direct-TS remux source](../../src/native/direct-ts-remux/)
- [Direct-TS parity source](../../src/native/direct-ts-parity/)
- [MOST transport writer](source/most-ts-writer/)
- [Optional vehicle-data/iAP2 adapter sources](source/vehicle-data/) (shared GEN2 build; host-tested source, no new Unit qualification)
- [Automatic direct runtime](../../runtime/auto-direct/)
- [Exclusive native display gate](../../src/native/isotx2-gate/)
- [Vehicle-tested artifact inventory](../../artifacts/mu1440/)

## Build, support, and evidence

- [Source coverage and limitations](../../docs/status/PUBLISHED_SOURCE_COVERAGE.md)
- [MU1440 R57 source build guide](../../docs/build/MU1440_R57_SOURCE.md)
- [Compatibility matrix](../../docs/testing/COMPATIBILITY_MATRIX.md)
- [Reference vehicle demonstration](../../docs/media/mu1440-stream111-poc-2026-09-29/README.md)

The demonstrated video path is tied to pinned MU1440 configurations. A vehicle-tested artifact or source build does not qualify a reorganized package, other firmware, or a current complete installer.
