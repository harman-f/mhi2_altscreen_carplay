#define _POSIX_C_SOURCE 200809L
#include "mibr_app_rw_lease.h"
#include <assert.h>
#include <stdio.h>
#include <signal.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
static void put(const char *path,const char *text){FILE *f=fopen(path,"w");assert(f);fputs(text,f);fclose(f);}
int main(void){
    char dir[]="/tmp/mibr-lease-host-XXXXXX",path[256],text[32];pid_t child;int status;
    assert(mkdtemp(dir));
    snprintf(path,sizeof(path),"%s/lease",dir);
    assert(!mibr_app_rw_lease_acquire(path,0));
    assert(!access(path,F_OK));
    mibr_app_rw_lease_release(path);
    assert(access(path,F_OK));
    /* a live other owner blocks, and its lease is not released by us */
    child=fork();assert(child>=0);
    if(!child){for(;;)pause();}
    snprintf(text,sizeof(text),"%ld\n",(long)child);
    put(path,text);
    assert(mibr_app_rw_lease_acquire(path,100)==-1);
    mibr_app_rw_lease_release(path);
    assert(!access(path,F_OK));
    assert(!kill(child,SIGTERM));
    assert(waitpid(child,&status,0)==child);
    unlink(path);
    /* a dead owner is taken over at once */
    child=fork();assert(child>=0);
    if(!child)_exit(0);
    assert(waitpid(child,&status,0)==child);
    snprintf(text,sizeof(text),"%ld\n",(long)child);
    put(path,text);
    assert(!mibr_app_rw_lease_acquire(path,0));
    mibr_app_rw_lease_release(path);
    /* an empty file (owner killed between create and write) is taken over after the wait */
    put(path,"");
    assert(!mibr_app_rw_lease_acquire(path,100));
    mibr_app_rw_lease_release(path);
    assert(!rmdir(dir));
    puts("MIBR_APP_RW_LEASE_HOST_PASS");
    return 0;
}
