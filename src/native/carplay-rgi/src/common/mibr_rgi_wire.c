/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_rgi_wire.h"

#include <string.h>

static size_t put16(uint8_t *p, unsigned v)
{
    p[0] = (uint8_t)(v >> 8);
    p[1] = (uint8_t)v;
    return 2;
}

static size_t param_u16(uint8_t *p, unsigned id, unsigned value)
{
    put16(p, 6);
    put16(p + 2, id);
    put16(p + 4, value);
    return 6;
}

size_t mibr_rgi_component(uint8_t *out, size_t cap)
{
    static const char name[] = "RouteGuidanceDisplayComponent";
    static const uint16_t limits[7] = {0x100, 0x100, 0x100, 0x100, 6, 0x100, 6};
    size_t n = 0, i;

    if (cap < 6 + 4 + sizeof(name) + 7 * 6) {
        return 0;
    }
    n += param_u16(out + n, 0, MIBR_RGI_COMPONENT_ID);
    put16(out + n, (unsigned)(4 + sizeof(name)));
    put16(out + n + 2, 1);
    memcpy(out + n + 4, name, sizeof(name)); /* includes the NUL iAP2 strings carry */
    n += 4 + sizeof(name);
    for (i = 0; i < 7; i++) {
        n += param_u16(out + n, (unsigned)(2 + i), limits[i]);
    }
    return n;
}

static size_t control_message(uint8_t *out, size_t cap, unsigned id, int requests)
{
    size_t n = 6;
    unsigned i;

    if (cap < 6 + 6 + (requests ? 3 * 4 : 0)) {
        return 0;
    }
    out[0] = out[1] = 0x40;
    put16(out + 4, id);
    n += param_u16(out + n, 0, MIBR_RGI_COMPONENT_ID);
    for (i = 1; requests && i <= 3; i++) {
        put16(out + n, 4);
        put16(out + n + 2, i);
        n += 4;
    }
    put16(out + 2, (unsigned)n);
    return n;
}

size_t mibr_rgi_start_message(uint8_t *out, size_t cap)
{
    return control_message(out, cap, MIBR_RGI_MSG_START, 1);
}

size_t mibr_rgi_stop_message(uint8_t *out, size_t cap)
{
    return control_message(out, cap, MIBR_RGI_MSG_STOP, 0);
}

/* Scanner states: 0 searching the marker, 1 searching " CTRL[" after it, 2 reading hex. */
static const char marker[] = "--?-- [msgid=52";
static const char ctrl[] = "CTRL[";

void mibr_rgi_scan_reset(struct mibr_rgi_scan *s)
{
    s->state = 0;
    s->match = 0;
    s->nibble = -1;
    s->len = 0;
}

static int hexval(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

void mibr_rgi_scan_feed(struct mibr_rgi_scan *s, const char *data, size_t n, mibr_rgi_msg_cb cb, void *ctx)
{
    size_t i;

    for (i = 0; i < n; i++) {
        char c = data[i];

        if (s->state == 0) {
            s->match = c == marker[s->match] ? s->match + 1 : (c == marker[0] ? 1u : 0u);
            if (s->match == sizeof(marker) - 1) {
                s->state = 1;
                s->match = 0;
            }
        } else if (s->state == 1) {
            if (c == '\n' && s->match == 0) {
                continue; /* the id digits and line breaks before CTRL[ */
            }
            s->match = c == ctrl[s->match] ? s->match + 1 : (c == ctrl[0] ? 1u : 0u);
            if (s->match == sizeof(ctrl) - 1) {
                s->state = 2;
                s->match = 0;
                s->nibble = -1;
                s->len = 0;
            } else if (c == '-' && s->match == 0) {
                mibr_rgi_scan_reset(s); /* next packet line started without a payload */
                s->match = 1;
            }
        } else {
            int v = hexval(c);

            if (v >= 0) {
                if (s->nibble < 0) {
                    s->nibble = v;
                } else {
                    if (s->len < sizeof(s->msg)) {
                        s->msg[s->len] = (uint8_t)(s->nibble << 4 | v);
                    }
                    s->len++;
                    s->nibble = -1;
                }
            } else if (c == ']') {
                if (s->len >= 6 && s->len <= sizeof(s->msg) && s->msg[0] == 0x40 && s->msg[1] == 0x40 &&
                    s->msg[4] == 0x52 && (size_t)(s->msg[2] << 8 | s->msg[3]) <= s->len) {
                    cb(ctx, s->msg, (size_t)(s->msg[2] << 8 | s->msg[3]));
                }
                mibr_rgi_scan_reset(s);
            } else if (c != ' ' && c != '\n' && c != '\r' && c != '\t') {
                mibr_rgi_scan_reset(s); /* not a hex dump after all */
            }
        }
    }
}
