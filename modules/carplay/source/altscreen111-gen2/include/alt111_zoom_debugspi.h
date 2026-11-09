#ifndef MIBR_ALT111_ZOOM_DEBUGSPI_H
#define MIBR_ALT111_ZOOM_DEBUGSPI_H
#include <stddef.h>
#include <stdint.h>

/* Receive-only DebugSPI parser. Emits only a right-wheel five-int tuple
 * temporally matched with f904/tag56 from the SAME original MLP stream.
 * Tag56's exact OEM Java method is not yet known; this is a correlation
 * detector, not an assertion about BAP call direction or VC focus.
 * There are NO key, menu, VIEW, volume or OEM-suppression operations here. */
#define ALT111_SPI_FRAME_MAX 262144u
#define ALT111_SPI_MATCH_WINDOW_MS 40u
typedef void (*alt111_spi_zoom_cb)(void *opaque, uint32_t source_ms, int signed_detent);
struct alt111_spi_zoom {
    unsigned char buf[ALT111_SPI_FRAME_MAX + 8192u];
    size_t used;
    uint32_t wheel_ms, tag_ms;
    int wheel_delta;
    unsigned wheel_source, tag, window_ms; /* configurable; defaults 40/56/40 */
    unsigned have_wheel, have_tag;
    uint64_t frames, bad_frames, wheel_count, tag_count, matches;
};
/* init resets ALL state including the signature to the defaults; a caller that
 * wants another signature must call configure after every init. configure keeps
 * stream state, rejects (returns 0, no change) window_ms outside 1..500 or
 * source/tag above 65535. */
void alt111_spi_zoom_init(struct alt111_spi_zoom *s);
int alt111_spi_zoom_configure(struct alt111_spi_zoom *s, unsigned wheel_source,
                              unsigned tag, unsigned window_ms);
void alt111_spi_zoom_feed(struct alt111_spi_zoom *s, const void *bytes, size_t n,
                         alt111_spi_zoom_cb on_zoom, void *opaque);
#endif
