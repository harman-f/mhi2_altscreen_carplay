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
    memset(&status,0,sizeof(status));status.tid=1;
    /* STATUS alone can report ESRCH for a departed high-numbered current
     * thread while lower threads still run. TIDSTATUS starts at the first
     * possible thread and asks procfs for the next existing thread. */
    return devctl(fd,DCMD_PROC_TIDSTATUS,&status,sizeof(status),NULL)==ESRCH;
#else
    struct pollfd p;
    memset(&p,0,sizeof(p));p.fd=fd;p.events=POLLIN;
    return poll(&p,1,0)==1 && (p.revents&POLLIN)!=0;
#endif
}
#endif
