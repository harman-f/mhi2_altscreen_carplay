/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "mibr_v3_runtime_observer.h"
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#define GEN2_CAP 8192u
static int exact_uint(const char *text,const char *name,uint64_t *value){
    char prefix[96];size_t n;const char *p=text;int seen=0;
    if(snprintf(prefix,sizeof(prefix),"%s=",name)>=(int)sizeof(prefix))return -1;
    n=strlen(prefix);
    while(p&&*p){
        const char *end=strchr(p,'\n'),*v;size_t len;
        if(!end)return -1;
        if(!strncmp(p,prefix,n)){
            unsigned long long z;char *stop;
            if(seen++||end==p+n)return -1;
            v=p+n;len=(size_t)(end-v);
            if(len>20||*v<'0'||*v>'9'||(len>1&&*v=='0'))return -1;
            errno=0;z=strtoull(v,&stop,10);
            if(errno||stop!=end)return -1;
            *value=(uint64_t)z;
        }
        p=end+1;
    }
    return seen==1?0:-1;
}
int mibr_v3_runtime_read(const char *path,struct mibr_v3_runtime_observation *out){
    char text[GEN2_CAP+1];struct stat a,z;struct timespec now;
    uint64_t session=0,stream=0,active=0,desired=0,confirmed=0,present=0,valid=0;
    int fd;size_t size=0;ssize_t n;
    if(!out)return -1;
    memset(out,0,sizeof(*out));
    if(!path||lstat(path,&a)||!S_ISREG(a.st_mode)||a.st_size<1||
       a.st_size>GEN2_CAP||clock_gettime(CLOCK_REALTIME,&now)||
       a.st_mtime>now.tv_sec||now.tv_sec-a.st_mtime>3)return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&z)||!S_ISREG(z.st_mode)||a.st_dev!=z.st_dev||a.st_ino!=z.st_ino||
       a.st_size!=z.st_size){close(fd);return -1;}
    while(size<(size_t)z.st_size){
        n=read(fd,text+size,(size_t)z.st_size-size);
        if(n<0&&errno==EINTR)continue;
        if(n<=0){close(fd);return -1;}size+=(size_t)n;
    }
    if(close(fd)||!size||text[size-1]!='\n'||memchr(text,0,size))return -1;
    text[size]=0;
    if(exact_uint(text,"control_session",&session)||
       exact_uint(text,"stream_gen",&stream)||
       exact_uint(text,"settings_active_revision",&active)||
       exact_uint(text,"settings_desired_revision",&desired)||
       exact_uint(text,"settings_active_confirmed",&confirmed)||
       exact_uint(text,"settings_active_present",&present)||
       exact_uint(text,"settings_valid",&valid)||
       confirmed>1||present>1||valid>1)return -1;
    /* The source uses distinct snapshots for core/session/settings locks. This
     * is observed diagnostics, not a transactionally correlated key-level ACK.
     * A disconnected/no-active source is observed but is NOT an ACTIVE claim. */
    out->observed=1;out->session=session;out->stream_gen=stream;
    out->active_revision=present?active:0;out->desired_revision=desired;
    out->confirmed=valid&&present&&confirmed&&session&&stream&&active;
    return 0;
}
