/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "alt111.h"
#include <assert.h>
#include <string.h>
#include <stdio.h>
int main(void)
{
    struct alt111_profile p,before;unsigned i;
    const unsigned widths[]={708,482,256},xs[]={151,264,377};
    alt111_profile_mu1440(&p,0);before=p;
    assert(alt111_profile_seat_mu1409_views(&p)==ALT111_OK);
    assert(alt111_profile_validate(&p)==ALT111_OK && p.view_count==3);
    assert(!memcmp(p.uuid,before.uuid,sizeof p.uuid) && p.type==before.type &&
           p.max_fps==before.max_fps && p.width_mm==before.width_mm &&
           p.height_mm==before.height_mm && p.features==before.features);
    for(i=0;i<3;i++){
        assert(p.views[i].area.width==1010 && p.views[i].area.height==376);
        assert(p.views[i].safe.x==xs[i] && p.views[i].safe.y==56);
        assert(p.views[i].safe.width==widths[i] && p.views[i].safe.height==244);
    }
    p.width=800;before=p;
    assert(alt111_profile_seat_mu1409_views(&p)==ALT111_INVALID && !memcmp(&p,&before,sizeof p));
    assert(alt111_profile_seat_mu1409_views(NULL)==ALT111_INVALID);
    alt111_profile_mu1440(&p,0);p.uuid[0]='z';before=p;
    assert(alt111_profile_seat_mu1409_views(&p)==ALT111_INVALID && !memcmp(&p,&before,sizeof p));
    alt111_profile_mu1440(&p,0);
    assert(p.view_count==1 && p.views[0].safe.width==1010);
    puts("SEAT_MU1409_VIEW_PROFILE_TEST=PASS");
    return 0;
}
