/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_v3_key40_oem_seam.h"
#include <string.h>
static int forward(struct mibr_v3_key40_oem_seam *s,int kbd,int key,int state){
    return s->original(s->original_context,kbd,key,state);
}
int mibr_v3_key40_oem_seam_init(struct mibr_v3_key40_oem_seam *s,
    struct mibr_v3_reader *r,uint64_t epoch,mibr_oem_key2_forward original,
    void *ctx,int slot24,int pre_select,int sole){
    if(!s)return -1;
    memset(s,0,sizeof(*s));
    s->original=original;s->original_context=ctx;s->reader=r;
    mibr_v3_input_init(&s->input,epoch);
    if(!original||slot24!=1||pre_select!=1||sole!=1||!r||
       !r->route_qualified||!r->route_read||!r->route_set||
       mibr_v3_input_arm(&s->input,1))return -1;
#if defined(__QNXNTO__)
    /* Stage-5 logical three-field model is NOT the actual five-int
     * DSIKeyPanelDispatcher updateKey2 ABI (includes arg4 + 0x80
     * confirmation in arg5). Its original fan-out/AID-local consumer is
     * not qualified. Never activate this approximation on MU1440 even if
     * synthetic opt-in flags are accidentally passed as true. */
    mibr_v3_input_revoke(&s->input);
    return -1;
#endif
    s->enabled=1;return 0;
}
void mibr_v3_key40_oem_seam_revoke(struct mibr_v3_key40_oem_seam *s){
    if(!s)return;
    /* Revocation mid-press must still swallow its orphaned release.
     * Preserve that safety latch until a physical KST0 is observed. */
    if(s->buffered||s->drop_until_release||s->input.key40.phase!=0)
        s->drop_until_release=1;
    s->enabled=0;s->buffered=0;
    mibr_v3_input_revoke(&s->input);
}
int mibr_v3_key40_oem_seam_feed(struct mibr_v3_key40_oem_seam *s,
    int kbd,int key,int kst,char *out,size_t cap){
    enum mibr_v3_input_result result;
    if(!s||!s->original||!out||!cap)return -1;
    out[0]=0;
    /* This is an identity-specific pre-dispatch decision: never delay any
     * OEM KEY41, encoder, volume or other family. */
    if(kbd!=4||key!=40)return forward(s,kbd,key,kst);
    if(s->drop_until_release){
        if(kst==0){s->drop_until_release=0;mibr_key40_reset(&s->input.key40);}
        return 0;
    }
    if(!s->enabled)return forward(s,kbd,key,kst);
    /* If proof disappears after KEY40-down has been buffered, drop this
     * incomplete gesture, not a partial synthetic OEM long press. */
    if(!s->reader||!s->reader->route_qualified||!s->reader->route_read||
       !s->reader->route_set){
        mibr_v3_input_revoke(&s->input);
        s->enabled=0;
        if(s->buffered){s->buffered=0;s->drop_until_release=(kst!=0);return 0;}
        return forward(s,kbd,key,kst);
    }
    if(kst==1&&s->input.key40.phase==0)s->buffered=1;
    result=mibr_v3_input_key2(&s->input,s->reader,kbd,key,kst,out,cap);
    if(result==MIBR_INPUT_OEM_SHORT){
        int rc;
        s->buffered=0;
        /* Original short consumer receives original family events exactly
         * once, in original order, only when a verified release occurred.
         * If the original callback fails, never auto-replay half a press. */
        rc=forward(s,kbd,key,1);
        if(!rc)rc=forward(s,kbd,key,0);
        if(rc)mibr_v3_key40_oem_seam_revoke(s);
        return rc;
    }
    if(result==MIBR_INPUT_ACTION){
        /* The action fires on KST4, not release. Once consumed, never
         * forward KST4-repeat/KST5/up to the OEM as an orphaned key even
         * if route qualification disappears before physical release. */
        s->buffered=0;s->drop_until_release=1;
        return 0;
    }
    if(result==MIBR_INPUT_NONE)return 0;
    /* Malformed/transport-loss KEY40 cannot be interpreted as a route
     * toggle. Do not replay partial down/long to the OEM dispatcher. */
    s->buffered=0;s->drop_until_release=(kst!=0);
    mibr_key40_reset(&s->input.key40);
    return 0;
}
