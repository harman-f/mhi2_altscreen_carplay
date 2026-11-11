# P1/P2/P5/P6 integration handoff (source-stage, 2026-11-11)

This is the **shared integration contract**, not evidence that an OEM Java
adapter, authenticated phone subscription, sound driver, amplifier, or
installed `mibr-v3-service` already consumes these entrypoints.

## Source of truth and process ownership

```text
OEM iAP2 / DIO CarPlay session (EXISTING owner, never cloned)
    |
    | one owner generation and original CarPlay session identity
    +-- P1 media:          mibr_media_ingress     -> future ASL/BAP media adapter
    +-- P2 phone:          mibr_phone_ingress     -> future OEM TEL/BAP delegate
    +-- P5 vehicle data:   existing mibr_vdata     -> original authenticated iAP2 sender
    |
OEM audio focus and route owner (EXISTING owner, never cloned)
    +-- P6 audio:          mibr_audio_owner       -> future qualified PCM adapter

MIBR/3 (ONE settings authority, no raw media or caller information)
    +-- desired feature opt-in, policy, version/CAS and request receipts
    +-- independent adapter observation/ACK required before ACTIVE claim

Firmware profile: SHA-256 of /ifs/lsd.jxe + exact Java SDK/ABI
    +-- Skoda MU1440 / SEAT MU1409 / SEAT MU1447 bindings (OFF, unbuilt)
```

**Transport lifecycle:** an OEM-proven adapter gives each feature a strictly
increasing owner-generation and session ID. On reconnect, each consumer
invalidates its prior snapshot and refuses stale callbacks. A torn-down
generation cannot activate its successor. The generation is a *logical*
source-owner identity, not a fabricated iAP2 ID; its producer and authority
still need a real exact-firmware hook.

**Data plane:** the source models are bounded C99 in-memory states, never
another TCP service or copy of the iAP2 session. Media cover bytes, BAP
picture-manager threading, phone call-control, and six-channel PCM stay
in **separate target-specific adapters**. Media track title/cover must never
be encoded as generic vehicle NMEA; vehicle status TLVs must never be sent
through a text-only NMEA entrypoint. Real-time data does not transit MIBR/3.

**Control plane:** MIBR/3 exclusively owns settings and validated actions.
No `media.*`, `phone.*` or `audio.*` key exists in the current canonical
`settings/registry.json`. Enabling a pure test fixture is not a deployed
toggle. The future sequence must be *desired -> stored/CAS -> owner apply ->
independent observed ACK -> ACTIVE*, with unavailable capabilities remaining
absent or `UNKNOWN`. Never equate a successful source compile with an active
vehicle setting.

**Audio priority:** only music focus may select a qualified SCENE/5.1 path.
Siri, native navigation announcements, telephone calls, and any unknown
focus revert to stock. The native audio owner must provide the focus state;
P2's state model alone is not a sound focus authority. A new session clears
P6's capability evidence until exact routing is requalified.

**OEM/rollback:** original HFP call stack, Bluetooth/radio cover source,
stock native map arrows, stock vehicle data send, stock audio driver and
MOST writer remain authoritative outside the precisely scoped new
feature. User data belongs only under `/mnt/app/root/mibr/`; no direct
write to `/ifs`, `/mnt/app/eso` or J525 coding is permitted in this stage.

## Test boundary

`modules/audio/tests/test_cross_feature_session.c` links the three
portable C99 feature models with a mocked *single* CarPlay owner. It
exercises a cover update, phone call interruption, audio stock fallback,
generation change, stale call/cover rejection and disabled-policy defaults.
It deliberately simulates ABI qualification and owner focus callbacks,
**not** actual QNX/IBM J9 integration or successful phone consumption.
All three exact-profile build/deployment guards remain closed.

## Blockers before activation

1. Prove the actual `dio_manager` / iAP2, OEM TEL/BAP and ASL picture
   entrypoints from each firmware and record class/ELF ABI fingerprints.
2. Prove a qualified **single** lifecycle-generation producer and safe
   callback thread dispatch, including ordered call/track deltas.
3. Add reviewed keys to the **single** registry, regenerate bindings,
   implement narrowly scoped MIBR/3 permissions and independent ACK.
4. Produce and provenance-record the exact target QNX/J9 artifact plus
   reversible deployment and complete three-profile ZIP validation.
5. Perform vehicle testing for phone subscription and P5 acceptance; for
   P6 first identify the actual installed amplifier and validate the
   stock PCM/MOST channel map without changing factory coding.

**Integration order:** #140 P1/P2 source stage -> #141 P6/P5 stage ->
separately reviewed exact firmware ABI and driver integration. Do not merge
a source-stage branch as permission to install its disabled features.
