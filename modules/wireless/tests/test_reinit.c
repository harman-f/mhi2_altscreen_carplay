/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Host-only lifecycle regression; no radio or target dependencies. */
#include "wcp_control.h"
#include <assert.h>
#include <string.h>

struct fake { int fail_stop; unsigned releases; };
static int claim(void *p, uint64_t g) { (void)p; (void)g; return 0; }
static int begin(void *p, uint64_t g, const struct wcp_ap *a, const struct wcp_peer *q)
{ (void)p; (void)g; (void)a; (void)q; return 0; }
static int send_msg(void *p, uint64_t g, uint64_t r, const unsigned char *b, size_t n)
{ (void)p; (void)g; (void)r; (void)b; (void)n; return 0; }
static int stop(void *p, uint64_t g) { (void)g; return ((struct fake *)p)->fail_stop; }
static void release(void *p, uint64_t g) { (void)g; ++((struct fake *)p)->releases; }
static void activate(struct wcp_control *c, const struct wcp_ap *ap, const struct wcp_peer *peer, uint64_t t)
{
    assert(wcp_start(c, ap, peer, t) == WCP_OK);
    assert(wcp_event(c, c->generation, WCP_BOOTSTRAPPED, t) == WCP_OK);
    assert(wcp_event(c, c->generation, WCP_VERIFIED, t) == WCP_OK);
    assert(wcp_event(c, c->generation, WCP_MEDIA_READY, t) == WCP_OK);
}
int main(void)
{
    struct wcp_control c;
    struct wcp_config cfg = {1, 100};
    struct fake f = {0, 0};
    struct wcp_ops ops = {WCP_ABI, sizeof(ops), WCP_CAP_REQUIRED, &f,
                          claim, begin, send_msg, stop, release};
    struct wcp_ap ap = {1, 2, 6, WCP_AP_WPA2, "synthetic", "synthetic-password"};
    struct wcp_peer peer = {{2,0,0,0,0,1}, 2, 0, 7000, 0};
    uint64_t old_gen, old_request, new_request;
    assert(wcp_init(&c, &cfg, &ops) == WCP_OK);
    activate(&c, &ap, &peer, 10);
    old_gen = c.generation;
    assert(wcp_send(&c, "old", 3, &old_request) == WCP_OK);
    f.fail_stop = WCP_ADAPTER_ERROR;
    assert(wcp_stop(&c) == WCP_ADAPTER_ERROR);
    assert(wcp_reinit(&c, &c.config, &c.ops) == WCP_BUSY);
    assert(c.owns && c.messages[0].used && f.releases == 0);
    f.fail_stop = 0;
    assert(wcp_stop(&c) == WCP_OK);
    assert(wcp_reinit(&c, &c.config, &c.ops) == WCP_OK);
    assert(c.last_now == 10);
    activate(&c, &ap, &peer, 11);
    assert(wcp_send(&c, "new", 3, &new_request) == WCP_OK);
    assert(c.generation != old_gen && new_request != old_request);
    assert(wcp_event(&c, old_gen, WCP_DISCONNECTED, 12) == WCP_STALE);
    assert(wcp_complete(&c, old_gen, old_request, WCP_OK) == WCP_STALE);
    assert(c.state == WCP_ACTIVE && c.messages[0].used);
    assert(!memcmp(c.messages[0].bytes, "new", 3));
    assert(wcp_complete(&c, c.generation, new_request, WCP_OK) == WCP_OK);
    assert(wcp_wired(&c, 1) == WCP_OK);
    assert(wcp_reinit(&c, &c.config, &c.ops) == WCP_OK && c.wired);
    assert(wcp_start(&c, &ap, &peer, 12) == WCP_BUSY);
    assert(wcp_wired(&c, 0) == WCP_OK);
    c.next_request = UINT64_MAX;
    assert(wcp_reinit(&c, &c.config, &c.ops) == WCP_OK);
    activate(&c, &ap, &peer, 12);
    assert(wcp_send(&c, "x", 1, &new_request) == WCP_UNAVAILABLE);
    assert(wcp_stop(&c) == WCP_OK);
    c.generation = UINT64_MAX;
    assert(wcp_reinit(&c, &c.config, &c.ops) == WCP_OK);
    assert(wcp_start(&c, &ap, &peer, 12) == WCP_INVALID);
    return 0;
}
