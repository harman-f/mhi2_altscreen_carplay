# Optional wireless control library

Status: **SOURCE / COMPILE-ONLY**, QNX 6.5 ARMv7 candidate. No working wireless
receiver, installed feature or vehicle result is claimed.

This independently authored C99 module provides bounded session coordination,
owned asynchronous message buffers and plaintext HTTP/TLV framing. It is off by
default. It does not install, start or replace any stock process, alter firewall
rules, configure a radio or open sockets. The existing wired/video code has no
dependency on it. The caller serializes all operations on its current owner
thread; the library adds no second session, media or MOST owner.

Go [up to modules](../README.md), across to the [existing menu](../menu/README.md)
and [CarPlay/video owner](../carplay/README.md), or down to the
[source API](source/wcp_control.h), [protocol helpers](source/wcp_protocol.h),
[normalized configuration records](source/wcp_config.h),
[build recipe](build/build.sh) and [synthetic tests](tests/test_wireless.c).

## Integration contract

`wcp_config_default` disables the feature. Enabling the configuration alone
does not enable wireless: `wcp_start` returns `WCP_UNAVAILABLE` until an external
adapter implements all required operations and capabilities. There is no
success-returning production adapter in this module. The callbacks are a new
project C interface, not a binary-compatible OEM delegate or SDK substitute.

The adapter must bind the current stock iAP, authentication, receiver and media
owners. It must implement Pair Setup/Verify, authenticated encrypted control,
peer identity/trust storage, discovery updates, notifications, iAP-over-control,
audio/video/touch and reconnect/power handling before claiming those
capabilities. Media readiness is accepted only after bootstrap and authenticated
verification. Discovering a controller is not authenticated pairing.

The caller supplies one validated current AP/peer snapshot. It must establish
snapshot freshness, exact interface/peer identity and regulatory channel
validity before calling `wcp_start`; the library cannot infer live radio state.
The project security enum is independent of driver Protocol/Cipher numbers.
Only explicit open or WPA2 input is represented. Unknown modes, including WEP,
are rejected. Open mode requires an empty key and should be presented as an
insecure network by the UI. WPA/cipher translation and raw-key acceptance by a
stock iAP adapter remain separate integration checks. Keys are never logged,
persisted or kept in the control object. `begin` borrows credentials only during
the call. A future adapter must isolate pairing records from WLAN credentials
and redact them from diagnostics.

`wcp_ap_record` accepts a project-owned normalized record, with required
`ssid`, `psk`, `channel`, `security` and `cipher` fields. It rejects duplicates,
unknown keys, WEP/WPA/unknown security, unsupported cipher combinations and
unequal producer generations around a snapshot. This is not a parser for a
stock driver configuration. A stock adapter must translate actual protocol
and cipher values without guessing their meaning. It must prove live
freshness independently. Temporary record copies are cleared on return.

For example, a **synthetic** record is:

```text
ssid=synthetic-access-point
psk=synthetic-key-123
channel=6,secondary
security=wpa2
cipher=ccmp
```

`wcp_config_parse` accepts `enabled=0|1` and `handshake_timeout_ms=1..120000`,
one `key=value` per line with a final newline. Omitted values use defaults.
Malformed input leaves the returned configuration disabled. It reads no
persistent state and does not apply a setting to the vehicle.

The adapter's atomic `claim` must reject a concurrent wired owner. A USB event
calls `wcp_wired(1)`, which blocks new starts and stops the wireless adapter.
Hook loading, if needed, must be scoped to an exact validated process and stay
loaded while borrowed callbacks or buffers exist. This library provides no
preload or process-wide hook. Adapter methods cannot reenter the API.

Each start has a generation. Events/completions from an earlier generation are
rejected. Four copied 4096-byte buffers remain owned until completion or a
successful quiescent stop. A failed stop keeps buffers and ownership, blocks a
new start and makes `wcp_uninstall_ready` false. The caller must retry stop and
keep the adapter loaded. There is no unsafe forced detach. Monotonic time is
injected; bootstrap/verification time out, backward time and overflow fail.

`wcp_http_feed` incrementally parses strict HTTP/1.1 request framing with
bounded headers/body. Duplicate lengths, transfer encoding, invalid line
endings and oversized bodies fail closed; consumed length preserves trailing
requests. It is not an HTTP server, RTSP stack or cryptographic transport.
`wcp_tlv_value` validates the entire TLV stream before copying a value and
supports adjacent 255-byte fragments. These helpers do not implement pairing.

## Build and validation

Run from the repository root on a workstation. Outputs must be outside the
source tree. A normal C99 compiler is sufficient for host fixtures:

```sh
bash modules/wireless/build/build.sh /tmp/wireless-host host
```

For QNX, use the repository's existing immutable compiler image selector; no
new toolchain or mutable fallback is introduced:

```sh
bash tools/ci_qnx65_image.sh
docker run --rm --platform=linux/amd64 \
  -v "$PWD:/src:ro" -v /tmp/wireless-qnx:/out -w /src \
  mhi2-qnx65-armv7-public:4.9 \
  bash modules/wireless/build/build.sh /out qnx
```

The build emits `libmibr-wireless.a`, four objects and `wireless-fixtures`.
The QNX fixture executable is compiled and inspected, never run as a vehicle
test. Target-only compile assertions check ARM, QNX and 32-bit callback widths.
Record the exact source commit, lockfile identity and output SHA-256 with the
build. Host fixtures and QNX compilation are separate commands. The repository's
publication and module gates check the source candidate; they do not execute a
dedicated wireless QNX build. Run the commands above for that compile-only check.
The pinned target archiver predates deterministic archive options; archive
metadata is not claimed to be byte-identical between builds. On a Windows
Docker bind mount, build inside the container's Linux temporary directory and
copy finished outputs back, because the older target archiver may reject a
cross-filesystem temporary-file operation.

Fixtures exercise disabled/unavailable paths, serialized callback boundaries,
USB ownership, start/stop/failed-stop retry, timeout, stale generation,
buffer ownership/backpressure, credential validation and fragmented malformed
HTTP/TLV input. No test simulates a working wireless receiver. Adapter process
isolation, firewall coexistence, AP freshness, pairing, crash recovery and the
stock wired session need adapter and unit evidence. The library itself has no
firewall, filesystem or process mutation API.

## Source and rights

All module implementation and fixtures are new project-authored code under
GPL-3.0-or-later. No OEM binary, decompiled implementation, SDK source, private
key, pairing database or upstream runtime is included. The public
[upstream v3.0 release](https://github.com/omonob/VW-MHI2-Wireless-Carplay-Maps/releases/tag/v3.0)
is a behavior/scope reference; its installer is not a complete implementation
source distribution or a license grant for an independent receiver rebuild.

Receiver reuse therefore remains a separate rights and ABI decision. This
library can be rebuilt independently, but its adapter and complete wireless
session remain unavailable. There is no installer or release artifact. Removing
the unreferenced library needs no stock restore; a future runtime integration
must first complete the quiescent stop contract and its own rollback checks.
