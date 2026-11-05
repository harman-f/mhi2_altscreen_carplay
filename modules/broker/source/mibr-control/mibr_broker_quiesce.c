/* SPDX-License-Identifier: GPL-3.0-or-later
 * Installer-only, fail-closed graceful stop for the exact MIBR/3 service.
 * No forced-kill path. The process is signalled only through a bound handle.
 */
#ifndef __QNXNTO__
#define _GNU_SOURCE
#endif
#define _POSIX_C_SOURCE 200809L
#include "../../../carplay/source/alt111-settings/include/mibr_paths.h"
#include "bound_process.h"
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#ifdef __QNXNTO__
#include <devctl.h>
#include <sys/procfs.h>
#endif

#define DEFAULT_PIDFILE "/tmp/mibr-v3-service.pid"
#define DEFAULT_EXEC MIBR_BIN_DIR "/mibr-v3-service"
#define QUIESCE_TIMEOUT_MS 10000
#define POLL_INTERVAL_MS 100

static int read_pid_file(const char *path,pid_t *pid)
{
    struct stat link_st,file_st;
    char data[64];size_t used=0;ssize_t n;int fd;long value=0;size_t i,digits;
    if(lstat(path,&link_st)||!S_ISREG(link_st.st_mode)||link_st.st_uid!=0)return -1;
    fd=open(path,O_RDONLY);
    if(fd<0)return -1;
    if(fstat(fd,&file_st)||!S_ISREG(file_st.st_mode)||file_st.st_uid!=0||
       file_st.st_dev!=link_st.st_dev||
       file_st.st_ino!=link_st.st_ino){close(fd);return -1;}
    for(;;){
        if(used==sizeof(data)){close(fd);return -1;}
        n=read(fd,data+used,sizeof(data)-used);
        if(n<0&&errno==EINTR)continue;
        if(n<0){close(fd);return -1;}
        if(n==0)break;
        used+=(size_t)n;
    }
    if(close(fd)||used==0)return -1;
    digits=used;
    if(data[used-1]=='\n')digits--;
    if(digits==0)return -1;
    for(i=0;i<digits;i++){
        int digit;
        if(data[i]<'0'||data[i]>'9')return -1;
        digit=data[i]-'0';
        if(value>(LONG_MAX-digit)/10)return -1;
        value=value*10+digit;
    }
    if(digits>1&&data[0]=='0')return -1;
    if(value<=1||(long)(pid_t)value!=value)return -1;
    *pid=(pid_t)value;return 0;
}

#ifndef __QNXNTO__
static int expected_executable(pid_t pid,const char *expected)
{
    char procpath[64],actual[PATH_MAX+1];ssize_t n;
    if(snprintf(procpath,sizeof(procpath),"/proc/%ld/exe",(long)pid)>=(int)sizeof(procpath))return -1;
    n=readlink(procpath,actual,sizeof(actual)-1);
    if(n<0||(size_t)n>=sizeof(actual)-1)return -1;
    actual[n]=0;
    return strcmp(actual,expected)?-1:0;
}
#endif

static int verify_bound_executable(int process_fd,pid_t pid,const char *expected)
{
#ifdef __QNXNTO__
    char *storage;procfs_debuginfo *info;int rc,match=-1;
    (void)pid;
    storage=(char*)malloc(sizeof(*info)+PATH_MAX);
    if(!storage)return -1;
    memset(storage,0,sizeof(*info)+PATH_MAX);info=(procfs_debuginfo*)storage;
    info->vaddr=0;
    rc=devctl(process_fd,DCMD_PROC_MAPDEBUG_BASE,info,sizeof(*info)+PATH_MAX,NULL);
    if(rc!=0){
        fprintf(stderr,"MIBR_QUIESCE_MAPDEBUG_BASE_FAILED rc=%d errno=%d\n",rc,errno);
        free(storage);return -1;
    }
    if(memchr(info->path,0,PATH_MAX)){
        if(!strcmp(info->path,expected))match=0;
        else if(expected[0]=='/'&&!strcmp(info->path,expected+1))match=0;
        else if(!strncmp(info->path,"/net/mmx",8)&&!strcmp(info->path+8,expected))match=0;
        if(match)fprintf(stderr,"MIBR_QUIESCE_MAPDEBUG_BASE_PATH=%s\n",info->path);
    }else{
        fprintf(stderr,"MIBR_QUIESCE_MAPDEBUG_BASE_UNTERMINATED\n");
    }
    free(storage);return match;
#else
    (void)process_fd;
    return expected_executable(pid,expected);
#endif
}

static int wait_bound_dead(int fd)
{
    struct timespec start,now,pause;long elapsed_ms,left_ms;
    if(clock_gettime(CLOCK_MONOTONIC,&start))return -1;
    for(;;){
        if(bound_process_dead(fd))return 0;
        if(clock_gettime(CLOCK_MONOTONIC,&now))return -1;
        elapsed_ms=(now.tv_sec-start.tv_sec)*1000L+
            (now.tv_nsec-start.tv_nsec)/1000000L;
        if(elapsed_ms>=QUIESCE_TIMEOUT_MS)return -1;
        left_ms=QUIESCE_TIMEOUT_MS-elapsed_ms;
        if(left_ms>POLL_INTERVAL_MS)left_ms=POLL_INTERVAL_MS;
        pause.tv_sec=left_ms/1000L;pause.tv_nsec=(left_ms%1000L)*1000000L;
        if(nanosleep(&pause,NULL)&&errno!=EINTR)return -1;
    }
}

static int quiesce(const char *pidfile,const char *expected,int check_only)
{
    pid_t pid;int fd,signal_rc;
    if(read_pid_file(pidfile,&pid))return 2;
    fd=bound_process_open(pid);
    if(fd<0){
        /* A stale, well-formed PID for an already-gone process is harmless. */
        if(errno==ESRCH||errno==ENOENT)return 1;
        return 3;
    }
    if(verify_bound_executable(fd,pid,expected)){
        close(fd);return 4;
    }
    if(bound_process_dead(fd)){close(fd);return 1;}
    if(check_only){close(fd);return 7;}
    signal_rc=bound_process_signal(fd,SIGTERM);
    if(signal_rc!=0){
        if(bound_process_dead(fd)){close(fd);return 1;}
        close(fd);return 5;
    }
    if(wait_bound_dead(fd)){close(fd);return 6;}
    close(fd);return 0;
}

int main(int argc,char **argv)
{
    const char *pidfile=DEFAULT_PIDFILE,*expected=DEFAULT_EXEC;
    int check_only=0;
#ifdef ALT111_SETTINGS_TEST
    if(argc!=3&&argc!=4){fputs("usage: mibr-broker-quiesce PIDFILE EXPECTED_EXEC [--check]\n",stderr);return 64;}
    pidfile=argv[1];expected=argv[2];
    if(argc==4){if(strcmp(argv[3],"--check")){fputs("invalid option\n",stderr);return 64;}check_only=1;}
#else
    if(argc==2&&!strcmp(argv[1],"--check"))check_only=1;
    else if(argc!=1){fputs("MIBR_QUIESCE_INVALID_ARGUMENTS\n",stderr);return 64;}
#endif
    switch(quiesce(pidfile,expected,check_only)){
    case 0:puts("BROKER_QUIESCED");return 0;
    case 1:puts("BROKER_ALREADY_EXITED");return 0;
    case 2:fputs("MIBR_QUIESCE_INVALID_PIDFILE\n",stderr);return 2;
    case 3:fputs("MIBR_QUIESCE_BIND_FAILED\n",stderr);return 3;
    case 4:fputs("MIBR_QUIESCE_IDENTITY_MISMATCH\n",stderr);return 4;
    case 5:fputs("MIBR_QUIESCE_TERM_FAILED\n",stderr);return 5;
    case 7:puts("BROKER_IDENTITY_VERIFIED");return 0;
    default:fputs("MIBR_QUIESCE_TIMEOUT_OR_STATUS_UNKNOWN\n",stderr);return 6;
    }
}
