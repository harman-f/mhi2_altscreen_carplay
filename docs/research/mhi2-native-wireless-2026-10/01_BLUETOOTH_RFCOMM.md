# 01. Bluetooth servicegraph, SDP and RFCOMM on MU1440

**Target:** MHI2 ER SKG13 P4526/MU1440, classic MHI2/QNX 6.5 ARM32. **Evidence:** static comparison of target firmware components and adjacent stock software generations, plus independent offline prototype tests. No live full-session proof.

## What was actually observed

An earlier classic MHI2 stock stack constructed a dedicated `IapServices` object within the ordinary `BluetoothServices` graph, with service type **`0x4000` (`SC_IAP2_HOST`)**. The generic service dispatcher locates registered services by type and calls the matching connectability hook; the old iAP implementation uses its enabled state to register an RFCOMM endpoint and advertise SDP, and its disabled state to reverse that registration.

MU1440 retains the generic servicegraph, dispatcher and service type vocabulary, but the corresponding `IapServices` constructor/insertion block is absent in the audited path. `enableIap=false` in a production Bluetooth configuration is an observed policy restriction, **not** proof that changing the Boolean creates a missing service endpoint. Some related proxy interfaces remain present; similarly named symbols are not proof of full ABI compatibility across firmware variants.

## Bounded architectural concept

```text
BluetoothServices owner
    -> opt-in, target-compatible service node (serviceType 0x4000)
       -> stock connectability callbacks
       -> native SDP + dynamic RFCOMM registration
       -> peer-scoped callback handler / generation ID
       -> QNX Resource Manager endpoint
       -> stock-compatible iAP2 transport adapter
```

This avoids transplanting an unrelated `btstack` image or assuming that enabling a hidden flag is sufficient. The exact native insertion/detach mechanics remain target-specific. The early implementation was subjected to an independent teardown/owner review; a green CI build was **not** treated as proof of a safe live patch.

## RFCOMM event contract and pitfalls

The static provider audit identified native event classes for connection request, established connection, incoming data, completion of outgoing data and disconnection. Two ownership distinctions matter more than the numeric event IDs:

- **Incoming bytes:** the native event's RX pointer is borrowed for the callback lifetime. Code that queues only that pointer risks using invalid storage after the callback returns. Copy bounded RX data to owned memory before asynchronous consumption.
- **Outgoing bytes:** transmit buffers can remain in flight after submission; release/cancel must be tied to the native completion and owner-generation contract, not merely a successful queue call.

On stop, link loss or peer replacement, invalidate the current generation and drain/cancel pending callbacks before unloading the endpoint. Service-registration ownership, QNX Resource Manager dispatch, cancellation and handler quiescence must agree on which component owns the endpoint.

## What another working implementation could compare

- Is service `0x4000` registered by the correct live Bluetooth owner, and is SDP withdrawal observable when it becomes non-connectable?
- Is the accepted RFCOMM channel the same one passed to the stock iAP2 adapter, rather than an unrelated discoverable Bluetooth channel?
- Are RX/TX storage and completion semantics correct across interrupted connections and rapid reconnect?
- Does one generation own the session and QNX endpoint, including detach/reload?

A visible SDP record alone does not prove that the receiver has an openable bidirectional byte stream or a complete iAP2 session.

## Related published source and binary evidence

The **stock firmware comparison** is described above; the **project's experimental replacement/adapter source** is in [servicegraph adapter C](prototype/probe/servicegraph-adapter/mhi2_iap_servicegraph_adapter.c) / [header](prototype/probe/servicegraph-adapter/mhi2_iap_servicegraph_adapter.h), [owner hook](prototype/probe/btstack-owner-hook/mhi2_btstack_owner_hook.c), and the [RFCOMM provider C](prototype/probe/rfcomm-provider/mhi2_rfcomm_provider.c) / [header](prototype/probe/rfcomm-provider/mhi2_rfcomm_provider.h) with [events](prototype/probe/rfcomm-provider/mhi2_rfcomm_provider_events.inc), [lifecycle](prototype/probe/rfcomm-provider/mhi2_rfcomm_provider_lifecycle.inc) and [QNX implementation](prototype/probe/rfcomm-provider/mhi2_rfcomm_provider_qnx.inc). See [complete six-part provider map and target/donor binary references](FIRMWARE_SOURCE_CROSS_REFERENCE.md).
