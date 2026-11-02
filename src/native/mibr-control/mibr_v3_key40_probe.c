/* SPDX-License-Identifier: GPL-3.0-or-later
 * Independent plain host test, no native IO or OEM suppression claim.
 */
#include "mibr_v3_key40.h"
#include <assert.h>
#include <stdio.h>
static void seq(struct mibr_key40 *s,const int *states,const int *wanted,unsigned n){
    unsigned i;for(i=0;i<n;i++)assert((int)mibr_key40_feed(s,4,40,states[i])==wanted[i]);
}
int main(void){
    struct mibr_key40 s;unsigned i;
    const int short_states[]={1,0},short_result[]={0,1};
    const int long_states[]={1,3,4,5,0},long_result[]={0,0,2,0,0};
    const int repeat_states[]={1,1,3,3,4,4,5,5,0};
    const int repeat_result[]={0,0,0,0,2,0,0,0,0};
    const int aborted[]={1,3,0},aborted_result[]={0,0,0};
    const int invalid[]={1,5,4,0},invalid_result[]={0,-1,-1,0};
    mibr_key40_reset(&s);seq(&s,short_states,short_result,2);
    seq(&s,long_states,long_result,5);
    seq(&s,repeat_states,repeat_result,9);
    seq(&s,aborted,aborted_result,3);
    seq(&s,invalid,invalid_result,4);
    assert(mibr_key40_feed(&s,4,41,1)==MIBR_KEY40_NONE);
    assert(mibr_key40_feed(&s,4,41,3)==MIBR_KEY40_NONE);
    assert(mibr_key40_feed(&s,4,41,4)==MIBR_KEY40_NONE);
    assert(mibr_key40_feed(&s,4,41,0)==MIBR_KEY40_NONE);
    seq(&s,long_states,long_result,5);
    assert(mibr_key40_feed(&s,4,40,4)==MIBR_KEY40_INVALID);
    for(i=0;i<100;i++){seq(&s,long_states,long_result,5);seq(&s,short_states,short_result,2);}
    puts("KEY40_KST4_ONCE_PASS");return 0;
}
