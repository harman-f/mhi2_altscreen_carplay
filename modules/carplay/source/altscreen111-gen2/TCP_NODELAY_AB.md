# Local renderer TCP policy

`alt111_tcp_nodelay.h` applies the existing experimental TCP_NODELAY policy only to the GEN2-to-renderer loopback connection. It does not change the phone-facing socket, M1AU record format, PTS clock, ownership or MOST worker.

The existing volatile marker selects the socket option; baseline Nagle mode remains the default. Runtime state uses a flat `/tmp` filename. This source publication preserves that existing experimental behavior and adds no user control or default change.

`tests/alt111_tcp_nodelay_test.c` checks the actual loopback socket option through 0 → 1 → 0. It is a host check, not evidence of measured vehicle latency improvement or independent vehicle qualification.
