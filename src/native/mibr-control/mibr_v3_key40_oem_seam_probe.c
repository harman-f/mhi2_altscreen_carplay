/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host-only synthetic pre-dispatch invocation. This is NOT an OEM hook test.
 */
#include "mibr_v3_key40_oem_seam.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct spy{int n;int kbd[8],key[8],state[8];};
static int orig(void *v,int b,int k,int s){
    struct spy *p=(struct spy*)v;
    assert(p->n<8);p->kbd[p->n]=b;p->key[p->n]=k;
    p->state[p->n++]=s;return 0;
}
static int stock(void *v,struct mibr_v3_route_observation *out){
    (void)v;memset(out,0,sizeof(*out));out->confirmed=1;
    out->session=7;out->generation=8;out->visible=MIBR_ROUTE_STOCK110;
    return 0;
}
static int set(void *v,enum mibr_v3_visible_route target,
    const struct mibr_v3_route_observation *expected,const char *rid,
    struct mibr_v3_route_observation *out){
    (void)v;(void)target;(void)rid;*out=*expected;return 1;
}
int main(void){
    struct spy p={0};struct mibr_v3_key40_oem_seam s;
    struct mibr_v3_reader r={0};char out[16384];
    r.route_qualified=1;r.route_read=stock;r.route_set=set;
    assert(mibr_v3_key40_oem_seam_init(&s,&r,99,orig,&p,0,1,1)<0);
    assert(!s.enabled);
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    assert(p.n==1&&p.state[0]==1);p.n=0;
    assert(!mibr_v3_key40_oem_seam_init(&s,&r,99,orig,&p,1,1,1));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,41,1,out,sizeof(out)));
    assert(p.n==1&&p.key[0]==41);p.n=0;
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,0,out,sizeof(out)));
    assert(p.n==2&&p.state[0]==1&&p.state[1]==0);p.n=0;
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,3,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,4,out,sizeof(out)));
    assert(strstr(out,"MIBR/3 ")!=NULL);
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,4,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,5,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,0,out,sizeof(out)));
    assert(p.n==0); /* no OEM select on successful long */
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    r.route_qualified=0;
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,3,out,sizeof(out)));
    assert(p.n==0&&!s.enabled); /* buffered partial key never replayed */
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,0,out,sizeof(out)));
    /* A completed long press may lose qualification BEFORE KST5 and KST0.
     * Neither orphaned event may be forwarded to the OEM select consumer. */
    p.n=0;r.route_qualified=1;
    assert(!mibr_v3_key40_oem_seam_init(&s,&r,100,orig,&p,1,1,1));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,3,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,4,out,sizeof(out)));
    r.route_qualified=0;
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,5,out,sizeof(out)));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,0,out,sizeof(out)));
    assert(p.n==0);
    /* Explicit revocation of buffered initial press must likewise drain
     * its later release, instead of delivering OEM KST0 without KST1. */
    r.route_qualified=1;
    assert(!mibr_v3_key40_oem_seam_init(&s,&r,101,orig,&p,1,1,1));
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    mibr_v3_key40_oem_seam_revoke(&s);
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,0,out,sizeof(out)));
    assert(p.n==0);
    /* After the matching up, subsequent unqualified KEY40 is original OEM. */
    assert(!mibr_v3_key40_oem_seam_feed(&s,4,40,1,out,sizeof(out)));
    assert(p.n==1&&p.key[0]==40&&p.state[0]==1);
    printf("KEY40_NARROW_PRESELECT_HOST_ONLY_PASS\\n");return 0;
}
