/* per-view 111 zoom transition coordinator. See alt111_viewscale.h. */
#include "alt111_viewscale.h"

#include <stdio.h>
#include <string.h>

static void copy_zoom(char *dst, const char *src)
{
    snprintf(dst, ALT111_VS_ZOOM_CAP, "%s", src ? src : "");
}

static void set_result(struct alt111_vs *vs, const char *r)
{
    snprintf(vs->last_result, sizeof(vs->last_result), "%s", r);
}

static int running(const struct alt111_vs *vs)
{
    return vs->state == ALT111_VS_APPLYING || vs->state == ALT111_VS_RESTORING;
}

void alt111_vs_init(struct alt111_vs *vs)
{
    memset(vs, 0, sizeof(*vs));
    vs->state = ALT111_VS_IDLE;
    set_result(vs, "none");
}

void alt111_vs_request(struct alt111_vs *vs, unsigned area, const char *zoom)
{
    if (!zoom || !zoom[0]) return;
    copy_zoom(vs->want, zoom);
    vs->want_area = area;
    vs->have_want = 1u;
}

static void end_run(struct alt111_vs *vs, enum alt111_vs_state st, const char *result, uint64_t now)
{
    vs->state = st;
    vs->ended_ms = now;
    vs->fail_now = 0u;
    set_result(vs, result);
}

enum alt111_vs_action alt111_vs_tick(struct alt111_vs *vs, const struct alt111_vs_config *cfg, uint64_t now)
{
    if (!cfg || !cfg->enabled) {
        vs->have_want = 0u;
        return ALT111_VS_ACT_NONE;
    }
    if (running(vs)) {
        const int timed_out = vs->fail_now ||
            (now >= vs->started_ms && now - vs->started_ms >= cfg->confirm_timeout_ms);
        if (!vs->fail_now && vs->seen_setup111 && vs->seen_info_target) {
            if (vs->state == ALT111_VS_APPLYING) {
                copy_zoom(vs->active, vs->target);
                vs->confirmed++;
                end_run(vs, ALT111_VS_CONFIRMED, "confirmed", now);
            } else {
                vs->restored++;
                end_run(vs, ALT111_VS_ROLLED_BACK, "rolled_back", now);
            }
            return ALT111_VS_ACT_NONE;
        }
        if (!timed_out) return ALT111_VS_ACT_NONE;
        if (vs->state == ALT111_VS_APPLYING && vs->active[0]) {
            /* exactly one restore with the last confirmed zoom */
            vs->state = ALT111_VS_RESTORING;
            vs->started_ms = now;
            vs->seen_setup111 = vs->seen_info_target = 0u;
            vs->fail_now = 0u;
            vs->failed++;
            set_result(vs, "restoring");
            return ALT111_VS_ACT_RESTORE;
        }
        if (vs->state == ALT111_VS_APPLYING) vs->failed++;
        end_run(vs, ALT111_VS_FAILED, vs->state == ALT111_VS_RESTORING ? "restore_failed" : "failed", now);
        return ALT111_VS_ACT_NONE;
    }
    if (!vs->have_want) return ALT111_VS_ACT_NONE;
    if (!vs->active[0]) {
        /* no verified zoom in this session: the next /info uses the selected view */
        vs->have_want = 0u;
        set_result(vs, "no_session");
        return ALT111_VS_ACT_NONE;
    }
    if (!strcmp(vs->want, vs->active)) {
        vs->have_want = 0u;
        vs->skipped_same++;
        if (vs->state == ALT111_VS_PENDING_RECONNECT) vs->state = ALT111_VS_IDLE;
        set_result(vs, "same_zoom");
        return ALT111_VS_ACT_NONE;
    }
    if (!strcmp(vs->want, "AUTO")) {
        vs->have_want = 0u;
        vs->pending_reconnect++;
        vs->state = ALT111_VS_PENDING_RECONNECT;
        set_result(vs, "pending_reconnect");
        return ALT111_VS_ACT_NONE;
    }
    if (vs->ended_ms && now >= vs->ended_ms && now - vs->ended_ms < cfg->min_interval_ms) {
        if (strcmp(vs->last_result, "deferred")) {
            vs->deferred++;
            set_result(vs, "deferred");
        }
        return ALT111_VS_ACT_NONE;
    }
    copy_zoom(vs->target, vs->want);
    vs->target_area = vs->want_area;
    vs->have_want = 0u;
    vs->state = ALT111_VS_APPLYING;
    vs->started_ms = now;
    vs->seen_setup111 = vs->seen_info_target = 0u;
    vs->fail_now = 0u;
    vs->runs++;
    set_result(vs, "applying");
    return ALT111_VS_ACT_START;
}

void alt111_vs_sent(struct alt111_vs *vs, enum alt111_vs_action act, int ok, uint64_t now)
{
    if (ok) return;
    if (act == ALT111_VS_ACT_START && vs->state == ALT111_VS_APPLYING) {
        /* a cycle may already have removed 111: the next tick restores */
        vs->fail_now = 1u;
        set_result(vs, "send_failed");
    } else if (act == ALT111_VS_ACT_RESTORE && vs->state == ALT111_VS_RESTORING) {
        end_run(vs, ALT111_VS_FAILED, "restore_send_failed", now);
    }
}

void alt111_vs_observe_info(struct alt111_vs *vs, const char *zoom, uint64_t now)
{
    if (!zoom || !zoom[0]) return;
    if (running(vs)) {
        const char *expect = vs->state == ALT111_VS_APPLYING ? vs->target : vs->active;
        if (now >= vs->started_ms && !strcmp(zoom, expect)) vs->seen_info_target = 1u;
        return;
    }
    copy_zoom(vs->active, zoom);
}

void alt111_vs_observe_setup111(struct alt111_vs *vs, uint64_t now)
{
    if (running(vs) && now >= vs->started_ms) vs->seen_setup111 = 1u;
}

void alt111_vs_observe_full_teardown(struct alt111_vs *vs)
{
    struct alt111_vs keep = *vs;
    alt111_vs_init(vs);
    vs->runs = keep.runs; vs->confirmed = keep.confirmed; vs->failed = keep.failed;
    vs->restored = keep.restored; vs->skipped_same = keep.skipped_same;
    vs->deferred = keep.deferred; vs->pending_reconnect = keep.pending_reconnect;
    set_result(vs, "session_reset");
}

const char *alt111_vs_advert_zoom(const struct alt111_vs *vs)
{
    if (vs->state == ALT111_VS_APPLYING) return vs->target;
    if (vs->state == ALT111_VS_RESTORING) return vs->active[0] ? vs->active : NULL;
    return NULL;
}

const char *alt111_vs_state_name(enum alt111_vs_state s)
{
    switch (s) {
    case ALT111_VS_IDLE: return "idle";
    case ALT111_VS_APPLYING: return "applying";
    case ALT111_VS_CONFIRMED: return "confirmed";
    case ALT111_VS_RESTORING: return "restoring";
    case ALT111_VS_ROLLED_BACK: return "rolled_back";
    case ALT111_VS_FAILED: return "failed";
    case ALT111_VS_PENDING_RECONNECT: return "pending_reconnect";
    }
    return "unknown";
}
