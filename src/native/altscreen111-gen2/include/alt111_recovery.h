/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_ALT111_RECOVERY_H
#define MIBR_ALT111_RECOVERY_H
#include "alt111_policy.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef ALT111_RECOVERY_PATH
#define ALT111_RECOVERY_PATH "/tmp/mibr-alt111-recovery.request"
#endif
#define ALT111_RECOVERY_CAP 256u
#define ALT111_RECOVERY_REASONS (ALT111_KF_BRIDGE_READY|ALT111_KF_SOURCE_GAP|ALT111_KF_LATENCY_RECOVERY|ALT111_KF_LIFECYCLE_RESET)
struct alt111_recovery_request {
    unsigned reasons;
    uint64_t stream,codec,consumer,ordinal,sequence;
};
static inline int alt111_recovery_parse(const char *data,size_t size,
                                        struct alt111_recovery_request *out)
{
    char copy[ALT111_RECOVERY_CAP],*p;
    uint64_t v[6];unsigned i;
    if(!data||!out||size<8u||size>=sizeof(copy)||data[size-1]!='\n'||
       memchr(data,0,size)||memcmp(data,"M1KF1 ",6))return -1;
    memcpy(copy,data,size);copy[size-1]=0;p=copy+6;
    for(i=0;i<6u;++i){
        if(*p<'0'||*p>'9'||(*p=='0'&&p[1]>='0'&&p[1]<='9'))return -1;
        v[i]=0;
        while(*p>='0'&&*p<='9'){
            unsigned digit=(unsigned)(*p-'0');
            if(v[i]>(UINT64_MAX-digit)/10u)return -1;
            v[i]=v[i]*10u+digit;++p;
        }
        if(i<5u ? *p!=' ' : *p!=0)return -1;
        p+=(i<5u);
    }
    if(!v[0]||(v[0]&~(uint64_t)ALT111_RECOVERY_REASONS)||
       !v[1]||!v[2]||!v[3]||!v[4]||!v[5])return -1;
    out->reasons=(unsigned)v[0];out->stream=v[1];out->codec=v[2];
    out->consumer=v[3];out->ordinal=v[4];out->sequence=v[5];
    return 0;
}
static inline int alt111_recovery_render(const struct alt111_recovery_request *r,
                                         char *out,size_t cap)
{
    int n;
    if(!r||!out)return -1;
    n=snprintf(out,cap,"M1KF1 %u %" PRIu64 " %" PRIu64 " %" PRIu64 " %" PRIu64 " %" PRIu64 "\n",
        r->reasons,r->stream,r->codec,r->consumer,r->ordinal,r->sequence);
    return n<0||(size_t)n>=cap ? -1 : n;
}
#ifdef ALT111_RECOVERY_POSIX
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
static inline int alt111_recovery_lock(const char *path)
{
    char name[192];struct flock lock;int fd;
    if(snprintf(name,sizeof(name),"%s.lock",path)>=(int)sizeof(name))return -1;
    fd=open(name,O_RDWR|O_CREAT,0600);if(fd<0)return -1;
    memset(&lock,0,sizeof(lock));lock.l_type=F_WRLCK;lock.l_whence=SEEK_SET;
    if(fcntl(fd,F_SETFD,FD_CLOEXEC)||fcntl(fd,F_SETLK,&lock)){close(fd);return -1;}
    return fd;
}
static inline int alt111_recovery_read(const char *path,struct alt111_recovery_request *r)
{
    char data[ALT111_RECOVERY_CAP];struct stat st;ssize_t n;int fd,rc;
    if(lstat(path,&st))return errno==ENOENT ? 1 : -1;
    if(!S_ISREG(st.st_mode)||st.st_size<=0||st.st_size>=(off_t)sizeof(data))return -1;
    fd=open(path,O_RDONLY);if(fd<0)return -1;
    n=read(fd,data,sizeof(data));close(fd);
    rc=n>0 ? alt111_recovery_parse(data,(size_t)n,r) : -1;
    return rc;
}
static inline int alt111_recovery_publish(const char *path,struct alt111_recovery_request *r)
{
    struct alt111_recovery_request old;
    char data[ALT111_RECOVERY_CAP],tmp[192];int lock,fd,n,ok=0;size_t used=0;
    lock=alt111_recovery_lock(path);if(lock<0)return -1;
    if(!alt111_recovery_read(path,&old) && old.stream==r->stream &&
       old.codec==r->codec && old.consumer==r->consumer)r->reasons|=old.reasons;
    n=alt111_recovery_render(r,data,sizeof(data));
    if(n<=0||snprintf(tmp,sizeof(tmp),"%s.new.%ld",path,(long)getpid())>=(int)sizeof(tmp)){
        close(lock);return -1;
    }
    fd=open(tmp,O_WRONLY|O_CREAT|O_TRUNC,0600);
    if(fd>=0){
        while(used<(size_t)n){
            ssize_t w=write(fd,data+used,(size_t)n-used);
            if(w<0&&errno==EINTR)continue;
            if(w<=0)break;
            used+=(size_t)w;
        }
        if(!close(fd)&&used==(size_t)n)ok=!rename(tmp,path);
        if(!ok)(void)unlink(tmp);
    }
    close(lock);return ok ? 0 : -1;
}
static inline int alt111_recovery_take(const char *path,struct alt111_recovery_request *r)
{
    int lock,rc;
    if(access(path,F_OK))return errno==ENOENT ? 1 : -1;
    lock=alt111_recovery_lock(path);
    if(lock<0)return 1;
    rc=alt111_recovery_read(path,r);
    if(rc!=1 && unlink(path))rc=-1;
    close(lock);return rc;
}
#endif
#endif
