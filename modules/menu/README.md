# Menu module

The menu module owns its Java adapter source, build scripts, tests, and owned scroll assets under `source/`.

## Source, editor, and runtime

- [OEM menu source, build scripts, and tests](../../modules/menu/source/)
- [Menu editor](../../tools/menu-editor/mibr-menu-editor.html)
- [Menu format and loader contract](../../tools/menu-editor/MENU_FILE_FORMAT.md)
- [Shared runtime menu loader](../../runtime/mibr-control/mibr-menu.ksh)
- [Menu, controller, and RGI build guide](../../docs/build/MU1440_MENU_RGI_SOURCE.md)
- [Owned scrollbar asset provenance](../../modules/menu/source/assets/scroll/README.md)

## Status and limits

- [Published source coverage](../../docs/status/PUBLISHED_SOURCE_COVERAGE.md)
- [Multi-profile status](../../docs/testing/MULTI_PROFILE_TESTING.md)
- [Native HMI and control-plane architecture](../../docs/architecture/NATIVE_HMI_AND_CONTROL_PLANE_2026-10-21.md)

The repository contains project-owned menu code and a neutral editor preview. Exact J9 rebuild inputs include external OEM/SDK material; some OEM-derived assets are excluded. Menu source/build evidence does not establish cross-profile appearance or vehicle acceptance.
