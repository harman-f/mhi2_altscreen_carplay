/* SPDX-License-Identifier: GPL-3.0-or-later
 * Merged route guidance state of one iAP2 connection and its text snapshot for the HMI.
 * Host-testable: no I/O here.
 */
#ifndef MIBR_RGI_GUIDANCE_H
#define MIBR_RGI_GUIDANCE_H

#include <stddef.h>
#include <stdint.h>

#include "routeguidance/rgd_tlv.h"

#define MIBR_RGI_CACHE 32u
#define MIBR_RGI_LANES_MAX 8u

struct mibr_rgi_cached_maneuver {
    int valid;
    unsigned index;
    unsigned type;
    int exit_angle;
    unsigned driving_side;
    unsigned junction_type;
    int angles[MAX_MANEUVER_LIST];
    unsigned angle_count;
    char after_road[128];
};

struct mibr_rgi_cached_lanes {
    int valid;
    unsigned index;
    unsigned count;
    unsigned position[MIBR_RGI_LANES_MAX];
    unsigned status[MIBR_RGI_LANES_MAX];
    int highlight[MIBR_RGI_LANES_MAX];
    int angles[MIBR_RGI_LANES_MAX][4];
    unsigned angle_count[MIBR_RGI_LANES_MAX];
};

struct mibr_rgi_guidance {
    unsigned seq;
    unsigned route_state, maneuver_state;
    int have_route_state;
    uint32_t distance_remaining, dist_to_maneuver;
    uint64_t time_remaining;
    int have_dist_rem, have_dist_man, have_time; /* unknown values are written as -1 */
    unsigned current_index;   /* first entry of the 0x5201 maneuver list */
    int have_current;
    unsigned lane_index;
    int lanes_showing;
    char road[128], destination[128];
    struct mibr_rgi_cached_maneuver man[MIBR_RGI_CACHE];
    struct mibr_rgi_cached_lanes lanes[MIBR_RGI_CACHE];
};

void mibr_rgi_guidance_reset(struct mibr_rgi_guidance *g);
void mibr_rgi_guidance_update(struct mibr_rgi_guidance *g, const rgd_update_t *u);
void mibr_rgi_guidance_maneuver(struct mibr_rgi_guidance *g, const rgd_maneuver_t *m);
void mibr_rgi_guidance_lanes(struct mibr_rgi_guidance *g, const rgd_lane_guidance_t *l);

/* Writes the snapshot ("MIBR_RGI/1" then key=value lines) for the HMI. Returns the length, 0 if
 * it did not fit. Strings are cut at the first newline. */
size_t mibr_rgi_guidance_text(const struct mibr_rgi_guidance *g, int receiving, unsigned long heartbeat,
                              char *out, size_t cap);

#endif
