/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_owner_gateway_adapter.h"
#include <string.h>

/* This is the only location combining the two independently sampled sources.
 * It must not infer AID visibility from the owner ACK, stream or stop ticket. */
static int sample(struct mibr_v3_owner_adapter *a){
    struct mibr_v3_physical_owner_sample owner;
    struct mibr_v3_aid_sample aid;
    struct mibr_owner_proof p;
    uint64_t now=0;
    if(!a)return -1;
    a->snapshot_valid=0;
    memset(&owner,0,sizeof(owner));memset(&aid,0,sizeof(aid));
    memset(&p,0,sizeof(p));
    if(!a->ops.now_ms||!a->ops.physical_owner_read||!a->ops.physical_aid_read||
       a->ops.now_ms(a->context,&now)||
       a->ops.physical_owner_read(a->context,&owner)||
       a->ops.physical_aid_read(a->context,&aid))goto invalid;
    /* The common monotonic clock is supplied externally. A valid-but-older
     * replay within the 500ms freshness window cannot roll the proof back. */
    if(!now||!owner.observed_ms||!aid.observed_ms||
       (a->last_now&&now<a->last_now)||
       (a->last_owner_ms&&owner.observed_ms<a->last_owner_ms)||
       (a->last_aid_ms&&aid.observed_ms<a->last_aid_ms))goto invalid;
    p.now_ms=now;p.owner_ms=owner.observed_ms;p.aid_ms=aid.observed_ms;
    p.stream_session=owner.stream_session;
    p.stream_generation=owner.stream_generation;
    p.source111_ready=owner.source111_ready;
    p.owner_authority=owner.owner_authority;
    p.owner_running=owner.owner_running;p.writer_count=owner.writer_count;
    p.backend_stock_restored=owner.backend_stock_restored;
    p.aid_confirmed=aid.confirmed;p.aid_visible=aid.visible;
    memcpy(p.owner_ack_rid,owner.ack_request_id,sizeof(p.owner_ack_rid));
    if(!a->initialized){
        if(mibr_owner_init(&a->lifecycle,&p))goto invalid;
        a->initialized=1;
    }else if(mibr_owner_observe(&a->lifecycle,&p)<0)goto invalid;
    a->proof=p;a->aid=aid;
    a->last_now=now;a->last_owner_ms=owner.observed_ms;
    a->last_aid_ms=aid.observed_ms;a->snapshot_valid=1;
    return 0;
invalid:
    if(a->initialized)mibr_owner_quarantine(&a->lifecycle);
    return -1;
}
int mibr_v3_owner_adapter_init(struct mibr_v3_owner_adapter *a,
    const struct mibr_v3_owner_adapter_ops *ops,void *ctx){
    if(!a)return -1;
    memset(a,0,sizeof(*a));
    if(!ops||!ops->now_ms||!ops->physical_owner_read||
       !ops->physical_aid_read||!ops->start_existing||!ops->stop_existing)return -1;
    a->ops=*ops;a->context=ctx;
    return sample(a);
}
static int adapter_clock(void *ctx,uint64_t *out){
    struct mibr_v3_owner_adapter *a=(struct mibr_v3_owner_adapter *)ctx;
    if(!out)return -1;
    *out=0;
    if(!a||!a->initialized||sample(a))return -1;
    *out=a->proof.now_ms;return 0;
}
static int adapter_owner_read(void *ctx,struct mibr_v3_owner_sample *out){
    struct mibr_v3_owner_adapter *a=(struct mibr_v3_owner_adapter *)ctx;
    struct mibr_v3_route_observation route;
    if(!out)return -1;
    memset(out,0,sizeof(*out));
    if(!a||!a->snapshot_valid||a->lifecycle.phase==MIBR_OWNER_QUARANTINED)return -1;
    if(a->lifecycle.phase==MIBR_OWNER_STARTING||
       a->lifecycle.phase==MIBR_OWNER_STOPPING){
        out->transition_pending=1;return 0;
    }
    if(mibr_owner_read(&a->lifecycle,&route))return -1;
    out->visible=route.visible;out->session=route.session;
    out->generation=route.generation;out->observed_ms=a->proof.owner_ms;
    out->confirmed=1;out->control_authority_verified=a->proof.owner_authority;
    memcpy(out->ack_request_id,route.ack_request_id,sizeof(out->ack_request_id));
    return 0;
}
static int adapter_aid_read(void *ctx,struct mibr_v3_aid_sample *out){
    struct mibr_v3_owner_adapter *a=(struct mibr_v3_owner_adapter *)ctx;
    if(!a||!out||!a->snapshot_valid)return -1;
    *out=a->aid;return 0;
}
static int adapter_owner_request(void *ctx,enum mibr_v3_visible_route target,
    const struct mibr_v3_route_observation *expected,const char *rid){
    struct mibr_v3_owner_adapter *a=(struct mibr_v3_owner_adapter *)ctx;
    struct mibr_v3_route_observation actual;
    struct mibr_owner_dispatch_ops dispatch;
    int result;
    if(!a||!a->initialized||!a->snapshot_valid||!expected||
       mibr_owner_read(&a->lifecycle,&actual)||
       expected->visible!=actual.visible||expected->session!=actual.session||
       expected->generation!=actual.generation)return -1;
    dispatch.start_existing=a->ops.start_existing;
    dispatch.stop_existing=a->ops.stop_existing;
    result=mibr_owner_dispatch(&a->lifecycle,&a->proof,target,
         expected->session,expected->generation,rid,&dispatch,a->context);
    /* Existing owner accepted dispatch: the gateway must still wait for the
     * original-RID ACK + separate actual AID readback; never synthesize it. */
    if(result==2)return -2;
    return result<0?-1:result;
}
int mibr_v3_owner_adapter_prepare_gateway(struct mibr_v3_owner_adapter *a,
    struct mibr_v3_route_gateway *gateway){
    struct mibr_v3_route_gateway_ops ops;
    if(!a||!gateway||!a->initialized||
       a->lifecycle.phase==MIBR_OWNER_QUARANTINED)return -1;
    memset(&ops,0,sizeof(ops));
    ops.now_ms=adapter_clock;ops.owner_read=adapter_owner_read;
    ops.aid_visible_read=adapter_aid_read;ops.owner_request=adapter_owner_request;
    mibr_v3_gateway_init(gateway,&ops,a);
    return 0;
}
void mibr_v3_owner_adapter_revoke(struct mibr_v3_owner_adapter *a,
    struct mibr_v3_route_gateway *gateway,struct mibr_v3_reader *reader){
    /* Do not release a possibly executed pending RID, even on owner loss. */
    if(gateway)mibr_v3_gateway_revoke(gateway,reader);
    if(a){
        a->snapshot_valid=0;
        mibr_owner_quarantine(&a->lifecycle);
    }
}
