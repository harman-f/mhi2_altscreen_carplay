/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "wcp_config.h"
#include "wcp_protocol.h"
#include <string.h>

static void clear(void *p, size_t n) {
    volatile unsigned char *b = (volatile unsigned char *)p;
    while (n--) *b++ = 0;
}
static int decimal(const char *s, unsigned max, unsigned *out) {
    unsigned n = 0, digit;
    if (!*s) return WCP_INVALID;
    for (; *s; ++s) {
        if (*s < '0' || *s > '9') return WCP_INVALID;
        digit = (unsigned)(*s - '0');
        if (digit > max || n > (max - digit) / 10) return WCP_INVALID;
        n = n * 10 + digit;
    }
    *out = n; return WCP_OK;
}
struct fields { char key[32], value[128]; size_t at; };
static int line(const unsigned char *b, size_t size, struct fields *f) {
    size_t end, eq, n, i;
    if (f->at == size) return 0;
    for (end = f->at; end < size && b[end] != '\n'; ++end) {}
    if (end == size) return WCP_INVALID;
    for (eq = f->at; eq < end && b[eq] != '='; ++eq) {}
    n = eq - f->at;
    if (!n || n >= sizeof(f->key) || eq == end || end - eq - 1 >= sizeof(f->value)) return WCP_INVALID;
    for (i = f->at; i < end; ++i) if (b[i] < 32 || b[i] == 127) return WCP_INVALID;
    memcpy(f->key, b + f->at, n); f->key[n] = 0;
    n = end - eq - 1; memcpy(f->value, b + eq + 1, n); f->value[n] = 0;
    f->at = end + 1; return 1;
}
int wcp_config_parse(const void *data, size_t length, struct wcp_config *out) {
    struct fields f; struct wcp_config cfg; unsigned seen = 0, bit, value; int rc;
    if (!out) return WCP_INVALID;
    wcp_config_default(out); wcp_config_default(&cfg); memset(&f, 0, sizeof(f));
    if ((!data && length) || length > 256) return WCP_INVALID;
    while ((rc = line((const unsigned char *)data, length, &f)) > 0) {
        if (!strcmp(f.key, "enabled")) {
            bit = 1; if (decimal(f.value, 1, &value)) return WCP_INVALID; cfg.enabled = value;
        } else if (!strcmp(f.key, "handshake_timeout_ms")) {
            bit = 2; if (decimal(f.value, 120000, &value) || !value) return WCP_INVALID; cfg.timeout_ms = value;
        } else return WCP_INVALID;
        if (seen & bit) return WCP_INVALID;
        seen |= bit;
    }
    if (rc < 0) return rc;
    *out = cfg; return WCP_OK;
}
int wcp_ap_record(const void *data, size_t length, uint64_t before, uint64_t after,
                   uint32_t interface_index, struct wcp_ap *out) {
    struct fields f; struct wcp_ap ap; unsigned seen = 0, bit, secure = 0, cipher = 0;
    int rc = WCP_INVALID, next;
    if (!out) return rc;
    clear(out, sizeof(*out)); memset(&ap, 0, sizeof(ap)); memset(&f, 0, sizeof(f));
    if (!before || before != after) return WCP_STALE;
    if ((!data && length) || !length || length > 1024 || !interface_index) return rc;
    while ((next = line((const unsigned char *)data, length, &f)) > 0) {
        if (!strcmp(f.key, "ssid")) {
            bit = 1; if (strlen(f.value) >= sizeof(ap.ssid)) goto done;
            strcpy(ap.ssid, f.value);
        } else if (!strcmp(f.key, "psk")) {
            bit = 2; if (strlen(f.value) >= sizeof(ap.psk)) goto done;
            strcpy(ap.psk, f.value);
        } else if (!strcmp(f.key, "channel")) {
            bit = 4; if (wcp_channel(f.value, &ap.channel) != WCP_PARSE_OK) goto done;
        } else if (!strcmp(f.key, "security")) {
            bit = 8;
            if (!strcmp(f.value, "open")) { secure = 0; ap.security = WCP_AP_OPEN; }
            else if (!strcmp(f.value, "wpa2")) { secure = 1; ap.security = WCP_AP_WPA2; }
            else { rc = WCP_SECURITY; goto done; }
        } else if (!strcmp(f.key, "cipher")) {
            bit = 16;
            if (!strcmp(f.value, "none")) cipher = 1;
            else if (!strcmp(f.value, "ccmp")) cipher = 2;
            else { rc = WCP_SECURITY; goto done; }
        } else goto done;
        if (seen & bit) goto done;
        seen |= bit;
    }
    if (next < 0 || seen != 31) goto done;
    if ((secure && cipher != 2) || (!secure && cipher != 1)) { rc = WCP_SECURITY; goto done; }
    ap.generation = before; ap.interface_index = interface_index;
    rc = wcp_ap_validate(&ap);
    if (!rc) *out = ap;
done:
    clear(&ap, sizeof(ap)); clear(&f, sizeof(f)); return rc;
}
