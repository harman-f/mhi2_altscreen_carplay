# Firmware profile index

The package contract defines three exact profile identifiers, but this repository does not currently contain the symmetric `profiles/<id>/` source tree or a complete modular distribution. Treat the table as a map to available evidence and source, not as a set of ready-to-install profiles.

| Profile candidate | Firmware | Source present here | Evidence status |
| --- | --- | --- | --- |
| `skoda-mu1440-p4526` | `MHI2_ER_SKG13_P4526_MU1440` | [RGI platform defaults](../../modules/navigation/source/platform-defaults/skoda-mu1440.conf); shared sources remain in their canonical module paths | Reference-vehicle observations apply to pinned earlier configurations; a reorganized package still needs acceptance |
| `seat-mu1409-p4708` | `MHI2_ER_SEG11_P4708_MU1409` | No profile directory found; see [local environment notes](../../docs/porting/SEAT_CUPRA_MU1409_LOCAL_ENVIRONMENT.md) and [collaboration/porting notes](../../docs/porting/SEAT_CUPRA_MU1409_COLLABORATION.md) | Java build/static integration candidate; native menu, icons, wheel behavior, geometry, and output await vehicle acceptance |
| `seat-mu1447-p4709` | `MHI2_ER_SEG11_P4709_MU1447` | No profile directory found; see [multi-profile report](../../docs/testing/MULTI_PROFILE_TESTING.md) | Focused firmware-delta candidate; independent vehicle acceptance remains open |

## Selection and package contract

- [Binding modular package layout](../../docs/build/PACKAGE_LAYOUT.md)
- [Profile testing and tester evidence](../../docs/testing/MULTI_PROFILE_TESTING.md)
- [Firmware profile research map](../../docs/research/MHI2_FIRMWARE_PROFILE_MAP_2026-09-28.md)
- [Package validator source](../../tools/validate_modular_package.py)
- [Source build coverage and gaps](../../docs/status/PUBLISHED_SOURCE_COVERAGE.md)

The contract requires exact, unique original-firmware SHA-256 selection and fail-closed behavior. A matching firmware fingerprint does not identify fitted cluster hardware or establish vehicle support. No complete three-profile installer is published.
