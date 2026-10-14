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
    unsigned have_wheel, have_tag;
    uint64_t frames, bad_frames, wheel_count, tag_count, matches;
};
void alt111_spi_zoom_init(struct alt111_spi_zoom *s);
void alt111_spi_zoom_feed(struct alt111_spi_zoom *s, const void *bytes, size_t n,
                         alt111_spi_zoom_cb on_zoom, void *opaque);
#endif
