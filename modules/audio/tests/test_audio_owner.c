/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../source/mibr_audio_owner.h"
#include <assert.h>
#include <stdio.h>
int main(void){
 mibr_audio_owner o;struct mibr_audio_evidence e={0};
 mibr_audio_owner_init(&o);
 assert(!mibr_audio_owner_attach(&o,11,0));
 assert(mibr_audio_owner_attach(&o,11,1));
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 e.explicit_opt_in=1; e.exact_firmware_fingerprint=1;
 e.target_native_audio_abi_proven=1; e.physical_amp_part_number_verified=1;
 e.external_amp_verified=1; e.exact_six_channel_route_proven=1;
 e.channel_order_and_lfe_verified=1;
 e.stream_ownership_and_voice_priority_proven=1;
 e.cpu_deadline_and_rollback_proven=1;
 e.apac_codec_supported=1; e.stereo_upmix_requested=1;
 e.spatial_audio_requested=1;
 assert(mibr_audio_owner_evidence(&o,11,&e));
 assert(mibr_audio_owner_focus(&o,11,1,0));
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STEREO_SCENE);
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_APAC51)==MIBR_AUDIO_DISCRETE_51);
 assert(mibr_audio_owner_focus(&o,11,1,1));
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_PHONE)==MIBR_AUDIO_STOCK);
 assert(!mibr_audio_owner_focus(&o,10,1,0)); /* stale owner */
 assert(mibr_audio_owner_focus(&o,11,1,0));
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STEREO_SCENE);
 mibr_audio_owner_detach(&o,10);
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STEREO_SCENE);
 mibr_audio_owner_detach(&o,11);
 assert(mibr_audio_owner_select(&o,11,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 assert(!mibr_audio_owner_attach(&o,11,1)); /* replay */
 assert(mibr_audio_owner_attach(&o,12,1));
 assert(mibr_audio_owner_focus(&o,12,1,0));
 assert(mibr_audio_owner_select(&o,12,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 assert(!mibr_audio_owner_evidence(&o,11,&e));
 assert(mibr_audio_owner_evidence(&o,12,&e));
 e.exact_six_channel_route_proven=0;
 assert(mibr_audio_owner_evidence(&o,12,&e));
 assert(mibr_audio_owner_select(&o,12,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
 puts("AUDIO_SAME_OWNER_FOCUS_TEST=PASS");
 return 0;
}
