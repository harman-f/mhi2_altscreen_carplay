/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_phone_state.h"
#include <string.h>
static void text_copy(char *dst,const char *src) {
    size_t n;
    if (!src) src = "";
    n = strlen(src);
    if (n >= MIBR_PHONE_TEXT_CAP) n = MIBR_PHONE_TEXT_CAP-1;
    memcpy(dst,src,n); dst[n]=0;
}
void mibr_phone_init(mibr_phone_state *s) { if (s) memset(s,0,sizeof(*s)); }
void mibr_phone_begin(mibr_phone_state *s, uint32_t session) {
    if (!s || !session) return;
    int enabled=s->phone_enabled;
    memset(s,0,sizeof(*s)); s->session=session; s->connected=1; s->phone_enabled=enabled;
}
void mibr_phone_set_enabled(mibr_phone_state *s, int enabled) {
    if (!s) return;
    s->phone_enabled=enabled!=0;
    if (!s->phone_enabled) {
        s->status=MIBR_CALL_NONE; s->call_id=0; s->carplay_phone_owner=0;
        s->display_name[0]=0; s->display_number[0]=0;
    }
}
int mibr_phone_update(mibr_phone_state *s, uint32_t session, uint32_t call_id,
                      enum mibr_call_status status, const char *name, const char *number,
                      int carplay_phone_owner) {
    if (!s || !s->connected || !session || session!=s->session
        || status < MIBR_CALL_NONE || status > MIBR_CALL_HELD) return 0;
    if (status == MIBR_CALL_NONE || !s->phone_enabled || !carplay_phone_owner) {
        s->status=MIBR_CALL_NONE; s->call_id=0; s->carplay_phone_owner=0;
        s->display_name[0]=0; s->display_number[0]=0;
        return 1;
    }
    if (!call_id) return 0;
    s->call_id=call_id; s->status=status; s->carplay_phone_owner=1;
    text_copy(s->display_name,name); text_copy(s->display_number,number);
    return 1;
}
int mibr_phone_can_request(const mibr_phone_state *s, uint32_t session, uint32_t call_id,
                           enum mibr_call_action action) {
    if (!s || !s->connected || !s->phone_enabled || !s->carplay_phone_owner
        || !session || session!=s->session || !call_id || call_id!=s->call_id) return 0;
    if (action == MIBR_CALL_ACCEPT) return s->status == MIBR_CALL_RINGING;
    if (action == MIBR_CALL_HANGUP) return s->status == MIBR_CALL_RINGING
           || s->status == MIBR_CALL_DIALING || s->status == MIBR_CALL_ACTIVE
           || s->status == MIBR_CALL_HELD;
    return 0;
}
void mibr_phone_end(mibr_phone_state *s, uint32_t session) {
    if (!s || !session || session!=s->session) return;
    int enabled=s->phone_enabled;
    memset(s,0,sizeof(*s)); s->phone_enabled=enabled;
}
