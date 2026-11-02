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
    assert(!strcmp(mibr_switch_defs[0].path,"/mnt/app/root/altscreen-u2/config/mibr-carplay-nav.conf"));
    assert(!strcmp(mibr_switch_defs[1].magic,"MIBR_SD_LOG/1"));
    assert(!strcmp(mibr_switch_defs[1].path,"/mnt/app/root/altscreen-u2/config/mibr-sd-log.conf"));
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
