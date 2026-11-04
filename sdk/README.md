# Build SDK and external inputs

This directory is the entry point for build SDK requirements. SDKs and OEM
inputs are provisioned locally; they are not vendored here. Build recipes and
evidence remain with their owning modules or build documentation.

| Build target | Required external input | Canonical instructions | Notes |
| --- | --- | --- | --- |
| QNX 6.5 ARMv7 native modules | Pinned public toolchain source and Docker | [QNX source build](../docs/build/MU1440_R57_SOURCE.md#build-native-source), [image recipe](../tools/build_qnx65_image.sh) | The helper verifies the pinned commit and Dockerfile hash. It does not distribute the QNX SDK. |
| OEM Java menu adapter | Exact target `lsd.jar`, IBM J9 SDK and local OEM source views | [Menu source build notes](../modules/menu/source/README.md), [MU1440 source status](../docs/build/MU1440_R57_SOURCE.md) | External inputs are required; no OEM JAR, JXE or extracted implementation is included. |

The owning build scripts remain authoritative. Do not copy toolchain binaries,
SDK archives, OEM classes or generated build outputs into this directory. For
the complete toolchain identity and known lineage limits, see [module build
lineage](../docs/build/MODULE_BUILD_LINEAGE.md) and [QNX toolchain image
contract](../docs/build/QNX_TOOLCHAIN_IMAGE.md).
