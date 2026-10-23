/* SPDX-License-Identifier: GPL-3.0-or-later
 * Source-only bridge to ONE existing qualified CPVC/Parity route owner.
 * No vehicle provider, DSI hook, second writer or startup activation here.
 */
#ifndef MIBR_V3_ROUTE_GATEWAY_H
#define MIBR_V3_ROUTE_GATEWAY_H
#include "mibr_v3_readonly.h"

/* Independent producers. The OWNER sample is supplied by the sole existing
 * serialized route owner. The AID sample MUST be real display readback, NOT
 * synthesized from owner, marker, stream111 or parity-session --stop ticket.
 * Times use a single real monotonic clock domain, never file modification time.
 */
struct mibr_v3_owner_sample {
    enum mibr_v3_visible_route visible;
    uint64_t session, generation, observed_ms;
    int confirmed;
    int control_authority_verified; /* qualified sole owner, even when STOCK */
    int transition_pending; /* owner has a pre-existing unresolved request */
    char ack_request_id[65];
};
struct mibr_v3_aid_sample {
    enum mibr_v3_visible_route visible;
    uint64_t observed_ms;
    int confirmed;
};
struct mibr_v3_route_gateway_ops {
    int (*now_ms)(void *,uint64_t *);
    int (*owner_read)(void *,struct mibr_v3_owner_sample *);
    int (*aid_visible_read)(void *,struct mibr_v3_aid_sample *);
    /* ONLY sole existing owner may dispatch; -1 PROVEN no dispatch;
     * -2 uncertain dispatch, >=0 accepted. Never start a second parity-session. */
    int (*owner_request)(void *,enum mibr_v3_visible_route,
                         const struct mibr_v3_route_observation *,const char *);
};
struct mibr_v3_route_gateway {
    struct mibr_v3_route_gateway_ops ops;
    void *context;
    uint64_t last_session,last_generation;
    unsigned qualified;
};
void mibr_v3_gateway_init(struct mibr_v3_route_gateway *,
                          const struct mibr_v3_route_gateway_ops *,void *);
 /* This is explicitly NOT called by current target service. Integrator must
  * FIRST qualify exact OEM AID signal, sole owner callbacks, lifecycle/rollback
  * and clock provenance on the parked unit, then attach in serialized context.
  * A mere boolean from a passive GEN2 record is NOT qualification. */
int mibr_v3_gateway_attach(struct mibr_v3_route_gateway *,
                           struct mibr_v3_reader *,int vehicle_qualified);
void mibr_v3_gateway_revoke(struct mibr_v3_route_gateway *,
                            struct mibr_v3_reader *);
int mibr_v3_gateway_read(void *,struct mibr_v3_route_observation *);
int mibr_v3_gateway_set(void *,enum mibr_v3_visible_route,
                        const struct mibr_v3_route_observation *,const char *,
                        struct mibr_v3_route_observation *);
#endif
