/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_key40.h"
#include <string.h>
void mibr_key40_reset(struct mibr_key40 *k){if(k)memset(k,0,sizeof(*k));}
enum mibr_key40_event mibr_key40_feed(struct mibr_key40 *k,int keyboard,int key,int state){
    return mibr_key40_feed_key(k,keyboard,key,state,40);
}
enum mibr_key40_event mibr_key40_feed_key(struct mibr_key40 *k,int keyboard,int key,int state,int wanted_key){
    if(!k)return MIBR_KEY40_INVALID;
    /* Ignore KEY41 Back entirely; never claim its OEM action. */
    if(keyboard!=4||key!=wanted_key)return MIBR_KEY40_NONE;
    if(state==1){
        if(k->phase==0){k->phase=1;return MIBR_KEY40_NONE;}
        if(k->phase==1)return MIBR_KEY40_NONE; /* repeat initial press */
        mibr_key40_reset(k);return MIBR_KEY40_INVALID;
    }
    if(state==0){
        enum mibr_key40_event result=k->phase==1?MIBR_KEY40_OEM_SHORT:MIBR_KEY40_NONE;
        mibr_key40_reset(k);return result;
    }
    if(state==3){
        if(k->phase==1){k->phase=3;return MIBR_KEY40_NONE;}
        if(k->phase==3)return MIBR_KEY40_NONE;
    }
    if(state==4){
        /* r29: owner wants a clearly deliberate hold: fire at KST=4 (~2 s) again. */
        if(k->phase==3&&!k->fired){
            k->phase=4;k->fired=1;return MIBR_KEY40_ROUTE_LONG;
        }
        if(k->phase==4&&k->fired)return MIBR_KEY40_NONE;
    }
    if(state==5){
        if((k->phase==4||k->phase==5)&&k->fired){
            k->phase=5;return MIBR_KEY40_NONE;
        }
    }
    mibr_key40_reset(k);
    return MIBR_KEY40_INVALID;
}
