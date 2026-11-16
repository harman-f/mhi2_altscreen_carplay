/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "wcp_control.h"
#include <string.h>
#include <limits.h>

static void wipe(void *data, size_t size) {
    volatile unsigned char *p = (volatile unsigned char *)data;
    while (size--) *p++ = 0;
}
static int bounded(const char *s, size_t cap, size_t *len) {
    size_t i;
    for (i = 0; i < cap; ++i) {
        if (!s[i]) { *len = i; return 1; }
        if ((unsigned char)s[i] < 32 || (unsigned char)s[i] == 127) return 0;
    }
    return 0;
}
void wcp_config_default(struct wcp_config *c) {
    if (c) { c->enabled = 0; c->timeout_ms = 15000; }
}
int wcp_init(struct wcp_control *c, const struct wcp_config *config,
             const struct wcp_ops *ops) {
    struct wcp_config config_copy;
    struct wcp_ops ops_copy;
    if (!c || !config || config->enabled > 1 || !config->timeout_ms ||
        config->timeout_ms > 120000) return WCP_INVALID;
    if (ops && (ops->abi != WCP_ABI || ops->size != sizeof(*ops))) return WCP_INVALID;
    /* Inputs may point into a quiescent control being reinitialized. */
    config_copy = *config;
    if (ops) ops_copy = *ops;
    memset(c, 0, sizeof(*c)); c->config = config_copy;
    if (ops) c->ops = ops_copy;
    c->state = config_copy.enabled ? WCP_IDLE : WCP_OFF;
    return WCP_OK;
}
int wcp_ap_validate(const struct wcp_ap *ap) {
    size_t ssid, psk, i;
    if (!ap || !ap->generation || !ap->interface_index || !ap->channel ||
        ap->channel > 196 || !bounded(ap->ssid, sizeof(ap->ssid), &ssid) ||
        !ssid || !bounded(ap->psk, sizeof(ap->psk), &psk)) return WCP_INVALID;
    if (ap->security == WCP_AP_OPEN) return psk ? WCP_SECURITY : WCP_OK;
    if (ap->security != WCP_AP_WPA2 || psk < 8) return WCP_SECURITY;
    if (psk == 64) {
        for (i = 0; i < psk; ++i)
            if (!((ap->psk[i] >= '0' && ap->psk[i] <= '9') ||
                  (ap->psk[i] >= 'a' && ap->psk[i] <= 'f') ||
                  (ap->psk[i] >= 'A' && ap->psk[i] <= 'F'))) return WCP_SECURITY;
    }
    return WCP_OK;
}
static int available(const struct wcp_control *c) {
    return c->ops.abi == WCP_ABI && c->ops.size == sizeof(c->ops) &&
        (c->ops.capabilities & WCP_CAP_REQUIRED) == WCP_CAP_REQUIRED &&
        c->ops.claim && c->ops.begin && c->ops.send && c->ops.stop && c->ops.release;
}
static int clock_check(struct wcp_control *c, uint64_t now) {
    if (now < c->last_now) return WCP_INVALID;
    c->last_now = now; return WCP_OK;
}
int wcp_start(struct wcp_control *c, const struct wcp_ap *ap,
              const struct wcp_peer *peer, uint64_t now) {
    int rc; unsigned i, nonzero = 0;
    if (!c || c->in_callback) return WCP_INVALID;
    if (!c->config.enabled) return WCP_DISABLED;
    if (c->owns || c->wired || (c->state != WCP_IDLE && c->state != WCP_FAILED)) return WCP_BUSY;
    if (!available(c)) return WCP_UNAVAILABLE;
    rc = wcp_ap_validate(ap); if (rc) return rc;
    if (!peer || !peer->port || peer->interface_index != ap->interface_index ||
        peer->ipv6 > 1 || (peer->ipv6 && peer->ipv6_scope != ap->interface_index)) return WCP_INVALID;
    for (i = 0; i < sizeof(peer->identity); ++i) nonzero |= peer->identity[i];
    if (!nonzero || (peer->identity[0] & 1)) return WCP_INVALID;
    if (clock_check(c, now) || now > UINT64_MAX - c->config.timeout_ms ||
        c->generation == UINT64_MAX) return WCP_INVALID;
    ++c->generation; c->last_error = WCP_OK; c->verified = 0;
    c->in_callback = 1; rc = c->ops.claim(c->ops.context, c->generation); c->in_callback = 0;
    if (rc) { c->last_error = rc; c->state = WCP_FAILED; return rc; }
    c->owns = 1; c->state = WCP_BOOTSTRAP; c->deadline = now + c->config.timeout_ms;
    c->in_callback = 1;
    rc = c->ops.begin(c->ops.context, c->generation, ap, peer);
    c->in_callback = 0;
    if (rc) { c->last_error = rc; (void)wcp_stop(c); return rc; }
    return WCP_OK;
}
int wcp_event(struct wcp_control *c, uint64_t generation, enum wcp_event event,
              uint64_t now) {
    int rc;
    if (!c || c->in_callback) return WCP_INVALID;
    if (!c->owns || c->generation != generation || c->state == WCP_STOPPING) return WCP_STALE;
    rc = wcp_tick(c, now); if (rc) return rc;
    if (event == WCP_DISCONNECTED) return wcp_stop(c);
    if (event == WCP_BOOTSTRAPPED && c->state == WCP_BOOTSTRAP) c->state = WCP_VERIFY;
    else if (event == WCP_VERIFIED && c->state == WCP_VERIFY) {
        /* Authentication completed by the adapter; media still not ready. */
        if (c->verified) return WCP_INVALID;
        c->verified = 1;
    } else if (event == WCP_MEDIA_READY && c->state == WCP_VERIFY && c->verified) {
        c->state = WCP_ACTIVE; c->last_error = WCP_OK; c->deadline = 0;
    } else return WCP_INVALID;
    return WCP_OK;
}
int wcp_send(struct wcp_control *c, const void *bytes, size_t length, uint64_t *request) {
    unsigned i; int rc; struct wcp_message *m;
    if (!c || c->in_callback || !bytes || !length || length > WCP_MESSAGE_MAX || !request) return WCP_INVALID;
    if (c->state != WCP_ACTIVE || !c->owns) return WCP_UNAVAILABLE;
    if (c->next_request == UINT64_MAX) return WCP_UNAVAILABLE;
    for (i = 0; i < WCP_QUEUE && c->messages[i].used; ++i) {}
    if (i == WCP_QUEUE) return WCP_BACKPRESSURE;
    m = &c->messages[i]; m->used = 1; m->length = length;
    m->request = ++c->next_request; memcpy(m->bytes, bytes, length);
    c->in_callback = 1;
    rc = c->ops.send(c->ops.context, c->generation, m->request, m->bytes, m->length);
    c->in_callback = 0;
    if (rc) { wipe(m, sizeof(*m)); return rc; }
    *request = m->request; return WCP_OK;
}
int wcp_complete(struct wcp_control *c, uint64_t generation, uint64_t request, int result) {
    unsigned i;
    if (!c || c->in_callback) return WCP_INVALID;
    if (!c->owns || generation != c->generation || !request) return WCP_STALE;
    for (i = 0; i < WCP_QUEUE; ++i) {
        if (c->messages[i].used && c->messages[i].request == request) {
            wipe(&c->messages[i], sizeof(c->messages[i]));
            if (result) c->last_error = result;
            return result;
        }
    }
    return WCP_STALE;
}
int wcp_stop(struct wcp_control *c) {
    int rc;
    if (!c || c->in_callback) return WCP_INVALID;
    if (!c->owns) { c->state = c->config.enabled ? WCP_IDLE : WCP_OFF; return WCP_OK; }
    c->state = WCP_STOPPING; c->in_callback = 1;
    rc = c->ops.stop(c->ops.context, c->generation); c->in_callback = 0;
    if (rc) { c->last_error = rc; return rc; }
    c->in_callback = 1; c->ops.release(c->ops.context, c->generation); c->in_callback = 0;
    wipe(c->messages, sizeof(c->messages)); c->owns = 0; c->deadline = 0; c->verified = 0;
    c->state = c->config.enabled ? WCP_IDLE : WCP_OFF; return WCP_OK;
}
int wcp_tick(struct wcp_control *c, uint64_t now) {
    int rc;
    if (!c || c->in_callback) return WCP_INVALID;
    rc = clock_check(c, now); if (rc) return rc;
    if (c->owns && c->state != WCP_ACTIVE && c->state != WCP_STOPPING && now >= c->deadline) {
        c->last_error = WCP_TIMEOUT; rc = wcp_stop(c); return rc ? rc : WCP_TIMEOUT;
    }
    return WCP_OK;
}
int wcp_wired(struct wcp_control *c, unsigned active) {
    if (!c || c->in_callback || active > 1) return WCP_INVALID;
    c->wired = active;
    return active ? wcp_stop(c) : WCP_OK;
}
int wcp_uninstall_ready(const struct wcp_control *c) {
    return c && !c->owns && !c->in_callback;
}
const char *wcp_state_name(enum wcp_state state) {
    static const char *const names[] = {"OFF", "IDLE", "BOOTSTRAP", "VERIFY", "ACTIVE", "STOPPING", "FAILED"};
    return (unsigned)state < sizeof(names) / sizeof(names[0]) ? names[state] : "UNKNOWN";
}
