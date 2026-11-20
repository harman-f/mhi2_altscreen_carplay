#define _POSIX_C_SOURCE 200809L
#include "mibr_durable_switch.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>
static int granted(void *x){(void)x;return 0;}
static int restored(void *x){(void)x;return 0;}

static void write_profile(const char *ppath,const char *body){
    char buf[4096];FILE *f;
    snprintf(buf,sizeof(buf),"%scrc32=%08x\n",body,(unsigned)mibr_view_profile_crc32(body,strlen(body)));
    f=fopen(ppath,"w");assert(f);fputs(buf,f);fclose(f);
}
static void read_all(const char *p,char *buf,size_t cap){
    FILE *f=fopen(p,"r");size_t n;assert(f);n=fread(buf,1,cap-1,f);fclose(f);buf[n]=0;
}
/* Profile-backed switch: one shared MIBR_NAV_VIEW_PROFILES/3 file, legacy file only as migration source. */
static void profile_one(const struct mibr_switch_def *def,const char *path,const char *a,const char *b){
    char ppath[600],lgood[620],raw[4096],error[80],legacy[96];
    struct mibr_switch state,after;
    struct mibr_switch_guard guard={granted,restored,NULL};
    FILE *f;
    snprintf(ppath,sizeof(ppath),"%s.profile",path);
    /* migration: a legacy value is reported until the first SET */
    snprintf(legacy,sizeof(legacy),"%s\nrevision=7\nvalue=%s\n",def->magic,a);
    f=fopen(path,"w");assert(f);fputs(legacy,f);fclose(f);
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error)));
    assert(state.stored&&state.revision==7&&!strcmp(state.value,a));
    assert(!mibr_switch_set(def,path,&state,b,7,&guard,error,sizeof(error)));
    assert(!mibr_switch_load(def,path,&after,error,sizeof(error)));
    assert(after.stored&&after.revision==8&&!strcmp(after.value,b));
    read_all(ppath,raw,sizeof(raw));
    assert(!strncmp(raw,"MIBR_NAV_VIEW_PROFILES/3\nversion=3\n",35)&&strstr(raw,"\nunit.revision=8\n")&&strstr(raw,"\ncrc32="));
    /* the legacy file is never written again */
    read_all(path,raw,sizeof(raw));assert(!strcmp(raw,legacy));
    assert(!unlink(path));
    /* stale revision and invalid value refused; same value is a no-op */
    assert(mibr_switch_set(def,path,&state,a,7,&guard,error,sizeof(error))!=0);
    assert(mibr_switch_set(def,path,&after,"maybe",8,&guard,error,sizeof(error))!=0);
    assert(mibr_switch_set(def,path,&after,b,8,&guard,error,sizeof(error))==1);
    /* configurator keys the unit does not know survive a SET byte for byte */
    read_all(ppath,raw,sizeof(raw));
    *strstr(raw,"crc32=")=0;
    strcat(raw,"view.center.native.tube=on\nview.center.geometry.zoom=70\n");
    write_profile(ppath,raw);
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error))&&state.revision==8&&!strcmp(state.value,b));
    assert(!mibr_switch_set(def,path,&state,a,8,&guard,error,sizeof(error)));
    read_all(ppath,raw,sizeof(raw));
    assert(strstr(raw,"\nview.center.native.tube=on\nview.center.geometry.zoom=70\n")&&strstr(raw,"\nunit.revision=9\n"));
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error))&&!strcmp(state.value,a));
    /* .lastgood = the previous valid file (revision 8); a damaged main file falls back to it, and the next SET
     * rebuilds the main file from it without touching the backup */
    snprintf(lgood,sizeof(lgood),"%s.lastgood",ppath);
    read_all(lgood,raw,sizeof(raw));
    assert(strstr(raw,"\nunit.revision=8\n")&&strstr(raw,"\nview.center.native.tube=on\n"));
    f=fopen(ppath,"w");assert(f);fputs("MIBR_NAV_VIEW_PROFILES/3\nversion=3\ncrc32=00000000\n",f);fclose(f);
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error))&&state.revision==8&&!strcmp(state.value,b));
    assert(!mibr_switch_set(def,path,&state,a,8,&guard,error,sizeof(error)));
    read_all(ppath,raw,sizeof(raw));
    assert(strstr(raw,"\nunit.revision=9\n")&&strstr(raw,"\nview.center.native.tube=on\n"));
    read_all(lgood,raw,sizeof(raw));assert(strstr(raw,"\nunit.revision=8\n"));
    assert(!unlink(lgood));
    /* a configurator file without unit.revision is revision 0; a missing key means the default */
    write_profile(ppath,"MIBR_NAV_VIEW_PROFILES/3\nversion=3\nbrand=skoda\n");
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error))&&state.revision==0&&!state.stored&&!strcmp(state.value,b));
    /* damaged crc, duplicate key or foreign magic: not taken */
    f=fopen(ppath,"w");assert(f);fputs("MIBR_NAV_VIEW_PROFILES/3\nversion=3\ncrc32=00000000\n",f);fclose(f);
    assert(mibr_switch_load(def,path,&state,error,sizeof(error))!=0);
    write_profile(ppath,"MIBR_NAV_VIEW_PROFILES/3\nversion=3\nversion=3\n");
    assert(mibr_switch_load(def,path,&state,error,sizeof(error))!=0);
    write_profile(ppath,"MIBR_NAV_VIEW_PROFILES/2\nversion=2\n");
    assert(mibr_switch_load(def,path,&state,error,sizeof(error))!=0);
    assert(!unlink(ppath));
    (void)unlink(lgood);
}
static void one(const struct mibr_switch_def *def){
    char dir[]="/tmp/mibr-switch-host-XXXXXX",expect[96],damaged[96],path[512],error[80];
    struct mibr_switch state,after;
    struct mibr_switch_guard guard={granted,restored,NULL};
    FILE *f;char raw[96];size_t n;
    assert(mkdtemp(dir)!=NULL);
    assert(snprintf(path,sizeof(path),"%s/switch.conf",dir)>0);
    /* a = a value other than the default, b = the default */
    char a[20]="10,58,100,100";const char *b=def->default_value;
    if(def->values){
        const char *at=def->values;
        size_t k=strcspn(at,"|");
        if(!strncmp(at,b,k)&&!b[k]){at+=k+1;k=strcspn(at,"|");}
        assert(k<sizeof(a));memcpy(a,at,k);a[k]=0;
    }
    assert(mibr_switch_valid(def,a)&&mibr_switch_valid(def,b)&&
           !mibr_switch_valid(def,"yes")&&!mibr_switch_valid(def,"")&&!mibr_switch_valid(def,"o"));
    /* missing file = default off */
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error)));
    assert(state.revision==0&&!state.stored&&!strcmp(state.value,b));
    if(mibr_switch_profile_backed(def)){profile_one(def,path,a,b);assert(!rmdir(dir));return;}
    assert(!mibr_switch_set(def,path,&state,a,0,&guard,error,sizeof(error)));
    assert(!mibr_switch_load(def,path,&after,error,sizeof(error)));
    assert(after.stored&&after.revision==1&&!strcmp(after.value,a));
    f=fopen(path,"r");assert(f);n=fread(raw,1,sizeof(raw)-1,f);fclose(f);raw[n]=0;
    snprintf(expect,sizeof(expect),"%s\nrevision=1\nvalue=%s\n",def->magic,a);
    assert(!strcmp(raw,expect));
    /* stale revision and invalid value refused */
    assert(mibr_switch_set(def,path,&state,b,0,&guard,error,sizeof(error))!=0);
    assert(mibr_switch_set(def,path,&after,"maybe",1,&guard,error,sizeof(error))!=0);
    assert(!mibr_switch_set(def,path,&after,b,1,&guard,error,sizeof(error)));
    assert(!mibr_switch_load(def,path,&state,error,sizeof(error)));
    assert(state.revision==2&&!strcmp(state.value,b));
    assert(mibr_switch_set(def,path,&state,b,2,&guard,error,sizeof(error))==1);
    /* a foreign or damaged file is not taken as a value */
    f=fopen(path,"w");assert(f);snprintf(damaged,sizeof(damaged),"%s\nrevision=2\nvalue=onnnnnnnnn\n",def->magic);fputs(damaged,f);fclose(f);
    assert(mibr_switch_load(def,path,&state,error,sizeof(error))!=0);
    assert(!unlink(path));assert(!rmdir(dir));
}
int main(void){
    unsigned i;
    int set=-1;
    mibr_switch_platform_path=NULL;
    for(i=0;i<MIBR_SWITCH_COUNT;i++)one(&mibr_switch_defs[i]);
    /* the file names and verbs the supervisor, the menu and earlier installs rely on */
    assert(!strcmp(mibr_switch_defs[0].magic,"MIBR_CARPLAY_NAV/1"));
    assert(!strcmp(mibr_switch_defs[0].path,"/mnt/app/root/mibr/config/navigation/carplay-nav.conf"));
    assert(!strcmp(mibr_switch_defs[1].magic,"MIBR_SD_LOG/1"));
    assert(!strcmp(mibr_switch_defs[1].path,"/mnt/app/root/mibr/config/features/sd-log.conf"));
    assert(mibr_switch_for_op("SD_LOG_SET",&set)==&mibr_switch_defs[1]&&set==1);
    assert(mibr_switch_for_op("CARPLAY_NAV_GET",&set)==&mibr_switch_defs[0]&&set==0);
    assert(mibr_switch_for_op("NOPE",&set)==NULL);
    assert(!strcmp(mibr_switch_defs[2].default_value,"dist"));
    assert(mibr_switch_valid(&mibr_switch_defs[2],"street")&&!mibr_switch_valid(&mibr_switch_defs[2],"both"));
    assert(!mibr_switch_valid(&mibr_switch_defs[0],"street"));
    {
        const struct mibr_switch_def *voll=mibr_switch_for_op("SAFE_VOLL_GET",&set);
        assert(voll&&voll->default_value&&mibr_switch_valid(voll,voll->default_value));
        assert(mibr_switch_valid(voll,"0,0,1010,376")&&mibr_switch_valid(voll,"910,316,100,60"));
        assert(!mibr_switch_valid(voll,"911,58,100,60")&&!mibr_switch_valid(voll,"0,317,100,60"));
        assert(!mibr_switch_valid(voll,"0,0,99,60")&&!mibr_switch_valid(voll,"0,0,100,59"));
        assert(!mibr_switch_valid(voll,"00,0,100,60")&&!mibr_switch_valid(voll,"0,0,100")&&
               !mibr_switch_valid(voll,"0,0,100,60,1")&&!mibr_switch_valid(voll,"-1,0,100,60"));
    }
    {
        char dir[]="/tmp/mibr-platform-host-XXXXXX",path[256],value[20];FILE *f;
        const struct mibr_switch_def *voll=mibr_switch_for_op("SAFE_VOLL_GET",&set);
        const struct mibr_switch_def *text=&mibr_switch_defs[2];
        assert(mkdtemp(dir));
        snprintf(path,sizeof(path),"%s/defaults.conf",dir);
        mibr_switch_platform_path=path;
        mibr_switch_default(voll,value,sizeof(value));
        assert(!strcmp(value,voll->default_value));
        f=fopen(path,"w");assert(f);
        fputs("# comment\nsafe_voll=10,50,900,200\nsafe_wide=0,0,5,5\nnav_line=street\nsd_log=maybe\n",f);fclose(f);
        mibr_switch_default(voll,value,sizeof(value));
        assert(!strcmp(value,"10,50,900,200"));
        mibr_switch_default(text,value,sizeof(value));
        assert(!strcmp(value,"street"));
        /* an invalid platform value means the compiled default */
        mibr_switch_default(mibr_switch_for_op("SAFE_WIDE_GET",&set),value,sizeof(value));
        assert(!strcmp(value,"200,58,590,248"));
        mibr_switch_default(&mibr_switch_defs[1],value,sizeof(value));
        assert(!strcmp(value,"off"));
        assert(!unlink(path));assert(!rmdir(dir));
        mibr_switch_platform_path=NULL;
    }
    puts("MIBR_DURABLE_SWITCH_HOST_PASS");
    return 0;
}
