/* SPDX-License-Identifier: GPL-3.0-or-later
 * Narrow OEM pre-dispatch seam. Requires exact fitted ObjectSwapper slot24
 * and installed original KEY40 consumer timing proof BEFORE enabling.
 * No registration, DSI patch, or vehicle activation occurs in this module.
 */
#ifndef MIBR_V3_KEY40_OEM_SEAM_H
#define MIBR_V3_KEY40_OEM_SEAM_H
#include "mibr_v3_input_bridge.h"
typedef int (*mibr_oem_key2_forward)(void *,int,int,int);
struct mibr_v3_key40_oem_seam {
    struct mibr_v3_input_bridge input;
    struct mibr_v3_reader *reader;
    mibr_oem_key2_forward original;
    void *original_context;
    int enabled,buffered,drop_until_release;
};
/* Preconditions must be independently and individually attested. 0 disables.
 * The actual OEM hook must use exactly ONE dispatcher and preserve KEY41.
 */
int mibr_v3_key40_oem_seam_init(struct mibr_v3_key40_oem_seam *,
    struct mibr_v3_reader *,uint64_t epoch,mibr_oem_key2_forward,void *,
    int exact_slot24_verified,int before_original_select_verified,
    int sole_dispatcher_verified);
/* Return -1 on invalid original forward or callback failures, 0 otherwise.
 * out is the same broker ACTION response for exactly one KST4 per press.
 */
int mibr_v3_key40_oem_seam_feed(struct mibr_v3_key40_oem_seam *,
    int keyboard,int key,int kst,char *out,size_t cap);
void mibr_v3_key40_oem_seam_revoke(struct mibr_v3_key40_oem_seam *);
#endif
