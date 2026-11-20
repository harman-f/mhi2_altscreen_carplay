# P2 phone references — source/provenance boundary

Selected independent Java extensions, copied verbatim for **research only** from
[ProManiFest2122/mhi2-k3346-carplay-vc](https://github.com/ProManiFest2122/mhi2-k3346-carplay-vc),
commit `1aaef38b1acd468702e05ffa21965cff682a22fc` (2026-11-03).
The component's `port_k3346/altscreen/LICENSE-GPL-3.0` and repository notices
apply. Upstream in turn credits luka-dev for its phone-service gating concepts.

| Selected source | Upstream blob | Purpose |
| --- | --- | --- |
| `K3346PpsCall.java` | `09cb9701f3b6e02e8e9c0cc2779938d977f40d30` | PPS telephony state parsing |
| `K3346GatedPhoneListener.java` | `58fc11ae24cc9203d80689b16160a7550b94da2f` | Action gate that forwards to OEM when not owned |
| `K3346CallCard.java` | `2a949606c2cc19a051e125f79ada3bdbed96b91c` | Privacy-conscious call-card state format |

**Not copied:** stock-derived `ServiceManagerPhone.java`, entire Audi OSGi
services, binary `JAR` patches, HUD/Cockpit overlay, iAP2 phone hooks, and
firmware libraries. The copied classes reference Audi-specific packages;
they are intentionally not compiled or shipped. Do not invent matching
Škoda/SEAT interfaces or force a phone-control delegate into their HMI.

The new first-party `modules/phone/source/` is a separate clean-room,
fail-closed **state model only**. Explicit phone-control authorization and
OEM callback routing are pending target-specific ABI and physical testing.
