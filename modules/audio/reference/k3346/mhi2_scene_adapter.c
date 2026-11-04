#include "mhi2_scene_adapter.h"
#include <string.h>
static short quantize(struct mhi2_scene_adapter *s,float x) {
 float v=x*32768.0f;
 if(v!=v){s->invalid++;return 0;}
 if(v>32767.0f){s->clipped++;return 32767;}
 if(v< -32768.0f){s->clipped++;return -32768;}
 return (short)v;
}
void mhi2_scene_adapter_reset(struct mhi2_scene_adapter *s) {
 if(!s||!s->initialized)return;
 scene_engine_reset_state(&s->scene);
 memset(s->fifo,0,sizeof(s->fifo));
 s->head=0;s->count=s->enabled?MHI2_AUDIO_LATENCY_FRAMES:0;
}
int mhi2_scene_adapter_init(struct mhi2_scene_adapter *s) {
 if(!s)return -1;
 memset(s,0,sizeof(*s));
 struct scene_config c;scene_config_defaults(&c);
 if(scene_engine_init(&s->scene,&c))return -1;
 s->initialized=1;s->level=2;return 0;
}
/* Upstream SCENE level targets, without B&O matrix/LFE calibration.
 * Level changes are applied at stream configuration, not from the HMI thread. */
int mhi2_scene_adapter_level(struct mhi2_scene_adapter *s,unsigned level) {
 static const float target[5][4]={{0,0,0.25f,7000},{0.5f,0.7f,0.35f,7000},{0.7f,0.9f,0.25f,7000},{0.9f,1,0.15f,11000},{1,1,0.10f,12000}};
 if(!s||!s->initialized||level>4)return -1;
 scene_engine_set_tuning(&s->scene,target[level][0],target[level][1],target[level][2],target[level][3]);
 s->level=level;return mhi2_scene_adapter_mode(s,level!=0,s->muted);
}
int mhi2_scene_adapter_mode(struct mhi2_scene_adapter *s,unsigned enabled,unsigned muted) {
 if(!s||!s->initialized||enabled>1||muted>1)return -1;
 if(s->enabled!=enabled||s->muted!=muted){s->enabled=enabled;s->muted=muted;mhi2_scene_adapter_reset(s);}
 return 0;
}
int mhi2_scene_adapter_process(struct mhi2_scene_adapter *s,const short *input,unsigned frames,short *output) {
 if(!s||!s->initialized||!input||!output||frames>MHI2_AUDIO_MAX_FRAMES)return -1;
 if(!frames)return 0;
 if(s->muted){memset(output,0,frames*6*sizeof(short));return 0;}
 if(!s->enabled){
  for(unsigned i=0;i<frames;i++){output[i*6]=input[i*2];output[i*6+1]=input[i*2+1];for(unsigned c=2;c<6;c++)output[i*6+c]=0;}
  return 0;
 }
 for(unsigned i=0;i<frames*2;i++)s->input[i]=input[i]/32768.0f;
 unsigned n=scene_engine_push(&s->scene,s->input,frames,s->rendered,MHI2_AUDIO_MAX_FRAMES+SCENE_HOP);
 if(s->count+n>MHI2_AUDIO_FIFO_FRAMES||s->count+n<frames)return -2;
 for(unsigned i=0;i<n;i++){
  unsigned pos=(s->head+s->count+i)%MHI2_AUDIO_FIFO_FRAMES;
  for(unsigned c=0;c<6;c++)s->fifo[pos*6+c]=quantize(s,s->rendered[i*6+c]);
 }
 s->count+=n;
 for(unsigned i=0;i<frames;i++){
  memcpy(output+i*6,s->fifo+s->head*6,6*sizeof(short));
  s->head=(s->head+1)%MHI2_AUDIO_FIFO_FRAMES;
 }
 s->count-=frames;
 return 0;
}
