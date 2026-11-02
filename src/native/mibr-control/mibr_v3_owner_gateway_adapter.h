/* SPDX-License-Identifier: GPL-3.0-or-later
 * SOURCE ONLY: bind the pure lifecycle to the qualified gateway without
 * inventing a vehicle observer, shell actuator, or second Parity writer.
 */
#ifndef MIBR_V3_OWNER_GATEWAY_ADAPTER_H
#define MIBR_V3_OWNER_GATEWAY_ADAPTER_H
#include "mibr_v3_owner_lifecycle.h"
#include "mibr_v3_route_gateway.h"

/* OWNER data MUST originate at the one existing Parity owner. This sample
 * never supplies the AID's visible source: it has a separate callback. */
struct mibr_v3_physical_owner_sample {
    uint64_t observed_ms, stream_session, stream_generation;
    int source111_ready, owner_authority, owner_running, writer_count;
    int backend_stock_restored;
    char ack_request_id[65];
};
struct mibr_v3_owner_adapter_ops {
    int (*now_ms)(void *,uint64_t *);
    int (*physical_owner_read)(void *,struct mibr_v3_physical_owner_sample *);
    int (*physical_aid_read)(void *,struct mibr_v3_aid_sample *);
    /* Dispatch exclusively through the ALREADY EXISTING owner. -1 means
     * PROVEN ZERO dispatch; all other negatives mean an uncertain outcome. */
    int (*start_existing)(void *,const char *);
    int (*stop_existing)(void *,const char *);
};
struct mibr_v3_owner_adapter {
    struct mibr_v3_owner_adapter_ops ops;
    void *context;
    struct mibr_owner_lifecycle lifecycle;
    struct mibr_owner_proof proof;
    struct mibr_v3_aid_sample aid;
    uint64_t last_now,last_owner_ms,last_aid_ms;
    int initialized,snapshot_valid;
};
/* Only initializes from independently witnessed, fresh, restored STOCK110.
 * This is NOT vehicle qualification, attachment or permission to dispatch. */
int mibr_v3_owner_adapter_init(struct mibr_v3_owner_adapter *,
    const struct mibr_v3_owner_adapter_ops *,void *);
/* Supplies callbacks to the existing gateway; caller still MUST explicitly
 * call gateway_attach(..., vehicle_qualified=1) after actual parked proof.
 * The production service deliberately does neither. */
int mibr_v3_owner_adapter_prepare_gateway(struct mibr_v3_owner_adapter *,
    struct mibr_v3_route_gateway *);
void mibr_v3_owner_adapter_revoke(struct mibr_v3_owner_adapter *,
    struct mibr_v3_route_gateway *,struct mibr_v3_reader *);
#endif
