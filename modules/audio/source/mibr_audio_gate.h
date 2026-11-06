/* SPDX-License-Identifier: GPL-3.0-or-later
 * P6 source-stage capability gate. Not linked into runtime or a sound device.
 * Never infer six-channel routing from the mere presence of an amplifier.
 */
#ifndef MIBR_AUDIO_GATE_H
#define MIBR_AUDIO_GATE_H
enum mibr_audio_input {
 MIBR_AUDIO_MUSIC_STEREO=1, MIBR_AUDIO_MUSIC_APAC51=2,
 MIBR_AUDIO_PHONE=3, MIBR_AUDIO_SIRI=4, MIBR_AUDIO_NAV_PROMPT=5
};
enum mibr_audio_path {
 MIBR_AUDIO_STOCK=0, MIBR_AUDIO_STEREO_SCENE=1,
 MIBR_AUDIO_DISCRETE_51=2
};
struct mibr_audio_evidence {
 int explicit_opt_in;
 int exact_firmware_fingerprint;
 int target_native_audio_abi_proven;
 int physical_amp_part_number_verified;
 int external_amp_verified;
 int exact_six_channel_route_proven;
 int channel_order_and_lfe_verified;
 int stream_ownership_and_voice_priority_proven;
 int cpu_deadline_and_rollback_proven;
 int apac_codec_supported;
 int stereo_upmix_requested;
 int spatial_audio_requested;
};
enum mibr_audio_path mibr_audio_select(const struct mibr_audio_evidence *e,
                                       enum mibr_audio_input in);
#endif
