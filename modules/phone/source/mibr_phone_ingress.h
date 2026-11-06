/* SPDX-License-Identifier: GPL-3.0-or-later
 * V1 seam for stock-owned CarPlay telephony -> optional BAP phone adapter.
 * Calls are NOT executed here: permission only, no second phone service.
 */
#ifndef MIBR_PHONE_INGRESS_H
#define MIBR_PHONE_INGRESS_H
#include "mibr_phone_state.h"
#include <stdint.h>
typedef struct {
 mibr_phone_state current;
 uint64_t active_generation,highest_generation;
 int exact_abi_qualified,stock_delegate_qualified,input_action_qualified;
} mibr_phone_ingress;
void mibr_phone_ingress_init(mibr_phone_ingress *p);
void mibr_phone_ingress_enable(mibr_phone_ingress *p,int broker_confirmed_enabled);
int mibr_phone_ingress_attach(mibr_phone_ingress *p,uint64_t generation,
                              uint32_t session,int exact_abi,
                              int stock_delegate_qualified,int input_action_qualified);
int mibr_phone_ingress_event(mibr_phone_ingress *p,uint64_t generation,
                             uint32_t session,uint32_t call_id,
                             enum mibr_call_status status,const char *name,
                             const char *number,int carplay_owner);
int mibr_phone_ingress_snapshot(const mibr_phone_ingress *p,uint64_t generation,
                                mibr_phone_state *out);
int mibr_phone_ingress_action_allowed(const mibr_phone_ingress *p,uint64_t generation,
                                      uint32_t session,uint32_t call_id,
                                      enum mibr_call_action action);
void mibr_phone_ingress_detach(mibr_phone_ingress *p,uint64_t generation,uint32_t session);
#endif
