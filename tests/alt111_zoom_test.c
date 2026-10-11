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
    assert(z.pending==0);
    assert(alt111_zoom_next(&z,81,500,&c)==ALT111_ZOOM_WAIT);
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
int main(void)
{
    test_measured_twelve();
    test_gating_and_reversal();
    test_bounds_session_and_failure();
    puts("alt111_zoom host PASS");
    return 0;
}
