/* SPDX-License-Identifier: GPL-3.0-or-later
 * One existing Parity owner transport + INDEPENDENT physical observation.
 * Compiling this bridge does not attach it to the production daemon.
 */
#ifndef MIBR_V3_PARITY_TARGET_BRIDGE_H
#define MIBR_V3_PARITY_TARGET_BRIDGE_H
#include "mibr_v3_parity_mailbox.h"
#include "mibr_v3_owner_gateway_adapter.h"
struct mibr_v3_parity_observers {
    int (*now_ms)(void *,uint64_t *);
    int (*owner_read)(void *,struct mibr_v3_physical_owner_sample *);
    int (*aid_read)(void *,struct mibr_v3_aid_sample *);
};
struct mibr_v3_parity_target_bridge {
    struct mibr_v3_parity_observers physical;
    void *physical_context;
    struct mibr_v3_parity_mailbox mailbox;
    struct mibr_v3_owner_adapter adapter;
    struct mibr_v3_route_gateway gateway;
};
/* Caller must supply a ZERO-INITIALIZED bridge. Prepare is single-use and
 * refuses reinitialization of an active/revoked adapter, retaining pending
 * original RID. Three independent unit qualifications required. The
 * production service never calls this. A successful prepare does not authorize route_qualified;
 * actual parked evidence + gateway_attach are separate release gates.
 */
int mibr_v3_parity_target_prepare(struct mibr_v3_parity_target_bridge *,
    const struct mibr_v3_parity_observers *,void *,const char *mailbox_path,
    int exact_sole_supervisor_verified,int original_supervisor_excluded,
    int physical_aid_source_verified);
void mibr_v3_parity_target_revoke(struct mibr_v3_parity_target_bridge *,
    struct mibr_v3_reader *);
#endif
