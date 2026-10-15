#include "alt111.h"
#include "alt111_bridge_status.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static struct alt111_resync_snapshot ready(void)
{
    struct alt111_resync_snapshot s;
    memset(&s,0,sizeof(s));
    s.stream=1;s.codec=2;s.consumer=3;
    s.source_aus=10;s.source_idrs=1;
    s.last_source_idr_ordinal=5;s.delivered_idr_ordinal=5;
    s.projection_desired=s.config_valid=s.consumer_primed=1;
    return s;
}
int main(void)
{
    struct alt111_resync r;struct alt111_resync_snapshot s=ready();
    struct alt111_bridge_status b={0};
    const char *stat="state=running\nclock_snapshot_mono_us=1000000\noutput_last_idr_completed_sequence=11\noutput_last_idr_completed_stream=1\noutput_last_idr_completed_codec=2\noutput_last_idr_completed_consumer=3\nblocks_written=19\nwrite_errors=0\n";
    assert(!alt111_bridge_status_parse(stat,&b));
    assert(b.sequence==11 && alt111_bridge_status_matches(&b,1500000,1,2,3));
    assert(!alt111_bridge_status_matches(&b,4500000,1,2,3)); /* stale */
    assert(!alt111_bridge_status_matches(&b,1500000,1,9,3)); /* wrong codec */
    assert(alt111_bridge_status_parse("state=waiting_idr\n",&b)<0);
    alt111_resync_init(&r);alt111_resync_set_enabled(&r,1);
    assert(alt111_resync_arm(&r,100,ALT111_RESYNC_REASON_MANUAL,&s)==ALT111_OK);
    assert(alt111_resync_tick(&r,100,&s)==ALT111_RESYNC_REQUEST_KEYFRAME);
    s.source_idrs=2;s.source_aus=11;s.last_source_idr_ordinal=11;
    assert(alt111_resync_tick(&r,101,&s)==ALT111_RESYNC_NONE); /* source IDR only */
    s.delivered_idr_ordinal=11;
    assert(alt111_resync_tick(&r,102,&s)==ALT111_RESYNC_SOURCE_RECOVERED);
    assert(r.state==ALT111_RESYNC_NEED_BRIDGE && r.completions==0);
    s.bridge_idr_ordinal=10;s.bridge_healthy=1;
    assert(alt111_resync_tick(&r,1200,&s)==ALT111_RESYNC_NONE); /* wrong ordinal */
    s.bridge_idr_ordinal=11;s.bridge_healthy=0;
    assert(alt111_resync_tick(&r,1500,&s)==ALT111_RESYNC_NONE); /* not healthy */
    s.bridge_healthy=1;
    assert(alt111_resync_tick(&r,1501,&s)==ALT111_RESYNC_NONE);
    assert(alt111_resync_tick(&r,2500,&s)==ALT111_RESYNC_NONE); /* less than 1s */
    assert(alt111_resync_tick(&r,2501,&s)==ALT111_RESYNC_COMPLETED);
    assert(r.completions==1 && r.source_recoveries==1);
    /* A second overload invalidates any old candidate / stale writer sample. */
    s=ready();alt111_resync_set_enabled(&r,1);
    assert(alt111_resync_arm(&r,3000,ALT111_RESYNC_REASON_OVERFLOW,&s)==ALT111_OK);
    s.soft_recovery_epoch=1;s.source_aus=11;s.source_idrs=2;
    s.last_source_idr_ordinal=s.delivered_idr_ordinal=11;
    assert(alt111_resync_tick(&r,3001,&s)==ALT111_RESYNC_REQUEST_KEYFRAME);
    assert(r.state==ALT111_RESYNC_NEED_IDR && r.candidate_idr_ordinal==0);
    assert(alt111_resync_tick(&r,3002,&s)==ALT111_RESYNC_NONE);
    s.source_aus=12;s.source_idrs=3;s.last_source_idr_ordinal=s.delivered_idr_ordinal=12;
    assert(alt111_resync_tick(&r,3003,&s)==ALT111_RESYNC_SOURCE_RECOVERED);
    s.bridge_healthy=1;s.bridge_idr_ordinal=11;
    assert(alt111_resync_tick(&r,4100,&s)==ALT111_RESYNC_NONE);
    s.bridge_idr_ordinal=12;
    assert(alt111_resync_tick(&r,4101,&s)==ALT111_RESYNC_NONE);
    assert(alt111_resync_tick(&r,5101,&s)==ALT111_RESYNC_COMPLETED);
    puts("ALT111_RESYNC_BRIDGE_TEST=PASS");
    return 0;
}
