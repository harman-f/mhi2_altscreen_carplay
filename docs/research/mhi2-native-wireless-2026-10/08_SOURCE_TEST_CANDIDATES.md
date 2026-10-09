# 08. Published prototype source and tests

**Public status: source published.** The dependency-complete prototype snapshot is now available in [prototype/](prototype/README.md). It contains 42 of the 43 entries in the private candidate manifest; the single excluded patch-builder and the reason are documented in [publication review](prototype/PUBLICATION_REVIEW.md). The six RFCOMM provider `.inc` modules are all present beside their C wrapper and header. The exact exported paths and SHA-256 values are in [SOURCE_MANIFEST.tsv](prototype/SOURCE_MANIFEST.tsv).

The source publication preserves relative include/build relationships, including the Makefile's generated QNX host-test fixtures. It includes C/H/INC files, the full RFCOMM provider, servicegraph owner hook, Type-3 transport adapter, MFi dynamic wrapper, A3/B0 modules, QNX helpers, shell tools and offline tests.

## Scope and limitations

All source candidates were reviewed for credentials and personal data, private repository/local paths, third-party license notices, and copied OEM/decompiler implementation bodies. No OEM firmware/binary, decompiled OEM function body, MFi certificate/key, real access credential, vehicle identifier, or private Research repository history is included. Runtime scripts are retained for source completeness and marked as historical/high-risk; they are not automatically executed. See the review record for scan caveats and per-file provenance.

The A3 parser still has the known Protocol=2/WEP misclassification and stale-field risk. B0 is not an authenticated controller directory. Pairing/Secure Session remains incomplete: no validated Pair Setup/Verify server, trusted peerstore, target DIO iAP command consumer or bidirectional encrypted iAP-over-AirPlay path is provided. Host tests are offline evidence only; `make test` could not pass its first compile step in the publication environment because `cc` is unavailable, so no test case ran. No vehicle validation is claimed.

The excluded `probe/ident-param24-test/make_candidate.py` is explicitly classified as `PATCH_SCRIPT_DO_NOT_EXPORT`; it creates a firmware patch candidate and is not a dependency of the exported prototype. No source file was withheld solely because the prototype is unvalidated.

## Per-firmware cross-reference

For the link from each analyzed stock **firmware or iOS binary** to our original C/H/INC prototype files and corresponding research/test chapters, use [Firmware / binary findings ↔ published prototype source](FIRMWARE_SOURCE_CROSS_REFERENCE.md). The [prototype README](prototype/README.md) now links directly to each major source module.
