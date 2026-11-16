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
/* per-view geometry and transition keys that only live in the view profile (no legacy file,
 * magic NULL). Same CAS revision (unit.revision) as every other profile-backed value; ops VIEW_PROFILE_GET/SET. */
const struct mibr_switch_def mibr_view_key_defs[MIBR_VIEW_KEY_COUNT]={
    {NULL,"inherit|70|85|100|125|150","inherit",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_zoom_wide",NULL,NULL},
    {NULL,"inherit|70|85|100|125|150","inherit",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_zoom_full",NULL,NULL},
    {NULL,"inherit|70|85|100|125|150","inherit",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_zoom_center",NULL,NULL},
    {NULL,"0|1","0",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_transition_enabled",NULL,NULL},
    {NULL,"panels|cycle","cycle",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_transition_mode",NULL,NULL},
    {NULL,"#100..3000","500",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_transition_gap_ms",NULL,NULL},
    {NULL,"#500..60000","3000",MIBR_CONFIG_DIR "/cockpit/view-profiles.conf","","","vp_transition_min_interval_ms",NULL,NULL},
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
    if(def->values[0]=='#'){        /* "#min..max": canonical decimal in range */
        unsigned long lo=0,hi=0,x=0;size_t i;
        if(sscanf(def->values+1,"%lu..%lu",&lo,&hi)!=2||n>6||(n>1&&v[0]=='0'))return 0;
        for(i=0;i<n;i++){if(v[i]<'0'||v[i]>'9')return 0;x=x*10u+(unsigned long)(v[i]-'0');}
        return x>=lo&&x<=hi;
    }
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
static int raw_read_cap(const char *path,char *buf,size_t cap,size_t *size){
    int fd;struct stat before,after;size_t n=0;ssize_t got;
    if(lstat(path,&before))return errno==ENOENT?1:-1;
    if(!S_ISREG(before.st_mode)||before.st_size<1||(size_t)before.st_size>=cap||
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
static int raw_read(const char *path,char *buf,size_t *size){return raw_read_cap(path,buf,SWITCH_CAP,size);}
static int canonical(const struct mibr_switch_def *def,const struct mibr_switch *state,char *out,size_t cap){
    int n=snprintf(out,cap,"%s\nrevision=%llu\nvalue=%s\n",def->magic,
        (unsigned long long)state->revision,state->value);
    return n>0&&(size_t)n<cap?n:-1;
}
static int legacy_load(const struct mibr_switch_def *def,const char *path,struct mibr_switch *out,
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
static int legacy_set(const struct mibr_switch_def *def,const char *path,const struct mibr_switch *observed,
 const char *value,uint64_t revision,const struct mibr_switch_guard *guard,
 char *error,size_t cap){
    struct mibr_switch now,next,confirm;char buf[SWITCH_CAP],stage[PATH_CAP],err[80];
    int n,rc=-1,renamed=0,ro;
    if(!def||!path||strlen(path)>PATH_CAP-40||!observed||!mibr_switch_valid(def,value)||
       !guard||!guard->enter_rw||!guard->restore_ro)
        return failure(error,cap,"INVALID_VALUE");
    if(legacy_load(def,path,&now,err,sizeof(err)))return failure(error,cap,err);
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
    if(legacy_load(def,path,&now,err,sizeof(err))||!same(&now,observed))
        goto done;
    if(create_file(stage,buf,(size_t)n)||rename(stage,path))goto done;
    renamed=1;
    if(sync_dir(path)||legacy_load(def,path,&confirm,err,sizeof(err))||
       !same(&confirm,&next))goto done;
    rc=0;
done:
    /* clean up while still RW: a stage left on flash blocks the next broker start */
    if(rc&&!renamed)(void)unlink(stage);
    ro=guard->restore_ro(guard->context);
    if(ro)return failure(error,cap,"RO_RESTORE_FAILED");
    if(rc){return failure(error,cap,renamed?"UNKNOWN_COMMIT":"STORAGE_UNAVAILABLE");}
    if(legacy_load(def,path,&confirm,err,sizeof(err))||!same(&confirm,&next))
        return failure(error,cap,"UNKNOWN_COMMIT");
    if(error&&cap)*error=0;
    return 0;
}

/* ---- view-profile backed switches ---------------------------------------------------------
 * Navigation and safe-area choices live in ONE file shared with the HTML configurator:
 * MIBR_NAV_VIEW_PROFILES/3 (key=value lines, last line crc32=<8 hex> over all bytes before it). The broker is the
 * only physical writer; it changes only the keys of the switch being set plus unit.revision and keeps every other
 * line (configurator keys the unit does not use yet) byte for byte. Verbs, values and revisions seen by the menu
 * are unchanged; unit.revision is the CAS revision for all profile-backed switches.
 * No profile file yet: values come once from the legacy per-switch files (migration source only); the first SET
 * creates the profile from all of them. Legacy files are never written again. */
#define PROFILE_CAP 16384u
#define PROFILE_MAGIC "MIBR_NAV_VIEW_PROFILES/3"
#define PROFILE_REV_KEY "unit.revision"
const char *mibr_view_profile_path=MIBR_CONFIG_DIR "/cockpit/view-profiles.conf";
enum {PK_PLAIN,PK_BOOL,PK_BOTTOM,PK_RECT};
struct profile_map {const char *capability,*key;int kind;};
static const struct profile_map profile_maps[]={
    {"nav_source","global.source",PK_PLAIN},
    {"nav_display","global.legacyDisplay",PK_PLAIN},
    {"nav_line","global.legacyLine",PK_PLAIN},
    {"nav_lanes","global.legacyLanes",PK_BOOL},
    {"nav_side","global.sideStreets",PK_BOOL},
    {"nav_bottom","global.bottom",PK_BOTTOM},
    {"safe_voll","view.full.safeArea",PK_RECT},
    {"safe_wide","view.wide.safeArea",PK_RECT},
    {"safe_center","view.center.safeArea",PK_RECT},
    {"vp_zoom_wide","view.wide.geometry.zoom",PK_PLAIN},
    {"vp_zoom_full","view.full.geometry.zoom",PK_PLAIN},
    {"vp_zoom_center","view.center.geometry.zoom",PK_PLAIN},
    {"vp_transition_enabled","global.transition.enabled",PK_PLAIN},
    {"vp_transition_mode","global.transition.mode",PK_PLAIN},
    {"vp_transition_gap_ms","global.transition.gap_ms",PK_PLAIN},
    {"vp_transition_min_interval_ms","global.transition.min_interval_ms",PK_PLAIN},
};
#define PROFILE_MAP_COUNT (sizeof(profile_maps)/sizeof(profile_maps[0]))
static const struct profile_map *profile_map_for(const struct mibr_switch_def *def){
    unsigned i;
    for(i=0;def&&i<PROFILE_MAP_COUNT;i++)if(!strcmp(def->capability,profile_maps[i].capability))return &profile_maps[i];
    return NULL;
}
int mibr_switch_profile_backed(const struct mibr_switch_def *def){return profile_map_for(def)!=NULL;}
const struct mibr_switch_def *mibr_view_key_for(const char *key){
    unsigned i;
    for(i=0;key&&i<MIBR_VIEW_KEY_COUNT;i++){
        const struct profile_map *m=profile_map_for(&mibr_view_key_defs[i]);
        if(m&&!strcmp(m->key,key))return &mibr_view_key_defs[i];
    }
    return NULL;
}
const char *mibr_view_key_name(const struct mibr_switch_def *def){
    const struct profile_map *m=profile_map_for(def);
    return m?m->key:NULL;
}
/* Production: the shared profile (any switch's production path selects it, so a view key can be served through
 * the slot of a profile-backed switch). Host builds pass their own per-switch path; the profile sits beside it. */
static int production_path(const struct mibr_switch_def *def,const char *path){
    unsigned i;
    if(!strcmp(path,def->path))return 1;
    for(i=0;i<MIBR_SWITCH_COUNT;i++)if(!strcmp(path,mibr_switch_defs[i].path))return 1;
    return 0;
}
static int profile_path(const struct mibr_switch_def *def,const char *path,char *out,size_t cap){
    int n=production_path(def,path)?snprintf(out,cap,"%s",mibr_view_profile_path):snprintf(out,cap,"%s.profile",path);
    return n>0&&(size_t)n<cap?0:-1;
}
uint32_t mibr_view_profile_crc32(const char *p,size_t n){
    uint32_t v=0xFFFFFFFFu;size_t i;int j;
    for(i=0;i<n;i++){v^=(unsigned char)p[i];for(j=0;j<8;j++)v=(v>>1)^((v&1u)?0xEDB88320u:0u);}
    return v^0xFFFFFFFFu;
}
/* Validates the whole file; on success *body_len = bytes before the crc32 line. */
static int profile_check(const char *raw,size_t n,size_t *body_len){
    const char *line=raw,*end=raw+n,*crcline=NULL;char want[16];size_t mlen=strlen(PROFILE_MAGIC);
    if(n<mlen+1||memcmp(raw,PROFILE_MAGIC,mlen)||raw[mlen]!='\n'||raw[n-1]!='\n')return -1;
    while(line<end){
        const char *nl=memchr(line,'\n',(size_t)(end-line)),*c;
        if(!nl)return -1;
        for(c=line;c<nl;c++)if((unsigned char)*c<0x20||(unsigned char)*c>0x7e)return -1;
        if(line!=raw){
            const char *eq=memchr(line,'=',(size_t)(nl-line)),*o;
            if(!eq||eq==line)return -1;
            if(nl-line>6&&!memcmp(line,"crc32=",6)){if(nl+1!=end)return -1;crcline=line;}
            /* duplicate keys are refused: one value per key */
            for(o=raw;o<line;){
                const char *onl=memchr(o,'\n',(size_t)(line-o));
                if(o!=raw&&(size_t)(onl-o)>(size_t)(eq-line)&&!memcmp(o,line,(size_t)(eq-line)+1))return -1;
                o=onl+1;
            }
        }
        line=nl+1;
    }
    if(!crcline)return -1;
    snprintf(want,sizeof(want),"crc32=%08x\n",(unsigned)mibr_view_profile_crc32(raw,(size_t)(crcline-raw)));
    if((size_t)(end-crcline)!=strlen(want)||memcmp(crcline,want,strlen(want)))return -1;
    *body_len=(size_t)(crcline-raw);
    return 0;
}
/* Value of key in a body (lines after the magic), NUL-terminated into out. 1 found, 0 missing, -1 too long. */
static int profile_get(const char *body,size_t n,const char *key,char *out,size_t cap){
    const char *line=body,*end=body+n;size_t k=strlen(key);
    while(line<end){
        const char *nl=memchr(line,'\n',(size_t)(end-line));
        if(!nl)break;
        if((size_t)(nl-line)>k&&!memcmp(line,key,k)&&line[k]=='='){
            size_t v=(size_t)(nl-line)-k-1;
            if(v>=cap)return -1;
            memcpy(out,line+k+1,v);out[v]=0;return 1;
        }
        line=nl+1;
    }
    return 0;
}
/* Replaces the key's value in place or appends the line; keeps every other byte. */
static int profile_put(char *body,size_t *n,size_t cap,const char *key,const char *value){
    char *line=body,*end=body+*n;size_t k=strlen(key),v=strlen(value);
    while(line<end){
        char *nl=memchr(line,'\n',(size_t)(end-line));
        if(!nl)return -1;
        if((size_t)(nl-line)>k&&!memcmp(line,key,k)&&line[k]=='='){
            size_t old=(size_t)(nl-line)-k-1;
            if(*n-old+v>=cap)return -1;
            memmove(line+k+1+v,nl,(size_t)(end-nl));
            memcpy(line+k+1,value,v);*n=*n-old+v;body[*n]=0;return 0;
        }
        line=nl+1;
    }
    if(*n+k+v+2>=cap)return -1;
    memcpy(body+*n,key,k);body[*n+k]='=';memcpy(body+*n+k+1,value,v);body[*n+k+1+v]='\n';
    *n+=k+v+2;body[*n]=0;return 0;
}
static int profile_decode(const struct profile_map *m,const char *body,size_t n,char *out,size_t cap){
    char v[24],key[64];
    static const char *const part[4]={"x","y","w","h"};
    int i;
    if(m->kind==PK_RECT){
        char x[4][8];
        for(i=0;i<4;i++){
            snprintf(key,sizeof(key),"%s.%s",m->key,part[i]);
            if(profile_get(body,n,key,x[i],sizeof(x[i]))!=1)return 0;
        }
        return snprintf(out,cap,"%s,%s,%s,%s",x[0],x[1],x[2],x[3])<(int)cap;
    }
    if(profile_get(body,n,m->key,v,sizeof(v))!=1)return 0;
    if(m->kind==PK_BOOL){
        if(!strcmp(v,"true"))snprintf(out,cap,"on");else if(!strcmp(v,"false"))snprintf(out,cap,"off");else return 0;
    }else if(m->kind==PK_BOTTOM){
        if(!strcmp(v,"remaining"))snprintf(out,cap,"rtt");else if(!strcmp(v,"eta"))snprintf(out,cap,"eta");else return 0;
    }else if(strlen(v)<cap)memcpy(out,v,strlen(v)+1);else return 0;
    return 1;
}
static int profile_encode(const struct profile_map *m,char *body,size_t *n,size_t cap,const char *value){
    static const char *const part[4]={"x","y","w","h"};
    char key[64],num[8];int i;const char *at=value;
    if(m->kind==PK_RECT){
        for(i=0;i<4;i++){
            size_t k=strcspn(at,",");
            if(k==0||k>=sizeof(num))return -1;
            memcpy(num,at,k);num[k]=0;at+=k+(at[k]==',');
            snprintf(key,sizeof(key),"%s.%s",m->key,part[i]);
            if(profile_put(body,n,cap,key,num))return -1;
        }
        return 0;
    }
    if(m->kind==PK_BOOL)return profile_put(body,n,cap,m->key,!strcmp(value,"on")?"true":"false");
    if(m->kind==PK_BOTTOM)return profile_put(body,n,cap,m->key,!strcmp(value,"rtt")?"remaining":"eta");
    return profile_put(body,n,cap,m->key,value);
}
static void platform_lookup(const char *key,char *out,size_t cap){
    char line[128];FILE *f=mibr_switch_platform_path?fopen(mibr_switch_platform_path,"r"):NULL;size_t k=strlen(key);
    if(!f)return;
    while(fgets(line,sizeof(line),f)){
        char *nl=strchr(line,'\n');
        if(nl)*nl=0;
        if(!strncmp(line,key,k)&&line[k]=='='&&line[k+1]&&strlen(line+k+1)<cap){snprintf(out,cap,"%s",line+k+1);break;}
    }
    fclose(f);
}
/* 1 = no profile yet, 0 = valid profile in body (without crc line), -1 = unreadable/invalid. */
static int profile_read(const char *ppath,char *body,size_t cap,size_t *n){
    size_t raw_n=0,len=0;int rc=raw_read_cap(ppath,body,cap,&raw_n);
    if(rc)return rc;
    if(profile_check(body,raw_n,&len))return -1;
    body[len]=0;*n=len;return 0;
}
/* main file, else its .lastgood backup (previous valid profile). *from_backup tells which one answered. */
static int profile_read_effective(const char *ppath,char *body,size_t cap,size_t *n,int *from_backup){
    char lp[PATH_CAP];int rc=profile_read(ppath,body,cap,n);
    *from_backup=0;
    if(rc>=0)return rc;
    if(snprintf(lp,sizeof(lp),"%s.lastgood",ppath)>=(int)sizeof(lp))return -1;
    if(profile_read(lp,body,cap,n))return -1;
    *from_backup=1;return 0;
}
static int profile_revision(const char *body,size_t n,uint64_t *rev){
    char v[24];int rc=profile_get(body,n,PROFILE_REV_KEY,v,sizeof(v));
    *rev=0;
    if(rc==0)return 0;
    return rc<0||decimal(v,strlen(v),rev)?-1:0;
}
static int profile_load(const struct mibr_switch_def *def,const struct profile_map *m,const char *path,
 struct mibr_switch *out,char *error,size_t cap){
    char ppath[PATH_CAP];size_t n=0;int rc,backup=0;
    static char body[PROFILE_CAP];
    if(profile_path(def,path,ppath,sizeof(ppath)))return failure(error,cap,"INVALID_PATH");
    rc=profile_read_effective(ppath,body,sizeof(body),&n,&backup);
    if(rc==1&&!def->magic){       /* profile-only key, no profile yet: default */
        memset(out,0,sizeof(*out));mibr_switch_default(def,out->value,sizeof(out->value));
        if(error&&cap)*error=0;
        return 0;
    }
    if(rc==1)return legacy_load(def,path,out,error,cap);        /* migration source until the first SET */
    memset(out,0,sizeof(*out));mibr_switch_default(def,out->value,sizeof(out->value));
    if(rc)return failure(error,cap,"INVALID_SWITCH_FILE");
    if(profile_revision(body,n,&out->revision))return failure(error,cap,"INVALID_SWITCH_FILE");
    {
        char v[sizeof(out->value)];
        if(profile_decode(m,body,n,v,sizeof(v))&&mibr_switch_valid(def,v)){strcpy(out->value,v);out->stored=1;}
    }
    if(error&&cap)*error=0;
    return 0;
}
/* A new profile: header, vehicle from the platform file, every profile-backed value from its legacy file. */
static int profile_initial(const char *path_of_def,const struct mibr_switch_def *self,char *body,size_t cap,size_t *n){
    char brand[24]="",unit[24]="",cluster[24]="",v[24];unsigned i;
    platform_lookup("profile.brand",brand,sizeof(brand));
    platform_lookup("profile.head_unit",unit,sizeof(unit));
    platform_lookup("profile.cluster",cluster,sizeof(cluster));
    *n=(size_t)snprintf(body,cap,"%s\nversion=3\n",PROFILE_MAGIC);
    if(*n>=cap)return -1;
    if(*brand&&profile_put(body,n,cap,"brand",brand))return -1;
    if(*unit&&profile_put(body,n,cap,"head_unit",unit))return -1;
    if(*cluster&&profile_put(body,n,cap,"cluster",cluster))return -1;
    for(i=0;i<MIBR_SWITCH_COUNT;i++){
        const struct mibr_switch_def *d=&mibr_switch_defs[i];
        const struct profile_map *m=profile_map_for(d);
        struct mibr_switch legacy;char err[80];const char *lp;char hostp[PATH_CAP];
        if(!m)continue;
        /* host builds keep the legacy file of this switch next to its own path */
        if(d==self)lp=path_of_def;
        else if(production_path(self,path_of_def))lp=d->path;
        else{snprintf(hostp,sizeof(hostp),"%s.legacy-%s",path_of_def,d->capability);lp=hostp;}
        if(legacy_load(d,lp,&legacy,err,sizeof(err))){memset(&legacy,0,sizeof(legacy));mibr_switch_default(d,legacy.value,sizeof(legacy.value));}
        snprintf(v,sizeof(v),"%s",legacy.value);
        if(profile_encode(m,body,n,cap,v))return -1;
    }
    return 0;
}
static int profile_set(const struct mibr_switch_def *def,const struct profile_map *m,const char *path,
 const struct mibr_switch *observed,const char *value,uint64_t revision,const struct mibr_switch_guard *guard,
 char *error,size_t cap){
    struct mibr_switch now,next,confirm;char ppath[PATH_CAP],stage[PATH_CAP],lgood[PATH_CAP],lstage[PATH_CAP],
         err[80],num[24],crcline[24];
    static char body[PROFILE_CAP],prev[PROFILE_CAP];size_t n=0,prev_n=0;int rc=-1,renamed=0,ro,have,backup=0;
    if(!def||!path||strlen(path)>PATH_CAP-60||!observed||!mibr_switch_valid(def,value)||
       !guard||!guard->enter_rw||!guard->restore_ro)
        return failure(error,cap,"INVALID_VALUE");
    if(profile_path(def,path,ppath,sizeof(ppath)))return failure(error,cap,"INVALID_PATH");
    if(profile_load(def,m,path,&now,err,sizeof(err)))return failure(error,cap,err);
    if(revision!=observed->revision||!same(&now,observed))return failure(error,cap,"STALE_REVISION");
    if(!strcmp(now.value,value)&&now.stored)return 1;
    if(revision==UINT64_MAX)return failure(error,cap,"REVISION_EXHAUSTED");
    if(snprintf(stage,sizeof(stage),"%s.stage.%ld",ppath,(long)getpid())>=(int)sizeof(stage)||
       snprintf(lgood,sizeof(lgood),"%s.lastgood",ppath)>=(int)sizeof(lgood)||
       snprintf(lstage,sizeof(lstage),"%s.lastgood.stage.%ld",ppath,(long)getpid())>=(int)sizeof(lstage))
        return failure(error,cap,"INVALID_PATH");
    if(guard->enter_rw(guard->context))return failure(error,cap,"STORAGE_UNAVAILABLE");
    if(profile_load(def,m,path,&now,err,sizeof(err))||!same(&now,observed))goto done;
    have=profile_read_effective(ppath,body,sizeof(body),&n,&backup);
    if(have<0)goto done;
    /* Keep the current valid file as .lastgood before replacing it (an invalid main file is never backed up;
     * the existing .lastgood then stays, and this SET rebuilds the main file from it). */
    if(have==0&&!backup){
        if(raw_read_cap(ppath,prev,sizeof(prev),&prev_n))goto done;
        if(create_file(lstage,prev,prev_n)||rename(lstage,lgood)){(void)unlink(lstage);goto done;}
    }
    if(have==1&&profile_initial(path,def,body,sizeof(body),&n))goto done;
    next=now;next.revision=now.revision+1;next.stored=1;strcpy(next.value,value);
    snprintf(num,sizeof(num),"%llu",(unsigned long long)next.revision);
    if(profile_encode(m,body,&n,sizeof(body),value)||profile_put(body,&n,sizeof(body),PROFILE_REV_KEY,num))goto done;
    snprintf(crcline,sizeof(crcline),"crc32=%08x\n",(unsigned)mibr_view_profile_crc32(body,n));
    if(n+strlen(crcline)>=sizeof(body))goto done;
    memcpy(body+n,crcline,strlen(crcline)+1);n+=strlen(crcline);
    if(create_file(stage,body,n)||rename(stage,ppath))goto done;
    renamed=1;
    if(sync_dir(ppath)||profile_load(def,m,path,&confirm,err,sizeof(err))||!same(&confirm,&next))goto done;
    rc=0;
done:
    if(rc&&!renamed)(void)unlink(stage);
    ro=guard->restore_ro(guard->context);
    if(ro)return failure(error,cap,"RO_RESTORE_FAILED");
    if(rc)return failure(error,cap,renamed?"UNKNOWN_COMMIT":"STORAGE_UNAVAILABLE");
    if(profile_load(def,m,path,&confirm,err,sizeof(err))||!same(&confirm,&next))
        return failure(error,cap,"UNKNOWN_COMMIT");
    if(error&&cap)*error=0;
    return 0;
}
int mibr_switch_load(const struct mibr_switch_def *def,const char *path,struct mibr_switch *out,
 char *error,size_t error_cap){
    const struct profile_map *m=profile_map_for(def);
    if(!def||!path||*path!='/'||strlen(path)>=PATH_CAP||!out)return failure(error,error_cap,"INVALID_PATH");
    return m?profile_load(def,m,path,out,error,error_cap):legacy_load(def,path,out,error,error_cap);
}
int mibr_switch_set(const struct mibr_switch_def *def,const char *path,const struct mibr_switch *observed,
 const char *value,uint64_t revision,const struct mibr_switch_guard *guard,
 char *error,size_t cap){
    const struct profile_map *m=profile_map_for(def);
    return m?profile_set(def,m,path,observed,value,revision,guard,error,cap):
             legacy_set(def,path,observed,value,revision,guard,error,cap);
}
