/* SPDX-License-Identifier: GPL-3.0-or-later
 * Diagnostic-only QNX procfs process-handle probe.
 * No MOST, DisplayManager, routing or persistent-state access.
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/devctl.h>
#include <sys/procfs.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void print_rc(const char *name, int rc)
{
    int e = errno;
    const char *msg = rc > 0 ? strerror(rc) : (e ? strerror(e) : "OK");
    printf("%s rc=%d errno=%d strerror=%s\n", name, rc, e, msg);
    fflush(stdout);
}

static int tidstatus(int fd)
{
    procfs_status status;
    memset(&status, 0, sizeof(status));
    status.tid = 1;
    errno = 0;
    return devctl(fd, DCMD_PROC_TIDSTATUS, &status, sizeof(status), NULL);
}

static int send_signal_fd(int fd, int signo)
{
    procfs_signal request;
    memset(&request, 0, sizeof(request));
    request.signo = signo;
    errno = 0;
    return devctl(fd, DCMD_PROC_SIGNAL, &request, sizeof(request), NULL);
}

int main(void)
{
    int ready[2], fd, rc, st = 0, i;
    pid_t child, observer;
    char path[64], token = 0;

    if (pipe(ready)) {
        print_rc("pipe", -1);
        return 1;
    }

    child = fork();
    if (child < 0) {
        print_rc("fork_child", -1);
        return 1;
    }
    if (child == 0) {
        close(ready[0]);
        signal(SIGTERM, SIG_DFL);
        token = 'R';
        if (write(ready[1], &token, 1) != 1) _exit(2);
        close(ready[1]);
        for (;;) pause();
    }

    close(ready[1]);
    if (read(ready[0], &token, 1) != 1 || token != 'R') {
        printf("child_ready=NO\n");
        kill(child, SIGKILL);
        waitpid(child, &st, 0);
        return 1;
    }
    close(ready[0]);

    printf("child_pid=%ld child_ready=YES\n", (long)child);

    snprintf(path, sizeof(path), "/proc/%ld/as", (long)child);
    errno = 0;
    fd = open(path, O_RDWR);
    print_rc("open_proc_as", fd);
    if (fd < 0) {
        kill(child, SIGKILL);
        waitpid(child, &st, 0);
        return 0;
    }

    errno = 0;
    rc = fcntl(fd, F_SETFD, FD_CLOEXEC);
    print_rc("fcntl_FD_CLOEXEC", rc);

    rc = tidstatus(fd);
    print_rc("tidstatus_alive_parent", rc);

    observer = fork();
    if (observer < 0) {
        print_rc("fork_observer", -1);
        kill(child, SIGKILL);
        waitpid(child, &st, 0);
        close(fd);
        return 0;
    }

    if (observer == 0) {
        rc = send_signal_fd(fd, SIGTERM);
        print_rc("observer_signal_SIGTERM", rc);

        for (i = 0; i < 30; ++i) {
            usleep(100000);
            rc = tidstatus(fd);
            if (i == 0) print_rc("observer_tidstatus_100ms", rc);
            if (rc != 0) {
                printf("observer_tidstatus_nonzero_after_ms=%d\n", (i + 1) * 100);
                print_rc("observer_tidstatus_nonzero", rc);
                _exit(0);
            }
        }

        printf("observer_tidstatus_nonzero_after_ms=NONE_3000\n");
        rc = tidstatus(fd);
        print_rc("observer_tidstatus_3000ms", rc);
        _exit(0);
    }

    waitpid(observer, &st, 0);
    printf("observer_wait_status=%d\n", st);

    errno = 0;
    rc = waitpid(child, &st, WNOHANG);
    print_rc("parent_waitpid_child_WNOHANG", rc);
    printf("child_wait_status=%d\n", st);

    rc = tidstatus(fd);
    print_rc("tidstatus_after_reap_attempt", rc);

    if (rc == 0) {
        errno = 0;
        rc = waitpid(child, &st, 0);
        print_rc("parent_waitpid_child_blocking", rc);
        printf("child_wait_status_blocking=%d\n", st);
        rc = tidstatus(fd);
        print_rc("tidstatus_after_reap", rc);
    }

    close(fd);
    puts("PROBE_DONE=YES");
    return 0;
}
