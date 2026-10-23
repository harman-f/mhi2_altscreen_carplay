/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "alt111_policy.h"
#include <string.h>

void alt111_policy_defaults(struct alt111_policy_config *c)
{
    memset(c, 0, sizeof(*c));
    c->mode = ALT111_SOURCE_FRAMES;
    c->interval_frames = 20; c->interval_ms = 2000;
    c->showui = c->gap_recovery = c->latency_recovery = 1;
}

int alt111_policy_configure(struct alt111_policy *p,
                           const struct alt111_policy_config *c)
{
    if (!p || !c || c->mode > ALT111_PERIODIC_OFF ||
        !c->interval_frames || c->interval_frames > 1000 ||
        c->interval_ms < 100 || c->interval_ms > 60000 ||
        c->showui > 1 || c->gap_recovery > 1 || c->latency_recovery > 1)
        return -1;
    if (!p->configured || p->config.mode != c->mode ||
        p->config.interval_ms != c->interval_ms) {
        p->have_time = 0; p->phase = 0;
    }
    p->config = *c; p->configured = 1;
    return 0;
}

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

unsigned alt111_policy_au(struct alt111_policy *p, uint64_t stream,
                          uint64_t ordinal, const uint8_t raw[8],
                          unsigned present, uint64_t arrival_us)
{
    uint64_t time, delta, delta_us, wall, threshold, phase;
    unsigned reason = 0;
    if (!p || !p->configured || !ordinal) return 0;
    if (p->stream != stream) {
        p->stream = stream; p->have_time = 0; p->phase = 0;
    }
    if (p->config.mode == ALT111_SOURCE_FRAMES &&
        ordinal % p->config.interval_frames == 0) {
        ++p->frames_opportunities; reason = ALT111_KF_PERIODIC_FRAMES;
    }
    p->source_time_available = present && raw != 0;
    if (!p->source_time_available) {
        p->have_time = 0; p->phase = 0;
        return reason;
    }
    time = ((uint64_t)le32(raw + 4) << 32) | le32(raw);
    if (!p->have_time) {
        p->previous_time = time; p->previous_arrival_us = arrival_us;
        p->have_time = 1; return reason;
    }
    /* Unsigned subtraction preserves the seconds-word rollover. A half-cycle
     * or backward step is deliberately ambiguous, never a huge deadline. */
    delta = time - p->previous_time;
    wall = arrival_us - p->previous_arrival_us;
    delta_us = (delta >> 32) * 1000000u +
               (((delta & UINT32_MAX) * 1000000u) >> 32);
    if (delta > INT64_MAX || arrival_us < p->previous_arrival_us ||
        wall > UINT64_MAX - 500000u || delta_us > wall + 500000u) {
        p->phase = 0; ++p->clock_resets;
    } else if (p->config.mode == ALT111_SOURCE_TIME) {
        threshold = (((uint64_t)p->config.interval_ms << 32) + 999u) / 1000u;
        phase = p->phase + delta;
        if (phase >= threshold) {
            ++p->time_opportunities; reason = ALT111_KF_PERIODIC_TIME;
        }
        /* At most one request for an AU; missed periods never create a burst. */
        p->phase = phase % threshold;
    }
    p->previous_time = time; p->previous_arrival_us = arrival_us;
    return reason;
}

unsigned alt111_policy_event(const struct alt111_policy_config *c,
                             unsigned reasons)
{
    reasons &= ALT111_KF_ALL;
    if (!c) return reasons & (ALT111_KF_BRIDGE_READY | ALT111_KF_LIFECYCLE_RESET);
    if (!c->showui) reasons &= ~ALT111_KF_SHOWUI;
    if (!c->gap_recovery) reasons &= ~ALT111_KF_SOURCE_GAP;
    if (!c->latency_recovery) reasons &= ~ALT111_KF_LATENCY_RECOVERY;
    return reasons;
}

const char *alt111_keyframe_reason_name(unsigned reason)
{
    switch (reason) {
    case ALT111_KF_PERIODIC_FRAMES: return "periodic_frames";
    case ALT111_KF_PERIODIC_TIME: return "periodic_time";
    case ALT111_KF_SHOWUI: return "showui";
    case ALT111_KF_BRIDGE_READY: return "bridge_ready";
    case ALT111_KF_SOURCE_GAP: return "source_gap";
    case ALT111_KF_LATENCY_RECOVERY: return "latency_recovery";
    case ALT111_KF_LIFECYCLE_RESET: return "lifecycle_reset";
    case ALT111_KF_MANUAL: return "manual";
    default: return "invalid";
    }
}
