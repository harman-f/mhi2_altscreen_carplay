# P6 third-party audio source extracts (inactive)

Files were copied unmodified from the following pinned *public* sources;
their original GPL-3.0-family licensing and authorship remain. Original Git
blob identifiers are from the GitHub contents API (SHA-1 object IDs, **not**
release SHA-256). All are research-only, **outside any runtime build graph**.

| Local file | Upstream repository / path | Pinned commit | Git blob SHA |
| --- | --- | --- | --- |
| `luka/scene_engine.c` | `luka-dev/mib2q-carplay-rgi/hook/audio/scene_engine.c` | `df73e061a29c4d996550716987f42a9243daa09a` | `c662f0b977081e0895347d9cefed59633d1730f0` |
| `luka/scene_engine.h` | `luka-dev/mib2q-carplay-rgi/hook/audio/scene_engine.h` | same | `b695e2d4b6c7e6ae5e26dcaacb19926f93660cca` |
| `k3346/mhi2_scene_adapter.c` | `yety-ua/mhi2-k3346-carplay-audio-upmix/audio_k3346/prototype/mhi2_scene_adapter.c` | `feb077310a10ce9aef357ebb6467c549eca972ee` | `53b7b73e647553ecd7b1b9e4e2bd5df02620d211` |
| `k3346/mhi2_scene_adapter.h` | corresponding `audio_k3346/prototype/` header | same | `4ac87634ca92c8f62aece12cca700b6fda6d0683` |
| `k3346/nvidia_pcm_sink.c` | corresponding `audio_k3346/prototype/` C source | same | `dfe7dff8deae6861c4753f523e73a5f36150e4dc` |
| `k3346/nvidia_pcm_sink.h` | corresponding `audio_k3346/prototype/` header | same | `1de977ff93855b00b0ec0192294ad45c048e4b98` |

Source status: selected interface/algorithm extracts, **incomplete and
unbuildable as a standalone audio package** (missing scene math, mask worker,
codec libs, exact OEM transport, DSP model). No OEM or licensed ODIS binary,
J525 firmware/dump, audio codec binary, third-party datasets, proprietary
model weights, sound calibration or original amplifier image was copied.

LuKa's 2026-10-29 release is the pinned upstream for audio semantics;
yety-ua is a GitHub fork of `ProManiFest2122/mhi2-k3346-carplay-vc` and
credits LuKa's algorithm. Different target ABI, not a later universal
replacement for the Audi MHI2Q reference. Do not silently replace the
reference or omit original copyright attribution during implementation.
