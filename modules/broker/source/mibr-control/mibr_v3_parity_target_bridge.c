/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_parity_target_bridge.h"
#include <string.h>
static int clock_adapter(void *v,uint64_t *out){
    struct mibr_v3_parity_target_bridge *b=(struct mibr_v3_parity_target_bridge*)v;
    return b->physical.now_ms(b->physical_context,out);
}
static int owner_adapter(void *v,struct mibr_v3_physical_owner_sample *out){
    struct mibr_v3_parity_target_bridge *b=(struct mibr_v3_parity_target_bridge*)v;
    return b->physical.owner_read(b->physical_context,out);
}
static int aid_adapter(void *v,struct mibr_v3_aid_sample *out){
    struct mibr_v3_parity_target_bridge *b=(struct mibr_v3_parity_target_bridge*)v;
    return b->physical.aid_read(b->physical_context,out);
}
static int start_existing(void *v,const char *rid){
    struct mibr_v3_parity_target_bridge *b=(struct mibr_v3_parity_target_bridge*)v;
    if(b->adapter.lifecycle.phase!=MIBR_OWNER_STARTING)return -1;
    b->mailbox.session=b->adapter.lifecycle.session;
    b->mailbox.stream_generation=b->adapter.lifecycle.stream_generation;
    return mibr_v3_parity_mailbox_start(&b->mailbox,rid);
}
static int stop_existing(void *v,const char *rid){
    struct mibr_v3_parity_target_bridge *b=(struct mibr_v3_parity_target_bridge*)v;
    if(b->adapter.lifecycle.phase!=MIBR_OWNER_STOPPING)return -1;
    b->mailbox.session=b->adapter.lifecycle.session;
    b->mailbox.stream_generation=b->adapter.lifecycle.stream_generation;
    return mibr_v3_parity_mailbox_stop(&b->mailbox,rid);
}
int mibr_v3_parity_target_prepare(struct mibr_v3_parity_target_bridge *b,
    const struct mibr_v3_parity_observers *physical,void *physical_context,
    const char *mailbox_path,int sole,int legacy_excluded,int aid_verified){
    struct mibr_v3_owner_adapter_ops ops;
    if(!b)return -1;
    /* Caller supplies a zero-initialized bridge. Never wipe an attached,
     * previously qualified or still-pending owner by calling prepare again;
     * after revoke, recovery requires separate verified reconciliation. */
    if(b->adapter.initialized||b->gateway.qualified||
       b->mailbox.qualified)return -1;
    memset(b,0,sizeof(*b));
    if(!physical||!physical->now_ms||!physical->owner_read||
       !physical->aid_read||sole!=1||legacy_excluded!=1||aid_verified!=1||
       !mailbox_path)return -1;
    b->physical=*physical;b->physical_context=physical_context;
    b->mailbox.request_path=mailbox_path;b->mailbox.qualified=1;
    memset(&ops,0,sizeof(ops));
    ops.now_ms=clock_adapter;ops.physical_owner_read=owner_adapter;
    ops.physical_aid_read=aid_adapter;
    ops.start_existing=start_existing;ops.stop_existing=stop_existing;
    if(mibr_v3_owner_adapter_init(&b->adapter,&ops,b)||
       mibr_v3_owner_adapter_prepare_gateway(&b->adapter,&b->gateway)){
        b->mailbox.qualified=0;return -1;
    }
    return 0;
}
void mibr_v3_parity_target_revoke(struct mibr_v3_parity_target_bridge *b,
    struct mibr_v3_reader *reader){
    if(!b)return;
    b->mailbox.qualified=0;
    mibr_v3_owner_adapter_revoke(&b->adapter,&b->gateway,reader);
}
