/* SPDX-License-Identifier: GPL-3.0-or-later
 * Stateless external I/O: one exact-MU1440 KEY40 PUSH gesture classifier.
 * Caller owns the single authenticated/native source subscription.
 */
#ifndef MIBR_V3_KEY40_H
#define MIBR_V3_KEY40_H
struct mibr_key40 {
    unsigned phase;     /* 0 idle; 1 press; 3 long-armed; 4 fired; 5 completed */
    unsigned fired;
};
enum mibr_key40_event { MIBR_KEY40_NONE=0,MIBR_KEY40_OEM_SHORT=1,
                        MIBR_KEY40_ROUTE_LONG=2,MIBR_KEY40_INVALID=-1 };
void mibr_key40_reset(struct mibr_key40 *k);
enum mibr_key40_event mibr_key40_feed(struct mibr_key40 *k,
    int keyboard,int key,int state);
/* r57: the same gesture machine for another push key of keyboard 4 (KEY44 = left roller push). */
enum mibr_key40_event mibr_key40_feed_key(struct mibr_key40 *k,
    int keyboard,int key,int state,int wanted_key);
#endif
