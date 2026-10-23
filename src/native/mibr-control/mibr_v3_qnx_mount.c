/* SPDX-License-Identifier: GPL-3.0-or-later
 * Target-only guard. Never infer write safety from a successful mount command:
 * separately inspect statvfs RO flag and st_dev before and after both transitions.
 * This is a compile-able candidate, NOT evidence of QNX media/powerloss PASS.
 */
#define _POSIX_C_SOURCE 200809L
#ifndef __QNXNTO__
#error MIBR_V3_QNX_TARGET_ONLY
#endif
#include "mibr_v3_qnx_mount.h"
#include "mibr_v3_recovery_gate.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/statvfs.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#define CPVC_PROFILE "/mnt/app/root/altscreen-u2/config/cpvc-r5.profile"
#define OWNER_MARKER "/mnt/app/root/altscreen-u2/config/mibr-v3-single-writer.enabled"
/* On-target explicit migration gate: a marker is necessary, NOT evidence by
 * itself that the historical alternate writers/boot order were retired.
 * The independent release preflight must verify their installed bytes. */
static int owner_marker(void){
    struct stat before,after;char value[3];int fd;ssize_t n;
    if(lstat(OWNER_MARKER,&before)||!S_ISREG(before.st_mode)||before.st_size!=2)return -1;
    fd=open(OWNER_MARKER,O_RDONLY);if(fd<0)return -1;
    if(fstat(fd,&after)||!S_ISREG(after.st_mode)||
       before.st_dev!=after.st_dev||before.st_ino!=after.st_ino||
       after.st_size!=2){close(fd);return -1;}
    n=read(fd,value,sizeof(value));
    if(close(fd)||n!=2||value[0]!='1'||value[1]!='\n')return -1;
    return 0;
}
static int probe(const struct mibr_v3_qnx_store *s,int ro){
    struct stat mount,root,profile;struct statvfs fs;
    if(!s||!s->profile||lstat("/mnt/app",&mount)||
       lstat("/mnt/app/root",&root)||lstat(s->profile,&profile)||
       statvfs("/mnt/app",&fs)||!S_ISDIR(mount.st_mode)||
       !S_ISDIR(root.st_mode)||!S_ISREG(profile.st_mode)||
       mount.st_dev!=s->mount_device||root.st_dev!=s->mount_device||
       profile.st_dev!=s->mount_device)return -1;
    return !!(fs.f_flag&ST_RDONLY)==!!ro?0:-1;
}
static int execute_mount(const char *mode){
    const char *executable=access("/proc/boot/mount",X_OK)==0?
        "/proc/boot/mount":"/bin/mount";
    char *const args[]={(char*)executable,(char*)mode,(char*)"/mnt/app",NULL};
    struct timespec delay={0,10000000L};pid_t pid;int status;unsigned i;
    if(access(executable,X_OK))return -1;
    pid=fork();if(pid<0)return -1;
    if(!pid){execv(executable,args);_exit(127);}
    for(i=0;i<500;i++){
        pid_t got=waitpid(pid,&status,WNOHANG);
        if(got==pid)return WIFEXITED(status)&&WEXITSTATUS(status)==0?0:-1;
        if(got<0&&errno!=EINTR)return -1;
        (void)nanosleep(&delay,NULL);
    }
    (void)kill(pid,SIGKILL);(void)waitpid(pid,&status,0);return -1;
}
int mibr_v3_qnx_preflight(struct mibr_v3_qnx_store *s,const char *profile,
                           const struct alt111_settings *observed){
    struct stat mount;
    if(!s||!profile||strcmp(profile,CPVC_PROFILE)||geteuid()!=0||
       owner_marker()||lstat("/mnt/app",&mount)||!S_ISDIR(mount.st_mode))return -1;
    memset(s,0,sizeof(*s));s->profile=profile;s->mount_device=mount.st_dev;
    return probe(s,1)||mibr_v3_recovery_check(profile)||
           mibr_v3_profile_parity(profile,observed)?-1:0;
}
static int enter_rw(void *context){
    struct mibr_v3_qnx_store *s=(struct mibr_v3_qnx_store*)context;
    if(!s||s->degraded||probe(s,1))return -1;
    if(execute_mount("-uw")||probe(s,0)){
        /* enter_rw must restore by itself if partial transition occurred. */
        (void)execute_mount("-ur");s->degraded=1;return -1;
    }
    return 0;
}
static int restore_ro(void *context){
    struct mibr_v3_qnx_store *s=(struct mibr_v3_qnx_store*)context;
    int rc;
    if(!s)return -1;
    sync();
    rc=execute_mount("-ur");
    if(rc||probe(s,1)){s->degraded=1;return -1;}
    return 0;
}
int mibr_v3_qnx_set(void *context,const struct alt111_settings_paths *paths,
    const struct alt111_settings *observed,unsigned id,const char *value,
    uint64_t revision,char *error,size_t cap){
    struct mibr_v3_qnx_store *s=(struct mibr_v3_qnx_store*)context;
    struct mibr_v3_mount_guard guard={enter_rw,restore_ro,s};
    if(!s||s->degraded){
        if(error&&cap)snprintf(error,cap,"RO_RESTORE_FAILED");
        return -2;
    }
    {int rc=mibr_v3_profile_set(paths,s->profile,observed,id,value,revision,&guard,
                               error,cap);
     if(s->degraded){if(error&&cap)snprintf(error,cap,"RO_RESTORE_FAILED");return -2;}
     return rc;}
}
