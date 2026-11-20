/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_media_ingress.h"
#include <string.h>
void mibr_media_ingress_init(mibr_media_ingress *m){
 if(!m)return;
 memset(m,0,sizeof(*m));mibr_media_init(&m->current);
}
void mibr_media_ingress_enable(mibr_media_ingress *m,int broker_confirmed_enabled){
 if(m)mibr_media_set_enabled(&m->current,broker_confirmed_enabled);
}
static int valid(const mibr_media_ingress *m,uint64_t gen,uint32_t session){
 return m&&m->active_generation&&m->active_generation==gen&&
        m->exact_abi_qualified&&m->asl_thread_qualified&&
        m->current.connected&&m->current.session==session;
}
int mibr_media_ingress_attach(mibr_media_ingress *m,uint64_t gen,uint32_t session,
                              int exact_abi,int asl_thread){
 if(!m||!gen||!session||gen<=m->highest_generation||
    !exact_abi||!asl_thread)return 0;
 /* A newer authenticated CarPlay owner invalidates all old track/cover data. */
 m->highest_generation=gen;
 m->active_generation=gen;
 m->exact_abi_qualified=1;
 m->asl_thread_qualified=1;
 mibr_media_begin(&m->current,session);
 return 1;
}
int mibr_media_ingress_track(mibr_media_ingress *m,uint64_t gen,uint32_t session,
                             const char *title,const char *artist,
                             const char *album,uint32_t transfer_id){
 if(!valid(m,gen,session)||!m->current.music_enabled)return 0;
 return mibr_media_track(&m->current,session,title,artist,album,transfer_id);
}
int mibr_media_ingress_cover(mibr_media_ingress *m,uint64_t gen,uint32_t session,
                             uint32_t epoch,uint32_t transfer_id){
 if(!valid(m,gen,session))return 0;
 /* 'cover' means the profile helper has already validated its image bytes.
  * An image buffer/path is intentionally NOT carried through this API. */
 return mibr_media_cover_ready(&m->current,session,epoch,transfer_id);
}
int mibr_media_ingress_snapshot(const mibr_media_ingress *m,uint64_t gen,
                                mibr_media_state *out){
 if(!out||!m||!valid(m,gen,m->current.session)||!m->current.music_enabled)return 0;
 *out=m->current;
 return 1;
}
void mibr_media_ingress_detach(mibr_media_ingress *m,uint64_t gen,uint32_t session){
 if(!valid(m,gen,session))return;
 mibr_media_end(&m->current,session);
 m->active_generation=0;
 m->exact_abi_qualified=0;
 m->asl_thread_qualified=0;
}
