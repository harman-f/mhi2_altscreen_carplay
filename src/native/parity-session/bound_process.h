/* SPDX-License-Identifier: GPL-3.0-or-later */
#ifndef MIBR_BOUND_PROCESS_H
#define MIBR_BOUND_PROCESS_H
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <unistd.h>
#ifdef __QNXNTO__
#include <devctl.h>
#include <sys/procfs.h>
#elif defined(__linux__)
#include <poll.h>
#include <sys/syscall.h>
#else
#error Bound process handles require an implemented target adapter
#endif

/* Open while our unreaped direct child is behind its exec barrier; fork the
 * independent watchdog only afterwards. PID files never authorize signals. */
static int bound_process_open(pid_t pid)
{
    int fd;
#ifdef __QNXNTO__
    char path[64];
    snprintf(path,sizeof(path),"/proc/%ld/as",(long)pid);
    fd=open(path,O_RDWR);
#else
    fd=(int)syscall(SYS_pidfd_open,pid,0);
#endif
    if(fd>=0 && fcntl(fd,F_SETFD,FD_CLOEXEC)){close(fd);return -1;}
    return fd;
}
static int bound_process_signal(int fd,int signo)
{
#ifdef __QNXNTO__
    procfs_signal request;
    memset(&request,0,sizeof(request));request.signo=signo;
    return devctl(fd,DCMD_PROC_SIGNAL,&request,sizeof(request),NULL);
#else
    return syscall(SYS_pidfd_send_signal,fd,signo,NULL,0)==0 ? 0 : errno;
#endif
}
static int bound_process_dead(int fd)
{
    if(fd<0)return 0;
#ifdef __QNXNTO__
    procfs_status status;
    int rc;
    memset(&status,0,sizeof(status));status.tid=1;
    /*
     * Exact MU1440/QNX 6.5 vehicle semantics:
     * - a live bound child returns EOK from TIDSTATUS;
     * - DCMD_PROC_SIGNAL can move it to the procfs debugger termination
     *   point while the O_RDWR handle's RLC flag keeps the process object
     *   present, so TIDSTATUS still returns EOK with why=TERMINATED;
     * - ESRCH means the process object is already gone.
     *
     * TERMINATED is writer-quiescent even though waitpid() cannot reap until
     * the last O_RDWR procfs handle is closed.
     */
    rc=devctl(fd,DCMD_PROC_TIDSTATUS,&status,sizeof(status),NULL);
    if(rc==ESRCH)return 1;
    if(rc!=0)return 0;
    return status.why==_DEBUG_WHY_TERMINATED;
#else
    struct pollfd p;
    memset(&p,0,sizeof(p));p.fd=fd;p.events=POLLIN;
    return poll(&p,1,0)==1 && (p.revents&POLLIN)!=0;
#endif
}
#endif
