# V3: runtime TCP_NODELAY A/B (MU1440 GEN2 only)

**Scope:** Only the already established `127.0.0.1:19820` GEN2 -> local renderer TCP connection. Not the iPhone Stream 111 socket, Stream 110, M1AU framing/PTS, direct-ts-parity, or MOST. This branch is an isolated source candidate based on the exact GEN2 R5 source commit `052cdccd6b9b44385bac0700dbf559bcdd4dc3f7`; it does not change frozen R5 artifacts or vehicle installation.

## Operation (after separately qualified/deployed binary)

The **default** is the baseline Nagle mode (TCP_NODELAY=0); the marker is volatile and does not persist after a reboot. On MU1440, `/tmp` points to `/dev/shmem`; create the marker at the root, without a subdirectory.

```sh
# A: TCP_NODELAY disabled (baseline)
rm -f /tmp/mibr-alt111-tcp-nodelay.enabled

# B: TCP_NODELAY enabled (send small writes promptly)
: > /tmp/mibr-alt111-tcp-nodelay.enabled

# Back to A
rm -f /tmp/mibr-alt111-tcp-nodelay.enabled

# Confirm the requested option was actually applied on the GEN2 socket:
grep 'GEN2 V3 TCP_NODELAY A/B' /tmp/altscreen111.log
```

GEN2 applies the current marker to the socket immediately on renderer connect, then polls at the existing control-worker interval of approximately 250 ms. No restart, disconnect, remount, binary swap, or recompile is necessary when switching A/B **after this build has been installed**. The implementation serializes `setsockopt` against socket close/replacement and socket sends through `g_lock`. It uses `getsockopt` read-back; log entries report `requested`, `verified`, and `errno`. It logs once per change/socket, not once per AU. Failed changes can be retried by switching the marker or reconnecting. It does not change write sizes, queue limits, loss policy, or transport clocks.

Keep the marker state, profile, resolution, FPS, CarPlay route and test sequence fixed for each A/B leg; record `GEN2 V3` log entries plus source/queue/bridge timing and any visible VC stutter. TCP_NODELAY is not a proven fix for VC decoder artifacts.

## Host smoke test

```sh
cc -std=c99 -Wall -Wextra -Werror -Isrc/native/altscreen111-gen2/include \
  tests/alt111_tcp_nodelay_test.c -o /tmp/alt111_tcp_nodelay_test
/tmp/alt111_tcp_nodelay_test
```

The test creates a loopback TCP connection, applies 0 -> 1 -> 0 using the same helper as GEN2, and verifies each state with `getsockopt`. Full target-build and in-vehicle tests remain separate acceptance gates.
