/* SPDX-License-Identifier: GPL-3.0-or-later
 * The lease is a pid file created exclusively. A dead owner's file is taken over; an unreadable one
 * (owner killed between create and write) only once the wait has run out.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_app_rw_lease.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#define STEP_MS 50u
static long owner(const char *path){
    char buf[24];ssize_t n;long v;char *end;
    int fd=open(path,O_RDONLY);
    if(fd<0)return -1;
    n=read(fd,buf,sizeof(buf)-1);
    close(fd);
    if(n<=0)return 0;
    buf[n]=0;
    v=strtol(buf,&end,10);
    return end!=buf&&v>1?v:0;
}
static int create(const char *path){
    char buf[24];int n,rc=0;
    int fd=open(path,O_WRONLY|O_CREAT|O_EXCL,0600);
    if(fd<0)return errno==EEXIST?1:-1;
    n=snprintf(buf,sizeof(buf),"%ld\n",(long)getpid());
    if(write(fd,buf,(size_t)n)!=n)rc=-1;
    if(close(fd))rc=-1;
    if(rc)(void)unlink(path);
    return rc;
}
int mibr_app_rw_lease_acquire(const char *path,unsigned wait_ms){
    struct timespec step={0,(long)STEP_MS*1000000L};unsigned waited=0;
    for(;;){
        long pid;int rc=create(path);
        if(rc==0)return 0;
        if(rc<0)return -1;
        pid=owner(path);
        if(pid==(long)getpid()||(pid>1&&kill((pid_t)pid,0)&&errno==ESRCH)){
            (void)unlink(path);continue;
        }
        if(waited>=wait_ms){
            if(pid!=0)return -1;
            (void)unlink(path);wait_ms+=STEP_MS;continue;
        }
        (void)nanosleep(&step,NULL);waited+=STEP_MS;
    }
}
void mibr_app_rw_lease_release(const char *path){
    if(owner(path)==(long)getpid())(void)unlink(path);
}
