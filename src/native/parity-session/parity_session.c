/*
 * Bounded MU1440 parity-session owner.
 *
 * Owns only the DMDT release/restore lifecycle around direct-ts-parity.
 * An independent watchdog process restores stock routing if the parent dies.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define DMDT "/eso/bin/apps/dmdt"
#define IPL_CONFIG "/etc/eso/production"
#define STATE_PATH "/tmp/mibr-parity-session.state"
#define PID_PATH "/tmp/mibr-parity-session.pid"
#define BRIDGE_PID_PATH "/tmp/mibr-parity-session-bridge.pid"
#define AU_MARKER "/tmp/mibr-alt111-au-framing.enabled"
#define OLD_DIRECT_MARKER "/tmp/mibr-isotx2-gate.direct"
#define SOURCE_STATE "/tmp/mibr-carplay111.state"
#define SOURCE_HB "/tmp/mibr-carplay111.heartbeat"
#define OLD_AUTO_PID "/tmp/mibr-direct-auto-supervisor.pid"
#define OLD_AUTO_TEMP "/tmp/mibr-carplay-autodirect"
#define OLD_AUTO_PERSIST "/mnt/app/root/mibr-carplay-autodirect"

static volatile sig_atomic_t g_stop;

static void on_signal(int sig) { (void)sig; g_stop = 1; }

static int write_text(const char *path, const char *text) {
    char tmp[192];
    int fd;
    size_t n = strlen(text);
    snprintf(tmp, sizeof(tmp), "%s.new.%ld", path, (long)getpid());
    fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return -1;
    if (write(fd, text, n) != (ssize_t)n) { close(fd); unlink(tmp); return -1; }
    if (close(fd) != 0) { unlink(tmp); return -1; }
    if (rename(tmp, path) != 0) { unlink(tmp); return -1; }
    return 0;
}

static int touch_file(const char *path) {
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return -1;
    return close(fd);
}

static int read_trimmed(const char *path, char *out, size_t cap) {
    int fd;
    ssize_t n;
    if (!out || cap < 2u) return -1;
    out[0] = 0;
    fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    n = read(fd, out, cap - 1u);
    close(fd);
    if (n <= 0) return -1;
    out[n] = 0;
    while (n > 0 && (out[n-1] == '\n' || out[n-1] == '\r' ||
                     out[n-1] == ' ' || out[n-1] == '\t'))
        out[--n] = 0;
    return n > 0 ? 0 : -1;
}

static int pid_alive_from_file(const char *path) {
    char b[48], *end = NULL;
    long pid;
    if (read_trimmed(path, b, sizeof(b)) != 0) return 0;
    errno = 0;
    pid = strtol(b, &end, 10);
    if (errno || end == b || *end || pid <= 1) return 0;
    return kill((pid_t)pid, 0) == 0 || errno == EPERM;
}

static int file_is_one(const char *path) {
    char b[16];
    return read_trimmed(path, b, sizeof(b)) == 0 && !strcmp(b, "1");
}

static int old_autodirect_enabled(void) {
    char b[16];
    if (read_trimmed(OLD_AUTO_TEMP, b, sizeof(b)) == 0)
        return !strcmp(b, "1");
    if (read_trimmed(OLD_AUTO_PERSIST, b, sizeof(b)) == 0)
        return !strcmp(b, "1");
    return 0;
}

static int run_argv(char *const argv[]) {
    pid_t p;
    int st = 0;
    p = fork();
    if (p < 0) return -1;
    if (p == 0) {
        setenv("IPL_CONFIG_DIR", IPL_CONFIG, 1);
        execv(DMDT, argv);
        _exit(127);
    }
    while (waitpid(p, &st, 0) < 0) {
        if (errno == EINTR) continue;
        return -1;
    }
    return WIFEXITED(st) && WEXITSTATUS(st) == 0 ? 0 : -1;
}

static int dmdt_dc72(void) {
    char *argv[] = { (char *)DMDT, "dc", "72", NULL };
    return run_argv(argv);
}
static int dmdt_sc4_72(void) {
    char *argv[] = { (char *)DMDT, "sc", "4", "72", NULL };
    return run_argv(argv);
}
static int dmdt_dc70_33(void) {
    char *argv[] = { (char *)DMDT, "dc", "70", "33", NULL };
    return run_argv(argv);
}
static int dmdt_sc4_70(void) {
    char *argv[] = { (char *)DMDT, "sc", "4", "70", NULL };
    return run_argv(argv);
}

static int route_release(void) {
    if (dmdt_dc72() != 0) return -1;
    if (dmdt_sc4_72() != 0) return -1;
    return 0;
}

static int route_restore(void) {
    int a = dmdt_dc70_33();
    int b = dmdt_sc4_70();
    return (a == 0 && b == 0) ? 0 : -1;
}

static void kill_pid_from_file(const char *path) {
    char b[48], *end = NULL;
    long v;
    if (read_trimmed(path, b, sizeof(b)) != 0) return;
    errno = 0;
    v = strtol(b, &end, 10);
    if (errno || end == b || *end || v <= 1) return;
    kill((pid_t)v, SIGTERM);
    usleep(300000);
    if (kill((pid_t)v, 0) == 0 || errno == EPERM) kill((pid_t)v, SIGKILL);
}

static void emergency_restore(void) {
    kill_pid_from_file(BRIDGE_PID_PATH);
    unlink(AU_MARKER);
    unlink(OLD_DIRECT_MARKER);
    (void)route_restore();
    (void)write_text(STATE_PATH, "emergency_restored\n");
    unlink(BRIDGE_PID_PATH);
    unlink(PID_PATH);
}

static void watchdog_main(int fd) {
    char token = 0;
    ssize_t n;
    do { n = read(fd, &token, 1); } while (n < 0 && errno == EINTR);
    close(fd);
    if (n == 1 && token == 'R') _exit(0);
    emergency_restore();
    _exit(0);
}

static int source_ready(void) {
    char b[64];
    if (read_trimmed(SOURCE_STATE, b, sizeof(b)) != 0 || strcmp(b, "streaming"))
        return 0;
    return access(SOURCE_HB, R_OK) == 0;
}

static int bridge_spawn(const char *bridge, const char *input, const char *output,
                        pid_t *out_pid) {
    pid_t p = fork();
    if (p < 0) return -1;
    if (p == 0) {
        execl(bridge, bridge, input, output, (char *)NULL);
        _exit(127);
    }
    *out_pid = p;
    return 0;
}

static void stop_bridge(pid_t p) {
    int i, st;
    if (p <= 1) return;
    if (waitpid(p, &st, WNOHANG) == p) return;
    kill(p, SIGTERM);
    for (i = 0; i < 20; ++i) {
        pid_t w = waitpid(p, &st, WNOHANG);
        if (w == p) return;
        if (w < 0 && errno == ECHILD) return;
        usleep(100000);
    }
    kill(p, SIGKILL);
    while (waitpid(p, &st, 0) < 0 && errno == EINTR) {}
}

static int self_test(void) {
    if (strcmp(DMDT, "/eso/bin/apps/dmdt")) return 1;
    if (strcmp(IPL_CONFIG, "/etc/eso/production")) return 2;
    if (strcmp(AU_MARKER, "/tmp/mibr-alt111-au-framing.enabled")) return 3;
    puts("PARITY_SESSION_SELFTEST=PASS");
    puts("release=/eso/bin/apps/dmdt dc 72 ; /eso/bin/apps/dmdt sc 4 72");
    puts("release_delay_us=500000");
    puts("restore=/eso/bin/apps/dmdt dc 70 33 ; /eso/bin/apps/dmdt sc 4 70");
    return 0;
}

int main(int argc, char **argv) {
    const char *bridge, *input, *output;
    long max_seconds;
    char *end = NULL, b[64];
    int pipefd[2] = {-1,-1}, st = 0, rc = 1, route_owned = 0, restore_ok = 0;
    pid_t watchdog = -1, bridge_pid = -1;
    uint64_t elapsed_ms = 0;

    if (argc == 2 && !strcmp(argv[1], "--self-test")) return self_test();
    if (argc != 5) {
        fprintf(stderr, "usage: %s BRIDGE INPUT OUTPUT MAX_SECONDS\n", argv[0]);
        return 64;
    }
    bridge = argv[1]; input = argv[2]; output = argv[3];
    errno = 0; max_seconds = strtol(argv[4], &end, 10);
    if (errno || end == argv[4] || *end || max_seconds < 5 || max_seconds > 600)
        return 65;

    if (access(DMDT, X_OK) != 0) { fprintf(stderr, "ERROR missing dmdt\n"); return 10; }
    if (access(bridge, X_OK) != 0) { fprintf(stderr, "ERROR missing bridge\n"); return 11; }
    if (!source_ready()) { fprintf(stderr, "ERROR stream111 not ready\n"); return 12; }
    if (old_autodirect_enabled() || pid_alive_from_file(OLD_AUTO_PID)) {
        fprintf(stderr, "ERROR legacy Auto-Direct must be disabled/stopped\n");
        return 13;
    }

    signal(SIGINT, on_signal); signal(SIGTERM, on_signal); signal(SIGHUP, on_signal);
    snprintf(b, sizeof(b), "%ld\n", (long)getpid());
    if (write_text(PID_PATH, b) != 0) return 14;
    (void)write_text(STATE_PATH, "preflight\n");
    unlink(OLD_DIRECT_MARKER);

    if (pipe(pipefd) != 0) goto done;
    watchdog = fork();
    if (watchdog < 0) goto done;
    if (watchdog == 0) {
        close(pipefd[1]);
        watchdog_main(pipefd[0]);
    }
    close(pipefd[0]); pipefd[0] = -1;

    if (touch_file(AU_MARKER) != 0) {
        fprintf(stderr, "ERROR cannot arm M1AU marker\n");
        goto done;
    }

    (void)write_text(STATE_PATH, "releasing_dmdt\n");
    if (route_release() != 0) {
        fprintf(stderr, "ERROR DMDT release failed\n");
        goto done;
    }
    route_owned = 1;

    usleep(500000);

    (void)write_text(STATE_PATH, "starting_bridge\n");
    if (bridge_spawn(bridge, input, output, &bridge_pid) != 0) {
        fprintf(stderr, "ERROR bridge spawn failed\n");
        goto done;
    }
    snprintf(b, sizeof(b), "%ld\n", (long)bridge_pid);
    if (write_text(BRIDGE_PID_PATH, b) != 0) goto done;
    (void)write_text(STATE_PATH, "direct\n");

    while (!g_stop && elapsed_ms < (uint64_t)max_seconds * 1000ull) {
        pid_t w = waitpid(bridge_pid, &st, WNOHANG);
        if (w == bridge_pid) { bridge_pid = -1; break; }
        if (w < 0 && errno != EINTR) { bridge_pid = -1; break; }
        usleep(100000);
        elapsed_ms += 100u;
    }
    rc = 0;

done:
    if (bridge_pid > 1) stop_bridge(bridge_pid);
    unlink(BRIDGE_PID_PATH);
    if (route_owned) {
        (void)write_text(STATE_PATH, "restoring_dmdt\n");
        restore_ok = route_restore() == 0;
    } else {
        /* A partial release can still leave routing inconsistent. */
        restore_ok = route_restore() == 0;
    }
    unlink(AU_MARKER);
    unlink(OLD_DIRECT_MARKER);

    if (restore_ok) {
        (void)write_text(STATE_PATH, rc == 0 ? "complete_stock\n" : "failed_stock\n");
        if (pipefd[1] >= 0) {
            char token = 'R';
            (void)write(pipefd[1], &token, 1);
        }
    } else {
        (void)write_text(STATE_PATH, "restore_retry_by_watchdog\n");
        rc = 20;
    }
    if (pipefd[1] >= 0) close(pipefd[1]);
    if (watchdog > 1) {
        while (waitpid(watchdog, &st, 0) < 0 && errno == EINTR) {}
    }
    unlink(PID_PATH);
    unlink(BRIDGE_PID_PATH);
    return rc;
}
