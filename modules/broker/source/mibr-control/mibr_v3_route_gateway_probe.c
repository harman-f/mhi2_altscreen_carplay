/* Host-only negative gate test; NEVER a vehicle owner implementation. */
#include "mibr_v3_route_gateway.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct scene {
    uint64_t now;
    struct mibr_v3_owner_sample owner;
    struct mibr_v3_aid_sample aid;
    unsigned requests;
    int mode; /* 0 confirmed, 1 uncertain, 2 proven-no-dispatch, 3 AID still old */
};
static int clock_read(void *ctx,uint64_t *ms){*ms=((struct scene*)ctx)->now;return 0;}
static int owner_read(void *ctx,struct mibr_v3_owner_sample *p){
    *p=((struct scene*)ctx)->owner;return 0;
}
static int aid_read(void *ctx,struct mibr_v3_aid_sample *p){
    *p=((struct scene*)ctx)->aid;return 0;
}
static int request(void *ctx,enum mibr_v3_visible_route target,
                   const struct mibr_v3_route_observation *expected,const char *rid){
    struct scene *s=(struct scene*)ctx;
    assert(expected->session==s->owner.session);
    ++s->requests;
    if(s->mode==1)return -2;
    if(s->mode==2)return -1;
    s->owner.visible=target;s->owner.generation++;
    s->owner.observed_ms=s->now;
    snprintf(s->owner.ack_request_id,sizeof(s->owner.ack_request_id),"%s",rid);
    if(s->mode!=3){s->aid.visible=target;s->aid.observed_ms=s->now;}
    return 0;
}
int main(void){
    struct scene s={0};
    struct mibr_v3_reader r={0};
    struct mibr_v3_route_gateway g;
    struct mibr_v3_route_observation before,after;
    const struct mibr_v3_route_gateway_ops ops={clock_read,owner_read,aid_read,request};
    s.now=10000;s.owner.visible=MIBR_ROUTE_STOCK110;s.owner.session=7;
    s.owner.generation=9;s.owner.observed_ms=9990;s.owner.confirmed=1;
    s.owner.control_authority_verified=1;
    s.aid.visible=MIBR_ROUTE_STOCK110;s.aid.observed_ms=9985;s.aid.confirmed=1;
    mibr_v3_gateway_init(&g,&ops,&s);
    assert(mibr_v3_gateway_read(&g,&before)!=0); /* default OFF */
    assert(mibr_v3_gateway_attach(&g,&r,0)!=0);
    assert(!r.route_qualified&&!r.route_set);
    s.aid.visible=MIBR_ROUTE_DIRECT111;
    assert(mibr_v3_gateway_attach(&g,&r,1)!=0); /* disagreement: NO attach */
    s.aid.visible=MIBR_ROUTE_STOCK110;s.aid.observed_ms=9000;
    assert(mibr_v3_gateway_attach(&g,&r,1)!=0); /* stale display */
    s.aid.observed_ms=9985;
    assert(!mibr_v3_gateway_attach(&g,&r,1));
    assert(r.route_qualified && r.route_read==mibr_v3_gateway_read);
    assert(!mibr_v3_gateway_read(&g,&before));
    s.owner.transition_pending=1;
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* restart with old owner request */
    s.owner.transition_pending=0;
    s.owner.control_authority_verified=0;
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* lock/lease authority absent */
    s.owner.control_authority_verified=1;
    assert(!mibr_v3_gateway_read(&g,&before));
    assert(before.visible==MIBR_ROUTE_STOCK110&&before.session==7&&before.generation==9);
    s.mode=0;
    assert(!mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&before,"ui1",&after));
    assert(s.requests==1 && after.visible==MIBR_ROUTE_DIRECT111 &&
           after.generation==10&&!strcmp(after.ack_request_id,"ui1"));
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_STOCK110,&before,"stale",&after)==-1);
    assert(s.requests==1); /* stale CAS cannot dispatch */
    assert(!mibr_v3_gateway_read(&g,&before));
    s.mode=3; /* owner ACK alone is NOT display proof */
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_STOCK110,&before,"ui2",&after)==1);
    assert(s.requests==2);
    assert(mibr_v3_gateway_read(&g,&after)!=0);
    s.aid.visible=MIBR_ROUTE_STOCK110;s.aid.observed_ms=s.now;
    assert(!mibr_v3_gateway_read(&g,&after));
    assert(after.generation==11&&!strcmp(after.ack_request_id,"ui2"));
    s.owner.observed_ms=9000;
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* stale owner */
    s.owner.observed_ms=s.now;
    s.aid.observed_ms=s.now+1;
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* impossible future */
    s.aid.observed_ms=s.now-400;
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* owner-AID skew */
    s.aid.observed_ms=s.now;
    s.owner.generation=10;
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* regression */
    s.owner.generation=11;
    s.owner.ack_request_id[0]='!';s.owner.ack_request_id[1]=0;
    assert(mibr_v3_gateway_read(&g,&after)!=0);
    strcpy(s.owner.ack_request_id,"ui2");
    assert(!mibr_v3_gateway_read(&g,&before));
    s.mode=1;
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&before,"uncertain",&after)==-2);
    assert(s.requests==3);
    s.mode=2;
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&before,"not-dispatched",&after)==-1);
    assert(s.requests==4);
    r.route_inflight=1;strcpy(r.route_inflight_rid,"uncertain");
    mibr_v3_gateway_revoke(&g,&r);
    assert(!r.route_qualified&&!r.route_read&&!r.route_set&&!r.route_context);
    assert(r.route_inflight && !strcmp(r.route_inflight_rid,"uncertain"));
    assert(mibr_v3_gateway_read(&g,&after)!=0); /* owner loss stays closed */
    puts("MIBR_V3_INDEPENDENT_GATEWAY_HOST_PASS_UNQUALIFIED_TARGET");
    return 0;
}
