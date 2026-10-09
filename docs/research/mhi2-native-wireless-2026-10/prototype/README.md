# Native Wireless CarPlay prototype source

> **EXPERIMENTAL PROTOTYPE – DEVELOPMENT PAUSED – NOT VEHICLE VALIDATED**

This directory publishes source snapshot commit `14fd533a67e3c0f54d553a2bb4f092c4b7ae04a7`. It contains 42 of the 43 manifest candidates. The sole omitted file is `probe/ident-param24-test/make_candidate.py`, explicitly classified `PATCH_SCRIPT_DO_NOT_EXPORT` / `EXCLUDE`; it is a hash-gated firmware patch builder and is outside this source publication. Both MFi adapter files were included as requested. See [publication review](PUBLICATION_REVIEW.md) and [source manifest](SOURCE_MANIFEST.tsv) for the per-file inventory, provenance and SHA-256 values.

## Related firmware research and source navigation

This experimental source is the implementation companion to the [Wireless research handoff](../README.md). For a **direct firmware-binary → research-finding → original source/test** lookup, use the **[firmware/source cross-reference table](../FIRMWARE_SOURCE_CROSS_REFERENCE.md)**. The underlying OEM firmware binaries and iOS framework binaries were analyzed but are not redistributed here.

Relevant chapters: [Bluetooth servicegraph/RFCOMM](../01_BLUETOOTH_RFCOMM.md) · [stock iAP2/MFi/WLAN](../02_IAP2_MFI_WIFI.md) · [receiver/DIO and secure-session gap](../03_RECEIVER_PAIRING_CONTROL.md) · [Bonjour discovery](../04_DISCOVERY_RECONNECT.md) · [QNX recovery](../06_QNX_RECOVERY.md) · [end-to-end architecture](../09_END_TO_END_ARCHITECTURE.md).

## Architecture and component map

The prototype explores an offline/native path around the stock MHI2 Bluetooth/iAP stack:

1. [Servicegraph adapter](probe/servicegraph-adapter/mhi2_iap_servicegraph_adapter.c) registers the iAP Bluetooth service in an owner process; the [btstack owner hook](probe/btstack-owner-hook/mhi2_btstack_owner_hook.c) is the integration hook.
2. The [RFCOMM provider](probe/rfcomm-provider/mhi2_rfcomm_provider.c) provides SDP/RFCOMM callbacks and a QNX resource-manager endpoint. The C wrapper includes all six adjacent `.inc` modules (`prelude`, `setup`, `lifecycle`, `streams`, `events`, `qnx`); keep this directory intact. [Component-by-component links](../FIRMWARE_SOURCE_CROSS_REFERENCE.md).
3. The [btstream transport](probe/transport-btstream/ipod_transport_btstream.c) adapts a raw endpoint to the stock Type-3 `ipod_transport` ABI.
4. [Protocol fixture](probe/src/wcp_probe.c) and [MFi dynamic adapter](probe/src/mhi2_mfi_airplay.c) reuse stock interfaces; neither includes a stock library, certificate, key or authentication response.
5. [A3 parser](probe/a3-credentials/mhi2_wcp_a3_credentials.c), [runtime iAP2 config](probe/runtime-iap2-config/mhi2_wcp_iap2_runtime_config.c) and [network preflight](probe/a3-network-preflight/mhi2_wcp_a3_network_preflight.sh) explore WLAN handoff and diagnostics.
6. The [B0 DNS-SD observer](probe/b0-discovery/mhi2_wcp_b0_discovery.c) is read-only. It does not authenticate or own a trusted controller.
7. [Host/mock tests](probe/tests/) include RFCOMM lifecycle and QNX callback fixtures. The [Makefile](probe/Makefile) preserves source extraction rules for generated QNX test fixtures.
8. [Receiver control ABI declarations](contracts/mu1440_receiver_control.h) are an interface aid, not copied OEM implementation code or a working secure-session adapter.

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
