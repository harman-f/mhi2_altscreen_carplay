/* SPDX-License-Identifier: GPL-3.0-or-later
 * CAS + atomic, readback-verified store for simple MIBR-only choices. No OEM DSIPersistence, no
 * Classic111 registry entry. A missing file means the default. A new one is one row in mibr_switch_defs.
 */
#define _POSIX_C_SOURCE 200809L
#include "../../../carplay/source/alt111-settings/include/mibr_paths.h"
#include "mibr_durable_switch.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>
#define SWITCH_CAP 96u
#define PATH_CAP 512u
const struct mibr_switch_def mibr_switch_defs[MIBR_SWITCH_COUNT]={
    {"MIBR_CARPLAY_NAV/1","on|off","off",MIBR_CONFIG_DIR "/navigation/carplay-nav.conf","CARPLAY_NAV_GET","CARPLAY_NAV_SET","carplay_nav",
     "MIBR_V3_HOST_CARPLAY_NAV_PATH","/tmp/mibr-carplay-nav-readonly.conf"},
    {"MIBR_SD_LOG/1","on|off","off",MIBR_CONFIG_DIR "/features/sd-log.conf","SD_LOG_GET","SD_LOG_SET","sd_log",
     "MIBR_V3_HOST_SD_LOG_PATH","/tmp/mibr-sd-log-readonly.conf"},
    {"MIBR_NAV_LINE/1","dist|street|off","dist",MIBR_CONFIG_DIR "/navigation/nav-line.conf","NAV_LINE_GET","NAV_LINE_SET","nav_line",
     "MIBR_V3_HOST_NAV_LINE_PATH","/tmp/mibr-nav-line-readonly.conf"},
    {"MIBR_NAV_NIGHT/1","auto|light|dark","auto",MIBR_CONFIG_DIR "/navigation/nav-night.conf","NAV_NIGHT_GET","NAV_NIGHT_SET","nav_night",
     "MIBR_V3_HOST_NAV_NIGHT_PATH","/tmp/mibr-nav-night-readonly.conf"},
    {"MIBR_NAV_SOURCE/1","auto|stock|phone","auto",MIBR_CONFIG_DIR "/navigation/nav-source.conf","NAV_SOURCE_GET","NAV_SOURCE_SET","nav_source",
     "MIBR_V3_HOST_NAV_SOURCE_PATH","/tmp/mibr-nav-source-readonly.conf"},
    {"MIBR_NAV_DISPLAY/1","side|top|both","side",MIBR_CONFIG_DIR "/navigation/nav-display.conf","NAV_DISPLAY_GET","NAV_DISPLAY_SET","nav_display",
     "MIBR_V3_HOST_NAV_DISPLAY_PATH","/tmp/mibr-nav-display-readonly.conf"},
    {"MIBR_NAV_BOTTOM/1","eta|rtt","eta",MIBR_CONFIG_DIR "/navigation/nav-bottom.conf","NAV_BOTTOM_GET","NAV_BOTTOM_SET","nav_bottom",
     "MIBR_V3_HOST_NAV_BOTTOM_PATH","/tmp/mibr-nav-bottom-readonly.conf"},
    {"MIBR_NAV_SIDE/1","on|off","on",MIBR_CONFIG_DIR "/navigation/nav-side.conf","NAV_SIDE_GET","NAV_SIDE_SET","nav_side",
     "MIBR_V3_HOST_NAV_SIDE_PATH","/tmp/mibr-nav-side-readonly.conf"},
    {"MIBR_NAV_LANES/1","on|off","on",MIBR_CONFIG_DIR "/navigation/nav-lanes.conf","NAV_LANES_GET","NAV_LANES_SET","nav_lanes",
     "MIBR_V3_HOST_NAV_LANES_PATH","/tmp/mibr-nav-lanes-readonly.conf"},
    {"MIBR_SAFE_VOLL/1",NULL,"0,58,1010,248",MIBR_CONFIG_DIR "/cockpit/safe-voll.conf","SAFE_VOLL_GET","SAFE_VOLL_SET","safe_voll",
     "MIBR_V3_HOST_SAFE_VOLL_PATH","/tmp/mibr-safe-voll-readonly.conf"},
    {"MIBR_SAFE_WIDE/1",NULL,"200,58,590,248",MIBR_CONFIG_DIR "/cockpit/safe-wide.conf","SAFE_WIDE_GET","SAFE_WIDE_SET","safe_wide",
     "MIBR_V3_HOST_SAFE_WIDE_PATH","/tmp/mibr-safe-wide-readonly.conf"},
    {"MIBR_SAFE_CENTER/1",NULL,"370,58,256,248",MIBR_CONFIG_DIR "/cockpit/safe-center.conf","SAFE_CENTER_GET","SAFE_CENTER_SET","safe_center",
     "MIBR_V3_HOST_SAFE_CENTER_PATH","/tmp/mibr-safe-center-readonly.conf"},
    {"MIBR_EXPERT_MODE/1","on|off","off",MIBR_CONFIG_DIR "/features/expert-mode.conf","EXPERT_MODE_GET","EXPERT_MODE_SET","expert_mode",
     "MIBR_V3_HOST_EXPERT_MODE_PATH","/tmp/mibr-expert-mode-readonly.conf"},
};
const char *mibr_switch_platform_path=MIBR_CONFIG_DIR "/platform/defaults.conf";
const struct mibr_switch_def *mibr_switch_for_op(const char *op,int *set){
    unsigned i;
    for(i=0;i<MIBR_SWITCH_COUNT;i++){
        const struct mibr_switch_def *d=&mibr_switch_defs[i];
        if(!strcmp(op,d->get_op)){if(set)*set=0;return d;}
        if(!strcmp(op,d->set_op)){if(set)*set=1;return d;}
    }
    return NULL;
}
static int failure(char *error,size_t cap,const char *value){
    if(error&&cap)snprintf(error,cap,"%s",value);
    return -1;
}
/* A safe area inside the 1010x376 stream, canonical decimals, not smaller than the menu allows. */
static int rect_valid(const char *v){
    long f[4];int i;
    for(i=0;i<4;i++){
        const char *start=v;long n=0;
        if(*v<'0'||*v>'9'||(*v=='0'&&v[1]>='0'&&v[1]<='9'))return 0;
        while(*v>='0'&&*v<='9'&&v-start<5)n=n*10+(*v++-'0');
        f[i]=n;
        if(i<3){if(*v!=',')return 0;v++;}
    }
    if(*v)return 0;
    return f[2]>=100&&f[3]>=60&&f[0]+f[2]<=1010&&f[1]+f[3]<=376;
}
int mibr_switch_valid(const struct mibr_switch_def *def,const char *v){
    const char *at;size_t n;
    if(!def||!v||!*v)return 0;
    if(!def->values)return rect_valid(v);
    n=strlen(v);
    for(at=def->values;at;at=strchr(at,'|'),at=at?at+1:NULL){
        if(!strncmp(at,v,n)&&(at[n]=='|'||!at[n]))return 1;
    }
    return 0;
}
void mibr_switch_default(const struct mibr_switch_def *def,char *out,size_t cap){
    char line[128];FILE *f=mibr_switch_platform_path?fopen(mibr_switch_platform_path,"r"):NULL;
    size_t k=strlen(def->capability);
    snprintf(out,cap,"%s",def->default_value);
    if(!f)return;
    while(fgets(line,sizeof(line),f)){
        char *nl=strchr(line,'\n');
        if(nl)*nl=0;
        if(!strncmp(line,def->capability,k)&&line[k]=='='&&strlen(line+k+1)<cap&&
           mibr_switch_valid(def,line+k+1)){
            snprintf(out,cap,"%s",line+k+1);
            break;
        }
    }
    fclose(f);
}
static int decimal(const char *s,size_t n,uint64_t *value){
    size_t i;uint64_t v=0;
    if(!n||(n>1&&*s=='0'))return -1;
    for(i=0;i<n;i++){
        unsigned d=(unsigned)(s[i]-'0');
        if(s[i]<'0'||s[i]>'9'||v>(UINT64_MAX-d)/10u)return -1;
        v=v*10u+d;
    }
    *value=v;return 0;
}
static int raw_read(const char *path,char *buf,size_t *size){
    int fd;struct stat before,after;size_t n=0;ssize_t got;
    if(lstat(path,&before))return errno==ENOENT?1:-1;
    if(!S_ISREG(before.st_mode)||before.st_size<1||before.st_size>=SWITCH_CAP||
       (before.st_mode&022))return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&after)||!S_ISREG(after.st_mode)||before.st_dev!=after.st_dev||
       before.st_ino!=after.st_ino||before.st_size!=after.st_size){close(fd);return -1;}
    while(n<(size_t)before.st_size){
        got=read(fd,buf+n,(size_t)before.st_size-n);
        if(got<0&&errno==EINTR)continue;
        if(got<=0){close(fd);return -1;}n+=(size_t)got;
    }
    if(close(fd))return -1;
    buf[n]=0;*size=n;return 0;
}
static int canonical(const struct mibr_switch_def *def,const struct mibr_switch *state,char *out,size_t cap){
    int n=snprintf(out,cap,"%s\nrevision=%llu\nvalue=%s\n",def->magic,
        (unsigned long long)state->revision,state->value);
    return n>0&&(size_t)n<cap?n:-1;
}
int mibr_switch_load(const struct mibr_switch_def *def,const char *path,struct mibr_switch *out,
 char *error,size_t error_cap){
    char raw[SWITCH_CAP],want[SWITCH_CAP];size_t n=0;int rc,k;
    const char *r,*v,*end;size_t head;
    if(!def||!path||*path!='/'||strlen(path)>=PATH_CAP||!out)
        return failure(error,error_cap,"INVALID_PATH");
    memset(out,0,sizeof(*out));mibr_switch_default(def,out->value,sizeof(out->value));
    rc=raw_read(path,raw,&n);
    if(rc==1){if(error&&error_cap)*error=0;return 0;}
    if(rc)return failure(error,error_cap,"STORAGE_UNAVAILABLE");
    head=strlen(def->magic);
    if(n<head+15||memcmp(raw,def->magic,head)||memcmp(raw+head,"\nrevision=",10))
        return failure(error,error_cap,"INVALID_SWITCH_FILE");
    r=raw+head+10;end=strchr(r,'\n');
    if(!end||decimal(r,(size_t)(end-r),&out->revision))
        return failure(error,error_cap,"INVALID_SWITCH_FILE");
    v=end+1;
    if(strncmp(v,"value=",6))return failure(error,error_cap,"INVALID_SWITCH_FILE");
    v+=6;end=strchr(v,'\n');
    if(!end||end[1]||end-v>=(long)sizeof(out->value))return failure(error,error_cap,"INVALID_SWITCH_FILE");
    memcpy(out->value,v,(size_t)(end-v));out->value[end-v]=0;
    if(!mibr_switch_valid(def,out->value))return failure(error,error_cap,"INVALID_SWITCH_FILE");
    k=canonical(def,out,want,sizeof(want));
    if(k<0||(size_t)k!=n||memcmp(raw,want,n))return failure(error,error_cap,"INVALID_SWITCH_FILE");
    out->stored=1;if(error&&error_cap)*error=0;return 0;
}
static int create_file(const char *path,const char *bytes,size_t length){
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600),s=0;size_t n=0;ssize_t k;
    if(fd<0)return -1;
    while(n<length){
        k=write(fd,bytes+n,length-n);
        if(k<0&&errno==EINTR)continue;
        if(k<=0){s=-1;break;}n+=(size_t)k;
    }
    if(fsync(fd))s=-1;
    if(close(fd))s=-1;
    return s;
}
static int sync_dir(const char *path){
    char dir[PATH_CAP],*slash;int fd,rc;
    if(strlen(path)>=sizeof(dir))return -1;
    strcpy(dir,path);slash=strrchr(dir,'/');
    if(!slash)return -1;
    if(slash==dir)slash[1]=0;else *slash=0;
    fd=open(dir,O_RDONLY);if(fd<0)return -1;
    rc=fsync(fd);if(close(fd))rc=-1;
    return rc;
}
static int same(const struct mibr_switch *a,const struct mibr_switch *b){
    return a->stored==b->stored&&a->revision==b->revision&&!strcmp(a->value,b->value);
}
int mibr_switch_set(const struct mibr_switch_def *def,const char *path,const struct mibr_switch *observed,
 const char *value,uint64_t revision,const struct mibr_switch_guard *guard,
 char *error,size_t cap){
    struct mibr_switch now,next,confirm;char buf[SWITCH_CAP],stage[PATH_CAP],err[80];
    int n,rc=-1,renamed=0,ro;
    if(!def||!path||strlen(path)>PATH_CAP-40||!observed||!mibr_switch_valid(def,value)||
       !guard||!guard->enter_rw||!guard->restore_ro)
        return failure(error,cap,"INVALID_VALUE");
    if(mibr_switch_load(def,path,&now,err,sizeof(err)))return failure(error,cap,err);
    if(revision!=observed->revision||!same(&now,observed))
        return failure(error,cap,"STALE_REVISION");
    if(!strcmp(now.value,value))return 1;
    if(revision==UINT64_MAX)return failure(error,cap,"REVISION_EXHAUSTED");
    next=now;next.revision++;next.stored=1;
    strcpy(next.value,value);n=canonical(def,&next,buf,sizeof(buf));
    if(n<0)return failure(error,cap,"INVALID_SWITCH_FILE");
    if(snprintf(stage,sizeof(stage),"%s.stage.%ld",path,(long)getpid())>=(int)sizeof(stage))
        return failure(error,cap,"INVALID_PATH");
    if(guard->enter_rw(guard->context))return failure(error,cap,"STORAGE_UNAVAILABLE");
    if(mibr_switch_load(def,path,&now,err,sizeof(err))||!same(&now,observed))
        goto done;
    if(create_file(stage,buf,(size_t)n)||rename(stage,path))goto done;
    renamed=1;
    if(sync_dir(path)||mibr_switch_load(def,path,&confirm,err,sizeof(err))||
       !same(&confirm,&next))goto done;
    rc=0;
done:
    /* clean up while still RW: a stage left on flash blocks the next broker start */
    if(rc&&!renamed)(void)unlink(stage);
    ro=guard->restore_ro(guard->context);
    if(ro)return failure(error,cap,"RO_RESTORE_FAILED");
    if(rc){return failure(error,cap,renamed?"UNKNOWN_COMMIT":"STORAGE_UNAVAILABLE");}
    if(mibr_switch_load(def,path,&confirm,err,sizeof(err))||!same(&confirm,&next))
        return failure(error,cap,"UNKNOWN_COMMIT");
    if(error&&cap)*error=0;
    return 0;
}
