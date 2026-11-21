/* host test for the per-view 111 zoom transition coordinator. */
#include "alt111_viewscale.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures;
#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL %s:%d %s\n", __FILE__, __LINE__, #c); failures++; } } while (0)

static const struct alt111_vs_config CFG = { 1u, 3000u, 10000u };

static void connected(struct alt111_vs *vs, const char *zoom)
{
    alt111_vs_init(vs);
    alt111_vs_observe_info(vs, zoom, 10u);   /* normal connect /info */
}

static void confirm(struct alt111_vs *vs, const char *zoom, uint64_t t)
{
    alt111_vs_observe_setup111(vs, t);
    alt111_vs_observe_info(vs, zoom, t + 5u);
}

static void test_happy_path_and_latest_wins(void)
{
    struct alt111_vs vs;
    connected(&vs, "100");
    CHECK(alt111_vs_advert_zoom(&vs) == NULL);
    alt111_vs_request(&vs, 2u, "70");
    CHECK(alt111_vs_tick(&vs, &CFG, 1000u) == ALT111_VS_ACT_START);
    alt111_vs_sent(&vs, ALT111_VS_ACT_START, 1, 1000u);
    CHECK(vs.state == ALT111_VS_APPLYING);
    CHECK(!strcmp(alt111_vs_advert_zoom(&vs), "70"));
    CHECK(!strcmp(vs.active, "100"));                      /* F1: sent is not applied */
    /* two fast menu inputs while applying: only the latest survives */
    alt111_vs_request(&vs, 0u, "85");
    alt111_vs_request(&vs, 1u, "125");
    CHECK(alt111_vs_tick(&vs, &CFG, 1200u) == ALT111_VS_ACT_NONE);   /* F5: no second run */
    alt111_vs_observe_info(&vs, "100", 1300u);             /* stale descriptor: not a confirmation */
    alt111_vs_observe_setup111(&vs, 1400u);
    CHECK(alt111_vs_tick(&vs, &CFG, 1500u) == ALT111_VS_ACT_NONE);
    CHECK(vs.state == ALT111_VS_APPLYING);
    alt111_vs_observe_info(&vs, "70", 1600u);
    CHECK(alt111_vs_tick(&vs, &CFG, 1700u) == ALT111_VS_ACT_NONE);
    CHECK(vs.state == ALT111_VS_CONFIRMED);
    CHECK(!strcmp(vs.active, "70"));
    CHECK(alt111_vs_advert_zoom(&vs) == NULL);
    /* min interval counts from the end of the run */
    CHECK(alt111_vs_tick(&vs, &CFG, 3000u) == ALT111_VS_ACT_NONE);
    CHECK(!strcmp(vs.last_result, "deferred"));
    CHECK(alt111_vs_tick(&vs, &CFG, 4700u) == ALT111_VS_ACT_START);
    CHECK(!strcmp(vs.target, "125") && vs.target_area == 1u);
    CHECK(vs.runs == 2u && vs.confirmed == 1u && vs.deferred == 1u);
}

static void test_same_zoom_is_noop(void)
{
    struct alt111_vs vs;
    connected(&vs, "100");
    alt111_vs_request(&vs, 0u, "100");
    CHECK(alt111_vs_tick(&vs, &CFG, 1000u) == ALT111_VS_ACT_NONE);
    CHECK(vs.skipped_same == 1u && vs.runs == 0u);
}

static void test_timeout_restores_once(void)
{
    struct alt111_vs vs;
    connected(&vs, "100");
    alt111_vs_request(&vs, 2u, "70");
    CHECK(alt111_vs_tick(&vs, &CFG, 1000u) == ALT111_VS_ACT_START);
    alt111_vs_sent(&vs, ALT111_VS_ACT_START, 1, 1000u);
    /* phone only ACKs: no SETUP(111) */
    CHECK(alt111_vs_tick(&vs, &CFG, 10999u) == ALT111_VS_ACT_NONE);
    CHECK(alt111_vs_tick(&vs, &CFG, 11000u) == ALT111_VS_ACT_RESTORE);   /* F2 */
    alt111_vs_sent(&vs, ALT111_VS_ACT_RESTORE, 1, 11000u);
    CHECK(vs.state == ALT111_VS_RESTORING);
    CHECK(!strcmp(alt111_vs_advert_zoom(&vs), "100"));
    confirm(&vs, "100", 12000u);
    CHECK(alt111_vs_tick(&vs, &CFG, 12100u) == ALT111_VS_ACT_NONE);
    CHECK(vs.state == ALT111_VS_ROLLED_BACK && !strcmp(vs.active, "100"));
    CHECK(vs.failed == 1u && vs.restored == 1u);
    /* restore without confirmation ends in FAILED, never a second restore */
    alt111_vs_request(&vs, 2u, "70");
    CHECK(alt111_vs_tick(&vs, &CFG, 20000u) == ALT111_VS_ACT_START);
    CHECK(alt111_vs_tick(&vs, &CFG, 30000u) == ALT111_VS_ACT_RESTORE);
    CHECK(alt111_vs_tick(&vs, &CFG, 40000u) == ALT111_VS_ACT_NONE);
    CHECK(vs.state == ALT111_VS_FAILED);
    CHECK(alt111_vs_tick(&vs, &CFG, 50000u) == ALT111_VS_ACT_NONE);
}

static void test_send_failure_restores(void)
{
    struct alt111_vs vs;
    connected(&vs, "85");
    alt111_vs_request(&vs, 2u, "70");
    CHECK(alt111_vs_tick(&vs, &CFG, 1000u) == ALT111_VS_ACT_START);
    alt111_vs_sent(&vs, ALT111_VS_ACT_START, 0, 1000u);   /* e.g. cycleB failed after cycleA */
    CHECK(!strcmp(vs.active, "85"));                       /* F1 */
    CHECK(alt111_vs_tick(&vs, &CFG, 1001u) == ALT111_VS_ACT_RESTORE);
    alt111_vs_sent(&vs, ALT111_VS_ACT_RESTORE, 0, 1001u);
    CHECK(vs.state == ALT111_VS_FAILED);
    CHECK(alt111_vs_tick(&vs, &CFG, 1002u) == ALT111_VS_ACT_NONE);
}

static void test_auto_and_no_session(void)
{
    struct alt111_vs vs;
    alt111_vs_init(&vs);
    alt111_vs_request(&vs, 0u, "70");                       /* before any /info */
    CHECK(alt111_vs_tick(&vs, &CFG, 1000u) == ALT111_VS_ACT_NONE);
    CHECK(!strcmp(vs.last_result, "no_session"));
    connected(&vs, "70");
    alt111_vs_request(&vs, 0u, "AUTO");                     /* F4 */
    CHECK(alt111_vs_tick(&vs, &CFG, 2000u) == ALT111_VS_ACT_NONE);
    CHECK(vs.state == ALT111_VS_PENDING_RECONNECT && vs.pending_reconnect == 1u);
    alt111_vs_request(&vs, 2u, "70");                       /* back to a view with the active zoom */
    CHECK(alt111_vs_tick(&vs, &CFG, 2100u) == ALT111_VS_ACT_NONE);
    CHECK(vs.state == ALT111_VS_IDLE);
}

static void test_disabled_and_teardown(void)
{
    struct alt111_vs vs;
    const struct alt111_vs_config off = { 0u, 3000u, 10000u };
    connected(&vs, "100");
    alt111_vs_request(&vs, 2u, "70");
    CHECK(alt111_vs_tick(&vs, &off, 1000u) == ALT111_VS_ACT_NONE);
    CHECK(vs.runs == 0u && !vs.have_want);
    alt111_vs_request(&vs, 2u, "70");
    CHECK(alt111_vs_tick(&vs, &CFG, 1000u) == ALT111_VS_ACT_START);
    alt111_vs_observe_full_teardown(&vs);
    CHECK(vs.state == ALT111_VS_IDLE && !vs.active[0] && vs.runs == 1u);
    CHECK(alt111_vs_advert_zoom(&vs) == NULL);
    CHECK(alt111_vs_tick(&vs, &CFG, 2000u) == ALT111_VS_ACT_NONE);
}

int main(void)
{
    test_happy_path_and_latest_wins();
    test_same_zoom_is_noop();
    test_timeout_restores_once();
    test_send_failure_restores();
    test_auto_and_no_session();
    test_disabled_and_teardown();
    if (failures) { fprintf(stderr, "ALT111_VIEWSCALE_TEST=FAIL %d\n", failures); return 1; }
    puts("ALT111_VIEWSCALE_TEST=PASS");
    return 0;
}
