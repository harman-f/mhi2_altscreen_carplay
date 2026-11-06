# P1 Media / Now Playing — staged additive module

**Status: portable model and upstream references only; no installed media integration.**
All source is on a feature branch for review, not enabled on a head unit.
This is a new capability, not a replacement for CarPlay/GEN2, Navigation,
the OEM music player, BAP service, `mm-ipod` or the current MIBR/3 broker.

- `source/mibr_media_state.[ch]`: first-party C99 host-buildable model for
  exact session/track/transfer-id association and suppression of stale covers.
- `tests/run_host.sh`: portable state regression (track switch, delayed image,
  reconnect, disabled switch, stale disconnect).
- `reference/omonob/`: selected GPLv3 **unmodified upstream sources for study**,
  excluded from compiled/runtime payloads. See [provenance](reference/PROVENANCE.md).

Planned adapter layers (currently **NOT IMPLEMENTED**):
1. Read-only MU-specific iAP2 Now Playing/transfer-id probe, no extra authenticated
   CarPlay session; prefer existing stock owner and exact exported ABI over new hooks.
2. Bounded artwork helper: JPEG validation before decode; contain-fit and image format
   selected by the verified OEM picture server, never guessed from the pixel canvas.
3. ASL-thread-affine Java/J9 BAP media bridge; must preserve radio, Bluetooth,
   USB and other stock picture providers, and clear CarPlay state only.
4. Optional MIBR/3 broker switch and menu rows after ACTION/ACK semantics are tested.
   No new settings registry, wrapper or `lsd.sh` mutation in this branch.

The same implementation will belong under `common/media/`. Only target-specific
HMI, iAP2 and picture/BAP bindings belong in the three firmware profiles;
`modules/profiles/*/integration/media-phone-abi.json` declares each pending
gate. Existing navigation arrows/video and native audio sources remain unchanged.

Do not package copied reference sources into runtime `common/media/bin/`.
A host `PASS` is **not** a working `VCInformation.jar` or an OEM ABI build.

## V1 handoff into MIBR runtime (source-only)

The unit root is `/mnt/app/root/mibr/` (M1 architecture), **not** the old
`altscreen-u2` directory. This module currently installs nothing and
stores no files. **Do not add another configuration parser or broker.**

`source/mibr_media_ingress.[ch]` is the first-party platform-neutral
contract for the *existing authenticated* iAP2 worker. It accepts a strictly
increasing owner generation + session id and requires both exact input ABI
and ASL thread-affinity proof. A fresh attach clears old track and artwork.
Track and cover updates must match generation, session, transfer ID and
track epoch. It exposes only a copyable state snapshot to a future
**firmware-specific ASL-thread dispatcher**, which must preserve the OEM
picture server. It neither calls BAP nor exposes its own socket/file IPC.

Desired enable/disable must be confirmed through the **one MIBR/3 broker**.
The current 48-setting/13-switch registry does **not** contain a functional
Media control. Until the broker gains a verified setting and a real owner
consumer, the adapter is NOT bound; testing the pure ingress with
`enable(1)` only exercises policy, not a vehicle function. Add the control
to `settings/registry.json` **once**, with generated native/J9 bindings and
ACTION/ACK evidence, only in a dedicated follow-up PR.

Profile-specific ABI manifests declare exact `/ifs/lsd.jxe` and
`hmi.api_jar_sha256` matching the canonical `profile.json`; they retain
`auto_install=false` and `compiled_artifact=null`. Source-only
adapter tests live in `tests/`. Do not introduce an `mm-ipod` wrapper,
second `dio_manager`, global image-provider replacement or raw album art
in a MIBR/3 message.
