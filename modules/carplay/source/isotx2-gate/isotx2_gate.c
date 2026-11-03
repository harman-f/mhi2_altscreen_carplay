/* SPDX-License-Identifier: GPL-3.0-or-later */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/uio.h>
#include <unistd.h>

#define DEFAULT_TARGET "/dev/mlb/isoTX2"
#define DIRECT_MARKER  "/tmp/mibr-isotx2-gate.direct"
#define RESET_MARKER   "/tmp/mibr-isotx2-gate.reset"
#define STATS_PATH     "/tmp/mibr-isotx2-gate.stats"
#define LOG_PATH       "/tmp/mibr-isotx2-gate.log"
#define MAX_TRACK_FD   2048

typedef int (*fn_open_t)(const char *, int, ...);
typedef int (*fn_open64_t)(const char *, int, ...);
typedef int (*fn_close_t)(int);
typedef ssize_t (*fn_writev_t)(int, const struct iovec *, int);

static fn_open_t real_open_fn;
static fn_open64_t real_open64_fn;
static fn_close_t real_close_fn;
static fn_writev_t real_writev_fn;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned char tracked[MAX_TRACK_FD];
static unsigned long long total_open_calls;
static unsigned long long total_open64_calls;
static unsigned long long total_writev_calls;
static unsigned long long total_close_calls;
static unsigned long long tracked_open_calls;
static unsigned long long tracked_close_calls;
static unsigned long long passed_calls;
static unsigned long long passed_bytes;
static unsigned long long dropped_calls;
static unsigned long long dropped_bytes;
static int tracked_fds;
static int last_mode = -1;
static int resolving;
static int last_open_fd = -1;
static int last_open64_fd = -1;
static int last_writev_fd = -1;
static int last_writev_iovcnt;
static unsigned long long last_writev_bytes;
static int last_open_flags;
static int last_open64_flags;
static char last_open_path[160];
static char last_open64_path[160];

static const char *target_path(void)
{
    const char *p = getenv("MIBR_ISOTX2_GATE_TARGET");
    return (p && *p) ? p : DEFAULT_TARGET;
}

static void resolve_real(void)
{
    if (real_open_fn && real_open64_fn && real_close_fn && real_writev_fn) return;
    if (resolving) return;
    resolving = 1;
    if (!real_open_fn) real_open_fn = (fn_open_t)dlsym(RTLD_NEXT, "open");
    if (!real_open64_fn) real_open64_fn = (fn_open64_t)dlsym(RTLD_NEXT, "open64");
    if (!real_close_fn) real_close_fn = (fn_close_t)dlsym(RTLD_NEXT, "close");
    if (!real_writev_fn) real_writev_fn = (fn_writev_t)dlsym(RTLD_NEXT, "writev");
    resolving = 0;
}

static int marker_direct(void)
{
    return access(DIRECT_MARKER, F_OK) == 0;
}

static void raw_append_log(const char *msg)
{
    int fd;
    if (!msg) return;
    resolve_real();
    if (!real_open_fn || !real_close_fn) return;
    fd = real_open_fn(LOG_PATH, O_WRONLY | O_CREAT | O_APPEND, 0666);
    if (fd >= 0) {
        (void)write(fd, msg, strlen(msg));
        (void)write(fd, "\n", 1);
        (void)real_close_fn(fd);
    }
}

static void write_stats_locked(int mode)
{
    char b[1536];
    int fd, n;
    resolve_real();
    if (!real_open_fn || !real_close_fn) return;
    n = snprintf(b, sizeof(b),
        "loaded=1\n"
        "diagnostic_revision=run51_no_open_churn\n"
        "mode=%s\n"
        "target=%s\n"
        "total_open_calls=%llu\n"
        "total_open64_calls=%llu\n"
        "total_writev_calls=%llu\n"
        "total_close_calls=%llu\n"
        "last_open_fd=%d\n"
        "last_open_flags=%d\n"
        "last_open_path=%s\n"
        "last_open64_fd=%d\n"
        "last_open64_flags=%d\n"
        "last_open64_path=%s\n"
        "last_writev_fd=%d\n"
        "last_writev_iovcnt=%d\n"
        "last_writev_bytes=%llu\n"
        "tracked_fds=%d\n"
        "tracked_open_calls=%llu\n"
        "tracked_close_calls=%llu\n"
        "passed_writev_calls=%llu\n"
        "passed_bytes=%llu\n"
        "dropped_writev_calls=%llu\n"
        "dropped_bytes=%llu\n",
        mode ? "direct" : "stock", target_path(),
        total_open_calls, total_open64_calls, total_writev_calls, total_close_calls,
        last_open_fd, last_open_flags, last_open_path,
        last_open64_fd, last_open64_flags, last_open64_path,
        last_writev_fd, last_writev_iovcnt, last_writev_bytes,
        tracked_fds, tracked_open_calls, tracked_close_calls,
        passed_calls, passed_bytes, dropped_calls, dropped_bytes);
    if (n <= 0) return;
    fd = real_open_fn(STATS_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd >= 0) {
        (void)write(fd, b, (size_t)n);
        (void)real_close_fn(fd);
    }
}

static void maybe_reset_locked(void)
{
    if (access(RESET_MARKER, F_OK) != 0) return;
    total_open_calls = 0;
    total_open64_calls = 0;
    total_writev_calls = 0;
    total_close_calls = 0;
    tracked_open_calls = 0;
    tracked_close_calls = 0;
    passed_calls = 0;
    passed_bytes = 0;
    dropped_calls = 0;
    dropped_bytes = 0;
    (void)unlink(RESET_MARKER);
    raw_append_log("COUNTERS RESET");
}

static size_t iov_total(const struct iovec *iov, int iovcnt)
{
    size_t total = 0;
    int i;
    if (!iov || iovcnt <= 0) return 0;
    for (i = 0; i < iovcnt; ++i) total += iov[i].iov_len;
    return total;
}

int open(const char *path, int flags, ...)
{
    int fd, mode_needed = 0;
    mode_t mode = 0;
    va_list ap;

    resolve_real();
    if (!real_open_fn) { errno = ENOSYS; return -1; }

    if (flags & O_CREAT) {
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
        mode_needed = 1;
    }

    fd = mode_needed ? real_open_fn(path, flags, mode) : real_open_fn(path, flags);
    pthread_mutex_lock(&lock);
    ++total_open_calls;
    last_open_fd = fd;
    last_open_flags = flags;
    snprintf(last_open_path, sizeof(last_open_path), "%s", path ? path : "<null>");
    pthread_mutex_unlock(&lock);
    if (fd >= 0 && path && strcmp(path, target_path()) == 0) {
        pthread_mutex_lock(&lock);
        if (fd < MAX_TRACK_FD && !tracked[fd]) {
            tracked[fd] = 1;
            ++tracked_fds;
        }
        ++tracked_open_calls;
        maybe_reset_locked();
        write_stats_locked(marker_direct());
        pthread_mutex_unlock(&lock);
        raw_append_log("TRACK open isoTX2");
    }
    return fd;
}

int open64(const char *path, int flags, ...)
{
    int fd, mode_needed = 0;
    mode_t mode = 0;
    va_list ap;

    resolve_real();
    if (!real_open64_fn) {
        /* QNX/libc variants without a distinct open64 symbol fall back to open. */
        real_open64_fn = (fn_open64_t)real_open_fn;
    }
    if (!real_open64_fn) { errno = ENOSYS; return -1; }

    if (flags & O_CREAT) {
        va_start(ap, flags);
        mode = va_arg(ap, mode_t);
        va_end(ap);
        mode_needed = 1;
    }

    fd = mode_needed ? real_open64_fn(path, flags, mode) : real_open64_fn(path, flags);
    pthread_mutex_lock(&lock);
    ++total_open64_calls;
    last_open64_fd = fd;
    last_open64_flags = flags;
    snprintf(last_open64_path, sizeof(last_open64_path), "%s", path ? path : "<null>");
    pthread_mutex_unlock(&lock);
    if (fd >= 0 && path && strcmp(path, target_path()) == 0) {
        pthread_mutex_lock(&lock);
        if (fd < MAX_TRACK_FD && !tracked[fd]) {
            tracked[fd] = 1;
            ++tracked_fds;
        }
        ++tracked_open_calls;
        maybe_reset_locked();
        write_stats_locked(marker_direct());
        pthread_mutex_unlock(&lock);
        raw_append_log("TRACK open64 isoTX2");
    }
    return fd;
}

int close(int fd)
{
    int was = 0;
    resolve_real();
    if (!real_close_fn) { errno = ENOSYS; return -1; }

    pthread_mutex_lock(&lock);
    ++total_close_calls;
    if (fd >= 0 && fd < MAX_TRACK_FD && tracked[fd]) {
        tracked[fd] = 0;
        if (tracked_fds > 0) --tracked_fds;
        ++tracked_close_calls;
        was = 1;
        write_stats_locked(marker_direct());
    }
    pthread_mutex_unlock(&lock);
    if (was) raw_append_log("TRACK close isoTX2");
    return real_close_fn(fd);
}

ssize_t writev(int fd, const struct iovec *iov, int iovcnt)
{
    size_t total;
    int is_tracked = 0;
    int direct;
    int saved_errno = errno;
    ssize_t rc;

    resolve_real();
    if (!real_writev_fn) { errno = ENOSYS; return -1; }

    total = iov_total(iov, iovcnt);
    pthread_mutex_lock(&lock);
    ++total_writev_calls;
    last_writev_fd = fd;
    last_writev_iovcnt = iovcnt;
    last_writev_bytes = (unsigned long long)total;
    if ((total_writev_calls & 31u) == 1u) write_stats_locked(marker_direct());
    if (fd >= 0 && fd < MAX_TRACK_FD && tracked[fd]) is_tracked = 1;
    pthread_mutex_unlock(&lock);

    if (!is_tracked) return real_writev_fn(fd, iov, iovcnt);

    direct = marker_direct();

    pthread_mutex_lock(&lock);
    maybe_reset_locked();
    if (direct != last_mode) {
        last_mode = direct;
        raw_append_log(direct ? "MODE DIRECT" : "MODE STOCK");
    }

    if (direct) {
        ++dropped_calls;
        dropped_bytes += (unsigned long long)total;
        if ((dropped_calls & 31u) == 1u) write_stats_locked(1);
        pthread_mutex_unlock(&lock);
        errno = saved_errno;
        return (ssize_t)total;
    }
    pthread_mutex_unlock(&lock);

    rc = real_writev_fn(fd, iov, iovcnt);

    pthread_mutex_lock(&lock);
    ++passed_calls;
    if (rc > 0) passed_bytes += (unsigned long long)rc;
    if ((passed_calls & 31u) == 1u) write_stats_locked(0);
    pthread_mutex_unlock(&lock);
    return rc;
}

__attribute__((constructor))
static void gate_ctor(void)
{
    resolve_real();
    raw_append_log("libmibr_isotx2_gate LOADED");
    pthread_mutex_lock(&lock);
    last_mode = marker_direct();
    maybe_reset_locked();
    write_stats_locked(last_mode);
    pthread_mutex_unlock(&lock);
}
