/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_audio_owner.h"
#include <string.h>
void mibr_audio_owner_init(mibr_audio_owner *o){
 if(o)memset(o,0,sizeof(*o));
}
static int same_owner(const mibr_audio_owner *o,uint64_t gen){
 return o&&o->active_generation&&o->active_generation==gen&&o->stock_owner_qualified;
}
int mibr_audio_owner_attach(mibr_audio_owner *o,uint64_t gen,int qualified){
 if(!o||!gen||gen<=o->highest_generation||!qualified)return 0;
 o->highest_generation=gen;
 o->active_generation=gen;
 o->stock_owner_qualified=1;
 o->music_has_focus=0;
 o->voice_or_announcement_active=0;
 memset(&o->evidence,0,sizeof(o->evidence));
 return 1;
}
int mibr_audio_owner_evidence(mibr_audio_owner *o,uint64_t gen,
                              const struct mibr_audio_evidence *e){
 if(!same_owner(o,gen)||!e)return 0;
 o->evidence=*e;
 return 1;
}
int mibr_audio_owner_focus(mibr_audio_owner *o,uint64_t gen,
                           int music,int voice){
 if(!same_owner(o,gen))return 0;
 o->music_has_focus=music!=0;
 o->voice_or_announcement_active=voice!=0;
 return 1;
}
enum mibr_audio_path mibr_audio_owner_select(const mibr_audio_owner *o,
                                             uint64_t gen,enum mibr_audio_input input){
 if(!same_owner(o,gen)||!o->music_has_focus||o->voice_or_announcement_active)
     return MIBR_AUDIO_STOCK;
 return mibr_audio_select(&o->evidence,input);
}
void mibr_audio_owner_detach(mibr_audio_owner *o,uint64_t gen){
 if(!same_owner(o,gen))return;
 memset(&o->evidence,0,sizeof(o->evidence));
 o->music_has_focus=0;
 o->voice_or_announcement_active=0;
 o->stock_owner_qualified=0;
 o->active_generation=0;
}
