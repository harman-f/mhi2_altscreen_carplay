# P1 media references — source/provenance boundary

These are **verbatim source extracts, not production inputs**. Nothing in this directory is
installed, loaded, compiled by the R3 build or added to an OEM classpath. Do not rename
the Java package, deploy `artwork-launcher.sh`, or replace `mm-ipod` from this tree.

Upstream: [omonob/MHI2-Carplay-Maps](https://github.com/omonob/MHI2-Carplay-Maps)
at commit `5ba6f7f579305960f8cae941fd4a4061f759b054` (2026-11-04),
GPL-3.0; the repository's own `LICENSE` applies. Exact upstream Git blob IDs:

| Selected source | Blob | Why |
| --- | --- | --- |
| `src/information/native/carplay_artwork_helper.c` | `e7ddc00a7976903b3da50c5c80da7659643ae6df` | iAP2 artwork transfer-id, `iap2_filexfer_read`, bound JPEG, atomic publish, track signature |
| `src/information/java/org/omonob/cpmap/information/InformationAslDispatch.java` | `6b6c9475794bab3c530539090b80053931ec2c56` | Single owning ASL thread, coalesced dispatch, attach result |
| `src/information/runtime/artwork-launcher.sh` | `3898bd64d8f0b4b69eb177b0eb5382659d66bd75` | Lifecycle reference only; **do not execute** |

Only the selected source is reproduced; **not** the author's OEM/SDK/firmware
libraries, third-party image headers, compiled JARs, QNX binaries, wrapper for
`mm-ipod` or historical instruction/bytecode dumps. The C file includes
upstream `vendor/stb_image*.h` paths that are intentionally absent here.
A future curated implementation must carry compatible license notices and
correct third-party header provenance or use another audited decoder.

The public upstream currently advertises v2.1 RC work as experimental.
A checked-in reference is not ABI evidence for Škoda MU1440 or SEAT MU1409/MU1447.
Do not assume `/ramdisk/pps/iap2/nowplaying`, `/dev/ipod0`, the original
`libiap2client.so.1` symbols or the ASL BAP API match another firmware.
