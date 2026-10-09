# 03. Receiver/DIO, Controller Connect and encrypted pairing

**Evidence:** detailed, exact-MU1440 binary/callback audit on 7 October 2026, combined with a separate stock-firmware semantic comparison. Target code is not a working backport.

## The most useful target-side finding

The MU1440 AirPlay receiver already contains a **generic `POST /command`** route. With an existing session, it parses an Apple binary-property-list dictionary containing a typed `type` and `params`, handles some known commands locally and forwards other commands through `AirPlayReceiverSessionPlatformControl` into the DIO event queue. The target also contains **`AirPlayReceiverSessionSendCommand`** for the outbound direction over the active session's client, with an optional asynchronous completion.

The inspected stock DIO receiver command consumer recognizes its own subset, but there is **no identified `iAPSendMessage` consumer** in that path. This is a narrower integration gap than "MU1440 has no generic AirPlay Control". It is *not* evidence that only one added selector will yield a complete secure Wireless CarPlay session.

### Two different request paths must not be conflated

- `/ctrl-int/1/connect`: the controller-side Connect operation in a compared stock wireless implementation.
- `/command`: the MU1440 receiver's generic command transport, including the possible `iAPSendMessage` envelope with a binary `data` parameter.

The outbound target `SendCommand` needs an active session/event client. Its asynchronous completion and response dictionary lifetimes are part of the contract; a queued pointer or successful serialization does not imply the downstream session consumer accepted the iAP message.

## Pair Setup/Verify sequence: semantic reference only

The compared wireless-capable stock design placed **Pair Setup and Pair Verify in the receiver-side HTTP server**. After a successful Verify exchange, the encrypted HTTP transport was installed **after the Verify response completion**, rather than before sending the completion response. A trusted peer record and a session-specific identity bind the new encrypted channel to the correct device.

This does not prove that an unchanged MU1440 receiver can perform Pair Setup/Verify: the audited MU1440 target does not expose the same expected pairing handlers and target adaptation, secure peer persistence and crypto/error contracts are still open. Do not import decompiled OEM code or protected cryptographic material as a purported independent implementation.

## Exact-target delegate/ABI caution

The MU1440 session delegate copy length is **0x38 bytes / 14 ARM32 words**, with ten statically identified callback relocations and several reserved/unknown fields. Its control path and finalizer must continue to preserve the original target context; similarly named types or C++ objects in another head unit cannot be transplanted by offset. A private typed header describes these observations but has not been natively compiled or installed as an active receiver extension.

## What to compare in a partly working implementation

1. Whether the selected Controller peer is the same Bluetooth/Wi-Fi device and session generation.
2. Whether Pair Setup/Verify roles, response completion and cipher enablement are ordered correctly.
3. Whether trusted-device state survives a legitimate reconnect without allowing stale peers to inherit it.
4. Whether the actual *inbound and outbound* iAP-over-Control operations reach the correct stock iAP2 owner.
5. Whether callback completion, cancellation and HMI/audio state changes use the same session owner rather than multiple competing state machines.

A working initial picture confirms neither secure reconnect nor correct iAP-over-Control completion, microphone or phone-switch lifecycle.

## iOS version and feature negotiation are independent gates

The investigated iOS sender distinguishes global AirPlay `CarPlayControl` feature bit 37 from a negotiated modern `iAPChannel` token. Neither advertised bit nor token alone proves receiver Pair Setup/Verify or a functioning specific iAP consumer. See [10_IOS_SENDER_BINARY_FINDINGS.md](10_IOS_SENDER_BINARY_FINDINGS.md).
