/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_rgi_guidance.h"

#include <stdarg.h>
#include <stdio.h>
#include <string.h>

void mibr_rgi_guidance_reset(struct mibr_rgi_guidance *g)
{
    unsigned seq = g->seq;

    memset(g, 0, sizeof(*g));
    g->seq = seq + 1;
}

static void copy_line(char *dst, size_t cap, const char *src)
{
    size_t i;

    for (i = 0; i + 1 < cap && src[i] && src[i] != '\n' && src[i] != '\r'; i++) {
        dst[i] = src[i];
    }
    dst[i] = 0;
}

void mibr_rgi_guidance_update(struct mibr_rgi_guidance *g, const rgd_update_t *u)
{
    if (u->present & RGD_UPD_ROUTE_STATE) {
        g->route_state = u->route_state;
        g->have_route_state = 1;
        if (u->route_state == RGD_STATE_NO_ROUTE_SET) {
            /* a new route starts with new maneuver indices */
            memset(g->man, 0, sizeof(g->man));
            memset(g->lanes, 0, sizeof(g->lanes));
            g->have_current = 0;
            g->lanes_showing = 0;
        }
    }
    if (u->present & RGD_UPD_MANEUVER_STATE) g->maneuver_state = u->maneuver_state;
    if (u->present & RGD_UPD_DISTANCE_REMAINING) {
        g->distance_remaining = u->distance_remaining;
        g->have_dist_rem = 1;
    }
    if (u->present & RGD_UPD_DIST_TO_MANEUVER) {
        g->dist_to_maneuver = u->dist_to_maneuver;
        g->have_dist_man = 1;
    }
    if (u->present & RGD_UPD_TIME_REMAINING) {
        g->time_remaining = u->time_remaining;
        g->have_time = 1;
    }
    if (u->present & RGD_UPD_CURRENT_ROAD) copy_line(g->road, sizeof(g->road), u->current_road);
    if (u->present & RGD_UPD_DESTINATION) copy_line(g->destination, sizeof(g->destination), u->destination);
    if (u->present & RGD_UPD_MANEUVER_LIST) {
        g->have_current = u->maneuver_list_count > 0;
        g->current_index = g->have_current ? u->maneuver_list[0] : 0;
    }
    if (u->present & RGD_UPD_LANE_INDEX) g->lane_index = u->lane_guidance_index;
    if (u->present & RGD_UPD_LANE_SHOWING) g->lanes_showing = u->lane_guidance_showing != 0;
    g->seq++;
}

void mibr_rgi_guidance_maneuver(struct mibr_rgi_guidance *g, const rgd_maneuver_t *m)
{
    struct mibr_rgi_cached_maneuver *c;
    unsigned i;

    if (!(m->present & RGD_MAN_INDEX)) {
        return;
    }
    c = &g->man[m->index % MIBR_RGI_CACHE];
    if (!c->valid || c->index != m->index) {
        memset(c, 0, sizeof(*c));
        c->exit_angle = 1000;
        c->type = MAN_TYPE_NOT_SET;
    }
    c->valid = 1;
    c->index = m->index;
    if (m->present & RGD_MAN_TYPE) c->type = m->maneuver_type;
    if (m->present & RGD_MAN_EXIT_ANGLE) c->exit_angle = m->exit_angle;
    if (m->present & RGD_MAN_DRIVING_SIDE) c->driving_side = m->driving_side;
    if (m->present & RGD_MAN_JUNCTION_TYPE) c->junction_type = m->junction_type;
    if (m->present & RGD_MAN_AFTER_ROAD) copy_line(c->after_road, sizeof(c->after_road), m->after_road_name);
    if (m->present & RGD_MAN_JUNCTION_ANGLES) {
        c->angle_count = m->junction_angle_count > MAX_MANEUVER_LIST ? MAX_MANEUVER_LIST : m->junction_angle_count;
        for (i = 0; i < c->angle_count; i++) {
            c->angles[i] = m->junction_angles[i];
        }
    }
    g->seq++;
}

void mibr_rgi_guidance_lanes(struct mibr_rgi_guidance *g, const rgd_lane_guidance_t *l)
{
    struct mibr_rgi_cached_lanes *c;
    unsigned i, k;

    if (!(l->present & RGD_LANE_GUIDANCE_INDEX)) {
        return;
    }
    c = &g->lanes[l->lane_guidance_index % MIBR_RGI_CACHE];
    memset(c, 0, sizeof(*c));
    /* an incomplete or truncated lane set is not shown: a road layout is never cut short */
    if (!(l->present & RGD_LANE_INFORMATIONS) || !l->lane_complete || l->lane_count > MIBR_RGI_LANES_MAX) {
        g->seq++;
        return;
    }
    c->valid = 1;
    c->index = l->lane_guidance_index;
    c->count = l->lane_count;
    for (i = 0; i < c->count; i++) {
        c->position[i] = l->lanes[i].position;
        c->status[i] = l->lanes[i].status;
        c->highlight[i] = l->lanes[i].direction;
        c->angle_count[i] = l->lanes[i].angle_count > 4 ? 4 : l->lanes[i].angle_count;
        for (k = 0; k < c->angle_count[i]; k++) {
            c->angles[i][k] = l->lanes[i].angles[k];
        }
    }
    g->seq++;
}

struct text {
    char *p;
    size_t cap, n;
    int overflow;
};

static void put(struct text *t, const char *fmt, ...)
{
    va_list ap;
    int k;

    if (t->overflow) {
        return;
    }
    va_start(ap, fmt);
    k = vsnprintf(t->p + t->n, t->cap - t->n, fmt, ap);
    va_end(ap);
    if (k < 0 || (size_t)k >= t->cap - t->n) {
        t->overflow = 1;
        return;
    }
    t->n += (size_t)k;
}

size_t mibr_rgi_guidance_text(const struct mibr_rgi_guidance *g, int receiving, unsigned long heartbeat,
                              char *out, size_t cap)
{
    struct text t = {out, cap, 0, 0};
    const struct mibr_rgi_cached_maneuver *m = NULL;
    const struct mibr_rgi_cached_lanes *l = NULL;
    unsigned i, k;

    if (g->have_current) {
        m = &g->man[g->current_index % MIBR_RGI_CACHE];
        if (!m->valid || m->index != g->current_index) {
            m = NULL;
        }
    }
    if (g->lanes_showing) {
        l = &g->lanes[g->lane_index % MIBR_RGI_CACHE];
        if (!l->valid || l->index != g->lane_index) {
            l = NULL;
        }
    }
    put(&t, "MIBR_RGI/1\nseq=%u\nhb=%lu\nreceiving=%d\n", g->seq, heartbeat, receiving);
    put(&t, "route_state=%d\nmaneuver_state=%u\n", g->have_route_state ? (int)g->route_state : -1,
        g->maneuver_state);
    put(&t, "dist_man=%ld\ndist_rem=%ld\ntime_rem=%ld\n", g->have_dist_man ? (long)g->dist_to_maneuver : -1L,
        g->have_dist_rem ? (long)g->distance_remaining : -1L, g->have_time ? (long)g->time_remaining : -1L);
    put(&t, "road=%s\ndest=%s\n", g->road, g->destination);
    if (m) {
        put(&t, "man_index=%u\ntype=%u\nangle=%d\nside=%u\njunction=%u\nafter=%s\nangles=", m->index, m->type,
            m->exit_angle, m->driving_side, m->junction_type, m->after_road);
        for (i = 0; i < m->angle_count; i++) {
            put(&t, i ? ",%d" : "%d", m->angles[i]);
        }
        put(&t, "\n");
    } else {
        put(&t, "man_index=-1\n");
    }
    if (l) {
        put(&t, "lanes=%u\n", l->count);
        for (i = 0; i < l->count; i++) {
            put(&t, "lane%u=%u,%u,%d", i, l->position[i], l->status[i], l->highlight[i]);
            for (k = 0; k < l->angle_count[i]; k++) {
                put(&t, ",%d", l->angles[i][k]);
            }
            put(&t, "\n");
        }
    } else {
        put(&t, "lanes=0\n");
    }
    put(&t, "end=1\n");
    return t.overflow ? 0 : t.n;
}
