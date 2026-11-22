/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/mibr_media_ingress.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 mibr_media_ingress m; mibr_media_state view;
 mibr_media_ingress_init(&m);
 assert(!mibr_media_ingress_attach(&m,5,9,0,1)); /* no exact ABI */
 assert(!mibr_media_ingress_attach(&m,5,9,1,0)); /* no ASL affinity */
 assert(mibr_media_ingress_attach(&m,5,9,1,1));
 assert(!mibr_media_ingress_snapshot(&m,5,&view)); /* no broker consent */
 assert(!mibr_media_ingress_track(&m,5,9,"A","B","C",31));
 mibr_media_ingress_enable(&m,1);
 assert(mibr_media_ingress_track(&m,5,9,"A","B","C",31)==2);
 assert(mibr_media_ingress_snapshot(&m,5,&view));
 assert(view.track_epoch==1 && !mibr_media_show_cover(&view));
 assert(!mibr_media_ingress_cover(&m,4,9,1,31)); /* prior owner */
 assert(mibr_media_ingress_cover(&m,5,9,1,31));
 assert(mibr_media_ingress_snapshot(&m,5,&view)&&mibr_media_show_cover(&view));
 assert(mibr_media_ingress_track(&m,5,9,"New","B","C",32)==2);
 assert(!mibr_media_ingress_cover(&m,5,9,1,31)); /* old artwork */
 mibr_media_ingress_detach(&m,4,9);
 assert(mibr_media_ingress_snapshot(&m,5,&view)); /* stale detach ignored */
 mibr_media_ingress_detach(&m,5,9);
 assert(!mibr_media_ingress_snapshot(&m,5,&view));
 assert(!mibr_media_ingress_attach(&m,5,9,1,1)); /* replayed generation */
 assert(mibr_media_ingress_attach(&m,6,10,1,1));
 assert(!mibr_media_ingress_track(&m,5,9,"Late",0,0,33));
 assert(!mibr_media_ingress_cover(&m,5,9,1,31));
 assert(mibr_media_ingress_track(&m,6,10,"A","B","C",33)==2);
 mibr_media_ingress_enable(&m,0);
 assert(!mibr_media_ingress_snapshot(&m,6,&view));
 puts("MEDIA_OWNER_INGRESS_HOST_TEST=PASS");
 return 0;
}
