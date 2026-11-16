/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "wcp_protocol.h"
#include <string.h>

void wcp_http_init(struct wcp_http *p) { if (p) memset(p, 0, sizeof(*p)); }
static unsigned char lower(unsigned char c) { return c >= 'A' && c <= 'Z' ? (unsigned char)(c + 32) : c; }
static int eq(const unsigned char *s, size_t n, const char *literal) {
    size_t i; if (strlen(literal) != n) return 0;
    for (i = 0; i < n; ++i) if (lower(s[i]) != (unsigned char)literal[i]) return 0;
    return 1;
}
static int token(unsigned char c) {
    return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
           (c >= '0' && c <= '9') || strchr("!#$%&'*+-.^_`|~", c) != NULL;
}
static int headers(struct wcp_http *p) {
    size_t at = 0, end, one, two, colon, value, i, n; unsigned found = 0;
    unsigned char *b = p->bytes;
    for (end = 0; end + 1 < p->header_length && !(b[end] == '\r' && b[end+1] == '\n'); ++end) {}
    for (one = 0; one < end && b[one] != ' '; ++one) {}
    for (two = one + 1; two < end && b[two] != ' '; ++two) {}
    if (!one || one >= sizeof(p->method) || two <= one + 1 || two - one - 1 >= sizeof(p->path) ||
        end - two != 9 || memcmp(b + two + 1, "HTTP/1.1", 8) || b[one + 1] != '/') return 0;
    for (i = 0; i < one; ++i) if (b[i] < 'A' || b[i] > 'Z') return 0;
    for (i = one + 1; i < two; ++i) if (b[i] < 33 || b[i] > 126) return 0;
    memcpy(p->method, b, one); memcpy(p->path, b + one + 1, two - one - 1);
    at = end + 2;
    while (at + 2 < p->header_length) {
        for (end = at; end + 1 < p->header_length && !(b[end] == '\r' && b[end+1] == '\n'); ++end) {}
        for (colon = at; colon < end && b[colon] != ':'; ++colon) if (!token(b[colon])) return 0;
        if (colon == at || colon == end) return 0;
        value = colon + 1;
        while (value < end && (b[value] == ' ' || b[value] == '\t')) ++value;
        for (i = value; i < end; ++i) if ((b[i] < 32 && b[i] != '\t') || b[i] == 127) return 0;
        if (eq(b + at, colon - at, "transfer-encoding")) return 0;
        if (eq(b + at, colon - at, "content-length")) {
            if (found++ || value == end) return 0;
            n = 0;
            for (i = value; i < end; ++i) {
                size_t digit;
                if (b[i] < '0' || b[i] > '9') return 0;
                digit = (size_t)(b[i] - '0');
                /* Check before multiplication so an arbitrarily long decimal
                 * value cannot wrap size_t and masquerade as a small body. */
                if (n > (WCP_HTTP_BODY_MAX - digit) / 10) return 0;
                n = n * 10 + digit;
            }
            p->body_length = n;
        }
        at = end + 2;
    }
    return at + 2 == p->header_length;
}
int wcp_http_feed(struct wcp_http *p, const void *data, size_t length, size_t *consumed) {
    const unsigned char *b = (const unsigned char *)data; size_t i = 0, n;
    if (!p || !consumed || (!data && length)) return WCP_PARSE_ERROR;
    *consumed = 0;
    if (p->failed) return WCP_PARSE_ERROR;
    if (p->complete) return WCP_PARSE_OK;
    while (i < length) {
        if (p->length >= sizeof(p->bytes) || (!p->headers_done && p->length >= WCP_HTTP_HEADER_MAX)) goto fail;
        p->bytes[p->length++] = b[i++]; *consumed = i;
        n = p->length;
        if (!p->headers_done) {
            if (!b[i-1] || (b[i-1] == '\n' && (n < 2 || p->bytes[n-2] != '\r')) ||
                (n > 1 && p->bytes[n-2] == '\r' && b[i-1] != '\n')) goto fail;
            if (n >= 4 && !memcmp(p->bytes + n - 4, "\r\n\r\n", 4)) {
                p->header_length = n;
                if (!headers(p)) goto fail;
                p->headers_done = 1;
            }
        }
        if (p->headers_done && p->length == p->header_length + p->body_length) {
            p->complete = 1; return WCP_PARSE_OK;
        }
    }
    return WCP_PARSE_MORE;
fail:
    p->failed = 1; return WCP_PARSE_ERROR;
}
const unsigned char *wcp_http_body(const struct wcp_http *p) {
    return p && p->complete && !p->failed ? p->bytes + p->header_length : NULL;
}
int wcp_tlv_value(const void *data, size_t length, unsigned char type,
                  void *out, size_t capacity, size_t *out_length) {
    const unsigned char *b = (const unsigned char *)data;
    unsigned char *dst = (unsigned char *)out;
    size_t at = 0, total = 0, n, previous = 0; unsigned found = 0, closed = 0;
    if (!out_length || (!data && length) || (!out && capacity)) return WCP_PARSE_ERROR;
    *out_length = 0;
    /* Validate the entire stream before copying anything. */
    while (at < length) {
        if (length - at < 2) return WCP_PARSE_ERROR;
        n = b[at+1];
        if (n > length - at - 2) return WCP_PARSE_ERROR;
        if (b[at] == type) {
            if (closed || (found && previous != 255) || n > capacity - total) return WCP_PARSE_ERROR;
            found = 1; previous = n; total += n;
        } else if (found) closed = 1;
        at += n + 2;
    }
    if (!found) return WCP_PARSE_MORE;
    at = 0; total = 0;
    while (at < length) {
        n = b[at+1];
        if (b[at] == type && n) { memcpy(dst + total, b + at + 2, n); total += n; }
        at += n + 2;
    }
    *out_length = total; return WCP_PARSE_OK;
}
int wcp_channel(const char *text, unsigned *channel) {
    unsigned n = 0, digits = 0; const unsigned char *p = (const unsigned char *)text;
    if (!text || !channel) return WCP_PARSE_ERROR;
    while (*p >= '0' && *p <= '9') {
        n = n * 10 + *p++ - '0';
        if (++digits > 3 || n > 196) return WCP_PARSE_ERROR;
    }
    if (!digits || !n || (*p && *p != ',')) return WCP_PARSE_ERROR;
    if (*p == ',') {
        ++p; if (!*p) return WCP_PARSE_ERROR;
        while (*p) { if (*p < 32 || *p > 126) return WCP_PARSE_ERROR; ++p; }
    }
    *channel = n; return WCP_PARSE_OK;
}
