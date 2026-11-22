# P2 CarPlay phone / calls — staged additive module

**Status: OEM-independent call state only; no active dial/accept/hangup hooks.**

- `source/mibr_phone_state.[ch]`: bounded session/call-id model. Incoming,
  dialing, active and held states; explicit CarPlay audio ownership; reject
  stale actions and allow only ringing/accept or active/hangup conditions.
- `tests/run_host.sh`: host-only safety fixtures; stores caller details only
  in memory and never prints the name, number or call ID in diagnostics.
- `reference/k3346/`: selected GPLv3 Audi-specific P2 Java source **only for
  comparison**, not a bundled adapter. See [provenance](reference/PROVENANCE.md).

Exact source-to-platform comparison:
- `chefranov/mhi2-au37x-carplay`: MHI2 AU37x, documented P5089/MU1326
  Audi A3 and Q2 AU276, uses Audi cluster phone tab; vehicle-tested on these,
  **not** a Škoda/SEAT binary.
- `ProManiFest2122/mhi2-k3346-carplay-vc`: Audi K3346-style Java BAP
  telephony wrappers/overlay with phone action gate; Audi APIs, not Škoda.
- `kamgurgul/mib2q-carplay`: MHI2Q Audi A5/MU1329 with working phone pages;
  incompatible Java/HMI binding with NVIDIA MHI2. Useful action patterns only.
- `omonob/MHI2-Carplay-Maps` v2.1 information: nav and music, **no integrated
  CarPlay telephone support** in that information module.

No direct assumption that the Škoda 790 or SEAT 790 cluster supports an Audi
phone service/binary. First determine HU→cluster phone BAP service, existing
HFP ownership and CarPlay telephony event source. The correct design wraps
the *existing* OEM delegate and forwards every call when CarPlay does not
explicitly own the phone interface. No global tel-key rerouting or HFP disable
is included. A BAP/telephone action is never sent merely because UI state
was stored.

R3 intended distribution: `common/phone/` + target-specific profile adapters.
All three target adapters stay `not-built` and `autoinstall=false` until
source ABI, a reversible classpath overlay, package hashes and vehicle tests exist.

## V1 handoff into MIBR runtime (source-only)

`source/mibr_phone_ingress.[ch]` consumes phone events from the **existing**
authenticated iAP2/CarPlay owner. Every active event must carry its owner
generation, session and call ID. A new generation discards cached caller data;
stale disconnects/events cannot change the current call. The exact-target
phone/BAP and stock-delegate ABI must both be qualified before attach.

The source permits a possible steering-wheel action **only** if the
target's input adapter was separately qualified and the user has explicitly
enabled the *broker-confirmed* feature; the current action/call is verified.
This is a permission predicate only: it does NOT send any action or replace
the factory HFP delegate. **Without an OEM call-control binding there is no
accept/hang-up function.**

Current MIBR/3 is the sole owner of settings and ACTION/ACK. There are no
new `settings/registry.json` phone keys or extra phone daemon; the planned
feature remains OFF. A future target wrapper must pass through to stock for
every unowned call and preserve stock TEL button behavior. Caller name and
number must never be sent to a broker log or persistent config.

Installation root for future project-owned files is
`/mnt/app/root/mibr/`; exact firmware/J9 API hashes and disabled
module state are verified by the per-profile integration contract checker.
