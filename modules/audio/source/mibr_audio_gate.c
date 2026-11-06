/* SPDX-License-Identifier: GPL-3.0-or-later
 * Fail closed on any missing requirement. No audio DSP, no device access.
 */
#include "mibr_audio_gate.h"
enum mibr_audio_path mibr_audio_select(const struct mibr_audio_evidence *e,
                                       enum mibr_audio_input in) {
 if (!e || in == MIBR_AUDIO_PHONE || in == MIBR_AUDIO_SIRI ||
     in == MIBR_AUDIO_NAV_PROMPT) return MIBR_AUDIO_STOCK;
 if (!e->explicit_opt_in || !e->exact_firmware_fingerprint ||
     !e->target_native_audio_abi_proven ||
     !e->physical_amp_part_number_verified || !e->external_amp_verified ||
     !e->exact_six_channel_route_proven ||
     !e->channel_order_and_lfe_verified ||
     !e->stream_ownership_and_voice_priority_proven ||
     !e->cpu_deadline_and_rollback_proven) return MIBR_AUDIO_STOCK;
 if (in == MIBR_AUDIO_MUSIC_APAC51 && e->spatial_audio_requested &&
     e->apac_codec_supported) return MIBR_AUDIO_DISCRETE_51;
 if (in == MIBR_AUDIO_MUSIC_STEREO && e->stereo_upmix_requested)
     return MIBR_AUDIO_STEREO_SCENE;
 return MIBR_AUDIO_STOCK;
}
