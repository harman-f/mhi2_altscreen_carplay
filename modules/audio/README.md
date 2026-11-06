# P6 — external-amplifier audio / Spatial Audio and Stereo UpMix

**Source-stage only. This adds NO runtime audio hook, no installer, no
modified OEM audio driver or amplifier coding, and no default-enabled feature.**

Public comparators:

- [LuKa's MHI2Q CarPlay](https://github.com/luka-dev/mib2q-carplay-rgi),
  exact reference `df73e061a29c4d996550716987f42a9243daa09a`:
  SCENE stereo -> 5.1 and APAC 5.1 -> six discrete channels. Real reference
  hardware is **Audi MHI2Q (Qualcomm)** with external MOST B&O/Bose; not our
  Škoda NVIDIA MU1440. The source's cabin-matrix constants are Audi-specific.
- [yety-ua's MHI2 K3346 port](https://github.com/yety-ua/mhi2-k3346-carplay-audio-upmix),
  exact reference `feb077310a10ce9aef357ebb6467c549eca972ee`:
  Audi **G22/MHI2/Tegra3/QNX6.5**, NVIDIA PCM sink and adapter. Its current
  six-channel gate is explicitly disabled (`MHI2_NV_SIX_CHANNEL_QUALIFIED=0`);
  host/emulator checks are not car acceptance. K3346's fitted amplifier is
  *internal*, so it is not proof for Škoda external Canton/Dynaudio either.

Selected original GPL source excerpts in `reference/` are preserved
byte-for-byte. They are not a complete decoder, buildable standalone DSP,
source of Škoda calibration or distributable installation package.
See [source mapping](reference/PROVENANCE.md).

Our only new executable source is `source/mibr_audio_gate.[ch]`, a
host-testable pure capability decision. It is not called by any runtime.
`tests/run_host.sh` verifies explicit opt-in, exact-firmware proof, physical
amp part number, six-channel route, codec, channel order, voice ownership and
CPU/recovery qualification. This is a **test of policy**, not of actual audio
signal quality or compatibility.

## Additive plan

1. Capture original HU/amp (J525) part number, coding, transport and audio
   channel layout, stock QNX PCM sink/device and existing CarPlay audio owner.
2. Compare G13/MU1440 vs Audi Qualcomm and G22 NVIDIA audio entrypoints.
   Do not reuse an Audi `deva-ctrl-qc.so` or fixed B&O speaker matrix.
3. Prove the *unaltered* 6-channel output path (silent/bounded probe in a
   controlled test) and preserve original HFP, Siri, announcement/focus paths.
4. Only then port a small, isolated scene DSP with hard timing/CPU guards;
   permit default stereo fallback, exact rollback and AB volume matching.
5. Build separate exact target bindings for `skoda-mu1440-p4526`,
   `seat-mu1409-p4708` and `seat-mu1447-p4709`; never infer SEAT audio
   compatibility from a Skoda menu or JXE fingerprint.

Intended eventual package owner: `common/audio/` + target-specific
`profiles/<firmware>/integration/audio-abi.json`. The directory is reserved,
**not included** in the assembled beta until compiled/vehicle tests pass.

Unverified assumptions: presence of an *external* amp is not confirmation of
its six-channel CarPlay input format; amplifier brand may be Canton, Dynaudio
or another SKU and affects routing, DSP matrices and controls.

## Same-owner integration seam and canonical storage (2026-11-06)

`source/mibr_audio_owner.[ch]` is a C99 **pure-data** gate prepared for
the current unit's original music/audio owner. Only a strictly increasing
owner-generation can attach; it resets all previously accumulated capability
evidence at reconnect. Music must own audio focus; any Siri, call or
announcement activity forces **STOCK** output. A stale owner cannot restore
multichannel playback or clear a newer connection.

The single configuration authority is the existing authenticated loopback
**MIBR/3** service, using `settings/registry.json`. No audio setting or
native action endpoint exists there today; `explicit_opt_in=1` in a host
fixture is not evidence of a working broker switch. A target integration
must wait for an independently qualified broker feature key, durable
value/version, readback, applied/ACTIVE receipt and reversible owner callback.
No extra sound daemon, second CarPlay owner or direct HMI configuration writer
may be introduced.

Future project-owned runtime files belong under **`/mnt/app/root/mibr/`**,
not legacy `altscreen-u2`. The three
`modules/profiles/*/integration/audio-abi.json` records additionally bind
their exact JXE/HMI API JAR SHA-256 from the canonical `profile.json`;
`mibr_audio_owner` remains unconnected until actual firmware/amp ABI proof.
This branch has **no deployable six-channel audio path**.
