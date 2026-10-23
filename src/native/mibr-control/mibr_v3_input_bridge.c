/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_input_bridge.h"
#include <stdio.h>
#include <string.h>
#include <inttypes.h>
void mibr_v3_input_init(struct mibr_v3_input_bridge *b,uint64_t epoch){
    if(!b)return;
    memset(b,0,sizeof(*b));b->epoch=epoch;
}
int mibr_v3_input_arm(struct mibr_v3_input_bridge *b,int qualified){
    if(!b||!qualified||!b->epoch)return -1;
    mibr_key40_reset(&b->key40);b->armed=1;return 0;
}
void mibr_v3_input_revoke(struct mibr_v3_input_bridge *b){
    if(!b)return;
    b->armed=0;mibr_key40_reset(&b->key40);
}
enum mibr_v3_input_result mibr_v3_input_key2(
    struct mibr_v3_input_bridge *b,struct mibr_v3_reader *r,
    int keyboard,int key,int kst,char *out,size_t cap){
    struct mibr_v3_route_observation observed;
    enum mibr_key40_event event;
    const char *target,*previous;
    char rid[65],frame[4097];int n;
    if(!out||!cap)return MIBR_INPUT_INVALID;
    out[0]=0;
    if(!b||!b->armed)return MIBR_INPUT_UNQUALIFIED;
    event=mibr_key40_feed(&b->key40,keyboard,key,kst);
    if(event==MIBR_KEY40_NONE)return MIBR_INPUT_NONE;
    if(event==MIBR_KEY40_OEM_SHORT)return MIBR_INPUT_OEM_SHORT;
    if(event!=MIBR_KEY40_ROUTE_LONG)return MIBR_INPUT_INVALID;
    /* KST4 was consumed exactly once even on missing/stale owner. No rerun
     * or direct CPVC/Parity script from here. The same ACTION handler used
     * by authenticated HMI serializes its route/epoch CAS. */
    if(!r||!r->route_qualified||!r->route_read||!r->route_set||
       r->route_read(r->route_context,&observed)||
       !observed.confirmed||!observed.session||!observed.generation)return MIBR_INPUT_UNQUALIFIED;
    if(observed.visible==MIBR_ROUTE_STOCK110){
        previous="STOCK110";target="DIRECT111";
    }else if(observed.visible==MIBR_ROUTE_DIRECT111){
        previous="DIRECT111";target="STOCK110";
    }else return MIBR_INPUT_UNQUALIFIED;
    if(++b->sequence==0)return MIBR_INPUT_UNQUALIFIED;
    n=snprintf(rid,sizeof(rid),"hw%" PRIu64 "_%" PRIu64,b->epoch,b->sequence);
    if(n<=0||(size_t)n>=sizeof(rid))return MIBR_INPUT_UNQUALIFIED;
    n=snprintf(frame,sizeof(frame),
        "MIBR/3 %s ACTION kind=SET_VISIBLE_ROUTE;target=%s;expected_route=%s;"
        "expected_session=%" PRIu64 ";expected_generation=%" PRIu64
        ";origin=KEY40_LONG;request_id=%s\n",
        rid,target,previous,observed.session,observed.generation,rid);
    if(n<=0||(size_t)n>=sizeof(frame))return MIBR_INPUT_UNQUALIFIED;
    (void)mibr_v3_handle(r,MIBR_V3_INPUT,frame,(size_t)n,out,cap);
    return MIBR_INPUT_ACTION;
}
