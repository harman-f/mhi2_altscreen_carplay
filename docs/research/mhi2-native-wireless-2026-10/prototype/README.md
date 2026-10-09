# Native Wireless CarPlay prototype source

> **EXPERIMENTAL PROTOTYPE – DEVELOPMENT PAUSED – NOT VEHICLE VALIDATED**

This directory publishes source snapshot commit `14fd533a67e3c0f54d553a2bb4f092c4b7ae04a7`. It contains 42 of the 43 manifest candidates. The sole omitted file is `probe/ident-param24-test/make_candidate.py`, explicitly classified `PATCH_SCRIPT_DO_NOT_EXPORT` / `EXCLUDE`; it is a hash-gated firmware patch builder and is outside this source publication. Both MFi adapter files were included as requested. See [publication review](PUBLICATION_REVIEW.md) and [source manifest](SOURCE_MANIFEST.tsv) for the per-file inventory, provenance and SHA-256 values.

## Architecture and component map

The prototype explores an offline/native path around the stock MHI2 Bluetooth/iAP stack:

1. `probe/servicegraph-adapter/` registers the iAP Bluetooth service in an owner process; `probe/btstack-owner-hook/` is the integration hook.
2. `probe/rfcomm-provider/` provides SDP/RFCOMM callbacks and a QNX resource-manager endpoint. The C wrapper includes all six adjacent `.inc` modules (`prelude`, `setup`, `lifecycle`, `streams`, `events`, `qnx`); keep this directory intact.
3. `probe/transport-btstream/` adapts a raw endpoint to the stock Type-3 `ipod_transport` ABI.
4. `probe/src/` contains protocol/ABI fixtures and the MFi adapter that dynamically calls the stock `libairplay.so`. It does not contain a stock library, certificate, key or authentication response.
5. `probe/a3-credentials/`, `probe/runtime-iap2-config/` and `probe/a3-network-preflight/` explore WLAN credential/configuration handoff and diagnostics.
6. `probe/b0-discovery/` is a read-only DNS-SD discovery observer. It does not authenticate or own a trusted controller.
7. `probe/tests/` contains offline host/mock tests, including RFCOMM lifecycle and QNX callback fixtures. The Makefile preserves the source extraction rules for its generated QNX test fixtures.
8. `contracts/` holds a reconstructed interface header; it is a declaration-level ABI aid, not copied OEM implementation code.

## Known defects and incomplete work

- The A3 credential parser has a known Protocol=2/WEP misclassification and stale-field risk. Do not use it to configure a vehicle or trust its security classification.
- B0 discovery does not establish peer identity or trust. Device correlation, Add/Remove handling and IPv6 scope behavior remain incomplete.
- Service registration, RFCOMM provider ownership and the Type-3 handoff are based on static ABI analysis and offline tests; target runtime integration is unproven.
- The MFi adapter has not been exercised against an authorized exact-target stock library or a real authentication exchange.
- The receiver/DIO path still lacks an identified `iAPSendMessage` consumer. A Controller owner, Pair Setup/Verify server, secure peer persistence, encrypted session and bidirectional iAP-over-AirPlay bridge are not implemented as a validated integrated path.
- No full Wireless CarPlay session has been demonstrated on a target vehicle. Green host tests do not change that status.

## Dependencies and tests

The host suite expects `make`, a C99 compiler (`cc`), POSIX shell utilities including `awk`, and Python 3. From this directory run:

```sh
cd probe
make test
```

`make test` is the intended host suite. In the publication environment it stopped before the first test because the MSYS `make` executable was available but `cc` was not (`make: cc: No such file or directory`). No host test case ran. `make qnx` requires the pinned QNX 6.5 ARM toolchain and is not expected to work on a generic host. No vehicle test is supplied or claimed.

## Historical runtime tools

`probe/btstack-preload/` and `probe/runtime-launcher/` contain historical diagnostic scripts that can replace/wrap process startup, overlay runtime files, change permissions, or stop processes. `probe/a3-network-preflight/` and the vehicle bundle verifier also inspect a target when explicitly invoked. They are published for source completeness and review only: **do not run these scripts automatically or on a vehicle**. The Makefile's tests only use their documented host/mock or help paths.

## Publication and licensing

These prototype files are represented as project-authored original work and are published under the destination repository's GPL-3.0-or-later terms. The public tree contains no OEM firmware/binaries, decompiled OEM function bodies, partner implementation, MFi certificate/key material, real Wi-Fi credentials, vehicle identifier or personal log. The source manifest preserves the private source commit/blob IDs and computes SHA-256 over the exported bytes. A runtime dependency on an authorized stock MHI2 library does not include or redistribute that library.

This publication is research source, not an installer, supported product, recommendation to modify a vehicle, or claim of legal permission to use Apple's or an OEM's services or credentials.
