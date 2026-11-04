# Build-confirmed QNX SHA-256 compatibility helper

Minimal project-owned SHA-256 file utility used by the guarded MU1440 developer deployment.
It is built from `modules/carplay/source/sha256sum-compat/sha256sum_compat.c` with the same pinned public
QNX 6.5 ARMv7 toolchain as the other support tools.

The deployment uses this helper so it has no hidden dependency on an existing M.I.B.
`/apps/sbin` SD-card layout.
