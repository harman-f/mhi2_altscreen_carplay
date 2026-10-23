/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_route_gateway.h"
#include <string.h>
#define MIBR_ROUTE_MAX_AGE_MS 500u
#define MIBR_ROUTE_MAX_SKEW_MS 250u
static int valid_route(enum mibr_v3_visible_route x){
    return x==MIBR_ROUTE_STOCK110||x==MIBR_ROUTE_DIRECT111;
}
static int valid_rid(const char *s,size_t cap){
    size_t i;
    if(!s)return 0;
    for(i=0;i<cap;i++){
        unsigned char ch=(unsigned char)s[i];
        if(!ch)return 1; /* empty is valid before any owner ACK */
        if(!((ch>='a'&&ch<='z')||(ch>='A'&&ch<='Z')||
             (ch>='0'&&ch<='9')||ch=='-'||ch=='_'))return 0;
    }
    return 0; /* not terminated within limit */
}
void mibr_v3_gateway_init(struct mibr_v3_route_gateway *g,
                          const struct mibr_v3_route_gateway_ops *ops,void *ctx){
    if(!g)return;
    memset(g,0,sizeof(*g));
    if(ops)g->ops=*ops;
    g->context=ctx;
}
void mibr_v3_gateway_revoke(struct mibr_v3_route_gateway *g,
                            struct mibr_v3_reader *r){
    if(r && g && r->route_context==g){
        r->route_qualified=0;r->route_read=NULL;r->route_set=NULL;r->route_context=NULL;
        /* Do NOT clear broker pending RID / receipts. Uncertain previous owner
         * must be externally reconciled, not automatically reissued. */
    }
    if(g){g->qualified=0;g->last_session=0;g->last_generation=0;}
}
int mibr_v3_gateway_read(void *ctx,struct mibr_v3_route_observation *out){
    struct mibr_v3_route_gateway *g=(struct mibr_v3_route_gateway*)ctx;
    struct mibr_v3_owner_sample owner;
    struct mibr_v3_aid_sample aid;
    uint64_t now,diff;
    if(!out)return -1;
    memset(out,0,sizeof(*out));memset(&owner,0,sizeof(owner));memset(&aid,0,sizeof(aid));
    if(!g||!g->qualified||!g->ops.now_ms||!g->ops.owner_read||
       !g->ops.aid_visible_read||!g->ops.owner_request||
       g->ops.now_ms(g->context,&now)||g->ops.owner_read(g->context,&owner)||
       g->ops.aid_visible_read(g->context,&aid))return -1;
    if(owner.confirmed!=1||aid.confirmed!=1||
       owner.control_authority_verified!=1||owner.transition_pending!=0||
       !valid_route(owner.visible)||aid.visible!=owner.visible||
       !owner.session||!owner.generation||
       !valid_rid(owner.ack_request_id,sizeof(owner.ack_request_id))||
       !now||!owner.observed_ms||!aid.observed_ms||
       owner.observed_ms>now||aid.observed_ms>now||
       now-owner.observed_ms>MIBR_ROUTE_MAX_AGE_MS||
       now-aid.observed_ms>MIBR_ROUTE_MAX_AGE_MS)return -1;
    diff=owner.observed_ms>aid.observed_ms?
        owner.observed_ms-aid.observed_ms:aid.observed_ms-owner.observed_ms;
    if(diff>MIBR_ROUTE_MAX_SKEW_MS ||
       (g->last_session && (owner.session<g->last_session||
       (owner.session==g->last_session&&owner.generation<g->last_generation))))return -1;
    out->visible=owner.visible;out->session=owner.session;
    out->generation=owner.generation;out->confirmed=1;
    memcpy(out->ack_request_id,owner.ack_request_id,sizeof(out->ack_request_id));
    g->last_session=owner.session;g->last_generation=owner.generation;
    return 0;
}
int mibr_v3_gateway_set(void *ctx,enum mibr_v3_visible_route target,
                        const struct mibr_v3_route_observation *expected,
                        const char *rid,struct mibr_v3_route_observation *out){
    struct mibr_v3_route_gateway *g=(struct mibr_v3_route_gateway*)ctx;
    struct mibr_v3_route_observation actual;
    int rc;
    if(!out)return -1;
    memset(out,0,sizeof(*out));
    if(!g||!g->qualified||!g->ops.owner_request||!valid_route(target)||
       !expected||!rid||!*rid||!valid_rid(rid,65)||
       mibr_v3_gateway_read(g,&actual)||
       actual.visible!=expected->visible||
       actual.session!=expected->session||
       actual.generation!=expected->generation)return -1; /* proven no dispatch */
    if(target==actual.visible){*out=actual;return 0;}
    rc=g->ops.owner_request(g->context,target,expected,rid);
    if(rc==-1)return -1; /* qualified owner explicitly proves zero dispatch */
    if(rc<0)return -2; /* outcome unknown; caller MUST hold in-flight RID */
    if(!mibr_v3_gateway_read(g,&actual)&&actual.visible==target&&
       actual.session==expected->session&&
       actual.generation>=expected->generation&&
       !strcmp(actual.ack_request_id,rid)){
        *out=actual;return 0;
    }
    return 1; /* accepted, not independently correlated; NEVER fake ACTIVE */
}
int mibr_v3_gateway_attach(struct mibr_v3_route_gateway *g,
                           struct mibr_v3_reader *r,int vehicle_qualified){
    struct mibr_v3_route_observation proof;
    /* A previously uncertain owner action cannot be laundered through a
     * newly attached provider. Reconciliation is an explicit external gate. */
    if(!g||!r||vehicle_qualified!=1||r->route_inflight||
       r->route_qualified||r->route_read||
       r->route_set||r->route_context||!g->ops.now_ms||
       !g->ops.owner_read||!g->ops.aid_visible_read||!g->ops.owner_request)return -1;
    g->qualified=1;
    if(mibr_v3_gateway_read(g,&proof)){g->qualified=0;return -1;}
    r->route_read=mibr_v3_gateway_read;r->route_set=mibr_v3_gateway_set;
    r->route_context=g;r->route_qualified=1;
    return 0;
}
