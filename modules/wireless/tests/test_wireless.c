/* SPDX-License-Identifier: GPL-3.0-or-later */
/* Synthetic adapter and protocol fixtures. This executable never accesses radios. */
#include "wcp_control.h"
#include "wcp_protocol.h"
#include "wcp_config.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

struct fake {
    unsigned claims, begins, sends, stops, releases;
    int fail_claim, fail_begin, fail_stop, fail_send;
    const unsigned char *borrowed;
    struct wcp_control *owner;
};
static int claim(void *p, uint64_t generation) {
    struct fake *f = p; assert(generation); ++f->claims; return f->fail_claim;
}
static int begin(void *p, uint64_t generation, const struct wcp_ap *ap, const struct wcp_peer *peer) {
    struct fake *f = p; assert(generation && ap && peer); ++f->begins;
    assert(wcp_stop(f->owner) == WCP_INVALID); return f->fail_begin;
}
static int send_message(void *p, uint64_t generation, uint64_t request, const unsigned char *b, size_t n) {
    struct fake *f = p; assert(generation && request && n); ++f->sends;
    f->borrowed = b; return f->fail_send;
}
static int stop(void *p, uint64_t generation) {
    struct fake *f = p; assert(generation); ++f->stops; return f->fail_stop;
}
static void release(void *p, uint64_t generation) {
    struct fake *f = p; assert(generation); ++f->releases; f->borrowed = NULL;
}
static void setup(struct wcp_control *c, struct fake *f, unsigned enabled) {
    struct wcp_config cfg; struct wcp_ops ops;
    memset(f, 0, sizeof(*f)); f->owner = c;
    wcp_config_default(&cfg); cfg.enabled = enabled;
    memset(&ops, 0, sizeof(ops)); ops.abi = WCP_ABI; ops.size = sizeof(ops);
    ops.capabilities = WCP_CAP_REQUIRED; ops.context = f;
    ops.claim = claim; ops.begin = begin; ops.send = send_message;
    ops.stop = stop; ops.release = release;
    assert(wcp_init(c, &cfg, &ops) == WCP_OK);
}
static struct wcp_ap ap_fixture(void) {
    struct wcp_ap ap; memset(&ap, 0, sizeof(ap));
    ap.generation = 7; ap.interface_index = 3; ap.channel = 6; ap.security = WCP_AP_WPA2;
    strcpy(ap.ssid, "synthetic-access-point"); strcpy(ap.psk, "synthetic-key-123"); return ap;
}
static struct wcp_peer peer_fixture(void) {
    struct wcp_peer p; memset(&p, 0, sizeof(p)); p.identity[0] = 2; p.identity[5] = 1;
    p.interface_index = 3; p.port = 7000; return p;
}
static void activate(struct wcp_control *c, const struct wcp_ap *ap, const struct wcp_peer *p, uint64_t now) {
    assert(wcp_start(c, ap, p, now) == WCP_OK);
    assert(wcp_event(c, c->generation, WCP_MEDIA_READY, now+1) == WCP_INVALID);
    assert(wcp_event(c, c->generation, WCP_BOOTSTRAPPED, now+1) == WCP_OK);
    assert(wcp_event(c, c->generation, WCP_MEDIA_READY, now+2) == WCP_INVALID);
    assert(wcp_event(c, c->generation, WCP_VERIFIED, now+2) == WCP_OK);
    assert(wcp_event(c, c->generation, WCP_MEDIA_READY, now+3) == WCP_OK);
    assert(c->state == WCP_ACTIVE);
}
static void lifecycle(void) {
    struct wcp_control c; struct fake f; struct wcp_ap ap = ap_fixture(); struct wcp_peer peer = peer_fixture();
    struct wcp_config cfg; uint64_t id[WCP_QUEUE], old, extra; unsigned i;
    unsigned char message[] = {1,2,3,4};
    wcp_config_default(&cfg); assert(!cfg.enabled);
    setup(&c, &f, 0); assert(wcp_start(&c, &ap, &peer, 1) == WCP_DISABLED); assert(!f.claims);
    cfg.enabled = 1; assert(wcp_init(&c, &cfg, NULL) == WCP_OK);
    assert(wcp_start(&c, &ap, &peer, 1) == WCP_UNAVAILABLE);
    setup(&c, &f, 1); assert(wcp_wired(&c, 1) == WCP_OK);
    assert(wcp_start(&c, &ap, &peer, 1) == WCP_BUSY); assert(!f.claims);
    assert(wcp_wired(&c, 0) == WCP_OK); activate(&c, &ap, &peer, 10); old = c.generation;
    for (i = 0; i < WCP_QUEUE; ++i) assert(wcp_send(&c, message, sizeof(message), &id[i]) == WCP_OK);
    message[0] = 99; assert(f.borrowed[0] == 1);
    assert(wcp_send(&c, message, sizeof(message), &extra) == WCP_BACKPRESSURE);
    assert(wcp_complete(&c, old + 1, id[0], 0) == WCP_STALE);
    assert(wcp_complete(&c, old, id[0], 0) == WCP_OK);
    assert(wcp_complete(&c, old, id[0], 0) == WCP_STALE);
    assert(wcp_send(&c, message, sizeof(message), &extra) == WCP_OK);
    f.fail_stop = WCP_ADAPTER_ERROR;
    assert(wcp_wired(&c, 1) == WCP_ADAPTER_ERROR);
    assert(c.state == WCP_STOPPING && c.owns && !f.releases && !wcp_uninstall_ready(&c));
    assert(f.borrowed[0] == 99); assert(wcp_start(&c, &ap, &peer, 20) == WCP_BUSY);
    assert(wcp_event(&c, old, WCP_VERIFIED, 20) == WCP_STALE);
    f.fail_stop = 0; assert(wcp_stop(&c) == WCP_OK); assert(f.releases == 1 && wcp_uninstall_ready(&c));
    for (i = 0; i < sizeof(c.messages); ++i) assert(!((unsigned char *)c.messages)[i]);
    assert(wcp_wired(&c, 0) == WCP_OK); activate(&c, &ap, &peer, 30);
    assert(c.generation != old && wcp_complete(&c, old, extra, 0) == WCP_STALE);
    assert(wcp_event(&c, old, WCP_DISCONNECTED, 40) == WCP_STALE); assert(c.state == WCP_ACTIVE);
    assert(wcp_tick(&c, 29) == WCP_INVALID); assert(wcp_stop(&c) == WCP_OK);
    assert(wcp_start(&c, &ap, &peer, 50) == WCP_OK);
    assert(wcp_tick(&c, 15050) == WCP_TIMEOUT && !c.owns);
    setup(&c, &f, 1); f.fail_begin = WCP_ADAPTER_ERROR; f.fail_stop = WCP_ADAPTER_ERROR;
    assert(wcp_start(&c, &ap, &peer, 0) == WCP_ADAPTER_ERROR && c.owns);
    f.fail_stop = 0; assert(wcp_stop(&c) == WCP_OK);
    setup(&c, &f, 1); f.fail_claim = WCP_BUSY;
    assert(wcp_start(&c, &ap, &peer, 0) == WCP_BUSY && !c.owns && !f.begins);
    setup(&c, &f, 1); c.ops.capabilities &= ~WCP_CAP_PAIRING;
    assert(wcp_start(&c, &ap, &peer, 0) == WCP_UNAVAILABLE && !f.claims);
    setup(&c, &f, 1); assert(wcp_start(&c, &ap, &peer, UINT64_MAX) == WCP_INVALID);
    peer.ipv6 = 1; peer.ipv6_scope = 0;
    assert(wcp_start(&c, &ap, &peer, 0) == WCP_INVALID);
}
static void ap_security(void) {
    struct wcp_ap ap = ap_fixture(); unsigned channel = 0;
    assert(wcp_ap_validate(&ap) == WCP_OK);
    ap.security = (enum wcp_security)2; assert(wcp_ap_validate(&ap) == WCP_SECURITY);
    ap.security = WCP_AP_OPEN; assert(wcp_ap_validate(&ap) == WCP_SECURITY);
    ap.psk[0] = 0; assert(wcp_ap_validate(&ap) == WCP_OK);
    ap.channel = 0; assert(wcp_ap_validate(&ap) == WCP_INVALID);
    ap = ap_fixture(); memset(ap.ssid, 'x', sizeof(ap.ssid)); assert(wcp_ap_validate(&ap) == WCP_INVALID);
    ap = ap_fixture(); memset(ap.psk, 'z', 64); ap.psk[64] = 0; assert(wcp_ap_validate(&ap) == WCP_SECURITY);
    memset(ap.psk, 'a', 64); assert(wcp_ap_validate(&ap) == WCP_OK);
    assert(wcp_channel("6,secondary", &channel) == WCP_PARSE_OK && channel == 6);
    assert(wcp_channel("0", &channel) == WCP_PARSE_ERROR);
    assert(wcp_channel("6,", &channel) == WCP_PARSE_ERROR);
    assert(wcp_channel("6x", &channel) == WCP_PARSE_ERROR);
    assert(wcp_channel("9999999999999999", &channel) == WCP_PARSE_ERROR);
}
static void http(const char *request, int expected) {
    struct wcp_http parser; size_t used, i; int result = WCP_PARSE_MORE;
    wcp_http_init(&parser);
    for (i = 0; i < strlen(request) && result == WCP_PARSE_MORE; ++i) {
        result = wcp_http_feed(&parser, request+i, 1, &used); assert(used == 1);
    }
    assert(result == expected);
}
static void protocol(void) {
    struct wcp_http parser; size_t used, n, i; unsigned char out[512], tlv[262];
    const char *request = "POST /pair-verify HTTP/1.1\r\nContent-Length: 3\r\n\r\nabcNEXT";
    wcp_http_init(&parser);
    assert(wcp_http_feed(&parser, request, strlen(request), &used) == WCP_PARSE_OK);
    assert(used == strlen(request)-4 && !strcmp(parser.path, "/pair-verify"));
    assert(!memcmp(wcp_http_body(&parser), "abc", 3));
    http("POST /pair-setup HTTP/1.1\r\nContent-Length: 1\r\n\r\nx", WCP_PARSE_OK);
    http("POST /x HTTP/1.1\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\nx", WCP_PARSE_ERROR);
    http("POST /x HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n", WCP_PARSE_ERROR);
    http("POST /x HTTP/1.1\r\nContent-Length: 9999999999999999999\r\n\r\n", WCP_PARSE_ERROR);
    http("POST /x HTTP/1.1\n\n", WCP_PARSE_ERROR);
    http("POST /x HTTP/1.1\r\n Bad: x\r\n\r\n", WCP_PARSE_ERROR);
    http("POST /x HTTP/1.1\r\nContent-Length: -1\r\n\r\n", WCP_PARSE_ERROR);
    tlv[0] = 1; tlv[1] = 255; memset(tlv+2, 7, 255); tlv[257] = 1; tlv[258] = 3;
    memset(tlv+259, 8, 3);
    assert(wcp_tlv_value(tlv, sizeof(tlv), 1, out, sizeof(out), &n) == WCP_PARSE_OK && n == 258);
    for (i = 0; i < n; ++i) assert(out[i] == (i < 255 ? 7 : 8));
    memset(out, 99, sizeof(out));
    assert(wcp_tlv_value(tlv, sizeof(tlv)-1, 1, out, sizeof(out), &n) == WCP_PARSE_ERROR && !n && out[0] == 99);
    assert(wcp_tlv_value(tlv, sizeof(tlv), 1, out, 256, &n) == WCP_PARSE_ERROR);
    assert(wcp_tlv_value("\1\1x\1\1y", 6, 1, out, sizeof(out), &n) == WCP_PARSE_ERROR);
    assert(wcp_tlv_value("\1\1x\2\0\1\1y", 8, 1, out, sizeof(out), &n) == WCP_PARSE_ERROR);
    assert(wcp_tlv_value("\2\0", 2, 1, out, sizeof(out), &n) == WCP_PARSE_MORE);
}
static void records(void) {
    struct wcp_config cfg; struct wcp_ap ap; unsigned i;
    const char *good = "ssid=synthetic\npsk=synthetic-key\nchannel=6,secondary\nsecurity=wpa2\ncipher=ccmp\n";
    const char *wep = "ssid=synthetic\npsk=\nchannel=6\nsecurity=wep\ncipher=none\n";
    const char *duplicate = "ssid=first\nssid=second\npsk=synthetic-key\nchannel=6\nsecurity=wpa2\ncipher=ccmp\n";
    const char *open = "ssid=synthetic\npsk=\nchannel=6\nsecurity=open\ncipher=none\n";
    const char *conflict = "ssid=synthetic\npsk=synthetic-key\nchannel=6\nsecurity=wpa2\ncipher=none\n";
    assert(wcp_config_parse(NULL, 0, &cfg) == WCP_OK && !cfg.enabled);
    assert(wcp_config_parse("enabled=1\n", 10, &cfg) == WCP_OK && cfg.enabled);
    assert(wcp_config_parse("enabled=1\nenabled=0\n", 20, &cfg) == WCP_INVALID && !cfg.enabled);
    assert(wcp_config_parse("enabled=1", 9, &cfg) == WCP_INVALID && !cfg.enabled);
    assert(wcp_config_parse("handshake_timeout_ms=999999999999999999999\n", 43, &cfg) == WCP_INVALID);
    assert(wcp_ap_record(good, strlen(good), 9, 9, 3, &ap) == WCP_OK && ap.channel == 6);
    assert(wcp_ap_record(good, strlen(good), 9, 10, 3, &ap) == WCP_STALE);
    for (i = 0; i < sizeof(ap); ++i) assert(!((unsigned char *)&ap)[i]);
    assert(wcp_ap_record(wep, strlen(wep), 9, 9, 3, &ap) == WCP_SECURITY);
    assert(wcp_ap_record(duplicate, strlen(duplicate), 9, 9, 3, &ap) == WCP_INVALID);
    assert(wcp_ap_record(conflict, strlen(conflict), 9, 9, 3, &ap) == WCP_SECURITY);
    assert(wcp_ap_record(open, strlen(open), 9, 9, 3, &ap) == WCP_OK && !ap.psk[0]);
}
static void init_alias(void) {
    struct wcp_control c; struct fake f;
    setup(&c, &f, 1);
    assert(wcp_uninstall_ready(&c));
    assert(wcp_reinit(&c, &c.config, &c.ops) == WCP_OK);
    assert(c.config.enabled && c.ops.abi == WCP_ABI && c.ops.context == &f);
    assert(wcp_start(&c, &(struct wcp_ap){
        7, 3, 6, WCP_AP_OPEN, "synthetic", ""
    }, &(struct wcp_peer){{2,0,0,0,0,1},3,0,7000,0}, 1) == WCP_OK);
    assert(wcp_stop(&c) == WCP_OK);
}
int main(void) {
    lifecycle(); ap_security(); protocol(); records(); init_alias();
    puts("wireless synthetic lifecycle/ownership/security/framing fixtures PASS"); return 0;
}
