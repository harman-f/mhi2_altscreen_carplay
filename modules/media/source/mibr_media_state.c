/* SPDX-License-Identifier: GPL-3.0-or-later
 * Pure session/cover association. All file transfer and picture-manager work
 * belongs to exact-firmware adapters, which are deliberately absent here.
 */
#include "mibr_media_state.h"
#include <string.h>
static void copy_text(char *out, const char *in) {
    size_t n;
    if (!in) in = "";
    n = strlen(in);
    if (n >= MIBR_MEDIA_TEXT_CAP) n = MIBR_MEDIA_TEXT_CAP - 1;
    memcpy(out, in, n);
    out[n] = 0;
}
void mibr_media_init(mibr_media_state *s) {
    if (s) memset(s, 0, sizeof(*s));
}
void mibr_media_begin(mibr_media_state *s, uint32_t session) {
    if (!s || !session) return;
    /* Preserve an explicitly disabled switch across reconnects. */
    int enabled = s->music_enabled;
    memset(s, 0, sizeof(*s));
    s->session = session;
    s->connected = 1;
    s->music_enabled = enabled;
}
void mibr_media_set_enabled(mibr_media_state *s, int enabled) {
    if (!s) return;
    s->music_enabled = enabled != 0;
    if (!s->music_enabled) {
        s->artwork_valid = 0;
        s->artwork_epoch = 0;
    }
}
int mibr_media_track(mibr_media_state *s, uint32_t session,
                     const char *title, const char *artist, const char *album,
                     uint32_t artwork_transfer_id) {
    char t[MIBR_MEDIA_TEXT_CAP], a[MIBR_MEDIA_TEXT_CAP], l[MIBR_MEDIA_TEXT_CAP];
    if (!s || !s->connected || !session || session != s->session) return 0;
    copy_text(t, title); copy_text(a, artist); copy_text(l, album);
    if (!strcmp(s->title,t) && !strcmp(s->artist,a) && !strcmp(s->album,l)
        && s->artwork_transfer_id == artwork_transfer_id) return 1;
    copy_text(s->title,t); copy_text(s->artist,a); copy_text(s->album,l);
    s->artwork_transfer_id = artwork_transfer_id;
    s->track_epoch += 1u;
    if (!s->track_epoch) s->track_epoch = 1;
    s->artwork_valid = 0;
    s->artwork_epoch = 0;
    return 2;
}
int mibr_media_cover_ready(mibr_media_state *s, uint32_t session,
                           uint32_t track_epoch, uint32_t artwork_transfer_id) {
    if (!s || !s->connected || !s->music_enabled || !session
        || session != s->session || !track_epoch || track_epoch != s->track_epoch
        || !artwork_transfer_id || artwork_transfer_id != s->artwork_transfer_id) return 0;
    s->artwork_epoch = track_epoch;
    s->artwork_valid = 1;
    return 1;
}
void mibr_media_end(mibr_media_state *s, uint32_t session) {
    if (!s || !session || session != s->session) return;
    int enabled = s->music_enabled;
    memset(s, 0, sizeof(*s));
    s->music_enabled = enabled;
}
int mibr_media_show_cover(const mibr_media_state *s) {
    return s && s->connected && s->music_enabled && s->artwork_valid
           && s->artwork_epoch == s->track_epoch;
}
