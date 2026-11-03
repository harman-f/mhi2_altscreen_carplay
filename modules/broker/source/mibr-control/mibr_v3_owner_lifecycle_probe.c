/* SPDX-License-Identifier: GPL-3.0-or-later
 * HOST-only pure policy fixture; no car access, spawning, signal, network or IO.
 */
#include "mibr_v3_owner_lifecycle.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct mibr_owner_proof stock0(void){
    struct mibr_owner_proof p;
    memset(&p,0,sizeof(p));
    p.now_ms=10000;p.owner_ms=9999;p.aid_ms=9998;
    p.stream_session=7;p.stream_generation=20;
    p.source111_ready=1;p.owner_authority=1;
    p.backend_stock_restored=1;p.aid_confirmed=1;
    p.aid_visible=MIBR_ROUTE_STOCK110;
    return p;
}
static void activate(struct mibr_owner_proof *p,const char *rid){
    p->owner_running=1;p->writer_count=1;p->backend_stock_restored=0;
    p->aid_visible=MIBR_ROUTE_DIRECT111;
    strcpy(p->owner_ack_rid,rid);
}
static void restore(struct mibr_owner_proof *p,const char *rid){
    p->owner_running=0;p->writer_count=0;p->backend_stock_restored=1;
    p->aid_visible=MIBR_ROUTE_STOCK110;
    strcpy(p->owner_ack_rid,rid);
}
struct dispatch_fixture { unsigned starts,stops;int start_rc,stop_rc; };
static int start_existing(void *v,const char *rid){
    struct dispatch_fixture *d=(struct dispatch_fixture *)v;
    assert(rid&&*rid);++d->starts;return d->start_rc;
}
static int stop_existing(void *v,const char *rid){
    struct dispatch_fixture *d=(struct dispatch_fixture *)v;
    assert(rid&&*rid);++d->stops;return d->stop_rc;
}
int main(void){
    struct mibr_owner_lifecycle s,other;
    struct mibr_v3_route_observation out;
    struct mibr_owner_proof p=stock0(),q;
    assert(mibr_owner_init(&s,&p)==0);
    assert(mibr_owner_read(&s,&out)==0&&out.visible==MIBR_ROUTE_STOCK110);
    assert(out.session==7&&out.generation==1);
    assert(mibr_owner_request(&s,&p,MIBR_ROUTE_DIRECT111,7,1,"go")==
           MIBR_OWNER_START_EXISTING);
    assert(mibr_owner_read(&s,&out)!=0); /* no false visible route while pending */
    assert(mibr_owner_request(&s,&p,MIBR_ROUTE_DIRECT111,7,1,"go")==MIBR_OWNER_PENDING);
    assert(mibr_owner_request(&s,&p,MIBR_ROUTE_DIRECT111,7,1,"other")==MIBR_OWNER_REJECT);
    assert(mibr_owner_observe(&s,&p)==0); /* no ACK */
    q=p;activate(&q,"go");
    q.aid_visible=MIBR_ROUTE_STOCK110; /* owner ACK without AID proof */
    assert(mibr_owner_observe(&s,&q)==0);
    activate(&q,"go");
    assert(mibr_owner_observe(&s,&q)==1);
    assert(mibr_owner_read(&s,&out)==0&&out.visible==MIBR_ROUTE_DIRECT111);
    assert(out.generation==2&&!strcmp(out.ack_request_id,"go"));
    assert(mibr_owner_request(&s,&q,MIBR_ROUTE_STOCK110,7,1,"old")==MIBR_OWNER_REJECT);
    assert(mibr_owner_request(&s,&q,MIBR_ROUTE_STOCK110,7,2,"back")==MIBR_OWNER_STOP_EXISTING);
    assert(mibr_owner_observe(&s,&q)==0); /* last known ACK go allowed */
    restore(&q,"back");
    q.aid_visible=MIBR_ROUTE_DIRECT111; /* ticket handed back, but AID still DIRECT */
    assert(mibr_owner_observe(&s,&q)==0);
    q.aid_visible=MIBR_ROUTE_STOCK110;
    assert(mibr_owner_observe(&s,&q)==1);
    assert(mibr_owner_read(&s,&out)==0&&out.visible==MIBR_ROUTE_STOCK110);
    assert(out.generation==3&&!strcmp(out.ack_request_id,"back"));
    /* Unlike the current shell supervisor WAIT_NEW_STREAM, a verified
     * same-generation stock handback can legitimately reenter exactly once. */
    assert(mibr_owner_request(&s,&q,MIBR_ROUTE_DIRECT111,7,3,"reenter")==
           MIBR_OWNER_START_EXISTING);
    assert(mibr_owner_observe(&s,&q)==0); /* prior ACK back is not foreign */
    activate(&q,"reenter");
    assert(mibr_owner_observe(&s,&q)==1&&s.route_generation==4);
    assert(mibr_owner_read(&s,&out)==0&&out.visible==MIBR_ROUTE_DIRECT111);
    /* Unexpected multiple writers, unknown actual AID, stale clock, foreign
     * original-RID ACK or changed stream/session always reject/quarantine. */
    other=s;p=q;strcpy(p.owner_ack_rid,"unsolicited");
    assert(mibr_owner_observe(&other,&p)==-1&&other.phase==MIBR_OWNER_QUARANTINED);
    other=s;p=q;p.writer_count=2;
    assert(mibr_owner_observe(&other,&p)==-1&&other.phase==MIBR_OWNER_QUARANTINED);
    other=s;p=q;p.aid_confirmed=0;
    assert(mibr_owner_observe(&other,&p)==-1&&other.phase==MIBR_OWNER_QUARANTINED);
    other=s;p=q;p.owner_ms=9000;
    assert(mibr_owner_observe(&other,&p)==-1&&other.phase==MIBR_OWNER_QUARANTINED);
    other=s;p=q;p.stream_generation++;
    assert(mibr_owner_observe(&other,&p)==-1&&other.phase==MIBR_OWNER_QUARANTINED);
    other=s;p=q;
    assert(mibr_owner_request(&other,&p,MIBR_ROUTE_STOCK110,7,4,"stop2")==
           MIBR_OWNER_STOP_EXISTING);
    strcpy(p.owner_ack_rid,"foreign");
    assert(mibr_owner_observe(&other,&p)==-1&&other.phase==MIBR_OWNER_QUARANTINED);
    /* At service restart, current direct/unknown owner cannot be adopted by a
     * newly zero-initialized lifecycle from just a marker or owner ticket. */
    assert(mibr_owner_init(&other,&q)==-1);
    p=stock0();p.owner_running=1;
    assert(mibr_owner_init(&other,&p)==-1);
    p=stock0();p.owner_ack_rid[0]='x';p.owner_ack_rid[1]=0;
    assert(mibr_owner_init(&other,&p)==-1);
    p=stock0();p.owner_authority=0;
    assert(mibr_owner_init(&other,&p)==-1);
    p=stock0();p.owner_ms=p.now_ms+1;
    assert(mibr_owner_init(&other,&p)==-1);
    p=stock0();assert(mibr_owner_init(&other,&p)==0);
    p.source111_ready=0;
    assert(mibr_owner_request(&other,&p,MIBR_ROUTE_DIRECT111,7,1,"no-stream")==MIBR_OWNER_REJECT);
    assert(other.phase==MIBR_OWNER_STOCK);
    /* Typed adapter calls the existing owner at most once. Ambiguous
     * transport errors retain the original RID and forbid a new dispatch. */
    {
        const struct mibr_owner_dispatch_ops ops={start_existing,stop_existing};
        struct dispatch_fixture d={0};
        p=stock0();assert(mibr_owner_init(&other,&p)==0);
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_DIRECT111,7,1,"start1",&ops,&d)==1);
        assert(d.starts==1);
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_DIRECT111,7,1,"start1",&ops,&d)==2);
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_DIRECT111,7,1,"different",&ops,&d)==-1);
        assert(d.starts==1);
        activate(&p,"start1");
        assert(mibr_owner_observe(&other,&p)==1&&other.route_generation==2);
        d.stop_rc=-1; /* qualified callback proves ZERO dispatch */
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_STOCK110,7,2,"stop0",&ops,&d)==-1);
        assert(other.phase==MIBR_OWNER_DIRECT&&other.pending_rid[0]==0&&d.stops==1);
        d.stop_rc=-2; /* may have dispatched: never issue again */
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_STOCK110,7,2,"stop1",&ops,&d)==2);
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_STOCK110,7,2,"stop1",&ops,&d)==2);
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_STOCK110,7,2,"stop2",&ops,&d)==-1);
        assert(d.stops==2);
        restore(&p,"stop1");
        assert(mibr_owner_observe(&other,&p)==1&&other.route_generation==3);
        assert(mibr_owner_read(&other,&out)==0&&out.visible==MIBR_ROUTE_STOCK110);
        assert(mibr_owner_dispatch(&other,&p,MIBR_ROUTE_DIRECT111,7,3,"again",&ops,&d)==1);
        assert(d.starts==2); /* verified same-stream reentry only after handback */
    }
    puts("MIBR_V3_OWNER_LIFECYCLE_HOST_PASS_ONLY_NOT_WIRED");
    return 0;
}
