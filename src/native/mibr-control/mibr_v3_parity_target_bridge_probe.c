/* SPDX-License-Identifier: GPL-3.0-or-later
 * HOST ONLY: synthetic independent witnesses, ACTUAL /tmp request file.
 * Neither an AID provider nor a vehicle action exists in this executable.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_parity_target_bridge.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
struct scene {
    uint64_t now;
    struct mibr_v3_physical_owner_sample owner;
    struct mibr_v3_aid_sample aid;
};
static int clock1(void *v,uint64_t *out){
    *out=((struct scene*)v)->now;return 0;
}
static int owner1(void *v,struct mibr_v3_physical_owner_sample *out){
    *out=((struct scene*)v)->owner;return 0;
}
static int aid1(void *v,struct mibr_v3_aid_sample *out){
    *out=((struct scene*)v)->aid;return 0;
}
static void tick(struct scene *s){
    s->now+=100;s->owner.observed_ms=s->now-1;
    s->aid.observed_ms=s->now-2;
}
static void check_file(const char *path,const char *wanted){
    char line[256];FILE *f=fopen(path,"r");
    assert(f&&fgets(line,sizeof(line),f));assert(!strcmp(line,wanted));
    assert(!fclose(f));assert(!unlink(path)); /* synthetic owner consumes */
}
int main(void){
    struct scene s={0};
    struct mibr_v3_parity_target_bridge b={0};
    struct mibr_v3_route_observation old,observed;
    struct mibr_v3_reader r={0};
    const struct mibr_v3_parity_observers ops={clock1,owner1,aid1};
    char path[256];
    assert(snprintf(path,sizeof(path),
        "/tmp/mibr-v3-parity-integration-%ld.req",(long)getpid())>0);
    assert(access(path,F_OK)!=0);
    s.now=10000;s.owner.observed_ms=9999;s.aid.observed_ms=9998;
    s.owner.stream_session=7;s.owner.stream_generation=20;
    s.owner.source111_ready=1;s.owner.owner_authority=1;
    s.owner.backend_stock_restored=1;s.aid.confirmed=1;
    s.aid.visible=MIBR_ROUTE_STOCK110;
    assert(mibr_v3_parity_target_prepare(&b,&ops,&s,path,1,1,0)==-1);
    assert(mibr_v3_parity_target_prepare(&b,&ops,&s,path,1,1,1)==0);
    assert(mibr_v3_gateway_attach(&b.gateway,&r,0)==-1);
    assert(!mibr_v3_gateway_attach(&b.gateway,&r,1)); /* TEST ONLY */
    assert(!mibr_v3_gateway_read(&b.gateway,&old));
    assert(old.visible==MIBR_ROUTE_STOCK110&&old.session==7&&old.generation==1);
    assert(mibr_v3_gateway_set(&b.gateway,MIBR_ROUTE_DIRECT111,
           &old,"go",&observed)==1);
    /* An accidental second prepare may NEVER erase the pending owner RID
     * or grant an extra command dispatch on this same in-process bridge. */
    assert(mibr_v3_parity_target_prepare(&b,&ops,&s,path,1,1,1)==-1);
    assert(!strcmp(b.adapter.lifecycle.pending_rid,"go"));
    check_file(path,"MIBR3|START|go|7|20\n");
    assert(mibr_v3_gateway_read(&b.gateway,&observed)<0);
    tick(&s);s.owner.owner_running=1;s.owner.writer_count=1;
    s.owner.backend_stock_restored=0;
    strcpy(s.owner.ack_request_id,"go");
    assert(mibr_v3_gateway_read(&b.gateway,&observed)<0); /* AID lag */
    tick(&s);s.aid.visible=MIBR_ROUTE_DIRECT111;
    assert(!mibr_v3_gateway_read(&b.gateway,&observed));
    assert(observed.visible==MIBR_ROUTE_DIRECT111&&observed.generation==2);
    assert(!strcmp(observed.ack_request_id,"go"));
    old=observed;
    assert(mibr_v3_gateway_set(&b.gateway,MIBR_ROUTE_STOCK110,
           &old,"back",&observed)==1);
    check_file(path,"MIBR3|STOP|back|7|20\n");
    tick(&s);s.owner.owner_running=0;s.owner.writer_count=0;
    s.owner.backend_stock_restored=1;
    strcpy(s.owner.ack_request_id,"back");
    assert(mibr_v3_gateway_read(&b.gateway,&observed)<0);
    tick(&s);s.aid.visible=MIBR_ROUTE_STOCK110;
    assert(!mibr_v3_gateway_read(&b.gateway,&observed));
    assert(observed.visible==MIBR_ROUTE_STOCK110&&observed.generation==3);
    old=observed;
    assert(mibr_v3_gateway_set(&b.gateway,MIBR_ROUTE_DIRECT111,
           &old,"again",&observed)==1);
    check_file(path,"MIBR3|START|again|7|20\n");
    mibr_v3_parity_target_revoke(&b,&r);
    assert(mibr_v3_parity_target_prepare(&b,&ops,&s,path,1,1,1)==-1);
    assert(!r.route_qualified&&r.route_read==NULL&&r.route_set==NULL);
    assert(!b.mailbox.qualified);
    puts("PARITY_REAL_MAILBOX_SYNTHETIC_AID_GATEWAY_HOST_PASS_NOT_VEHICLE");
    return 0;
}
