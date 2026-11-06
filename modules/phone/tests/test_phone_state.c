/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/mibr_phone_state.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    mibr_phone_state p;
    mibr_phone_init(&p);
    mibr_phone_set_enabled(&p,1);
    mibr_phone_begin(&p,8);
    assert(mibr_phone_update(&p,8,19,MIBR_CALL_RINGING,"Name","123",1));
    assert(mibr_phone_can_request(&p,8,19,MIBR_CALL_ACCEPT));
    assert(!mibr_phone_can_request(&p,8,18,MIBR_CALL_HANGUP));
    assert(!mibr_phone_can_request(&p,9,19,MIBR_CALL_ACCEPT));
    assert(mibr_phone_update(&p,8,19,MIBR_CALL_ACTIVE,"Name","123",1));
    assert(!mibr_phone_can_request(&p,8,19,MIBR_CALL_ACCEPT));
    assert(mibr_phone_can_request(&p,8,19,MIBR_CALL_HANGUP));
    assert(mibr_phone_update(&p,8,0,MIBR_CALL_NONE,0,0,0));
    assert(!mibr_phone_can_request(&p,8,19,MIBR_CALL_HANGUP));
    assert(!p.display_name[0]);
    assert(mibr_phone_update(&p,8,22,MIBR_CALL_RINGING,"Private","123",1));
    mibr_phone_set_enabled(&p,0);
    assert(!p.display_name[0]);
    assert(!mibr_phone_can_request(&p,8,22,MIBR_CALL_ACCEPT));
    mibr_phone_set_enabled(&p,1);
    assert(mibr_phone_update(&p,8,22,MIBR_CALL_RINGING,"Name","123",0));
    assert(!mibr_phone_can_request(&p,8,22,MIBR_CALL_ACCEPT));
    mibr_phone_end(&p,7);
    assert(p.connected);
    mibr_phone_end(&p,8);
    assert(!p.connected);
    puts("PHONE_STATE_HOST_TEST=PASS");
    return 0;
}
