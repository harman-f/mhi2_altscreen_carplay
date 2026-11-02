/* SPDX-License-Identifier: GPL-3.0-or-later
 * iAP2 route guidance wire helpers shared by the mm-ipod library and the mibr-rgi helper.
 * Pure functions, no libc beyond string.h: host-testable.
 */
#ifndef MIBR_RGI_WIRE_H
#define MIBR_RGI_WIRE_H

#include <stddef.h>
#include <stdint.h>

#define MIBR_RGI_IDENT_GROUP   30u     /* RouteGuidanceDisplayComponent */
#define MIBR_RGI_COMPONENT_ID  1237u   /* unique: Location 1234, VehicleInformation 1235, VehicleStatus 1236 */
#define MIBR_RGI_COMPONENT_MAX 96u

#define MIBR_RGI_MSG_START     0x5200u
#define MIBR_RGI_MSG_UPDATE    0x5201u
#define MIBR_RGI_MSG_MANEUVER  0x5202u
#define MIBR_RGI_MSG_STOP      0x5203u
#define MIBR_RGI_MSG_LANES     0x5204u

/* Inner parameters of identification group 30 (packet_addparam_blob adds the outer header).
 * Layout as accepted by iOS per luka-dev/mib2q-carplay-rgi rgd_build_component_tlv:
 * 0 Identifier, 1 Name, 2-5 max string lengths, 6 maneuver capacity, 7 lane description length,
 * 8 lane capacity. Returns the byte count, 0 if cap is too small. */
size_t mibr_rgi_component(uint8_t *out, size_t cap);

/* Complete iAP2 control message (0x4040, length, id, params) for 0x5200 (start: component id plus
 * the empty sourceName/sourceSupportsRouteGuidance/supportsExitInfo requests) or 0x5203 (stop).
 * This is the buffer iap2_raw_msg_send expects. Returns the byte count, 0 if cap is too small. */
size_t mibr_rgi_start_message(uint8_t *out, size_t cap);
size_t mibr_rgi_stop_message(uint8_t *out, size_t cap);

/* Incremental reader for the driver's -l log. print_packet writes an unnamed control message as
 * "--?-- [msgid=52xx] CTRL[40 40 .. ..]" (hex may wrap). Feed raw log bytes; each complete 0x52xx
 * message found is passed to the callback as the full control message starting with 0x40 0x40. */
struct mibr_rgi_scan {
    int state;
    unsigned match;
    int nibble;
    size_t len;
    uint8_t msg[4096];
};
typedef void (*mibr_rgi_msg_cb)(void *ctx, const uint8_t *msg, size_t len);
void mibr_rgi_scan_reset(struct mibr_rgi_scan *s);
void mibr_rgi_scan_feed(struct mibr_rgi_scan *s, const char *data, size_t n, mibr_rgi_msg_cb cb, void *ctx);

#endif
