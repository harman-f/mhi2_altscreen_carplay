/* SPDX-License-Identifier: GPL-3.0-or-later
 * ONE trusted OEM pre-dispatch KEY40 input -> existing native MIBR/3 handler.
 * No physical callback, patch, socket or OEM dispatch suppression is installed.
 */
#ifndef MIBR_V3_INPUT_BRIDGE_H
#define MIBR_V3_INPUT_BRIDGE_H
#include "mibr_v3_readonly.h"
#include "mibr_v3_key40.h"
struct mibr_v3_input_bridge {
    struct mibr_key40 key40;
    uint64_t epoch,sequence;
    int armed;
};
enum mibr_v3_input_result {
    MIBR_INPUT_INVALID=-1,MIBR_INPUT_NONE=0,
    MIBR_INPUT_OEM_SHORT=1,MIBR_INPUT_ACTION=2,
    MIBR_INPUT_UNQUALIFIED=3
};
void mibr_v3_input_init(struct mibr_v3_input_bridge *b,uint64_t unique_epoch);
/* Only verified exact OEM pre-dispatch integration may authorize this. The
 * product contains no such binding in PR102; initial state is always OFF. */
int mibr_v3_input_arm(struct mibr_v3_input_bridge *b,int qualified);
void mibr_v3_input_revoke(struct mibr_v3_input_bridge *b);
enum mibr_v3_input_result mibr_v3_input_key2(
    struct mibr_v3_input_bridge *b,struct mibr_v3_reader *owner,
    int keyboard,int key,int kst,char *response,size_t cap);
#endif
