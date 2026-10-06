/* SPDX-License-Identifier: GPL-3.0-or-later
 * Diagnostic-only MU1440 QNX bound-process probe v3.
 * Mirrors parity-session identity_self_test with the stock SignalKill path.
 * No MOST, DisplayManager, routing or persistent-state access.
 */
#include <devctl.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/neutrino.h>
#include <sys/procfs.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void print_wait(const char *name, pid_t rc, int st)
{
    if (rc > 0) {
        printf("%s=reaped pid=%ld status=%d signaled=%d signal=%d exited=%d exit=%d\n",
               name, (long)rc, st,
               WIFSIGNALED(st) ? 1 : 0,
               WIFSIGNALED(st) ? WTERMSIG(st) : 0,
               WIFEXITED(st) ? 1 : 0,
               WIFEXITED(st) ? WEXITSTATUS(st) : 0);
    } else {
        printf("%s=not_reaped rc=%ld errno=%d strerror=%s\n",
               name, (long)rc, errno, errno ? strerror(errno) : "OK");
    }
    fflush(stdout);
}

static int status_fd(int fd, const char *tag, procfs_status *out)
{
    procfs_status st;
    int rc;
    memset(&st, 0, sizeof(st));
    st.tid = 1;
    errno = 0;
    rc = devctl(fd, DCMD_PROC_TIDSTATUS, &st, sizeof(st), NULL);
    printf("%s rc=%d errno=%d strerror=%s", tag, rc, errno,
           rc ? strerror(rc) : "OK");
    if (rc == 0) {
        printf(" pid=%ld tid=%ld flags=0x%08lx why=%u what=%u",
               (long)st.pid, (long)st.tid, (unsigned long)st.flags,
               (unsigned)st.why, (unsigned)st.what);
        if (out) *out = st;
    }
    putchar('\n');
    fflush(stdout);
    return rc;
}

static pid_t spawn_child(void)
{
    int ready[2];
    char token = 0;
    pid_t child;
    if (pipe(ready) != 0) return -1;
    child = fork();
    if (child < 0) return -1;
    if (child == 0) {
        close(ready[0]);
        signal(SIGTERM, SIG_DFL);
        signal(SIGKILL, SIG_DFL);
        token='R';
        if (write(ready[1], &token, 1) != 1) _exit(2);
        close(ready[1]);
        for (;;) pause();
    }
    close(ready[1]);
    if (read(ready[0], &token, 1) != 1 || token != 'R') {
        close(ready[0]);
        (void)SignalKill(0, child, 0, SIGKILL, SI_USER, 0);
        waitpid(child, NULL, 0);
        return -1;
    }
    close(ready[0]);
    return child;
}

int main(void)
{
    pid_t child, observer, w;
    int fd, st=0, ost=0, rc, i;
    char path[64];
    procfs_status ps;

    child=spawn_child();
    if(child<0){puts("spawn=FAIL");return 1;}
    printf("child_pid=%ld child_ready=YES\n",(long)child);

    snprintf(path,sizeof(path),"/proc/%ld/as",(long)child);
    errno=0;
    fd=open(path,O_RDWR);
    printf("open_proc_as rc=%d errno=%d strerror=%s\n",fd,errno,
           fd<0?strerror(errno):"OK");
    if(fd<0)return 1;
    printf("fcntl_FD_CLOEXEC rc=%d\n",fcntl(fd,F_SETFD,FD_CLOEXEC));

    (void)status_fd(fd,"parent_status_before",&ps);

    observer=fork();
    if(observer<0){close(fd);return 1;}
    if(observer==0){
        procfs_status os;
        int src;
        puts("observer_started=YES");
        if(status_fd(fd,"observer_status_before",&os)!=0)_exit(11);
        errno=0;
        src=SignalKill(0,(pid_t)os.pid,0,SIGTERM,SI_USER,0);
        printf("observer_SignalKill_SIGTERM rc=%d errno=%d strerror=%s target_pid=%ld\n",
               src,errno,src<0?strerror(errno):"OK",(long)os.pid);
        fflush(stdout);
        if(src!=0)_exit(12);
        for(i=0;i<30;i++){
            procfs_status after;
            usleep(100000);
            rc=status_fd(fd,i==0?"observer_status_100ms":"observer_status_poll",&after);
            if(rc==ESRCH){
                printf("observer_terminal=ESRCH after_ms=%d\n",(i+1)*100);
                _exit(0);
            }
            if(rc==0 && after.why==_DEBUG_WHY_TERMINATED){
                printf("observer_terminal=WHY_TERMINATED after_ms=%d flags=0x%08lx tid=%ld\n",
                       (i+1)*100,(unsigned long)after.flags,(long)after.tid);
                _exit(0);
            }
        }
        puts("observer_terminal=NONE_3000");
        _exit(13);
    }

    w=waitpid(observer,&ost,0);
    print_wait("observer_wait",w,ost);

    (void)status_fd(fd,"parent_status_after_observer",&ps);

    errno=0;
    w=waitpid(child,&st,WNOHANG);
    print_wait("child_wait_before_close",w,st);

    printf("parent_close_proc_handle rc=%d\n",close(fd));
    fd=-1;

    for(i=0;i<20;i++){
        errno=0;
        w=waitpid(child,&st,WNOHANG);
        if(w==child)break;
        usleep(100000);
    }
    print_wait("child_wait_after_close",w,st);

    if(w!=child){
        puts("cleanup=SignalKill_SIGKILL");
        (void)SignalKill(0,child,0,SIGKILL,SI_USER,0);
        for(i=0;i<10;i++){
            w=waitpid(child,&st,WNOHANG);
            if(w==child)break;
            usleep(100000);
        }
        print_wait("cleanup_wait",w,st);
    }

    puts("PROBE_DONE=YES");
    return 0;
}
