/* SPDX-License-Identifier: GPL-3.0-or-later
 * Single-writer CPVC R5 profile candidate -> native validation -> guarded
 * same-directory atomic rename -> directory sync -> readback -> verified RO.
 * Does not reinterpret desired as GEN2 ACTIVE. No shell mount commands.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_profile_store.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#define PROFILE_CAP 8192u
/* Simulate abrupt process loss at known stages only in the isolated HOST
 * test binary. This never compiles into production builds. */
#ifdef ALT111_SETTINGS_TEST
#define HOST_CUT(point) do {const char *v=getenv("MIBR_V3_HOST_CUTPOINT"); \
    if(v&&!strcmp(v,point))_exit(96);} while(0)
#else
#define HOST_CUT(point) do {(void)0;} while(0)
#endif
#define FILEPATH_CAP 512u
static int fail(char *e,size_t c,const char *v){
    if(e&&c)snprintf(e,c,"%s",v);
    return -1;
}
static int read_profile(const char *p,char *buf,size_t *size){
    struct stat before,after;int fd;size_t n=0;ssize_t r;
    if(lstat(p,&before)||!S_ISREG(before.st_mode)||
       before.st_size<1||before.st_size>PROFILE_CAP)return -1;
    fd=open(p,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&after)||!S_ISREG(after.st_mode)||before.st_dev!=after.st_dev||
       before.st_ino!=after.st_ino){close(fd);return -1;}
    while(n<(size_t)after.st_size){
        r=read(fd,buf+n,(size_t)after.st_size-n);
        if(r<0&&errno==EINTR)continue;
        if(r<=0){close(fd);return -1;}n+=(size_t)r;
    }
    if(close(fd)||n!=(size_t)before.st_size||buf[n-1]!='\n'||
       memchr(buf,0,n)||memchr(buf,'\r',n))return -1;
    buf[n]=0;*size=n;return 0;
}
static int profile_candidate(const char *old,size_t n,
    const struct alt111_settings *observed,unsigned selected,const char *value,
    int strict,char *candidate,size_t *next_size){
    char line[ALT111_SETTING_VALUE_CAP+80];unsigned seen[ALTSET_COUNT]={0},count=0;
    size_t p=0,used=0;int found=0;
    while(p<n){
        const char *end=memchr(old+p,'\n',n-p);const char *equal;
        size_t width,keylen,newlen;int id;const char *selected_value;
        if(!end||end==old+p)return -1;
        width=(size_t)(end-(old+p));if(width>=sizeof(line))return -1;
        memcpy(line,old+p,width);line[width]=0;
        equal=strchr(line,'=');
        if(!equal||equal==line||!equal[1])return -1;
        keylen=(size_t)(equal-line);
        if(keylen>64)return -1;
        line[keylen]=0;id=alt111_setting_find(line);
        /* A fixed/read-only descriptor may occur as an unchanged sibling in
         * the original CPVC 45-row profile (e.g. display.uuid). Only the
         * SELECTED mutation is prohibited from targeting a read-only key. */
        if(id<0||seen[id]++||alt111_setting_validate((unsigned)id,equal+1))return -1;
        /* Startup parity is strict. For a SET (r13) a line whose runtime TEMP
         * value was rewritten from outside (iPhone reconnect, GEN2) keeps its
         * profile bytes; only the selected line changes. */
        if(strict&&strcmp(observed->value[id],equal+1))return -1; /* old TEMP/profile parity */
        selected_value=(unsigned)id==selected?value:equal+1;
        if((unsigned)id==selected)found=1;
        newlen=keylen+1+strlen(selected_value)+1;
        if(newlen>PROFILE_CAP-used)return -1;
        memcpy(candidate+used,line,keylen);used+=keylen;
        candidate[used++]='=';
        memcpy(candidate+used,selected_value,strlen(selected_value));
        used+=strlen(selected_value);candidate[used++]='\n';
        count++;p=(size_t)(end-old)+1;
    }
    if(count!=45||!found)return -1;
    candidate[used]=0;*next_size=used;return 0;
}
int mibr_v3_profile_parity(const char *path,const struct alt111_settings *observed){
    char original[PROFILE_CAP+1],candidate[PROFILE_CAP+1];size_t n=0,next=0;
    int id=alt111_setting_find("maxFPS");
    if(!observed||id<0||read_profile(path,original,&n)||
       profile_candidate(original,n,observed,(unsigned)id,observed->value[id],
                         1,candidate,&next)||next!=n||memcmp(candidate,original,n))return -1;
    return 0;
}
static int write_exclusive(const char *path,const char *data,size_t n){
    int fd;size_t used=0;ssize_t k;
    fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);if(fd<0)return -1;
    while(used<n){
        k=write(fd,data+used,n-used);
        if(k<0&&errno==EINTR)continue;
        if(k<=0){close(fd);return -1;}used+=(size_t)k;
    }
    {int synced=fsync(fd);int closed=close(fd);if(synced||closed)return -1;}
    return 0;
}
static int sync_parent(const char *path){
    char parent[FILEPATH_CAP];char *slash;int fd,rc;
    if(strlen(path)>=sizeof(parent))return -1;
    strcpy(parent,path);slash=strrchr(parent,'/');
    if(!slash)return -1;
    if(slash==parent)slash[1]=0;else *slash=0;
    fd=open(parent,O_RDONLY);if(fd<0)return -1;
    rc=fsync(fd);if(close(fd))rc=-1;return rc;
}
int mibr_v3_profile_set(const struct alt111_settings_paths *paths,
    const char *profile_path,const struct alt111_settings *observed,
    unsigned id,const char *value,uint64_t expected_revision,
    const struct mibr_v3_mount_guard *guard,char *error,size_t error_cap){
    struct alt111_settings candidate,after;
    char original[PROFILE_CAP+1],next[PROFILE_CAP+1],readback[PROFILE_CAP+1];
    char staged[FILEPATH_CAP],bakstage[FILEPATH_CAP],backup[FILEPATH_CAP],err[256]={0};
    const char *values[1];unsigned ids[1];size_t oldn=0,newn=0,n=0;
    int rw=0,renamed=0,rc=-1,ro=0,materialized=0;
    if(!paths||!profile_path||profile_path[0]!='/'||!observed||id>=ALTSET_COUNT||
       !value||!guard||!guard->enter_rw||!guard->restore_verified_ro)
        return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    if(observed->revision!=expected_revision||!expected_revision)
        return fail(error,error_cap,"STALE_REVISION");
    if(alt111_setting(id)->read_only||alt111_setting_validate(id,value))
        return fail(error,error_cap,"INVALID_VALUE");
    if(read_profile(profile_path,original,&oldn))
        return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    if(profile_candidate(original,oldn,observed,id,value,0,next,&newn))
        return fail(error,error_cap,"DEPENDENCY_CONFLICT");
    candidate=*observed;
    if(alt111_settings_set(&candidate,id,value,ALT111_TEMP)||
       alt111_settings_validate(&candidate,err,sizeof(err)))
        return fail(error,error_cap,"DEPENDENCY_CONFLICT");
    /* r13: decide "no flash" on the profile bytes, not on the resolved TEMP
     * value. After an outside TEMP rewrite both may differ, and skipping the
     * write would lose the user's choice at the next boot replay. */
    if(newn==oldn&&!memcmp(next,original,oldn)){
        if(!strcmp(observed->value[id],value))return 0; /* no flash, no change */
        ids[0]=id;values[0]=value;
        if(!alt111_settings_mutate(paths,ALT111_TEMP,ids,values,1,
                                  observed->revision,&after,err,sizeof(err))&&
           !strcmp(after.value[id],value))return 1;
        return 2;
    }
    if(snprintf(staged,sizeof(staged),"%s.stage.%ld",profile_path,(long)getpid())>=
       (int)sizeof(staged)||
       snprintf(bakstage,sizeof(bakstage),"%s.lastgood.stage.%ld",profile_path,(long)getpid())>=
       (int)sizeof(bakstage)||
       snprintf(backup,sizeof(backup),"%s.lastgood",profile_path)>=
       (int)sizeof(backup))
        return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    /* The caller proves this is the intended physical RW mount and no old
     * cpvc_config.sh instance can run. We never infer target mount state. */
    if(guard->enter_rw(guard->context))return fail(error,error_cap,"STORAGE_UNAVAILABLE");
    rw=1;
    if(read_profile(profile_path,readback,&n)||n!=oldn||memcmp(readback,original,n))
        goto done;
    if(write_exclusive(bakstage,original,oldn))goto done;
    HOST_CUT("BACKUP_STAGED");
    if(rename(bakstage,backup)||sync_parent(profile_path))goto done;
    HOST_CUT("BACKUP_COMMITTED");
    if(write_exclusive(staged,next,newn))goto done;
    HOST_CUT("PROFILE_STAGED");
    if(rename(staged,profile_path))goto done;
    renamed=1;
    HOST_CUT("PROFILE_RENAMED");
    if(sync_parent(profile_path))goto done;
    HOST_CUT("PROFILE_SYNCED");
    if(read_profile(profile_path,readback,&n)||
       n!=newn||memcmp(readback,next,n))goto done;
    rc=2;
done:
    /* This must be attempted on EVERY path after successful enter_rw. */
    if(rw){ro=guard->restore_verified_ro(guard->context);}
    if(ro){
        rc=-2;fail(error,error_cap,"RO_RESTORE_FAILED");
    }else{
        if(rw)HOST_CUT("RO_VERIFIED");
        if(renamed&&rc<0){rc=-2;fail(error,error_cap,"UNKNOWN_COMMIT");}
        else if(rc<0){fail(error,error_cap,"DURABILITY_UNCONFIRMED");}
    }
    if(rc==2){
        if(read_profile(profile_path,readback,&n)||n!=newn||memcmp(readback,next,n)){
            rc=-2;fail(error,error_cap,"UNKNOWN_COMMIT");
        } else {
            ids[0]=id;values[0]=value;
            /* Volatile compatibility materialization is AFTER durable+RO
             * readback. Failure leaves VERIFIED profile for CPVC boot replay. */
            if(!alt111_settings_mutate(paths,ALT111_TEMP,ids,values,1,
                                      observed->revision,&after,err,sizeof(err))&&
               !strcmp(after.value[id],value))materialized=1;
            rc=materialized?1:2;
        }
    }
    return rc;
}

int mibr_v3_live_apply(const struct alt111_settings_paths *paths,const struct alt111_settings *observed,
    unsigned id,const char *value,uint64_t *revision_out){
    struct alt111_settings after;char err[128]={0};
    const char *values[1];unsigned ids[1];
    if(!paths||!observed||id>=ALTSET_COUNT||!value||!revision_out)return -1;
    ids[0]=id;values[0]=value;
    if(alt111_settings_mutate(paths,ALT111_TEMP,ids,values,1,observed->revision,&after,err,sizeof(err))||
       strcmp(after.value[id],value))return -1;
    *revision_out=after.revision;
    return 0;
}
int mibr_v3_live_revert(const struct alt111_settings_paths *paths,unsigned id,const char *old_value,
    uint64_t revision){
    struct alt111_settings after;char err[128]={0};
    const char *values[1];unsigned ids[1];
    if(!paths||id>=ALTSET_COUNT||!old_value)return -1;
    ids[0]=id;values[0]=old_value;
    return alt111_settings_mutate(paths,ALT111_TEMP,ids,values,1,revision,&after,err,sizeof(err));
}
