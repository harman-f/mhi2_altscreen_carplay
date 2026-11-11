/* SPDX-License-Identifier: GPL-3.0-or-later
 * Source-stage same-owner media/focus bridge. No audio hooks, PCM writes or
 * driver modifications. Never substitutes a second CarPlay/audio session.
 */
#ifndef MIBR_AUDIO_OWNER_H
#define MIBR_AUDIO_OWNER_H
#include "mibr_audio_gate.h"
#include <stdint.h>
typedef struct {
 struct mibr_audio_evidence evidence;
 uint64_t active_generation, highest_generation;
 int stock_owner_qualified;
 int music_has_focus;
 int voice_or_announcement_active;
} mibr_audio_owner;
void mibr_audio_owner_init(mibr_audio_owner *o);
int mibr_audio_owner_attach(mibr_audio_owner *o,uint64_t gen,
                            int stock_audio_owner_qualified);
int mibr_audio_owner_evidence(mibr_audio_owner *o,uint64_t gen,
                              const struct mibr_audio_evidence *e);
int mibr_audio_owner_focus(mibr_audio_owner *o,uint64_t gen,
                           int music_has_focus,int voice_or_announcement_active);
enum mibr_audio_path mibr_audio_owner_select(const mibr_audio_owner *o,
                                             uint64_t gen,enum mibr_audio_input input);
void mibr_audio_owner_detach(mibr_audio_owner *o,uint64_t gen);
#endif
