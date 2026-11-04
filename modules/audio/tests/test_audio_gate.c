/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/mibr_audio_gate.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
 struct mibr_audio_evidence e = {0};
 assert(mibr_audio_select(0,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 e.explicit_opt_in=1; e.exact_firmware_fingerprint=1;
 e.target_native_audio_abi_proven=1; e.physical_amp_part_number_verified=1;
 e.external_amp_verified=1; e.exact_six_channel_route_proven=1;
 e.channel_order_and_lfe_verified=1;
 e.stream_ownership_and_voice_priority_proven=1;
 e.cpu_deadline_and_rollback_proven=1; e.stereo_upmix_requested=1;
 e.spatial_audio_requested=1; e.apac_codec_supported=1;
 assert(mibr_audio_select(&e,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STEREO_SCENE);
 assert(mibr_audio_select(&e,MIBR_AUDIO_MUSIC_APAC51)==MIBR_AUDIO_DISCRETE_51);
 assert(mibr_audio_select(&e,MIBR_AUDIO_PHONE)==MIBR_AUDIO_STOCK);
 assert(mibr_audio_select(&e,MIBR_AUDIO_SIRI)==MIBR_AUDIO_STOCK);
 assert(mibr_audio_select(&e,MIBR_AUDIO_NAV_PROMPT)==MIBR_AUDIO_STOCK);
 e.exact_six_channel_route_proven=0;
 assert(mibr_audio_select(&e,MIBR_AUDIO_MUSIC_APAC51)==MIBR_AUDIO_STOCK);
 assert(mibr_audio_select(&e,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 e.exact_six_channel_route_proven=1; e.apac_codec_supported=0;
 assert(mibr_audio_select(&e,MIBR_AUDIO_MUSIC_APAC51)==MIBR_AUDIO_STOCK);
 e.apac_codec_supported=1; e.explicit_opt_in=0;
 assert(mibr_audio_select(&e,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 puts("AUDIO_GATE_HOST_TEST=PASS");
 return 0;
}
