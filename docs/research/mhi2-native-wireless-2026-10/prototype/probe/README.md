# MHI2 native Wireless CarPlay probe area

Status: A0/A1 research fixtures; no end-to-end vehicle candidate.

The project direction changed materially after the SKG11 to SKG13 generation-delta audit. MU1440 already contains the stock iAP2 protocol implementation required for Bluetooth identification, MFi/iAP2 link handling, Wi-Fi transport metadata and the 0x5702 to 0x5703 credential exchange. The exact MU1433 and MU1440 ipod-drvr-iap2.so code sections are identical, including all 228 matched named functions.

Therefore the preferred path is no longer to implement the bootstrap protocol beside the stock driver. The preferred path is:

    MU1440 Bluetooth/RFCOMM
        -> prove or restore raw iAP endpoint/provider
        -> stock ipod_transport v2 boundary
        -> stock ipod-drvr-iap2.so
        -> bounded Wireless-CarPlay bootstrap

Directory roles

- endpoint-observer/
  Read-only A0 diagnostic. Watches /dev, PPS and shmem metadata for endpoint lifecycle changes without opening candidate nodes.

- transport-btstream/
  A1 stock-ABI transport fixture. It reports transport type 3 and adapts an explicitly proven raw endpoint to the exact MU1440 ipod_transport v2 callback ABI. It still requires an explicit endpoint path and explicit 12-byte link-parameter block.

- ident-param24-test/
  A2 analysis-only SHA-gated patch builder for the known WirelessCarPlayTransportComponent presence mismatch. Keep frozen until A0/A1 proves the stock path.

- src/wcp_probe.c and src/mhi2_mfi_airplay.c
  Protocol/ABI reference tests only. They are no longer the intended vehicle implementation because the relevant iAP2 and MFi semantics should remain stock wherever possible.

Current staged milestones

A0: Observe and identify the exact MU1440 endpoint/provider lifecycle.

A1: Feed the proven raw endpoint through transport-btstream into the unmodified stock iAP2 driver.

A2: Only if required by live evidence, apply the narrowly SHA-gated Identification param-24 test so Bluetooth bootstrap can advertise TransportSupportsiAP2Connection.

A3: Stop the first vehicle milestone at:

    BT connect
    -> iAP2 link/Identification
    -> 0x5702
    -> 0x5703
    -> iPhone associates with the target AP

Successful A3 is not complete Wireless CarPlay.

B0: Session-plane work after AP association. P2711 proves a newer production path containing _carplay-ctrl._tcp discovery, CarPlayControlClient, BT-MAC/controller correlation, HomeKit pair setup/verify, iAP-over-AirPlay and a newer wireless-audio path. Exact MU1440 AirPlay 210.81 does not contain those components, so endpoint activation alone cannot deliver the complete production P2711 behavior.

What is deliberately not guessed

- no assumed /dev/iapDevice pathname on MU1440;
- no assumed compatibility of the old IapDeviceServices provider with the MU1440 proxy;
- no silent reuse of P2711 Bluetooth link parameters;
- no Audi/MH2P binary transplant;
- no claim that 0x5703 equals working Wireless CarPlay.

Build

Host reference tests:

    make test

Host observer build:

    make observer

QNX ARM objects/binaries are built by the pinned GitHub Actions QNX 6.5 ARMv7 workflow.
