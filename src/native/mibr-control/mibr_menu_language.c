/* SPDX-License-Identifier: GPL-3.0-or-later
 * CAS + atomic, readback-verified MIBR-only menu language store. No OEM
 * DSIPersistence, no Classic111 registry entry, no GPS or CarPlay side effects.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_menu_language.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <unistd.h>
#define LANG_CAP 96u
#define PATH_CAP 512u
static int failure(char *error,size_t cap,const char *value){
    if(error&&cap)snprintf(error,cap,"%s",value);
    return -1;
}
int mibr_menu_language_valid(const char *v){
    return v&&(!strcmp(v,"AUTO")||!strcmp(v,"de")||!strcmp(v,"en"));
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
    if(!S_ISREG(before.st_mode)||before.st_size<1||before.st_size>=LANG_CAP||
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
static int canonical(const struct mibr_menu_language *state,char *out,size_t cap){
    int n=snprintf(out,cap,"MIBR_MENU_LANGUAGE/1\nrevision=%llu\nvalue=%s\n",
        (unsigned long long)state->revision,state->value);
    return n>0&&(size_t)n<cap?n:-1;
}
int mibr_menu_language_load(const char *path,struct mibr_menu_language *out,
 char *error,size_t error_cap){
    char raw[LANG_CAP],want[LANG_CAP];size_t n=0;int rc,k;
    const char *r,*v,*end;
    if(!path||*path!='/'||strlen(path)>=PATH_CAP||!out)
        return failure(error,error_cap,"INVALID_PATH");
    memset(out,0,sizeof(*out));strcpy(out->value,"AUTO");
    rc=raw_read(path,raw,&n);
    if(rc==1){if(error&&error_cap)*error=0;return 0;}
    if(rc)return failure(error,error_cap,"STORAGE_UNAVAILABLE");
    if(n<35||memcmp(raw,"MIBR_MENU_LANGUAGE/1\nrevision=",30))
        return failure(error,error_cap,"INVALID_LANGUAGE_FILE");
    r=raw+30;end=strchr(r,'\n');
    if(!end||decimal(r,(size_t)(end-r),&out->revision))
        return failure(error,error_cap,"INVALID_LANGUAGE_FILE");
    v=end+1;
    if(strncmp(v,"value=",6))return failure(error,error_cap,"INVALID_LANGUAGE_FILE");
    v+=6;end=strchr(v,'\n');
    if(!end||end[1]||end-v>=5)return failure(error,error_cap,"INVALID_LANGUAGE_FILE");
    memcpy(out->value,v,(size_t)(end-v));out->value[end-v]=0;
    if(!mibr_menu_language_valid(out->value))return failure(error,error_cap,"INVALID_LANGUAGE_FILE");
    k=canonical(out,want,sizeof(want));
    if(k<0||(size_t)k!=n||memcmp(raw,want,n))return failure(error,error_cap,"INVALID_LANGUAGE_FILE");
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
static int same(const struct mibr_menu_language *a,const struct mibr_menu_language *b){
    return a->stored==b->stored&&a->revision==b->revision&&!strcmp(a->value,b->value);
}
int mibr_menu_language_set(const char *path,const struct mibr_menu_language *observed,
 const char *value,uint64_t revision,const struct mibr_menu_language_guard *guard,
 char *error,size_t cap){
    struct mibr_menu_language now,next,confirm;char buf[LANG_CAP],stage[PATH_CAP],err[80];
    int n,rc=-1,renamed=0,ro;
    if(!path||strlen(path)>PATH_CAP-40||!observed||!mibr_menu_language_valid(value)||
       !guard||!guard->enter_rw||!guard->restore_ro)
        return failure(error,cap,"INVALID_VALUE");
    if(mibr_menu_language_load(path,&now,err,sizeof(err)))return failure(error,cap,err);
    if(revision!=observed->revision||!same(&now,observed))
        return failure(error,cap,"STALE_REVISION");
    if(!strcmp(now.value,value))return 1;
    if(revision==UINT64_MAX)return failure(error,cap,"REVISION_EXHAUSTED");
    next=now;next.revision++;next.stored=1;
    strcpy(next.value,value);n=canonical(&next,buf,sizeof(buf));
    if(n<0)return failure(error,cap,"INVALID_LANGUAGE_FILE");
    if(snprintf(stage,sizeof(stage),"%s.stage.%ld",path,(long)getpid())>=(int)sizeof(stage))
        return failure(error,cap,"INVALID_PATH");
    if(guard->enter_rw(guard->context))return failure(error,cap,"STORAGE_UNAVAILABLE");
    if(mibr_menu_language_load(path,&now,err,sizeof(err))||!same(&now,observed))
        goto done;
    if(create_file(stage,buf,(size_t)n)||rename(stage,path))goto done;
    renamed=1;
    if(sync_dir(path)||mibr_menu_language_load(path,&confirm,err,sizeof(err))||
       !same(&confirm,&next))goto done;
    rc=0;
done:
    /* clean up while still RW: a stage left on flash blocks the next broker start */
    if(rc&&!renamed)(void)unlink(stage);
    ro=guard->restore_ro(guard->context);
    if(ro)return failure(error,cap,"RO_RESTORE_FAILED");
    if(rc){return failure(error,cap,renamed?"UNKNOWN_COMMIT":"STORAGE_UNAVAILABLE");}
    if(mibr_menu_language_load(path,&confirm,err,sizeof(err))||!same(&confirm,&next))
        return failure(error,cap,"UNKNOWN_COMMIT");
    if(error&&cap)*error=0;
    return 0;
}
