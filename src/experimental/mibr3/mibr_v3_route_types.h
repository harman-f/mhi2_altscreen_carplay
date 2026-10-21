/* SPDX-License-Identifier: GPL-3.0-or-later
 * Standalone interface shared by the public host-only owner-policy examples.
 * An observed physical VC route must come from a qualified independent provider.
 */
#ifndef MIBR_V3_ROUTE_TYPES_H
#define MIBR_V3_ROUTE_TYPES_H
#include <stdint.h>
enum mibr_v3_visible_route {
    MIBR_ROUTE_UNKNOWN=0,
    MIBR_ROUTE_STOCK110=110,
    MIBR_ROUTE_DIRECT111=111
};
struct mibr_v3_route_observation {
    enum mibr_v3_visible_route visible;
    uint64_t session, generation;
    int confirmed;
    char ack_request_id[65];
};
#endif
