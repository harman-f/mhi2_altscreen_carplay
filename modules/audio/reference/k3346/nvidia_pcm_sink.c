#include "nvidia_pcm_sink.h"
#include <string.h>
#define MAX_WRITE_FRAMES 512u
#define WRITE_TIMEOUT_MS 20u
#define MAX_TRANSACTION_FRAMES 1024u
static void next_generation(struct mhi2_nv_sink *s){if(++s->generation==0)++s->generation;}
static int start_locked(struct mhi2_nv_sink *s){
 unsigned cfg[3]={48000,2,6};unsigned char sad[20]={0,252,0,1,16,16};unsigned rate=48000;int r;
 if(s->handle)return MHI2_NV_INVALID;
 next_generation(s);s->ready=0;s->fault=0;
 r=s->api.open(&s->handle,s->device);
 if(r||!s->handle){if(!r)r=MHI2_NV_CONFIG;goto fail;}
 r=s->api.configure(s->handle,cfg);if(r)goto fail;
 memcpy(sad+8,&rate,sizeof(rate));r=s->api.metadata(s->handle,sad,s->metadata);if(r)goto fail;
 s->ready=1;return 0;
fail:
 s->fault=r;
 if(s->handle){int closed=s->api.close(s->handle);if(!closed)s->handle=0;}
 return r;
}
int mhi2_nv_sink_init(struct mhi2_nv_sink *s,const struct mhi2_nv_api *api,const char *device,int qualified){
 if(!s||!api||!api->open||!api->configure||!api->metadata||!api->write||!api->close||!device||!*device)return MHI2_NV_INVALID;
 if(!qualified)return MHI2_NV_UNQUALIFIED;
 memset(s,0,sizeof(*s));if(pthread_mutex_init(&s->mutex,0))return MHI2_NV_INVALID;
 s->api=*api;s->device=device;s->initialized=1;return 0;
}
int mhi2_nv_sink_start(struct mhi2_nv_sink *s){
 int r;if(!s||!s->initialized)return MHI2_NV_INVALID;
 pthread_mutex_lock(&s->mutex);r=start_locked(s);pthread_mutex_unlock(&s->mutex);return r;
}
unsigned mhi2_nv_sink_generation(struct mhi2_nv_sink *s){
 unsigned r;if(!s||!s->initialized)return 0;
 pthread_mutex_lock(&s->mutex);r=s->generation;pthread_mutex_unlock(&s->mutex);return r;
}
struct mhi2_nv_result mhi2_nv_sink_write(struct mhi2_nv_sink *s,unsigned generation,const int16_t *pcm,size_t frames){
 struct mhi2_nv_result result={0,0,MHI2_NV_INVALID};
 if(!s||!s->initialized||(!pcm&&frames)||frames>MAX_TRANSACTION_FRAMES)return result;
 pthread_mutex_lock(&s->mutex);
 if(generation!=s->generation){result.status=MHI2_NV_STALE;goto done;}
 if(s->fault){result.status=s->fault;goto done;}
 if(!s->ready||!s->handle){result.status=MHI2_NV_CLOSED;goto done;}
 result.status=0;
 while(result.confirmed_frames<frames){
  size_t n=frames-result.confirmed_frames;if(n>MAX_WRITE_FRAMES)n=MAX_WRITE_FRAMES;
  int r=s->api.write(s->handle,pcm+result.confirmed_frames*6,(unsigned)(n*12),s->metadata,WRITE_TIMEOUT_MS);
  if(r){s->fault=r;s->ready=0;result.status=r;result.uncertain_frames=n;break;}
  result.confirmed_frames+=n;
 }
done:
 pthread_mutex_unlock(&s->mutex);return result;
}
int mhi2_nv_sink_flush(struct mhi2_nv_sink *s){
 int r=0;if(!s||!s->initialized)return MHI2_NV_INVALID;
 pthread_mutex_lock(&s->mutex);s->ready=0;next_generation(s);
 if(s->handle){r=s->api.close(s->handle);if(!r)s->handle=0;}
 if(!r)r=start_locked(s);else s->fault=r;
 pthread_mutex_unlock(&s->mutex);return r;
}
int mhi2_nv_sink_close(struct mhi2_nv_sink *s){
 int r=0;if(!s||!s->initialized)return MHI2_NV_INVALID;
 pthread_mutex_lock(&s->mutex);s->ready=0;next_generation(s);
 if(s->handle){r=s->api.close(s->handle);if(!r)s->handle=0;}
 s->fault=r;pthread_mutex_unlock(&s->mutex);return r;
}
int mhi2_nv_sink_destroy(struct mhi2_nv_sink *s){
 int r;if(!s||!s->initialized)return MHI2_NV_INVALID;
 r=mhi2_nv_sink_close(s);if(r)return r;
 r=pthread_mutex_destroy(&s->mutex);if(!r)s->initialized=0;return r;
}
