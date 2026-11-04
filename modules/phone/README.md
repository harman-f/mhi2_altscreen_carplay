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
