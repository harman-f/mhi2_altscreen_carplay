/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_owner_lifecycle.h"
#include <string.h>
#define MAX_AGE_MS 500u
#define MAX_SKEW_MS 250u
static int rid_ok(const char *s,int nonempty){
    unsigned i;
    if(!s||(!*s&&nonempty))return 0;
    for(i=0;i<65;i++){
        unsigned char x=(unsigned char)s[i];
        if(!x)return 1;
        if(!((x>='a'&&x<='z')||(x>='A'&&x<='Z')||
             (x>='0'&&x<='9')||x=='_'||x=='-'))return 0;
    }
    return 0;
}
static int fresh(const struct mibr_owner_proof *p){
    uint64_t diff;
    if(!p||!p->now_ms||!p->owner_ms||!p->aid_ms||
       p->owner_ms>p->now_ms||p->aid_ms>p->now_ms||
       p->now_ms-p->owner_ms>MAX_AGE_MS||
       p->now_ms-p->aid_ms>MAX_AGE_MS||
       p->owner_authority!=1||p->aid_confirmed!=1||
       !rid_ok(p->owner_ack_rid,0))return 0;
    diff=p->owner_ms>p->aid_ms?p->owner_ms-p->aid_ms:p->aid_ms-p->owner_ms;
    return diff<=MAX_SKEW_MS;
}
static int same_stream(const struct mibr_owner_lifecycle *s,
                       const struct mibr_owner_proof *p){
    return p->stream_session==s->session && p->stream_generation==s->stream_generation;
}
static int stock(const struct mibr_owner_proof *p){
    return p->aid_visible==MIBR_ROUTE_STOCK110&&
           !p->owner_running&&p->writer_count==0&&
           p->backend_stock_restored==1;
}
static int direct(const struct mibr_owner_proof *p){
    return p->aid_visible==MIBR_ROUTE_DIRECT111&&
           p->owner_running==1&&p->writer_count==1&&
           p->backend_stock_restored==0&&p->source111_ready==1;
}
int mibr_owner_init(struct mibr_owner_lifecycle *s,
                    const struct mibr_owner_proof *p){
    if(!s)return -1;
    memset(s,0,sizeof(*s));
    if(!fresh(p)||!p->stream_session||!p->stream_generation||!stock(p)||
       p->owner_ack_rid[0])return -1;
    s->phase=MIBR_OWNER_STOCK;s->session=p->stream_session;
    s->stream_generation=p->stream_generation;s->route_generation=1;
    return 0;
}
void mibr_owner_quarantine(struct mibr_owner_lifecycle *s){
    if(s)s->phase=MIBR_OWNER_QUARANTINED;
}
int mibr_owner_observe(struct mibr_owner_lifecycle *s,const struct mibr_owner_proof *p){
    if(!s||s->phase==MIBR_OWNER_UNQUALIFIED||s->phase==MIBR_OWNER_QUARANTINED)return -1;
    if(!fresh(p)||!same_stream(s,p)||p->writer_count<0||p->writer_count>1){
        mibr_owner_quarantine(s);return -1;
    }
    if(s->phase==MIBR_OWNER_STARTING||s->phase==MIBR_OWNER_STOPPING){
        int verified=s->phase==MIBR_OWNER_STARTING?direct(p):stock(p);
        if(verified && !strcmp(p->owner_ack_rid,s->pending_rid)){
            s->phase=s->phase==MIBR_OWNER_STARTING?MIBR_OWNER_DIRECT:MIBR_OWNER_STOCK;
            ++s->route_generation;
            strcpy(s->last_ack_rid,s->pending_rid);
            s->pending_rid[0]=0;s->pending_target=MIBR_ROUTE_UNKNOWN;
            return 1;
        }
        /* An owner that is still transitioning may briefly differ from its
         * prior route. Keep PENDING; no new dispatch, including after timeout.
         * A verified conflicting foreign ACK is an authority violation. */
        if(p->owner_ack_rid[0]&&strcmp(p->owner_ack_rid,s->pending_rid)&&
           strcmp(p->owner_ack_rid,s->last_ack_rid)){
            mibr_owner_quarantine(s);return -1;
        }
        return 0;
    }
    /* A fresh unsolicited ACK in an otherwise stable state indicates another
     * actuator/owner; never issue a further command on such authority drift. */
    if(strcmp(p->owner_ack_rid,s->last_ack_rid)||
       (s->phase==MIBR_OWNER_STOCK&&!stock(p))||
       (s->phase==MIBR_OWNER_DIRECT&&!direct(p))){
        mibr_owner_quarantine(s);return -1;
    }
    return 0;
}
enum mibr_owner_decision mibr_owner_request(struct mibr_owner_lifecycle *s,
      const struct mibr_owner_proof *p,enum mibr_v3_visible_route target,
      uint64_t session,uint64_t generation,const char *rid){
    if(!s||!rid_ok(rid,1)||!fresh(p)||!same_stream(s,p)||
       session!=s->session||generation!=s->route_generation)return MIBR_OWNER_REJECT;
    if(s->phase==MIBR_OWNER_STARTING||s->phase==MIBR_OWNER_STOPPING)return
        !strcmp(rid,s->pending_rid)?MIBR_OWNER_PENDING:MIBR_OWNER_REJECT;
    if(s->phase!=MIBR_OWNER_STOCK&&s->phase!=MIBR_OWNER_DIRECT)return MIBR_OWNER_REJECT;
    if(mibr_owner_observe(s,p)<0)return MIBR_OWNER_REJECT;
    if((s->phase==MIBR_OWNER_STOCK&&target==MIBR_ROUTE_STOCK110)||
       (s->phase==MIBR_OWNER_DIRECT&&target==MIBR_ROUTE_DIRECT111))return MIBR_OWNER_NOOP;
    if(s->phase==MIBR_OWNER_STOCK&&target==MIBR_ROUTE_DIRECT111&&p->source111_ready==1){
        s->phase=MIBR_OWNER_STARTING;s->pending_target=target;
        strcpy(s->pending_rid,rid);return MIBR_OWNER_START_EXISTING;
    }
    if(s->phase==MIBR_OWNER_DIRECT&&target==MIBR_ROUTE_STOCK110){
        s->phase=MIBR_OWNER_STOPPING;s->pending_target=target;
        strcpy(s->pending_rid,rid);return MIBR_OWNER_STOP_EXISTING;
    }
    return MIBR_OWNER_REJECT;
}
int mibr_owner_dispatch(struct mibr_owner_lifecycle *s,
    const struct mibr_owner_proof *p,enum mibr_v3_visible_route target,
    uint64_t session,uint64_t generation,const char *rid,
    const struct mibr_owner_dispatch_ops *ops,void *ctx){
    enum mibr_owner_decision d;
    int rc;
    if(!s||!ops||!rid)return -1;
    /* Validate callback BEFORE reserving any in-flight owner slot. */
    if(target==MIBR_ROUTE_DIRECT111&&!ops->start_existing)return -1;
    if(target==MIBR_ROUTE_STOCK110&&!ops->stop_existing)return -1;
    d=mibr_owner_request(s,p,target,session,generation,rid);
    if(d==MIBR_OWNER_REJECT)return -1;
    if(d==MIBR_OWNER_NOOP)return 0;
    if(d==MIBR_OWNER_PENDING)return 2; /* same original RID: no second dispatch */
    rc=d==MIBR_OWNER_START_EXISTING?
        ops->start_existing(ctx,rid):ops->stop_existing(ctx,rid);
    if(rc==-1){
        /* Only a qualified callback's explicit ZERO-DISPATCH proof can
         * release this reservation. All ambiguous outcomes stay pending. */
        s->phase=d==MIBR_OWNER_START_EXISTING?MIBR_OWNER_STOCK:MIBR_OWNER_DIRECT;
        s->pending_rid[0]=0;s->pending_target=MIBR_ROUTE_UNKNOWN;
        return -1;
    }
    return rc<0?2:1; /* never assert visible route from callback return */
}
int mibr_owner_read(const struct mibr_owner_lifecycle *s,
                    struct mibr_v3_route_observation *out){
    if(!out)return -1;
    memset(out,0,sizeof(*out));
    if(!s||!s->session||!s->route_generation||
       (s->phase!=MIBR_OWNER_STOCK&&s->phase!=MIBR_OWNER_DIRECT))return -1;
    out->session=s->session;out->generation=s->route_generation;
    out->visible=s->phase==MIBR_OWNER_STOCK?MIBR_ROUTE_STOCK110:MIBR_ROUTE_DIRECT111;
    out->confirmed=1;strcpy(out->ack_request_id,s->last_ack_rid);
    return 0;
}
