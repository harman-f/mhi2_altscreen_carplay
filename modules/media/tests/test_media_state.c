/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/mibr_media_state.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    mibr_media_state s;
    mibr_media_init(&s);
    mibr_media_set_enabled(&s,1);
    mibr_media_begin(&s,41);
    assert(mibr_media_track(&s,41,"Track A","Artist","Album",17)==2);
    unsigned int e=s.track_epoch;
    assert(mibr_media_cover_ready(&s,41,e,17));
    assert(mibr_media_show_cover(&s));
    assert(mibr_media_track(&s,41,"Track A","Artist","Album",17)==1);
    assert(mibr_media_track(&s,41,"Track B","Artist","Album",18)==2);
    assert(!mibr_media_show_cover(&s));
    assert(!mibr_media_cover_ready(&s,41,e,17)); /* delayed old image */
    assert(!mibr_media_cover_ready(&s,40,s.track_epoch,18)); /* old session */
    assert(mibr_media_cover_ready(&s,41,s.track_epoch,18));
    mibr_media_set_enabled(&s,0);
    assert(!mibr_media_show_cover(&s));
    assert(!mibr_media_cover_ready(&s,41,s.track_epoch,18));
    mibr_media_set_enabled(&s,1);
    assert(!mibr_media_show_cover(&s)); /* same artwork may be re-published */
    mibr_media_end(&s,40); /* old disconnect must not clear current */
    assert(s.connected);
    mibr_media_end(&s,41);
    assert(!s.connected && !mibr_media_show_cover(&s));
    mibr_media_begin(&s,42);
    assert(!mibr_media_show_cover(&s));
    assert(!mibr_media_track(&s,41,"late",0,0,1));
    puts("MEDIA_STATE_HOST_TEST=PASS");
    return 0;
}
