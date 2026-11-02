/* SPDX-License-Identifier: GPL-3.0-or-later
 * Synthetic independent producers, NOT a vehicle provider or dispatch.
 */
#include "mibr_v3_owner_gateway_adapter.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct scene {
    uint64_t now;
    struct mibr_v3_physical_owner_sample owner;
    struct mibr_v3_aid_sample aid;
    int failed_owner,failed_aid,start_result,stop_result;
    unsigned starts,stops;
};
static int clock_read(void *ctx,uint64_t *out){
    *out=((struct scene*)ctx)->now;return 0;
}
static int owner_read(void *ctx,struct mibr_v3_physical_owner_sample *out){
    struct scene *s=(struct scene*)ctx;
    if(s->failed_owner)return -1;
    *out=s->owner;return 0;
}
static int aid_read(void *ctx,struct mibr_v3_aid_sample *out){
    struct scene *s=(struct scene*)ctx;
    if(s->failed_aid)return -1;
    *out=s->aid;return 0;
}
static int start(void *ctx,const char *rid){
    struct scene *s=(struct scene*)ctx;
    assert(rid&&*rid);++s->starts;return s->start_result;
}
static int stop(void *ctx,const char *rid){
    struct scene *s=(struct scene*)ctx;
    assert(rid&&*rid);++s->stops;return s->stop_result;
}
static struct scene stock(void){
    struct scene s;
    memset(&s,0,sizeof(s));s.now=10000;
    s.owner.observed_ms=9999;s.owner.stream_session=7;
    s.owner.stream_generation=20;s.owner.source111_ready=1;
    s.owner.owner_authority=1;s.owner.backend_stock_restored=1;
    s.aid.observed_ms=9998;s.aid.visible=MIBR_ROUTE_STOCK110;
    s.aid.confirmed=1;return s;
}
static void tick(struct scene *s){
    s->now+=100;s->owner.observed_ms=s->now-1;s->aid.observed_ms=s->now-2;
}
static void direct_owner(struct scene *s,const char *rid){
    s->owner.owner_running=1;s->owner.writer_count=1;
    s->owner.backend_stock_restored=0;
    strcpy(s->owner.ack_request_id,rid);
}
static void stock_owner(struct scene *s,const char *rid){
    s->owner.owner_running=0;s->owner.writer_count=0;
    s->owner.backend_stock_restored=1;
    strcpy(s->owner.ack_request_id,rid);
}
static const struct mibr_v3_owner_adapter_ops ops={
    clock_read,owner_read,aid_read,start,stop
};
int main(void){
    struct scene s=stock(),other;
    struct mibr_v3_owner_adapter a,b;
    struct mibr_v3_route_gateway g;
    struct mibr_v3_reader reader={0};
    struct mibr_v3_route_observation old,observed;
    assert(mibr_v3_owner_adapter_init(&a,&ops,&s)==0);
    assert(!mibr_v3_owner_adapter_prepare_gateway(&a,&g));
    assert(mibr_v3_gateway_attach(&g,&reader,0)==-1);
    assert(!reader.route_qualified);
    assert(!mibr_v3_gateway_attach(&g,&reader,1)); /* TEST-ONLY explicit opt-in */
    assert(!mibr_v3_gateway_read(&g,&old));
    assert(old.visible==MIBR_ROUTE_STOCK110&&old.session==7&&old.generation==1);
    /* Existing owner only: start is dispatched ONCE. No fake immediate ACK. */
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&old,"go",&observed)==1);
    assert(s.starts==1&&s.stops==0);
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&old,"other",&observed)==-1);
    assert(s.starts==1);
    tick(&s);direct_owner(&s,"go");
    assert(mibr_v3_gateway_read(&g,&observed)==-1); /* AID still 110 */
    tick(&s);s.aid.visible=MIBR_ROUTE_DIRECT111;
    assert(!mibr_v3_gateway_read(&g,&observed));
    assert(observed.visible==MIBR_ROUTE_DIRECT111&&observed.generation==2);
    assert(!strcmp(observed.ack_request_id,"go"));
    old=observed;
    /* Same-stream stop requires actual backend restore + real AID STOCK. */
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_STOCK110,&old,"back",&observed)==1);
    assert(s.stops==1);
    tick(&s);stock_owner(&s,"back");
    assert(mibr_v3_gateway_read(&g,&observed)==-1); /* ticket not visible */
    tick(&s);s.aid.visible=MIBR_ROUTE_STOCK110;
    assert(!mibr_v3_gateway_read(&g,&observed));
    assert(observed.generation==3&&!strcmp(observed.ack_request_id,"back"));
    old=observed;
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&old,"again",&observed)==1);
    assert(s.starts==2&&s.owner.stream_generation==20);
    tick(&s);direct_owner(&s,"again");s.aid.visible=MIBR_ROUTE_DIRECT111;
    assert(!mibr_v3_gateway_read(&g,&observed));
    assert(observed.generation==4&&!strcmp(observed.ack_request_id,"again"));
    /* A restart during active owner cannot bootstrap from claimed DIRECT. */
    other=s;assert(mibr_v3_owner_adapter_init(&b,&ops,&other)==-1);
    /* Sample rollback WITHIN freshness window invalidates qualified context. */
    s.aid.observed_ms-=50;
    assert(mibr_v3_gateway_read(&g,&old)==-1);
    assert(a.lifecycle.phase==MIBR_OWNER_QUARANTINED);
    assert(mibr_v3_gateway_read(&g,&old)==-1);
    assert(reader.route_inflight==0);
    mibr_v3_owner_adapter_revoke(&a,&g,&reader);
    assert(!reader.route_qualified&&!reader.route_read&&!reader.route_set);

    /* Ambiguous actual owner dispatch can never cause a second start. */
    s=stock();s.start_result=-2;
    assert(!mibr_v3_owner_adapter_init(&a,&ops,&s));
    assert(!mibr_v3_owner_adapter_prepare_gateway(&a,&g));
    memset(&reader,0,sizeof(reader));
    assert(!mibr_v3_gateway_attach(&g,&reader,1));
    assert(!mibr_v3_gateway_read(&g,&old));
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&old,"uncertain",&observed)==-2);
    assert(s.starts==1);
    assert(mibr_v3_gateway_set(&g,MIBR_ROUTE_DIRECT111,&old,"second",&observed)==-1);
    assert(s.starts==1);
    reader.route_inflight=1;strcpy(reader.route_inflight_rid,"uncertain");
    mibr_v3_owner_adapter_revoke(&a,&g,&reader);
    assert(reader.route_inflight&&!strcmp(reader.route_inflight_rid,"uncertain"));
    /* A fresh provider must NOT silently adopt a broker's unresolved RID. */
    s=stock();
    assert(!mibr_v3_owner_adapter_init(&a,&ops,&s));
    assert(!mibr_v3_owner_adapter_prepare_gateway(&a,&g));
    assert(mibr_v3_gateway_attach(&g,&reader,1)==-1);
    memset(&reader,0,sizeof(reader)); /* isolated new broker fixture only */

    /* Missing independently sampled AID fails closed before attachment. */
    s=stock();s.failed_aid=1;
    assert(mibr_v3_owner_adapter_init(&b,&ops,&s)==-1);
    s.failed_aid=0;assert(!mibr_v3_owner_adapter_init(&b,&ops,&s));
    assert(!mibr_v3_owner_adapter_prepare_gateway(&b,&g));
    s.failed_owner=1;
    assert(mibr_v3_gateway_attach(&g,&reader,1)==-1);
    assert(b.lifecycle.phase==MIBR_OWNER_QUARANTINED);
    puts("MIBR_V3_OWNER_GATEWAY_ADAPTER_HOST_PASS_NO_TARGET_PROVIDER");
    return 0;
}
