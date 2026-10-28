/* SPDX-License-Identifier: GPL-3.0-or-later
 * Fast host regression for MU1440 soft overflow and incomplete-M1AU safety.
 * cc -std=c99 -Wall -Wextra -Werror -Isrc/native/altscreen111-gen2/include \
 *   tests/alt111_video_queue_recovery_test.c \
 *   src/native/altscreen111-gen2/src/alt111_video.c -o /tmp/alt111_video_queue_recovery_test
 */
#include "alt111.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static const uint8_t avcc[]={
    1,0x42,0,31,0xff,0xe1,0,4,0x67,0x42,0,31,1,0,2,0x68,0xce
};
static const uint8_t idr[]={0,0,0,2,0x65,0x88};
static const uint8_t pframe[]={0,0,0,2,0x41,0x88};
static const uint8_t raw_ts[8]={1,2,3,4,5,6,7,8};
static uint64_t setup(struct alt111_video *v)
{
    uint64_t s;
    alt111_video_init(v);
    s=alt111_video_begin(v,1);
    assert(alt111_video_config(v,s,avcc,sizeof(avcc))==ALT111_OK);
    assert(alt111_video_attach(v)==ALT111_OK);
    return s;
}
static void consume(struct alt111_video *v)
{
    struct alt111_output_ticket t;
    const uint8_t *b=NULL;
    size_t n=0;
    assert(alt111_video_peek(v,&b,&n,&t)==ALT111_OK && b && n);
    assert(alt111_video_advance(v,&t,n)==ALT111_OK);
}
static void pinned_header_overflow(void)
{
    struct alt111_video v;
    struct alt111_output_ticket t;
    const uint8_t *b=NULL;size_t n=0;
    uint64_t s=setup(&v),consumer=v.consumer,old_ordinal;
    unsigned i;
    assert(alt111_video_submit_timed(&v,s,idr,sizeof(idr),1,raw_ts)==ALT111_OK);
    assert(alt111_video_peek(&v,&b,&n,&t)==ALT111_OK);
    assert(t.priming && t.idr && t.source_time_present &&
           memcmp(t.source_ts_raw,raw_ts,8)==0);
    /* Simulate only a partial M1AU header being sent: payload offset still 0. */
    assert(alt111_video_mark_wire_started(&v,&t)==ALT111_OK);
    for(i=1;i<ALT111_QUEUE_CAP;++i)
        assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_OK);
    old_ordinal=v.source_ordinal;
    assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_SOFT_RESYNC);
    assert(v.attached && v.consumer==consumer && v.count==1 &&
           v.recovery_wait_idr && v.recovery_draining &&
           v.source_ordinal==old_ordinal+1);
    assert(alt111_video_peek(&v,&b,&n,&t)==ALT111_OK && t.offset==0);
    /* Even a fresh IDR cannot bypass an already-started TCP record. */
    assert(alt111_video_submit(&v,s,idr,sizeof(idr),1)==ALT111_WAIT);
    assert(v.count==1);
    consume(&v);
    assert(v.count==0 && v.recovery_wait_idr && !v.recovery_draining &&
           v.recovery_request_due && !v.consumer_primed);
    assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_WAIT);
    assert(alt111_video_submit_timed(&v,s,idr,sizeof(idr),1,raw_ts)==ALT111_OK);
    assert(alt111_video_peek(&v,&b,&n,&t)==ALT111_OK);
    assert(t.priming && t.idr && t.source_ordinal==v.source_ordinal &&
           memcmp(t.source_ts_raw,raw_ts,8)==0 && n>sizeof(idr));
    consume(&v);
    assert(v.consumer_primed && v.attached && v.consumer==consumer);
    assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_OK);
    alt111_video_destroy(&v);
}
static void unsent_head_overflow(void)
{
    struct alt111_video v;
    uint64_t s=setup(&v),consumer=v.consumer;
    unsigned i;
    assert(alt111_video_submit(&v,s,idr,sizeof(idr),1)==ALT111_OK);
    consume(&v);
    for(i=0;i<ALT111_QUEUE_CAP;++i)
        assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_OK);
    assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_SOFT_RESYNC);
    assert(v.attached && v.consumer==consumer && v.count==0 &&
           v.recovery_wait_idr && !v.recovery_draining && !v.consumer_primed);
    assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_WAIT);
    assert(alt111_video_submit(&v,s,idr,sizeof(idr),1)==ALT111_OK);
    consume(&v);
    assert(v.consumer_primed && v.consumer==consumer && !v.recovery_wait_idr);
    alt111_video_destroy(&v);
}
static void partial_payload_overflow(void)
{
    struct alt111_video v;
    struct alt111_output_ticket ticket,stale;
    const uint8_t *bytes=NULL;size_t n=0;
    uint64_t s=setup(&v),consumer=v.consumer;
    unsigned i;
    assert(alt111_video_submit(&v,s,idr,sizeof(idr),1)==ALT111_OK);
    assert(alt111_video_peek(&v,&bytes,&n,&ticket)==ALT111_OK && n>1);
    stale=ticket;
    /* Already sent a payload prefix, even in raw Annex-B mode. */
    assert(alt111_video_advance(&v,&ticket,1)==ALT111_OK);
    for(i=1;i<ALT111_QUEUE_CAP;++i)
        assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_OK);
    assert(alt111_video_submit(&v,s,pframe,sizeof(pframe),1)==ALT111_SOFT_RESYNC);
    assert(v.count==1 && v.recovery_draining && v.consumer==consumer);
    assert(alt111_video_peek(&v,&bytes,&n,&ticket)==ALT111_OK && ticket.offset==1);
    assert(alt111_video_mark_wire_started(&v,&stale)==ALT111_STALE);
    assert(alt111_video_advance(&v,&ticket,n)==ALT111_OK);
    assert(v.recovery_request_due && !v.consumer_primed);
    assert(alt111_video_submit(&v,s,idr,sizeof(idr),1)==ALT111_OK);
    consume(&v);
    assert(v.consumer_primed && v.consumer==consumer);
    alt111_video_destroy(&v);
}
static void monotonic_age_backlog(void)
{
    struct alt111_video v;
    uint64_t s=setup(&v),consumer=v.consumer;
    assert(alt111_video_submit_timed_at(&v,s,idr,sizeof(idr),1,NULL,1000000u)==ALT111_OK);
    consume(&v);
    /* One static/delayed AU alone must NEVER be removed for age. */
    assert(alt111_video_submit_timed_at(&v,s,pframe,sizeof(pframe),1,NULL,1000001u)==ALT111_OK);
    assert(alt111_video_submit_timed_at(&v,s,pframe,sizeof(pframe),1,NULL,2500002u)==ALT111_OK);
    assert(v.count==2 && !v.queue_stale_events);
    /* A new incoming AU with two queued stale AUs triggers loss of only
     * unsent records; source-time bytes are irrelevant to this decision. */
    assert(alt111_video_submit_timed_at(&v,s,pframe,sizeof(pframe),1,raw_ts,2500003u)==ALT111_SOFT_RESYNC);
    assert(v.queue_stale_events==1 && v.queue_overflow_events==0);
    assert(v.count==0 && v.attached && v.consumer==consumer && v.recovery_wait_idr);
    assert(alt111_video_submit_timed_at(&v,s,pframe,sizeof(pframe),1,NULL,2500004u)==ALT111_WAIT);
    assert(alt111_video_submit_timed_at(&v,s,idr,sizeof(idr),1,raw_ts,2500005u)==ALT111_OK);
    consume(&v);
    assert(v.consumer_primed && v.consumer==consumer && v.delivered_idr_ordinal==v.source_ordinal);
    alt111_video_destroy(&v);
}
static void byte_budget_overflow(void)
{
    struct alt111_video v;
    uint64_t stream=setup(&v),consumer=v.consumer;
    const size_t payload=1024u*1024u, size=payload+4u;
    uint8_t *au=(uint8_t *)malloc(size);
    unsigned accepted=0;
    int rc;
    assert(au);
    memset(au,0x88,size);
    au[0]=0;au[1]=0x10;au[2]=0;au[3]=0;au[4]=0x41;
    assert(alt111_video_submit(&v,stream,idr,sizeof(idr),1)==ALT111_OK);
    consume(&v);
    do {
        rc=alt111_video_submit(&v,stream,au,size,1);
        if(rc==ALT111_OK)++accepted;
    } while(rc==ALT111_OK && accepted<ALT111_QUEUE_CAP);
    assert(rc==ALT111_SOFT_RESYNC && accepted<ALT111_QUEUE_CAP);
    assert(v.attached && v.consumer==consumer && !v.count &&
           !v.queued_bytes && v.recovery_wait_idr);
    assert(alt111_video_submit(&v,stream,pframe,sizeof(pframe),1)==ALT111_WAIT);
    assert(alt111_video_submit(&v,stream,idr,sizeof(idr),1)==ALT111_OK);
    consume(&v);
    assert(v.consumer_primed && v.consumer==consumer);
    free(au);alt111_video_destroy(&v);
}
int main(void)
{
    byte_budget_overflow();
    monotonic_age_backlog();
    pinned_header_overflow();
    unsent_head_overflow();
    partial_payload_overflow();
    puts("ALT111_VIDEO_QUEUE_RECOVERY_TEST=PASS");
    return 0;
}
