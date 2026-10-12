#include "alt111_zoom.h"
#include <assert.h>
#include <stdio.h>

static void context(struct alt111_zoom *z, uint64_t session)
{
    assert(alt111_zoom_polarity(z,session,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_context(z,session,1,1,1)==ALT111_ZOOM_OK);
}
static void test_measured_twelve(void)
{
    struct alt111_zoom z; struct alt111_zoom_command c;
    int i,sign,dir; uint64_t now=1000;
    alt111_zoom_init(&z);alt111_zoom_begin(&z,77);context(&z,77);
    /* Actual twelve field vectors, right +/- x3, left +/- x3. */
    for(sign=1;sign>=-1;sign-=2){
        for(i=0;i<3;i++){
            assert(alt111_zoom_encoder(&z,77,4,40,sign,0,1)==ALT111_ZOOM_OK);
            assert(alt111_zoom_next(&z,77,now,&c)==ALT111_ZOOM_OK);
            dir=sign>0?ALT111_ZOOM_IN:ALT111_ZOOM_OUT;
            assert(c.direction==(unsigned)dir);
            assert(alt111_zoom_complete(&z,77,c.request,1,now+1)==ALT111_ZOOM_OK);
            assert(z.pending==0);now+=150;
        }
    }
    for(sign=1;sign>=-1;sign-=2)for(i=0;i<3;i++)
        assert(alt111_zoom_encoder(&z,77,4,44,sign,0,1)==ALT111_ZOOM_WAIT);
    assert(z.accepted==6 && z.rejected==6 && z.completed==6);
}
static void test_gating_and_reversal(void)
{
    struct alt111_zoom z;struct alt111_zoom_command c;
    alt111_zoom_init(&z);alt111_zoom_begin(&z,81);
    assert(alt111_zoom_encoder(&z,81,4,40,1,0,1)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_polarity(&z,81,0)==ALT111_ZOOM_OK);
    assert(alt111_zoom_context(&z,81,1,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_encoder(&z,81,4,40,1,0,1)==ALT111_ZOOM_WAIT);
    context(&z,81);
    assert(alt111_zoom_encoder(&z,81,4,40,1,0,0x81)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_encoder(&z,81,4,40,1,1,1)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_encoder(&z,81,4,40,0,0,1)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_encoder(&z,81,4,40,17,0,1)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_encoder(&z,81,4,40,1,0,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_next(&z,81,200,&c)==ALT111_ZOOM_OK);
    assert(c.direction==ALT111_ZOOM_IN);
    /* Opposite input while a +step command is in flight must queue
     * a compensating -step after its accepted completion. */
    assert(alt111_zoom_encoder(&z,81,4,40,-1,0,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_complete(&z,81,c.request,1,201)==ALT111_ZOOM_OK);
    assert(z.pending==-1);
    assert(alt111_zoom_next(&z,81,300,&c)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_next(&z,81,342,&c)==ALT111_ZOOM_OK);
    assert(c.direction==ALT111_ZOOM_OUT);
    assert(alt111_zoom_complete(&z,81,c.request,1,343)==ALT111_ZOOM_OK);
    assert(z.pending==0);
    assert(alt111_zoom_encoder(&z,81,4,40,2,0,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_context(&z,81,0,1,1)==ALT111_ZOOM_OK);
    assert(z.pending==0 && z.vc_map_focus==0 && z.owner==0);
    /* Reacquired picture is not renewed focus/owner proof. */
    assert(alt111_zoom_context(&z,81,z.vc_map_focus,1,z.owner)==ALT111_ZOOM_OK);
    assert(alt111_zoom_encoder(&z,81,4,40,1,0,1)==ALT111_ZOOM_WAIT);
    assert(alt111_zoom_next(&z,81,500,&c)==ALT111_ZOOM_WAIT);
    context(&z,81);
    assert(alt111_zoom_encoder(&z,81,4,40,1,0,1)==ALT111_ZOOM_OK);
}
static void test_bounds_session_and_failure(void)
{
    struct alt111_zoom z;struct alt111_zoom_command c;int i;
    alt111_zoom_init(&z);alt111_zoom_begin(&z,1);context(&z,1);
    for(i=0;i<20;i++)assert(alt111_zoom_encoder(&z,1,4,40,1,0,1)==ALT111_ZOOM_OK);
    assert(z.pending==ALT111_ZOOM_BACKLOG && z.dropped==8);
    assert(alt111_zoom_next(&z,1,0,&c)==ALT111_ZOOM_OK);
    assert(alt111_zoom_complete(&z,1,c.request,0,1)==ALT111_ZOOM_OK);
    assert(z.pending==0 && z.failed==1);
    assert(alt111_zoom_complete(&z,1,c.request,1,2)==ALT111_ZOOM_STALE);
    assert(alt111_zoom_encoder(&z,1,4,40,-1,0,1)==ALT111_ZOOM_OK);
    alt111_zoom_end(&z);
    assert(alt111_zoom_next(&z,1,999,&c)==ALT111_ZOOM_STALE);
    alt111_zoom_begin(&z,2);
    assert(alt111_zoom_encoder(&z,1,4,40,1,0,1)==ALT111_ZOOM_STALE);
    assert(alt111_zoom_next(&z,2,1000,&c)==ALT111_ZOOM_WAIT);
}
static void test_native_zoom_selective_routing(void)
{
    struct alt111_zoom z;
    struct alt111_zoom_command cmd;
    int i;
    alt111_zoom_init(&z);
    alt111_zoom_begin(&z,55);
    assert(alt111_zoom_polarity(&z,55,1)==ALT111_ZOOM_OK);

    /* Stream exists, but no verified VC map focus or DIRECT owner. */
    assert(alt111_zoom_context(&z,55,0,1,0)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    assert(z.pending==0);

    /* Actual CarPlay map visible + focus/owner, but origin not proven. */
    assert(alt111_zoom_context(&z,55,1,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,55,0,4,40,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    /* Left volume, key/encoder confusion and bad validity can never redirect. */
    assert(alt111_zoom_route_map_action(&z,55,1,4,44,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,0x81)==ALT111_ZOOM_ROUTE_STOCK);
    assert(z.pending==0);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_CARPLAY);
    assert(z.pending==1);
    assert(alt111_zoom_next(&z,55,1000,&cmd)==ALT111_ZOOM_OK);
    assert(cmd.direction==ALT111_ZOOM_IN);
    assert(alt111_zoom_complete(&z,55,cmd.request,1,1001)==ALT111_ZOOM_OK);

    /* In VC menu with running 111, stock menu input must retain ownership. */
    assert(alt111_zoom_context(&z,55,0,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    assert(z.pending==0 && z.owner==0);

    /* Freshly confirmed map focus, then loss of native/direct ownership. */
    assert(alt111_zoom_context(&z,55,1,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,-1,0,1)==ALT111_ZOOM_ROUTE_CARPLAY);
    assert(z.pending==-1);
    assert(alt111_zoom_context(&z,55,1,1,0)==ALT111_ZOOM_OK);
    assert(z.pending==0);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,-1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    /* Source re-appearing does not magically revalidate focus/owner. */
    assert(alt111_zoom_context(&z,55,z.vc_map_focus,1,z.owner)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,-1,0,1)==ALT111_ZOOM_ROUTE_STOCK);

    assert(alt111_zoom_context(&z,55,1,1,1)==ALT111_ZOOM_OK);
    for(i=0;i<ALT111_ZOOM_BACKLOG;i++)
        assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_CARPLAY);
    assert(z.pending==ALT111_ZOOM_BACKLOG);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    assert(z.pending==ALT111_ZOOM_BACKLOG);
    alt111_zoom_end(&z);
    assert(alt111_zoom_route_map_action(&z,55,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
}


/* Sanitized chronological evidence from native-41771151 / vc-r2-capture-41648264:
 * five +1, then six -1 right-wheel detents. Each has one f904/tag56
 * correlation and DSIBAP(50,45) indication/request/ack trio. Scale-like
 * values are evidence only, not a proven OEM BAP units/field ABI.
 *
 * This exercises the *routing policy* with synthetic semantic_action_verified=1.
 * It DOES NOT claim an exact MU1440 Java callsite or vehicle suppression.
 */
static void test_measured_eleven_scale_route(void)
{
    static const int signed_detent[11] =
        { 1,1,1,1,1,-1,-1,-1,-1,-1,-1 };
    static const int scale_like[11] =
        { 4000,3000,2000,1500,1000,1500,2000,3000,4000,5000,7500 };
    struct alt111_zoom z;
    struct alt111_zoom_command cmd;
    uint64_t now = 1000;
    int i;
    alt111_zoom_init(&z);
    alt111_zoom_begin(&z, 91);
    context(&z, 91);
    for (i=0; i<11; ++i) {
        if (i) {
            if (signed_detent[i]>0) assert(scale_like[i]<scale_like[i-1]);
            else assert(scale_like[i]>scale_like[i-1]);
        }
        /* One authoritative semantic route, not an extra raw encoder enqueue. */
        assert(alt111_zoom_route_map_action(&z,91,1,4,40,
                signed_detent[i],0,1)==ALT111_ZOOM_ROUTE_CARPLAY);
        assert(z.pending==signed_detent[i]);
        assert(alt111_zoom_next(&z,91,now,&cmd)==ALT111_ZOOM_OK);
        assert(cmd.direction==(signed_detent[i]>0 ?
                ALT111_ZOOM_IN:ALT111_ZOOM_OUT));
        assert(alt111_zoom_complete(&z,91,cmd.request,1,now+1)==ALT111_ZOOM_OK);
        assert(z.pending==0);
        now+=150;
    }
    assert(z.accepted==11 && z.completed==11 && z.sent==11);
    /* Same physical detent while the VC menu is active must remain OEM. */
    assert(alt111_zoom_context(&z,91,0,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,91,1,4,40,1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    assert(z.pending==0);
    /* Returning to visible native/STOCK never consumes its map zoom. */
    assert(alt111_zoom_context(&z,91,1,1,0)==ALT111_ZOOM_OK);
    assert(alt111_zoom_route_map_action(&z,91,1,4,40,-1,0,1)==ALT111_ZOOM_ROUTE_STOCK);
    assert(z.pending==0);
}

int main(void)
{
    test_measured_twelve();
    test_gating_and_reversal();
    test_bounds_session_and_failure();
    test_native_zoom_selective_routing();
    test_measured_eleven_scale_route();
    puts("alt111_zoom host PASS");
    return 0;
}
