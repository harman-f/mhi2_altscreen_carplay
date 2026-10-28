/* SPDX-License-Identifier: GPL-3.0-or-later
 * Compile the real automatic-adapter helper against explicit host context models.
 */
#define _POSIX_C_SOURCE 200809L
#include "alt111_zoom.h"
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <pthread.h>
static pthread_mutex_t g2_core_lock=PTHREAD_MUTEX_INITIALIZER;
static struct alt111_zoom g2_zoom;
static uint64_t g2_control_session=1,clock_ms=1000;
static unsigned g2_command_ready=1,direct_present,manual_present;
static const char *g2_zoom_v1_arm="/manual-test-arm";
static struct {unsigned active,desired,shown_ack,reacquiring;} g2_control={1,1,1,0};
static struct {uint64_t session,stream,codec,consumer;unsigned active,config_valid,attached,consumer_primed;} g2_video={1,1,1,1,1,1,1,1};
static uint64_t monotonic_ms(void){return clock_ms;}
#ifndef F_OK
#define F_OK 0
#endif
static int mock_access(const char *p,int mode){
    (void)mode;
    if(!strcmp(p,g2_zoom_v1_arm))return manual_present?0:-1;
    assert(!strcmp(p,"/tmp/mibr-isotx2-gate.direct"));return direct_present?0:-1;
}
#define access mock_access
#include "../src/native/altscreen111-gen2/seat_zoom_auto.inc"
#undef access
int main(void){
    alt111_zoom_begin(&g2_zoom,1);
    assert(!unsetenv("ALTSCREEN111_SEAT_WHEEL_ZOOM"));
    assert(!gen2_zoom_spi_requested());
    assert(!setenv("ALTSCREEN111_SEAT_WHEEL_ZOOM","1",1));
    assert(!gen2_zoom_spi_requested());
    direct_present=1;assert(gen2_zoom_spi_requested());
    assert(seat_zoom_epoch_fresh(&g_seat_zoom_epoch,1000,1000));
    assert(alt111_zoom_polarity(&g2_zoom,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_context(&g2_zoom,1,1,1,1)==ALT111_ZOOM_OK);
    assert(alt111_zoom_encoder(&g2_zoom,1,4,40,1,0,1)==ALT111_ZOOM_OK);
    assert(g2_zoom.pending==1);
    clock_ms+=10;assert(gen2_zoom_spi_requested() && g2_zoom.pending==1);
    ++g2_video.consumer;
    assert(gen2_zoom_spi_requested() && g2_zoom.pending==0 && !g2_zoom.vc_map_focus);
    assert(alt111_zoom_context(&g2_zoom,1,1,1,1)==ALT111_ZOOM_OK);
    g2_video.consumer_primed=0;
    assert(gen2_zoom_spi_requested() && !g2_zoom.vc_map_focus);
    g2_video.consumer_primed=1;g2_zoom.failed=1;
    assert(!gen2_zoom_spi_requested());
    g2_zoom.failed=0;g2_video.session=2;
    assert(!gen2_zoom_spi_requested());
    g2_video.session=1;direct_present=0;
    assert(!gen2_zoom_spi_requested());
    manual_present=1;
    assert(gen2_zoom_spi_requested()); /* Explicit original manual behavior. */
    puts("SEAT_ZOOM_AUTO_CONTEXT_TEST=PASS");return 0;
}
