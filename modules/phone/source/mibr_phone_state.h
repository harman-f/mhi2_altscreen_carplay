/* SPDX-License-Identifier: GPL-3.0-or-later
 * Pure call state. No OEM classes, iAP2 write API or phone commands.
 */
#ifndef MIBR_PHONE_STATE_H
#define MIBR_PHONE_STATE_H
#include <stdint.h>
#define MIBR_PHONE_TEXT_CAP 128
enum mibr_call_status { MIBR_CALL_NONE=0, MIBR_CALL_RINGING=1,
                        MIBR_CALL_DIALING=2, MIBR_CALL_ACTIVE=3, MIBR_CALL_HELD=4 };
enum mibr_call_action { MIBR_CALL_ACCEPT=1, MIBR_CALL_HANGUP=2 };
typedef struct {
    uint32_t session, call_id;
    enum mibr_call_status status;
    int connected, phone_enabled, carplay_phone_owner;
    char display_name[MIBR_PHONE_TEXT_CAP];
    char display_number[MIBR_PHONE_TEXT_CAP];
} mibr_phone_state;
void mibr_phone_init(mibr_phone_state *s);
void mibr_phone_begin(mibr_phone_state *s, uint32_t session);
void mibr_phone_set_enabled(mibr_phone_state *s, int enabled);
int mibr_phone_update(mibr_phone_state *s, uint32_t session, uint32_t call_id,
                      enum mibr_call_status status, const char *name, const char *number,
                      int carplay_phone_owner);
int mibr_phone_can_request(const mibr_phone_state *s, uint32_t session, uint32_t call_id,
                           enum mibr_call_action action);
void mibr_phone_end(mibr_phone_state *s, uint32_t session);
#endif
