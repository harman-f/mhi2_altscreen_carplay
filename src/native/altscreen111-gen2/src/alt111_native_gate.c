/* Native payload exclusion around the historically retained writev gate.
 * No device is opened by this component. It tracks the qualified target ABI:
 * open/open64/close, dup/dup2, write/writev and QNX device-control calls.
 * Inherited descriptors and other descriptor aliases require target audit.
 * SPDX-License-Identifier: GPL-3.0-or-later */
#define _GNU_SOURCE
#include "alt111_native_gate.h"
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/uio.h>
#include <time.h>
#include <unistd.h>
#ifdef __QNXNTO__
#include <devctl.h>
#endif

#define GATE_TARGET "/dev/mlb/isoTX2"
#define GATE_FD_CAP 2048u
static int (*next_open)(const char *,int,...);
static int (*next_open64)(const char *,int,...);
static int (*next_close)(int),(*next_dup)(int),(*next_dup2)(int,int);
static ssize_t (*next_write)(int,const void *,size_t);
static ssize_t (*next_writev)(int,const struct iovec *,int);
#ifdef __QNXNTO__
static int (*next_devctl)(int,int,void *,size_t,int *);
#endif
static pthread_once_t resolve_key_once=PTHREAD_ONCE_INIT,resolve_once=PTHREAD_ONCE_INIT;
static pthread_key_t resolving_key;
static unsigned resolving_key_valid;
static pthread_mutex_t gate_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t fd_lifecycle_lock=PTHREAD_MUTEX_INITIALIZER;
static unsigned char tracked[GATE_FD_CAP];
static uint64_t inflight,dropped,tracked_count,request_token;
static unsigned suppression,unsupported;

static void create_resolving_key(void){resolving_key_valid=pthread_key_create(&resolving_key,NULL)==0;}
static void resolve_symbols(void)
{
    next_write=dlsym(RTLD_NEXT,"write");next_writev=dlsym(RTLD_NEXT,"writev");
    next_open=dlsym(RTLD_NEXT,"open");next_open64=dlsym(RTLD_NEXT,"open64");
    next_close=dlsym(RTLD_NEXT,"close");next_dup=dlsym(RTLD_NEXT,"dup");next_dup2=dlsym(RTLD_NEXT,"dup2");
    if(!next_open64)next_open64=next_open;
#ifdef __QNXNTO__
    next_devctl=dlsym(RTLD_NEXT,"devctl");
#endif
}
static void resolve_real(void)
{
    pthread_once(&resolve_key_once,create_resolving_key);
    if(!resolving_key_valid)return;
    if(pthread_getspecific(resolving_key))return;
    if(pthread_setspecific(resolving_key,(void *)(uintptr_t)1))return;
    pthread_once(&resolve_once,resolve_symbols);
    (void)pthread_setspecific(resolving_key,NULL);
}
static const char *target_path(void)
{
#ifdef ALT111_NATIVE_GATE_TEST
    const char *path=getenv("ALT111_NATIVE_GATE_TARGET");if(path)return path;
#endif
    return GATE_TARGET;
}
static const char *request_path(void)
{
#ifdef ALT111_NATIVE_GATE_TEST
    const char *path=getenv("ALT111_NATIVE_GATE_REQUEST");if(path)return path;
#endif
    return ALT111_NATIVE_GATE_REQUEST;
}
static const char *status_path(void)
{
#ifdef ALT111_NATIVE_GATE_TEST
    const char *path=getenv("ALT111_NATIVE_GATE_STATUS");if(path)return path;
#endif
    return ALT111_NATIVE_GATE_STATUS;
}
static uint64_t now_ms(void)
{
    struct timespec ts;if(clock_gettime(CLOCK_MONOTONIC,&ts))return 0;
    return (uint64_t)ts.tv_sec*1000u+(uint64_t)ts.tv_nsec/1000000u;
}
static void track_fd_locked(int fd,unsigned value)
{
    if(fd<0)return;
    if((unsigned)fd>=GATE_FD_CAP){if(value)unsupported=1u;return;}
    if(tracked[fd]==value)return;
    if(value)++tracked_count;else if(tracked_count)--tracked_count;
    tracked[fd]=(unsigned char)value;
}
static unsigned target_fd_locked(int fd)
{
    return fd>=0 && (unsigned)fd<GATE_FD_CAP && tracked[fd];
}
static uint64_t read_request(unsigned *exists)
{
    char data[32];ssize_t n;uint64_t value=0;unsigned i;int fd;struct stat before,after;
    *exists=lstat(request_path(),&before)==0;
    if(!*exists && errno!=ENOENT){*exists=1u;return 0;}
    if(!*exists)return 0;
    if(!S_ISREG(before.st_mode)||before.st_size<2||before.st_size>21)return 0;
    fd=next_open(request_path(),O_RDONLY|O_NONBLOCK);if(fd<0)return 0;
    if(fstat(fd,&after)||!S_ISREG(after.st_mode)||before.st_dev!=after.st_dev||
       before.st_ino!=after.st_ino){next_close(fd);return 0;}
    n=read(fd,data,sizeof(data));next_close(fd);
    if(n<2||n>21||data[n-1]!='\n')return 0;
    for(i=0;i<(unsigned)n-1u;++i){
        unsigned digit=(unsigned)(data[i]-'0');
        if(digit>9u||value>(UINT64_MAX-digit)/10u)return 0;
        value=value*10u+digit;
    }
    return value;
}
static void publish_status(const struct alt111_native_gate_status *snapshot)
{
    char data[ALT111_NATIVE_GATE_CAP],temp[192];size_t used=0;int fd,n;
    n=snprintf(data,sizeof(data),"M1GATE1 %" PRIu64 " %ld %" PRIu64 " %" PRIu64 " %" PRIu64 " %" PRIu64 " %u\n",
        snapshot->token,(long)getpid(),snapshot->tracked,snapshot->inflight,snapshot->dropped,
        snapshot->heartbeat,(unsigned)snapshot->state);
    if(n<=0||(size_t)n>=sizeof(data)||
       snprintf(temp,sizeof(temp),"%s.new.%ld",status_path(),(long)getpid())>=(int)sizeof(temp))return;
    fd=next_open(temp,O_WRONLY|O_CREAT|O_TRUNC,0600);if(fd<0)return;
    while(used<(size_t)n){
        ssize_t w=next_write(fd,data+used,(size_t)n-used);
        if(w<0&&errno==EINTR)continue;
        if(w<=0)break;
        used+=(size_t)w;
    }
    if(!next_close(fd)&&used==(size_t)n)(void)rename(temp,status_path());
    (void)unlink(temp);
}
static void *gate_worker(void *unused)
{
    (void)unused;
    for(;;){
        struct alt111_native_gate_status snapshot;
        unsigned exists;uint64_t token=read_request(&exists);
        pthread_mutex_lock(&gate_lock);
        suppression=exists;request_token=token;
        snapshot.token=token;snapshot.process=(uint64_t)getpid();snapshot.tracked=tracked_count;
        snapshot.inflight=inflight;snapshot.dropped=dropped;snapshot.heartbeat=now_ms();
        snapshot.state=!suppression ? 0u : unsupported ? 3u :
            inflight || !tracked_count || !request_token ? 1u : 2u;
        pthread_mutex_unlock(&gate_lock);
        /* The downstream frozen gate may call our write hook while updating
         * its own counters. No real libc/interposer I/O runs under gate_lock. */
        publish_status(&snapshot);
        usleep(20000);
    }
    return NULL;
}
static int open_target(const char *path,int flags,mode_t mode,unsigned large)
{
    int fd;unsigned value=path && !strcmp(path,target_path());resolve_real();
    if(!next_open||!next_open64){errno=ENOSYS;return -1;}
    pthread_mutex_lock(&fd_lifecycle_lock);
    fd=large ? next_open64(path,flags,mode) : next_open(path,flags,mode);
    if(fd>=0){
        pthread_mutex_lock(&gate_lock);track_fd_locked(fd,value);pthread_mutex_unlock(&gate_lock);
        if(value && (unsigned)fd>=GATE_FD_CAP){next_close(fd);errno=EMFILE;fd=-1;}
    }
    pthread_mutex_unlock(&fd_lifecycle_lock);
    return fd;
}
int open(const char *path,int flags,...)
{
    mode_t mode=0;if(flags&O_CREAT){va_list ap;va_start(ap,flags);mode=va_arg(ap,mode_t);va_end(ap);}
    return open_target(path,flags,mode,0u);
}
int open64(const char *path,int flags,...)
{
    mode_t mode=0;if(flags&O_CREAT){va_list ap;va_start(ap,flags);mode=va_arg(ap,mode_t);va_end(ap);}
    return open_target(path,flags,mode,1u);
}
int close(int fd)
{
    int rc;resolve_real();if(!next_close){errno=ENOSYS;return -1;}
    pthread_mutex_lock(&fd_lifecycle_lock);
    rc=next_close(fd);
    pthread_mutex_lock(&gate_lock);
    if(!rc)track_fd_locked(fd,0u);
    else if(target_fd_locked(fd))unsupported=1u;
    pthread_mutex_unlock(&gate_lock);pthread_mutex_unlock(&fd_lifecycle_lock);return rc;
}
int dup(int fd)
{
    int out;unsigned value;resolve_real();if(!next_dup){errno=ENOSYS;return -1;}
    pthread_mutex_lock(&fd_lifecycle_lock);
    pthread_mutex_lock(&gate_lock);value=target_fd_locked(fd);pthread_mutex_unlock(&gate_lock);
    out=next_dup(fd);
    if(out>=0){pthread_mutex_lock(&gate_lock);track_fd_locked(out,value);pthread_mutex_unlock(&gate_lock);}
    if(value && out>=0 && (unsigned)out>=GATE_FD_CAP){next_close(out);errno=EMFILE;out=-1;}
    pthread_mutex_unlock(&fd_lifecycle_lock);return out;
}
int dup2(int fd,int destination)
{
    int out;unsigned value;resolve_real();if(!next_dup2){errno=ENOSYS;return -1;}
    pthread_mutex_lock(&fd_lifecycle_lock);
    pthread_mutex_lock(&gate_lock);value=target_fd_locked(fd);pthread_mutex_unlock(&gate_lock);
    if(value && destination>=0 && (unsigned)destination>=GATE_FD_CAP) {
        pthread_mutex_lock(&gate_lock);unsupported=1u;pthread_mutex_unlock(&gate_lock);
        pthread_mutex_unlock(&fd_lifecycle_lock);errno=EMFILE;return -1;
    }
    out=next_dup2(fd,destination);
    if(out>=0){pthread_mutex_lock(&gate_lock);track_fd_locked(out,value);pthread_mutex_unlock(&gate_lock);}
    pthread_mutex_unlock(&fd_lifecycle_lock);return out;
}
static unsigned enter_io(int fd)
{
    unsigned mode=0;
    pthread_mutex_lock(&gate_lock);
    if(target_fd_locked(fd)){
        if(suppression){++dropped;mode=2u;}
        else{++inflight;mode=1u;}
    }
    pthread_mutex_unlock(&gate_lock);return mode;
}
static void leave_io(unsigned mode)
{
    if(mode!=1u)return;
    pthread_mutex_lock(&gate_lock);--inflight;pthread_mutex_unlock(&gate_lock);
}
ssize_t write(int fd,const void *data,size_t size)
{
    ssize_t rc;unsigned mode;int saved=errno;
    resolve_real();if(!next_write){errno=ENOSYS;return -1;}
    mode=enter_io(fd);
    if(mode==2u){if(size>SIZE_MAX/2u){errno=EINVAL;return -1;}errno=saved;return (ssize_t)size;}
    rc=next_write(fd,data,size);saved=errno;leave_io(mode);errno=saved;return rc;
}
ssize_t writev(int fd,const struct iovec *iov,int count)
{
    ssize_t rc;unsigned mode;int i,saved=errno;size_t size=0;
    resolve_real();if(!next_writev){errno=ENOSYS;return -1;}
    mode=enter_io(fd);
    if(mode==2u){
        if(count<0 || (count>0&&!iov)){errno=EINVAL;return -1;}
        for(i=0;i<count;++i){if(iov[i].iov_len>SIZE_MAX-size){errno=EINVAL;return -1;}size+=iov[i].iov_len;}
        if(size>SIZE_MAX/2u){errno=EINVAL;return -1;}
        errno=saved;return (ssize_t)size;
    }
    rc=next_writev(fd,iov,count);saved=errno;leave_io(mode);errno=saved;return rc;
}
#ifdef __QNXNTO__
int devctl(int fd,int command,void *data,size_t size,int *info)
{
    unsigned mode;int rc;
    resolve_real();if(!next_devctl)return ENOSYS;
    mode=enter_io(fd);
    if(mode==2u){
        /* Queries are read-only. Never let native flush/start/control mutate
         * the queue while the custom writer owns it. */
        if(command!=0x4004050c && command!=0x4004050d && command!=0x40040510){
            pthread_mutex_lock(&gate_lock);unsupported=1u;pthread_mutex_unlock(&gate_lock);
            return EBUSY;
        }
    }
    rc=next_devctl(fd,command,data,size,info);leave_io(mode);return rc;
}
#endif
__attribute__((constructor))
static void native_gate_init(void)
{
    pthread_t worker;unsigned exists;
    resolve_real();
    if(!next_open||!next_close||!next_write||!next_writev||!next_dup||!next_dup2)return;
#ifdef __QNXNTO__
    if(!next_devctl)return;
#endif
    request_token=read_request(&exists);suppression=exists;
    if(!pthread_create(&worker,NULL,gate_worker,NULL))pthread_detach(worker);
}
