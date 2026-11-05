# Documentation maintenance and publication rules

The product has three separate versioned surfaces: **public source**, a **specific package**, and **physical vehicle evidence**. Do not replace one with another. See the [current feature evidence](status/FEATURE_STATUS.md) and [package generations](packages/README.md).

## Canonical owners

| Question | Maintained page | Supporting, dated material |
| --- | --- | --- |
| First impression and getting started | [Root README](../README.md) and [documentation hub](README.md) | [Reference media](media/mu1440-stream111-poc-2026-09-29/README.md) |
| Features and per-platform test status | [Feature status](status/FEATURE_STATUS.md) and [compatibility](testing/COMPATIBILITY_MATRIX.md) | [Dated integration snapshot](status/INTEGRATION_STATUS_2026-10-21.md) |
| Real ZIP availability, installer and release | [Package index](packages/README.md), [package contract](build/PACKAGE_LAYOUT.md) | [Frozen MU1440 release](../release/CURRENT.md) |
| Code ownership and runtime storage | [Architecture index](architecture/README.md), [module index](../modules/) | [Historical studies](research/README.md) |
| Config keys, presets, profile selector | [Registry](../settings/registry.json), [profiles](../modules/profiles/) | [Default matrix](configuration/DEFAULT_CONFIGURATION_MATRIX.md) |
| Build and contributed target code | [QNX image](build/QNX_TOOLCHAIN_IMAGE.md), [Java/RGI guide](build/MU1440_MENU_RGI_SOURCE.md) | [R57 reference source](build/MU1440_R57_SOURCE.md) |

## Checklist on implementation or release changes

1. **Source merged:** update module README and source-coverage page. Update feature status only for newly proven implementation/build evidence.
2. **Profile changed:** update `profile.json` and generated profile table through its generator; review compatibility and the separate `install_enabled` versus `unit_tested` wording.
3. **Configuration changed:** regenerate definitions and check the 48 CarPlay settings/13 broker switches; do not edit generated values blindly or equate stored state with applied state.
4. **Assembler/installer changed:** update package contract and package index. Label new packages by their actual manifest and validation, not by presence of source.
5. **Vehicle run completed:** attach date, firmware hash, installed SHA, exact feature and result. Distinguish media frames, broker ACK, applied settings and physically visible result.
6. **Historical docs:** keep dated evidence intact; add a superseding current reference or archive label instead of rewriting observations into fictitious contemporary tests.
7. **Publication:** check internal links, anchors, referenced paths and programmatic profile/doc correspondence; do not copy private handoffs, OEM source bytes or restricted artifacts to the public repo.

## CI coverage

`python3 tools/docs/check_docs.py --self-test` runs parser fixtures; `--scope active` is the required strict index/status/link gate. `--scope all` strictly checks every tracked Markdown file, including historical studies. `--report-only` remains available for local diagnostics when investigating old references. The repository already runs generator and package validators; they govern machine-readable behavior, not a prose claim that an untested ZIP has passed real-world qualification.

Do not turn this document into a second roadmap. The [roadmap](../ROADMAP.md) lists remaining product gates; this page governs how to keep the documentation coherent.
