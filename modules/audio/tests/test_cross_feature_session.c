/* SPDX-License-Identifier: GPL-3.0-or-later
 * Host-only composition: one CarPlay generation fans out to Media, Phone
 * and Audio. Simulates callbacks from the existing owner, not real transport.
 * No OEM BAP, PCM, AirPlay, broker, device or sound side effects.
 */
#include "../../media/source/mibr_media_ingress.h"
#include "../../phone/source/mibr_phone_ingress.h"
#include "../source/mibr_audio_owner.h"
#include <assert.h>
#include <stdio.h>

static struct mibr_audio_evidence qualified_fixture(void) {
    struct mibr_audio_evidence e={0};
    e.explicit_opt_in=1;
    e.exact_firmware_fingerprint=1;
    e.target_native_audio_abi_proven=1;
    e.physical_amp_part_number_verified=1;
    e.external_amp_verified=1;
    e.exact_six_channel_route_proven=1;
    e.channel_order_and_lfe_verified=1;
    e.stream_ownership_and_voice_priority_proven=1;
    e.cpu_deadline_and_rollback_proven=1;
    e.apac_codec_supported=1;
    e.stereo_upmix_requested=1;
    e.spatial_audio_requested=1;
    return e;
}
int main(void) {
    mibr_media_ingress media;
    mibr_phone_ingress phone;
    mibr_audio_owner audio;
    mibr_media_state cover;
    mibr_phone_state call;
    struct mibr_audio_evidence approved=qualified_fixture();

    mibr_media_ingress_init(&media);
    mibr_phone_ingress_init(&phone);
    mibr_audio_owner_init(&audio);

    /* Existing CarPlay owner establishes ONE generation for every subscriber. */
    assert(mibr_media_ingress_attach(&media,101,41,1,1));
    assert(mibr_phone_ingress_attach(&phone,101,41,1,1,0));
    assert(mibr_audio_owner_attach(&audio,101,1));
    assert(mibr_audio_owner_select(&audio,101,MIBR_AUDIO_MUSIC_STEREO)==MIBR_AUDIO_STOCK);
    assert(!mibr_phone_ingress_snapshot(&phone,101,&call));
    assert(!mibr_media_ingress_snapshot(&media,101,&cover));

    /* A broker-confirmed opt-in is simulated only for portable policy tests. */
    mibr_media_ingress_enable(&media,1);
    mibr_phone_ingress_enable(&phone,1);
    assert(mibr_media_ingress_track(&media,101,41,"Track","Artist","Album",500)==2);
    assert(mibr_media_ingress_snapshot(&media,101,&cover));
    assert(!mibr_media_show_cover(&cover));
    assert(mibr_media_ingress_cover(&media,101,41,cover.track_epoch,500));
    assert(mibr_media_ingress_snapshot(&media,101,&cover));
    assert(mibr_media_show_cover(&cover));

    /* This test deliberately fabricates qualifications: no car is qualified. */
    assert(mibr_audio_owner_evidence(&audio,101,&approved));
    assert(mibr_audio_owner_focus(&audio,101,1,0));
    assert(mibr_audio_owner_select(&audio,101,MIBR_AUDIO_MUSIC_STEREO)==
           MIBR_AUDIO_STEREO_SCENE);

    /* The existing phone owner indicates a call: dispatcher MUST update focus.
     * There is no automated runtime dispatcher in this source-only test. */
    assert(mibr_phone_ingress_event(&phone,101,41,9,MIBR_CALL_RINGING,
                                    "Caller","555",1));
    assert(mibr_phone_ingress_snapshot(&phone,101,&call));
    assert(call.status==MIBR_CALL_RINGING);
    assert(mibr_audio_owner_focus(&audio,101,1,1));
    assert(mibr_audio_owner_select(&audio,101,MIBR_AUDIO_MUSIC_STEREO)==
           MIBR_AUDIO_STOCK);
    assert(mibr_audio_owner_select(&audio,101,MIBR_AUDIO_MUSIC_APAC51)==
           MIBR_AUDIO_STOCK);
    assert(!mibr_phone_ingress_action_allowed(&phone,101,41,9,MIBR_CALL_ACCEPT));
    assert(mibr_phone_ingress_event(&phone,101,41,9,MIBR_CALL_NONE,0,0,0));
    assert(mibr_audio_owner_focus(&audio,101,1,0));
    assert(mibr_audio_owner_select(&audio,101,MIBR_AUDIO_MUSIC_STEREO)==
           MIBR_AUDIO_STEREO_SCENE);

    /* A new authenticated owner closes every old generation and resets the
     * Audio evidence, so a reconnect NEVER auto-restores multichannel output. */
    mibr_media_ingress_detach(&media,101,41);
    mibr_phone_ingress_detach(&phone,101,41);
    mibr_audio_owner_detach(&audio,101);
    assert(mibr_media_ingress_attach(&media,102,42,1,1));
    assert(mibr_phone_ingress_attach(&phone,102,42,1,1,0));
    assert(mibr_audio_owner_attach(&audio,102,1));
    assert(!mibr_media_ingress_track(&media,101,41,"Late",0,0,500));
    assert(!mibr_media_ingress_cover(&media,101,41,1,500));
    assert(!mibr_phone_ingress_event(&phone,101,41,9,MIBR_CALL_ACTIVE,
                                     "Stale","555",1));
    assert(!mibr_phone_ingress_snapshot(&phone,101,&call));
    assert(mibr_audio_owner_select(&audio,101,MIBR_AUDIO_MUSIC_STEREO)==
           MIBR_AUDIO_STOCK);
    assert(mibr_audio_owner_focus(&audio,102,1,0));
    assert(mibr_audio_owner_select(&audio,102,MIBR_AUDIO_MUSIC_STEREO)==
           MIBR_AUDIO_STOCK);
    assert(mibr_media_ingress_track(&media,102,42,"Fresh","Artist","Album",700)==2);
    assert(mibr_media_ingress_snapshot(&media,102,&cover));
    assert(!mibr_media_show_cover(&cover));
    assert(!mibr_phone_ingress_snapshot(&phone,102,&call) ||
           call.status==MIBR_CALL_NONE);
    mibr_media_ingress_enable(&media,0);
    mibr_phone_ingress_enable(&phone,0);
    assert(!mibr_media_ingress_snapshot(&media,102,&cover));
    assert(!mibr_phone_ingress_action_allowed(&phone,102,42,9,MIBR_CALL_HANGUP));
    puts("CROSS_FEATURE_ONE_OWNER_COMPOSITION=PASS");
    return 0;
}
