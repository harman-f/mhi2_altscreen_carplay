/* SPDX-License-Identifier: GPL-3.0-or-later
 * V1 seam: existing iAP2 owner -> common media state -> firmware ASL/BAP.
 * PURE SOURCE, unbound: not an iAP2 reader, BAP writer or TCP service.
 */
#ifndef MIBR_MEDIA_INGRESS_H
#define MIBR_MEDIA_INGRESS_H
#include "mibr_media_state.h"
#include <stdint.h>
typedef struct {
    mibr_media_state current;
    uint64_t active_generation, highest_generation;
    int exact_abi_qualified, asl_thread_qualified;
} mibr_media_ingress;
void mibr_media_ingress_init(mibr_media_ingress *m);
void mibr_media_ingress_enable(mibr_media_ingress *m,int broker_confirmed_enabled);
int mibr_media_ingress_attach(mibr_media_ingress *m,uint64_t owner_generation,
                               uint32_t session,int exact_abi_qualified,
                               int asl_thread_qualified);
int mibr_media_ingress_track(mibr_media_ingress *m,uint64_t generation,
                             uint32_t session,const char *title,
                             const char *artist,const char *album,uint32_t transfer_id);
int mibr_media_ingress_cover(mibr_media_ingress *m,uint64_t generation,
                             uint32_t session,uint32_t track_epoch,uint32_t transfer_id);
int mibr_media_ingress_snapshot(const mibr_media_ingress *m,uint64_t generation,
                                mibr_media_state *out);
void mibr_media_ingress_detach(mibr_media_ingress *m,uint64_t generation,uint32_t session);
#endif
