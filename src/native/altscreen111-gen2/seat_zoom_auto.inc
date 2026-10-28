/* SPDX-License-Identifier: GPL-3.0-or-later
 * Optional SEAT correlated-wheel bridge, parallel OEM behavior unchanged.
 * DIRECT/session eligibility is not independent proof of visible VC focus.
 * A fresh measured native-scale-associated detent is still required.
 */
#include "seat_zoom_epoch.h"
static struct seat_zoom_epoch g_seat_zoom_epoch;
static unsigned gen2_seat_zoom_auto_enabled(void)
{
    const char *v=getenv("ALTSCREEN111_SEAT_WHEEL_ZOOM");
    return v && !strcmp(v,"1");
}
/* Caller holds g2_core_lock. Do not revoke a healthy connection for an ordinary
 * keyframe transaction; only queued command context is invalidated as needed. */
static unsigned gen2_seat_zoom_refresh_locked(void)
{
    unsigned eligible=g2_control_session && g2_control.active &&
        g2_control.desired && g2_video.active &&
        g2_video.session==g2_control_session && g2_zoom.active &&
        g2_zoom.session==g2_control_session && !g2_zoom.failed &&
        access("/tmp/mibr-isotx2-gate.direct",F_OK)==0;
    if(seat_zoom_epoch_update(&g_seat_zoom_epoch,g2_control_session,
            g2_video.stream,g2_video.codec,g2_video.consumer,
            eligible,(uint32_t)monotonic_ms()))
        (void)alt111_zoom_context(&g2_zoom,g2_zoom.session,0u,0u,0u);
    if(!g2_command_ready || !g2_control.shown_ack || g2_control.reacquiring ||
       !g2_video.config_valid || !g2_video.attached || !g2_video.consumer_primed)
        (void)alt111_zoom_context(&g2_zoom,g2_zoom.session,0u,0u,0u);
    return eligible;
}
static unsigned gen2_zoom_spi_requested(void)
{
    unsigned eligible;
    if(access(g2_zoom_v1_arm,F_OK)==0)return 1u;
    if(!gen2_seat_zoom_auto_enabled())return 0u;
    pthread_mutex_lock(&g2_core_lock);
    eligible=gen2_seat_zoom_refresh_locked();
    pthread_mutex_unlock(&g2_core_lock);
    return eligible;
}
