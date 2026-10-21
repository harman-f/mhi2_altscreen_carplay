/* SPDX-License-Identifier: GPL-3.0-or-later
 * Broker -> ALREADY EXISTING Parity supervisor, source-only request sender.
 * This is NOT the independently attested actual AID or owner ACK provider.
 */
#ifndef MIBR_V3_PARITY_MAILBOX_H
#define MIBR_V3_PARITY_MAILBOX_H
#include <stdint.h>
struct mibr_v3_parity_mailbox {
    const char *request_path; /* qualified /tmp leaf, never user input */
    uint64_t session,stream_generation;
    int qualified; /* must be set only AFTER original supervisor exclusivity */
};
/* Returns 0 on accepted atomic handoff; -1 proven pre-handoff rejection;
 * -2 uncertain, including mailbox already occupied: NEVER retry with new RID.
 * Caller maps zero to accepted but still PENDING until separate owner+AID ACK.
 */
int mibr_v3_parity_mailbox_start(void *,const char *rid);
int mibr_v3_parity_mailbox_stop(void *,const char *rid);
#endif
