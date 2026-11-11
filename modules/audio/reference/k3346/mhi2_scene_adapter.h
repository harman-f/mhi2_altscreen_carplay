#ifndef MHI2_SCENE_ADAPTER_H
#define MHI2_SCENE_ADAPTER_H
#include "scene_engine.h"
#define MHI2_AUDIO_MAX_FRAMES 1024
#define MHI2_AUDIO_FIFO_FRAMES 4096
#define MHI2_AUDIO_LATENCY_FRAMES 1024
/* Experimental S16/48k stereo -> 6ch adapter. Own one instance per stream;
 * calls must be serialized by the audio owner. No allocation after init.
 * C and LFE remain zero. Does not allocate a device or change media routing. */
struct mhi2_scene_adapter {
 struct scene_state scene;
 float input[MHI2_AUDIO_MAX_FRAMES*2];
 float rendered[(MHI2_AUDIO_MAX_FRAMES+SCENE_HOP)*6];
 short fifo[MHI2_AUDIO_FIFO_FRAMES*6];
 unsigned head, count, enabled, muted, initialized;
 unsigned clipped, invalid;
 unsigned level;
};
int mhi2_scene_adapter_init(struct mhi2_scene_adapter *s);
void mhi2_scene_adapter_reset(struct mhi2_scene_adapter *s);
int mhi2_scene_adapter_level(struct mhi2_scene_adapter *s,unsigned level);
int mhi2_scene_adapter_mode(struct mhi2_scene_adapter *s,unsigned enabled,unsigned muted);
/* Exactly frames output on success. Input/output must not overlap.
 * Invalid arguments return -1 before consuming input. */
int mhi2_scene_adapter_process(struct mhi2_scene_adapter *s,const short *input,unsigned frames,short *output);
#endif
