/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/mibr_phone_ingress.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 mibr_phone_ingress p; mibr_phone_state view;
 mibr_phone_ingress_init(&p);
 assert(!mibr_phone_ingress_attach(&p,17,4,0,1,1));
 assert(!mibr_phone_ingress_attach(&p,17,4,1,0,1));
 assert(mibr_phone_ingress_attach(&p,17,4,1,1,0));
 assert(!mibr_phone_ingress_snapshot(&p,17,&view));
 mibr_phone_ingress_enable(&p,1);
 assert(mibr_phone_ingress_event(&p,17,4,8,MIBR_CALL_RINGING,"Name","123",1));
 assert(mibr_phone_ingress_snapshot(&p,17,&view));
 assert(!mibr_phone_ingress_action_allowed(&p,17,4,8,MIBR_CALL_ACCEPT));
 assert(!mibr_phone_ingress_action_allowed(&p,16,4,8,MIBR_CALL_ACCEPT));
 assert(!mibr_phone_ingress_action_allowed(&p,17,4,9,MIBR_CALL_HANGUP));
 mibr_phone_ingress_detach(&p,16,4);
 assert(mibr_phone_ingress_snapshot(&p,17,&view));
 mibr_phone_ingress_detach(&p,17,4);
 assert(!mibr_phone_ingress_snapshot(&p,17,&view));
 assert(!mibr_phone_ingress_attach(&p,17,4,1,1,1));
 assert(mibr_phone_ingress_attach(&p,18,5,1,1,1));
 assert(!mibr_phone_ingress_event(&p,17,4,9,MIBR_CALL_RINGING,"Old","123",1));
 assert(mibr_phone_ingress_event(&p,18,5,9,MIBR_CALL_RINGING,"N","123",0));
 assert(!mibr_phone_ingress_action_allowed(&p,18,5,9,MIBR_CALL_ACCEPT));
 assert(mibr_phone_ingress_event(&p,18,5,9,MIBR_CALL_RINGING,"N","123",1));
 assert(mibr_phone_ingress_action_allowed(&p,18,5,9,MIBR_CALL_ACCEPT));
 assert(!mibr_phone_ingress_action_allowed(&p,18,5,9,MIBR_CALL_HANGUP+5));
 mibr_phone_ingress_enable(&p,0);
 assert(!mibr_phone_ingress_action_allowed(&p,18,5,9,MIBR_CALL_ACCEPT));
 puts("PHONE_OWNER_INGRESS_HOST_TEST=PASS");
 return 0;
}
