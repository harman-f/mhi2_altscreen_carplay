#ifndef MHI2_NVIDIA_PCM_SINK_H
#define MHI2_NVIDIA_PCM_SINK_H
#include <stddef.h>
#include <stdint.h>
#include <pthread.h>
/* Native API reports status, never a consumed byte count. A failed call is
 * ambiguous: never retry it or credit it as a known prefix. */
struct mhi2_nv_api {
 int (*open)(void **,const char *);
 int (*configure)(void *,const void *);
 int (*metadata)(void *,const void *,unsigned *);
 int (*write)(void *,const void *,unsigned,const unsigned *,unsigned);
 int (*close)(void *);
};
struct mhi2_nv_result {size_t confirmed_frames,uncertain_frames;int status;};
struct mhi2_nv_sink {
 pthread_mutex_t mutex;
 struct mhi2_nv_api api;
 void *handle;
 const char *device;
 unsigned metadata[2],generation;
 int initialized,ready,fault;
};
enum {MHI2_NV_INVALID=-1,MHI2_NV_UNQUALIFIED=-2,MHI2_NV_CLOSED=-3,MHI2_NV_STALE=-4,MHI2_NV_CONFIG=-5};
/* Six-channel eligibility is supplied by the deployment route gate, never
 * inferred from MMX accepting six channels. Device string remains caller-owned. */
int mhi2_nv_sink_init(struct mhi2_nv_sink *,const struct mhi2_nv_api *,const char *,int six_channel_route_qualified);
int mhi2_nv_sink_start(struct mhi2_nv_sink *);
unsigned mhi2_nv_sink_generation(struct mhi2_nv_sink *);
struct mhi2_nv_result mhi2_nv_sink_write(struct mhi2_nv_sink *,unsigned generation,const int16_t *,size_t frames);
/* Reopens the native connection: caller must reset its queued PCM/DSP timeline
 * to the returned generation. It is NOT a seamless underrun recovery. */
int mhi2_nv_sink_flush(struct mhi2_nv_sink *);
int mhi2_nv_sink_close(struct mhi2_nv_sink *);
/* Call only after all client threads have joined. */
int mhi2_nv_sink_destroy(struct mhi2_nv_sink *);
#endif
