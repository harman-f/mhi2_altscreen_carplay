/* Behavioral tests of the real pure producer policy and serialized controller. */
#include "alt111.h"
#include "alt111_recovery.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static void timestamp(uint8_t raw[8], uint64_t value)
{
    unsigned i;
    for (i = 0; i < 8; ++i) raw[i] = (uint8_t)(value >> (i * 8));
}

int main(void)
{
    struct alt111_recovery_request request={ALT111_KF_SOURCE_GAP,1,2,3,4,5},parsed;
    char record[ALT111_RECOVERY_CAP];int length;
    length=alt111_recovery_render(&request,record,sizeof(record));assert(length>0);
    assert(!alt111_recovery_parse(record,(size_t)length,&parsed));
    assert(parsed.consumer==3 && parsed.reasons==ALT111_KF_SOURCE_GAP);
    assert(alt111_recovery_parse(record,(size_t)length-1u,&parsed)<0);
    {
        const char *invalid[]={"M1KF1 16 1 2 3 4 05\n","M1KF1 128 1 2 3 4 5\n",
            "M1KF1 16 1 2 3 4 5x\n","M1KF1 16 1 2 3 4 18446744073709551616\n"};
        unsigned j;
        for(j=0;j<sizeof(invalid)/sizeof(invalid[0]);++j)
            assert(alt111_recovery_parse(invalid[j],strlen(invalid[j]),&parsed)<0);
    }
    struct alt111_policy p;
    struct alt111_policy_config cfg;
    struct alt111_control c;
    struct alt111_command cmd;
    uint8_t raw[8];
    uint64_t session, i, rawtime, requests;
    memset(&p, 0, sizeof(p)); alt111_policy_defaults(&cfg);
    assert(alt111_policy_configure(&p, &cfg) == 0);
    for (i = 1; i <= 60; ++i) {
        timestamp(raw, (i << 32) / 15);
        assert(alt111_policy_au(&p, 1, i, raw, 1, i * 1000000 / 15) ==
               (i % 20 == 0 ? ALT111_KF_PERIODIC_FRAMES : 0));
    }
    cfg.interval_frames = 10; assert(!alt111_policy_configure(&p, &cfg));
    assert(!alt111_policy_au(&p, 1, 23, raw, 1, 5000000));
    assert(alt111_policy_au(&p, 1, 30, raw, 1, 5000000) == ALT111_KF_PERIODIC_FRAMES);
    cfg.mode = ALT111_SOURCE_TIME; cfg.interval_ms = 2000;
    assert(!alt111_policy_configure(&p, &cfg));
    /* Initial exactly-zero is real time. VFR is not frame_no/maxFPS. */
    requests = 0;
    for (i = 0; i <= 60; ++i) {
        rawtime = (i << 32) / 15; timestamp(raw, rawtime);
        requests += !!alt111_policy_au(&p, 2, i + 1, raw, 1, i * 1000000 / 15);
    }
    assert(requests == 2);
    /* Quiet 12-second pause yields one opportunity, not six queued requests. */
    timestamp(raw, (uint64_t)16 << 32);
    assert(alt111_policy_au(&p, 2, 62, raw, 1, 16000000) == ALT111_KF_PERIODIC_TIME);
    assert(!alt111_policy_au(&p, 2, 63, raw, 1, 16000001));
    /* Missing time never uses arrival-clock periodics. */
    assert(!alt111_policy_au(&p, 2, 64, raw, 0, 30000000));
    assert(!p.source_time_available);
    timestamp(raw, 0); assert(!alt111_policy_au(&p, 2, 65, raw, 1, 30000001));
    assert(p.source_time_available);
    timestamp(raw, (uint64_t)2 << 32);
    assert(alt111_policy_au(&p, 2, 66, raw, 1, 32000001) == ALT111_KF_PERIODIC_TIME);
    /* Fractional borrow and seconds wrap; arrival catches up with source. */
    timestamp(raw, UINT64_MAX - (((uint64_t)1 << 32) - 1));
    assert(!alt111_policy_au(&p, 3, 1, raw, 1, 0));
    timestamp(raw, (uint64_t)1 << 32);
    assert(alt111_policy_au(&p, 3, 2, raw, 1, 2000000) == ALT111_KF_PERIODIC_TIME);
    timestamp(raw, 0); assert(!alt111_policy_au(&p, 3, 3, raw, 1, 2000001));
    assert(p.clock_resets > 0);
    cfg.mode = ALT111_PERIODIC_OFF; cfg.showui = 0;
    assert(!alt111_policy_configure(&p, &cfg));
    assert(!alt111_policy_au(&p, 4, 20, raw, 1, 2000000));
    assert(alt111_policy_event(&cfg, ALT111_KF_SHOWUI | ALT111_KF_SOURCE_GAP) == ALT111_KF_SOURCE_GAP);
    cfg.gap_recovery = 0;
    assert(alt111_policy_event(&cfg, ALT111_KF_SOURCE_GAP | ALT111_KF_BRIDGE_READY) == ALT111_KF_BRIDGE_READY);
    cfg.interval_frames = 0; assert(alt111_policy_configure(&p, &cfg) < 0);

    assert(!alt111_control_init(&c, 2)); session = alt111_control_begin(&c);
    assert(!alt111_control_intent(&c, 1, 0));
    assert(!alt111_control_next(&c, 0, &cmd) && cmd.type == ALT111_CMD_SHOW);
    assert(alt111_control_complete(&c, session + 1, cmd.request, 1, 1) == ALT111_STALE);
    assert(c.keyframe_wanted == 0);
    assert(!alt111_control_complete(&c, session, cmd.request, 1, 1));
    assert(!alt111_control_next(&c, 2, &cmd) && cmd.type == ALT111_CMD_KEYFRAME);
    assert(cmd.keyframe_reasons == ALT111_KF_SHOWUI);
    assert(!alt111_control_keyframe_reason(&c, session, ALT111_KF_SOURCE_GAP));
    assert(!alt111_control_complete(&c, session, cmd.request, 1, 3));
    assert(!alt111_control_next(&c, 4, &cmd) && cmd.keyframe_reasons == ALT111_KF_SOURCE_GAP);
    assert(!alt111_control_complete(&c, session, cmd.request, 1, 5));
    for (i = 0; i < 3; ++i) {
        assert(!alt111_control_next(&c, 10000 + i * 2000, &cmd) && cmd.type == ALT111_CMD_VIEW);
        assert(!alt111_control_complete(&c, session, cmd.request, 0, 10001 + i * 2000));
    }
    assert(c.view_exhausted && !c.exhausted);
    assert(!alt111_control_keyframe_reason(&c, session, ALT111_KF_PERIODIC_FRAMES));
    assert(!alt111_control_next(&c, 15000, &cmd) && cmd.type == ALT111_CMD_KEYFRAME);
    puts("ALT111_POLICY_TEST=PASS");
    return 0;
}
