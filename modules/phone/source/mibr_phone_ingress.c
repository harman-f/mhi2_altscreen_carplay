/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_phone_ingress.h"
#include <string.h>
void mibr_phone_ingress_init(mibr_phone_ingress *p){
 if(!p)return;
 memset(p,0,sizeof(*p));mibr_phone_init(&p->current);
}
void mibr_phone_ingress_enable(mibr_phone_ingress *p,int enabled){
 if(p)mibr_phone_set_enabled(&p->current,enabled);
}
static int current(const mibr_phone_ingress *p,uint64_t generation,uint32_t session){
 return p&&p->active_generation&&p->active_generation==generation&&
        p->exact_abi_qualified&&p->stock_delegate_qualified&&
        p->current.connected&&p->current.session==session;
}
int mibr_phone_ingress_attach(mibr_phone_ingress *p,uint64_t generation,
                              uint32_t session,int abi,int delegate,int input){
 if(!p||!generation||!session||generation<=p->highest_generation||!abi||!delegate)return 0;
 p->highest_generation=generation;
 p->active_generation=generation;
 p->exact_abi_qualified=1;
 p->stock_delegate_qualified=1;
 p->input_action_qualified=input!=0;
 mibr_phone_begin(&p->current,session);
 return 1;
}
int mibr_phone_ingress_event(mibr_phone_ingress *p,uint64_t generation,
                             uint32_t session,uint32_t call_id,
                             enum mibr_call_status status,const char *name,
                             const char *number,int carplay_owner){
 if(!current(p,generation,session))return 0;
 return mibr_phone_update(&p->current,session,call_id,status,name,number,carplay_owner);
}
int mibr_phone_ingress_snapshot(const mibr_phone_ingress *p,uint64_t generation,
                                mibr_phone_state *out){
 if(!p||!out||!current(p,generation,p->current.session)||
    !p->current.phone_enabled)return 0;
 *out=p->current; /* Caller name/number stay in-memory and never enter logs. */
 return 1;
}
int mibr_phone_ingress_action_allowed(const mibr_phone_ingress *p,uint64_t generation,
                                      uint32_t session,uint32_t call_id,
                                      enum mibr_call_action action){
 return current(p,generation,session)&&p->input_action_qualified&&
        mibr_phone_can_request(&p->current,session,call_id,action);
}
void mibr_phone_ingress_detach(mibr_phone_ingress *p,uint64_t generation,uint32_t session){
 if(!current(p,generation,session))return;
 mibr_phone_end(&p->current,session);
 p->active_generation=0;
 p->exact_abi_qualified=0;
 p->stock_delegate_qualified=0;
 p->input_action_qualified=0;
}
