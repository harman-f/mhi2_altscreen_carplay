/* SPDX-License-Identifier: GPL-3.0-or-later
 * Single existing CPVC/Parity owner's reversible route decision core.
 * SOURCE ONLY. No DSI hook, process spawn, stop signal, file-based activation
 * or writev/isoTX2 sender is implemented here.
 */
#ifndef MIBR_V3_OWNER_LIFECYCLE_H
#define MIBR_V3_OWNER_LIFECYCLE_H
#include "mibr_v3_readonly.h"
#include <stdint.h>
enum mibr_owner_phase {
    MIBR_OWNER_UNQUALIFIED=0, MIBR_OWNER_STOCK=1,
    MIBR_OWNER_STARTING=2, MIBR_OWNER_DIRECT=3,
    MIBR_OWNER_STOPPING=4, MIBR_OWNER_QUARANTINED=5
};
enum mibr_owner_decision {
    MIBR_OWNER_REJECT=-1, MIBR_OWNER_NOOP=0,
    MIBR_OWNER_START_EXISTING=1, MIBR_OWNER_STOP_EXISTING=2,
    MIBR_OWNER_PENDING=3
};
/* A real integrator MUST gather these from authoritative, independent live
 * providers. 'owner_ack_rid' is emitted by the sole existing owner AFTER
 * actuating and witnessing requested route; not inferred from request file.
 * aid_* are separately witnessed actual AID screen data.
 */
struct mibr_owner_proof {
    uint64_t now_ms, owner_ms, aid_ms;
    uint64_t stream_session, stream_generation;
    int source111_ready, owner_authority, owner_running, writer_count;
    int backend_stock_restored, aid_confirmed;
    enum mibr_v3_visible_route aid_visible;
    char owner_ack_rid[65];
};
struct mibr_owner_lifecycle {
    enum mibr_owner_phase phase;
    uint64_t session, stream_generation, route_generation;
    char pending_rid[65], last_ack_rid[65];
    enum mibr_v3_visible_route pending_target;
};
/* Initial proof must independently confirm STOCK + restored backend + zero
 * custom writers; never adopt an unknown pre-existing session. */
int mibr_owner_init(struct mibr_owner_lifecycle *,
                    const struct mibr_owner_proof *);
/* Every decision is made against fresh full proof and original route CAS.
 * START_EXISTING/STOP_EXISTING are decisions for a *future* qualified
 * single-owner dispatcher, not work performed by this pure module.
 * Caller must report dispatch outcome separately; unknown outcome retains
 * the pending slot and is NEVER retried blindly.
 */
enum mibr_owner_decision mibr_owner_request(struct mibr_owner_lifecycle *,
      const struct mibr_owner_proof *,enum mibr_v3_visible_route target,
      uint64_t expected_session,uint64_t expected_generation,const char *rid);
/* Accepts complete owner+independent AID snapshots. A transition completes
 * only on original RID ACK plus matching actual visible screen AND backend/
 * sole-writer proof. Physical recovery failure quarantines; late/foreign ACK
 * never releases a pending request. Returns 1 only for completed transition. */
int mibr_owner_observe(struct mibr_owner_lifecycle *,const struct mibr_owner_proof *);
/* These are injected calls into the ALREADY EXISTING sole CPVC owner; no
 * subprocess or signalling implementation is included. Return -1 ONLY if
 * proven zero dispatch; 0/1 accepted; -2/other negatives uncertain. */
struct mibr_owner_dispatch_ops {
    int (*start_existing)(void *,const char *);
    int (*stop_existing)(void *,const char *);
};
/* 0 = already selected; 1 = dispatched/accepted but pending independent ACK;
 * 2 = outcome unknown or original RID already pending, NEVER call again;
 * -1 = no actuation, rejected or proven no-dispatch. */
int mibr_owner_dispatch(struct mibr_owner_lifecycle *,
    const struct mibr_owner_proof *,enum mibr_v3_visible_route target,
    uint64_t session,uint64_t generation,const char *rid,
    const struct mibr_owner_dispatch_ops *,void *);
void mibr_owner_quarantine(struct mibr_owner_lifecycle *);
int mibr_owner_read(const struct mibr_owner_lifecycle *,
                    struct mibr_v3_route_observation *);
#endif
