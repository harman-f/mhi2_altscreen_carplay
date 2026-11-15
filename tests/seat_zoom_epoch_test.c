/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "seat_zoom_epoch.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    struct seat_zoom_epoch e={0};
    assert(seat_zoom_epoch_update(&e,1,2,3,4,1,1000));
    assert(!seat_zoom_epoch_update(&e,1,2,3,4,1,1100));
    assert(seat_zoom_epoch_fresh(&e,1001,1100));
    assert(!seat_zoom_epoch_fresh(&e,999,1100));
    assert(!seat_zoom_epoch_fresh(&e,1001,1600));
    assert(!seat_zoom_epoch_fresh(&e,1200,1100));
    assert(seat_zoom_epoch_update(&e,1,2,3,5,1,1200));
    assert(!seat_zoom_epoch_fresh(&e,1199,1200));
    assert(seat_zoom_epoch_update(&e,1,2,3,5,0,1300));
    assert(!seat_zoom_epoch_fresh(&e,1300,1300));
    assert(seat_zoom_epoch_update(&e,2,6,7,8,1,1400));
    assert(seat_zoom_epoch_fresh(&e,1401,1450));
    assert(seat_zoom_epoch_update(&e,3,9,10,11,1,0xfffffff0u));
    assert(seat_zoom_epoch_fresh(&e,5u,10u));
    puts("SEAT_ZOOM_EPOCH_TEST=PASS");return 0;
}
