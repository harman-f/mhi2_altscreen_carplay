# Experimental semantic zoom source

The project-owned `alt111_zoom.c` queue and `alt111_zoom_debugspi.c` parser form part of the canonical GEN2 implementation. Eligible input is converted into `changeMapZoomLevel` for the active negotiated display UUID through the existing authenticated session. The queue is bounded, generation-aware and paced; disarming or losing session readiness cancels pending work.

The reference observer accepts receive-only framed loopback input and correlates right-encoder events with a nearby semantic marker. It does not send DebugSPI bytes, replace OEM listeners, suppress native zoom, create another CarPlay session, or write MOST payload. The opt-in marker is off by default. This correlation is experimental and is not independent proof of current visible VC map focus or owner state.

Publishing this existing implementation does not approve a new physical gesture assignment or qualify exclusive input routing. OEM short-press, navigation, volume and unrelated controls retain their existing ownership. The source-level route policy is not a qualified OEM call-site interceptor.

Run `bash tools/test_alt111_zoom_host.sh` for queue, tuple, correlation, segmentation, duplicate and timestamp-wrap regressions. Host parser/queue checks and a QNX build do not establish visible phone-map zoom, target input focus, or a safe vehicle installation. See the [source baseline](../../../docs/build/MU1440_R50_SOURCE.md).
