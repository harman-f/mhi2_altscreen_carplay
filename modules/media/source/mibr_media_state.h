/* SPDX-License-Identifier: GPL-3.0-or-later
 * Additive, OEM-independent Now Playing session model.
 * NO /dev/ipod0 access, no BAP calls, no HMI hooks, no installation.
 */
#ifndef MIBR_MEDIA_STATE_H
#define MIBR_MEDIA_STATE_H
#include <stdint.h>
#define MIBR_MEDIA_TEXT_CAP 192
typedef struct {
    uint32_t session;
    uint32_t track_epoch;
    uint32_t artwork_transfer_id;
    uint32_t artwork_epoch;
    int connected, music_enabled, artwork_valid;
    char title[MIBR_MEDIA_TEXT_CAP];
    char artist[MIBR_MEDIA_TEXT_CAP];
    char album[MIBR_MEDIA_TEXT_CAP];
} mibr_media_state;
void mibr_media_init(mibr_media_state *s);
void mibr_media_begin(mibr_media_state *s, uint32_t session);
void mibr_media_set_enabled(mibr_media_state *s, int enabled);
int mibr_media_track(mibr_media_state *s, uint32_t session,
                     const char *title, const char *artist, const char *album,
                     uint32_t artwork_transfer_id);
int mibr_media_cover_ready(mibr_media_state *s, uint32_t session,
                           uint32_t track_epoch, uint32_t artwork_transfer_id);
void mibr_media_end(mibr_media_state *s, uint32_t session);
int mibr_media_show_cover(const mibr_media_state *s);
#endif
