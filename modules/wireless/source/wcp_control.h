/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_WCP_CONTROL_H
#define MIBR_WCP_CONTROL_H

#include <stddef.h>
#include <stdint.h>

/* Project-owned C boundary. This is NOT an OEM object/delegate layout.
 * Call on one serialized owner thread. Callbacks must not reenter this API.
 * No radio, crypto, media, firewall or stock-process adapter ships here. */
#define WCP_ABI 1u
#define WCP_QUEUE 4u
#define WCP_MESSAGE_MAX 4096u
#define WCP_CAP_PAIRING 1u
#define WCP_CAP_CONTROL 2u
#define WCP_CAP_STOCK_IAP 4u
#define WCP_CAP_STOCK_MEDIA 8u
#define WCP_CAP_REQUIRED 15u

enum wcp_result {
    WCP_OK = 0, WCP_DISABLED = -1, WCP_UNAVAILABLE = -2,
    WCP_INVALID = -3, WCP_BUSY = -4, WCP_STALE = -5,
    WCP_TIMEOUT = -6, WCP_SECURITY = -7, WCP_BACKPRESSURE = -8,
    WCP_ADAPTER_ERROR = -9
};
enum wcp_state { WCP_OFF, WCP_IDLE, WCP_BOOTSTRAP, WCP_VERIFY,
                 WCP_ACTIVE, WCP_STOPPING, WCP_FAILED };
enum wcp_event { WCP_BOOTSTRAPPED, WCP_VERIFIED, WCP_MEDIA_READY,
                 WCP_DISCONNECTED };
enum wcp_security { WCP_AP_OPEN = 0, WCP_AP_WPA2 = 1 };

struct wcp_ap {
    uint64_t generation;
    uint32_t interface_index;
    unsigned channel;
    enum wcp_security security;
    char ssid[33];
    char psk[65];
};
struct wcp_peer {
    unsigned char identity[6];
    uint32_t interface_index, ipv6_scope;
    uint16_t port;
    unsigned ipv6;
};
struct wcp_config { unsigned enabled; uint32_t timeout_ms; };

/* claim must be atomic against USB/other owners. begin borrows AP/peer only
 * during the call; retaining credentials requires an adapter-owned copy.
 * send borrows a copied queue slot UNTIL completion or successful stop.
 * A failed send must retain neither the buffer nor its completion callback.
 * stop returns OK only after all borrowed buffers/callbacks are quiescent.
 * Failed stop retains owner and buffers; retry it. Never unload that adapter.
 * Callbacks receive the generation and exact request ID; reject late events.
 * No callback may report success for an unimplemented operation. */
struct wcp_ops {
    uint32_t abi, size, capabilities;
    void *context;
    int (*claim)(void *, uint64_t generation);
    int (*begin)(void *, uint64_t generation, const struct wcp_ap *,
                 const struct wcp_peer *);
    int (*send)(void *, uint64_t generation, uint64_t request,
                const unsigned char *, size_t);
    int (*stop)(void *, uint64_t generation);
    void (*release)(void *, uint64_t generation);
};
struct wcp_message {
    uint64_t request;
    size_t length;
    unsigned used;
    unsigned char bytes[WCP_MESSAGE_MAX];
};
struct wcp_control {
    struct wcp_config config;
    struct wcp_ops ops;
    enum wcp_state state;
    uint64_t generation, next_request, deadline, last_now;
    unsigned owns, wired, in_callback, verified;
    int last_error;
    struct wcp_message messages[WCP_QUEUE];
};

/* Initialize fresh storage, or reinitialize only after wcp_uninstall_ready()
 * is true. Calling this on an active/unquiesced instance would erase ownership
 * and buffer state; the function cannot safely inspect uninitialized storage
 * to detect that misuse. */
void wcp_config_default(struct wcp_config *);
int wcp_init(struct wcp_control *, const struct wcp_config *, const struct wcp_ops *);
int wcp_ap_validate(const struct wcp_ap *);
int wcp_start(struct wcp_control *, const struct wcp_ap *, const struct wcp_peer *,
              uint64_t now_ms);
int wcp_event(struct wcp_control *, uint64_t generation, enum wcp_event,
              uint64_t now_ms);
int wcp_send(struct wcp_control *, const void *, size_t, uint64_t *request);
int wcp_complete(struct wcp_control *, uint64_t generation, uint64_t request, int result);
int wcp_stop(struct wcp_control *);
int wcp_tick(struct wcp_control *, uint64_t now_ms);
int wcp_wired(struct wcp_control *, unsigned active);
int wcp_uninstall_ready(const struct wcp_control *);
const char *wcp_state_name(enum wcp_state);

#endif
