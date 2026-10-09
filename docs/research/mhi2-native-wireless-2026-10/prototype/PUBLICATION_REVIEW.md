# Prototype publication review

Source snapshot commit: `14fd533a67e3c0f54d553a2bb4f092c4b7ae04a7`.

## Manifest reconciliation

- 43 candidates were reviewed by exact path and source blob ID.
- 42 files were exported with directory layout and relative includes intact, including all six RFCOMM `.inc` modules, C/H/INC sources, Makefile, wrappers, transport adapter, MFi adapter and tests.
- One file was excluded: `probe/ident-param24-test/make_candidate.py` (`PATCH_SCRIPT_DO_NOT_EXPORT`, `EXCLUDE`). It builds a firmware patch candidate, rather than being a source dependency of the exported prototype; it is not run by `make test`.
- No candidate was excluded merely because it lacks vehicle validation. Runtime-mutation scripts and the reconstructed ABI header are retained and labeled.

## Content review

The exported bytes were reviewed for credential/key/certificate material, personal data, private repository/local-path references, third-party code notices, and OEM or decompiler implementation bodies. The matching candidates are source/header/build/test files, not binaries. Pattern scans were used as a supplement to manual source review; matches for generic SSID/PSK identifiers and synthetic `oldsecret` test data are code/test fixtures, not actual credentials. No real credential, VIN/MAC, private key, certificate, raw vehicle log, OEM binary, decompiled OEM function body, or unrelated private repository URL was found in the published candidate set.

The code is represented as project-authored original work and uses the destination repository's existing GPL-3.0-or-later license. The MFi files are a dynamic adapter around stock-exported API symbols; no Apple reference implementation, stock library, certificate or key is copied. The contract header is reconstructed declarations only. No third-party implementation body was identified in the published source candidates.

## Safety labels

`probe/btstack-preload/`, `probe/runtime-launcher/`, `probe/a3-network-preflight/` and `probe/vehicle-bundle/` include target-facing diagnostics or runtime mutation logic. These files are included for reproducible source review, are explicitly called out in the prototype README, and were not executed against a vehicle. `make test` uses host fixtures and help/syntax checks only.

## Hashes and tests

`SOURCE_MANIFEST.tsv` records each exported path, source commit, source blob SHA-1, byte size, exported SHA-256, project authorship attribution, classification, license basis, privacy-review result and test level. `make test` was attempted from `prototype/probe` but stopped before compiling because `cc` is unavailable; no test case ran. QNX cross-compilation is not claimed because the pinned toolchain is unavailable. No vehicle test is claimed.
