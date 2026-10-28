/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
struct mock_display { int zoom_present; int64_t zoom; int width, height; };
typedef struct mock_display *CFMutableDictionaryRef;
static int allocation_fails;
static int set_i64(CFMutableDictionaryRef d,const char *key,int64_t value)
{
    assert(!strcmp(key,"zoomFactor"));
    if(allocation_fails)return -1;
    d->zoom_present=1;d->zoom=value;return 0;
}
static void logf_u2(const char *fmt,...){(void)fmt;}
#include "../src/native/altscreen111-gen2/aux_zoom_factor.inc"
int main(void)
{
    struct mock_display primary={0,0,800,480},aux={0,0,1010,376};
    const char *bad[]={"69","151","-70","+70","70.0","70x"," 70","70 ","999999999999999999999999"};
    unsigned i;
    assert(!unsetenv("ALTSCREEN111_ZOOM_FACTOR"));
    assert(!apply_aux_zoom_factor(&aux) && !aux.zoom_present);
    assert(!setenv("ALTSCREEN111_ZOOM_FACTOR","0",1));
    assert(!apply_aux_zoom_factor(&aux) && !aux.zoom_present);
    assert(!setenv("ALTSCREEN111_ZOOM_FACTOR","70",1));
    assert(!apply_aux_zoom_factor(&aux) && aux.zoom_present && aux.zoom==70);
    assert(!primary.zoom_present && primary.width==800 && primary.height==480);
    assert(aux.width==1010 && aux.height==376);
    allocation_fails=1;assert(apply_aux_zoom_factor(&aux)<0);allocation_fails=0;
    for(i=0;i<sizeof(bad)/sizeof(bad[0]);++i)
        assert(aux_zoom_percent(bad[i])<0);
    assert(aux_zoom_percent("100")==100 && aux_zoom_percent("150")==150);
    puts("ALT111_AUX_ZOOM_FACTOR_TEST=PASS");
    return 0;
}
