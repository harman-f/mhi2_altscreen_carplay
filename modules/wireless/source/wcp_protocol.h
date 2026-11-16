/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_WCP_PROTOCOL_H
#define MIBR_WCP_PROTOCOL_H
#include <stddef.h>
#include <stdint.h>

/* Bounded, transport-neutral framing helpers; no pairing/crypto implementation.
 * The caller supplies plaintext only after its authenticated transport accepts it.
 * A caller must explicitly reject pipelined bytes it cannot process. */
#define WCP_HTTP_HEADER_MAX 2048u
#define WCP_HTTP_BODY_MAX 4096u
enum wcp_parse { WCP_PARSE_OK, WCP_PARSE_MORE, WCP_PARSE_ERROR };
struct wcp_http {
    size_t length, header_length, body_length;
    unsigned headers_done, complete, failed;
    char method[9], path[65];
    unsigned char bytes[WCP_HTTP_HEADER_MAX + WCP_HTTP_BODY_MAX];
};
void wcp_http_init(struct wcp_http *);
/* consumed allows the caller to retain bytes belonging to the next request. */
int wcp_http_feed(struct wcp_http *, const void *, size_t, size_t *consumed);
const unsigned char *wcp_http_body(const struct wcp_http *);
/* Return a single contiguous value, or adjacent 255-byte TLV fragments.
 * Reject separated duplicate values, truncation and insufficient output space.
 * No data from a malformed stream is returned. */
int wcp_tlv_value(const void *, size_t, unsigned char type,
                  void *, size_t capacity, size_t *length);
/* Strict producer channel decimal prefix with optional comma suffix. */
int wcp_channel(const char *, unsigned *channel);
#endif
