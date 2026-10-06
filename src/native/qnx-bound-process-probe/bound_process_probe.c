/* SPDX-License-Identifier: GPL-3.0-or-later
 * Diagnostic-only QNX procfs process-handle probe v2.
 * No MOST, DisplayManager, routing or persistent-state access.
 */
#include <devctl.h>
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/procfs.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

static void print_syscall(const char *name, long rc)
{
    int e = errno;
    printf("%s rc=%ld errno=%d strerror=%s\n",
           name, rc, e, rc < 0 ? strerror(e) : "OK");
    fflush(stdout);
}

static void print_devctl(const char *name, int rc)
{
    printf("%s rc=%d strerror=%s\n", name, rc, rc ? strerror(rc) : "OK");
    fflush(stdout);
}

static pid_t spawn_child(void)
{
    int ready[2];
    char token = 0;
    pid_t child;

    if (pipe(ready)) {
        print_syscall("pipe", -1);
        return -1;
    }
    child = fork();
    if (child < 0) {
        print_syscall("fork_child", -1);
        close(ready[0]);
        close(ready[1]);
        return -1;
    }
    if (child == 0) {
        close(ready[0]);
        signal(SIGTERM, SIG_DFL);
        signal(SIGINT, SIG_DFL);
        token = 'R';
        if (write(ready[1], &token, 1) != 1) _exit(2);
        close(ready[1]);
        for (;;) pause();
    }

    close(ready[1]);
    if (read(ready[0], &token, 1) != 1 || token != 'R') {
        close(ready[0]);
        kill(child, SIGKILL);
        waitpid(child, NULL, 0);
        return -1;
    }
    close(ready[0]);
    return child;
}

static int wait_bounded(pid_t child, unsigned timeout_ms, int *st)
{
    unsigned elapsed = 0;
    for (;;) {
        pid_t rc;
        errno = 0;
        rc = waitpid(child, st, WNOHANG);
        if (rc == child) return 1;
        if (rc < 0) return -1;
        if (elapsed >= timeout_ms) return 0;
        usleep(100000);
        elapsed += 100;
    }
}

static void print_wait_result(const char *name, int rc, int st)
{
    if (rc == 1) {
        printf("%s=reaped status=%d signaled=%d signal=%d exited=%d exit=%d\n",
               name, st,
               WIFSIGNALED(st) ? 1 : 0,
               WIFSIGNALED(st) ? WTERMSIG(st) : 0,
               WIFEXITED(st) ? 1 : 0,
               WIFEXITED(st) ? WEXITSTATUS(st) : 0);
    } else if (rc == 0) {
        printf("%s=alive_after_timeout\n", name);
    } else {
        printf("%s=waitpid_error errno=%d strerror=%s\n", name, errno, strerror(errno));
    }
    fflush(stdout);
}

static int proc_status(int fd, const char *name)
{
    procfs_status status;
    int rc;
    memset(&status, 0, sizeof(status));
    status.tid = 1;
    errno = 0;
    rc = devctl(fd, DCMD_PROC_TIDSTATUS, &status, sizeof(status), NULL);
    print_devctl(name, rc);
    if (rc == 0) {
        printf("%s_detail pid=%ld tid=%ld flags=0x%08lx why=%u what=%u\n",
               name,
               (long)status.pid,
               (long)status.tid,
               (unsigned long)status.flags,
               (unsigned)status.why,
               (unsigned)status.what);
        fflush(stdout);
    }
    return rc;
}

static int proc_signal(int fd, int signo, const char *name)
{
    procfs_signal request;
    int rc;
    memset(&request, 0, sizeof(request));
    request.tid = 0;
    request.signo = signo;
    request.code = 0;
    request.value = 0;
    errno = 0;
    rc = devctl(fd, DCMD_PROC_SIGNAL, &request, sizeof(request), NULL);
    print_devctl(name, rc);
    return rc;
}

static int proc_run(int fd, const char *name)
{
    procfs_run run;
    int rc;
    memset(&run, 0, sizeof(run));
    errno = 0;
    rc = devctl(fd, DCMD_PROC_RUN, &run, sizeof(run), NULL);
    print_devctl(name, rc);
    return rc;
}

static void cleanup_child(pid_t child, int fd)
{
    int st = 0, rc;
    if (fd >= 0) (void)proc_run(fd, "cleanup_proc_run");
    errno = 0;
    rc = kill(child, SIGKILL);
    print_syscall("cleanup_kill_SIGKILL", rc);
    rc = wait_bounded(child, 1500, &st);
    print_wait_result("cleanup_wait", rc, st);
    if (fd >= 0) close(fd);
}

static void case_kill_control(void)
{
    pid_t child;
    int st = 0, rc;

    puts("=== CASE kill_control ===");
    child = spawn_child();
    if (child < 0) {
        puts("kill_control_spawn=FAIL");
        return;
    }
    printf("child_pid=%ld child_ready=YES\n", (long)child);
    errno = 0;
    rc = kill(child, SIGTERM);
    print_syscall("kill_SIGTERM", rc);
    rc = wait_bounded(child, 1500, &st);
    print_wait_result("kill_control_wait", rc, st);
    if (rc != 1) cleanup_child(child, -1);
}

static void case_procfs(const char *label, int flags, int do_run)
{
    pid_t child;
    int fd = -1, st = 0, wr;
    char path[64];

    printf("=== CASE %s ===\n", label);
    child = spawn_child();
    if (child < 0) {
        printf("%s_spawn=FAIL\n", label);
        return;
    }
    printf("child_pid=%ld child_ready=YES\n", (long)child);

    snprintf(path, sizeof(path), "/proc/%ld/as", (long)child);
    errno = 0;
    fd = open(path, flags);
    print_syscall("open_proc_as", fd);
    if (fd < 0) {
        cleanup_child(child, -1);
        return;
    }

    errno = 0;
    print_syscall("fcntl_FD_CLOEXEC", fcntl(fd, F_SETFD, FD_CLOEXEC));
    (void)proc_status(fd, "tidstatus_before_signal");
    (void)proc_signal(fd, SIGTERM, "proc_signal_SIGTERM");

    wr = wait_bounded(child, 1000, &st);
    print_wait_result("wait_after_proc_signal", wr, st);
    if (wr == 1) {
        close(fd);
        return;
    }

    (void)proc_status(fd, "tidstatus_after_signal");

    if (do_run) {
        (void)proc_run(fd, "proc_run_after_signal");
        wr = wait_bounded(child, 1500, &st);
        print_wait_result("wait_after_proc_run", wr, st);
        if (wr == 1) {
            close(fd);
            return;
        }
        (void)proc_status(fd, "tidstatus_after_run");
    }

    cleanup_child(child, fd);
}

int main(void)
{
    case_kill_control();
    case_procfs("procfs_RDONLY", O_RDONLY, 0);
    case_procfs("procfs_RDWR_signal_then_RUN", O_RDWR, 1);
    puts("PROBE_DONE=YES");
    return 0;
}
