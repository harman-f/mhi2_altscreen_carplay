/* SPDX-License-Identifier: GPL-3.0-or-later
 * Regression for the MU1440 /dev/shmem lock behaviour measured on the vehicle (2026-11-06):
 * lstat() of an existing lock name transiently fails with EINVAL (streaks up to 169 ms), and the
 * old unlock skipped the unlink on such an error, leaving a permanent lock. Host libc never does
 * this, so lstat is redirected to an injector. HOST-ONLY; not a QNX execution claim.
 */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

static int inject_einval;            /* number of lstat calls on a matching path that fail */
static const char *inject_match;     /* substring of the path to fail */
static int test_lstat(const char *path, struct stat *st);
#define lstat test_lstat
#include "../modules/carplay/source/alt111-settings/settings_posix.c"
#undef lstat

static int test_lstat(const char *path, struct stat *st)
{
    if (inject_einval > 0 && inject_match && strstr(path, inject_match)) {
        --inject_einval;
        errno = EINVAL;
        return -1;
    }
    return lstat(path, st);
}

static long dead_pid(void)
{
    pid_t child = fork();
    assert(child >= 0);
    if (!child) _exit(0);
    assert(waitpid(child, NULL, 0) == child);
    return (long)child;
}

int main(void)
{
    char root[] = "/tmp/mibr-shmem-errno-XXXXXX";
    char lock[512], file[512], error[512], buf[64];
    struct alt111_settings_paths paths;
    struct stat st;
    size_t size = 0;
    int fd, n;

    assert(mkdtemp(root) != NULL);
    paths.temp = root;
    paths.persistent = root;
    assert(path_for(lock, sizeof(lock), root, "mibr-alt111-settings.lock-v2") == 0);
    inject_match = "lock-v2";

    /* 1. unlock while lstat keeps failing with EINVAL: the holder must still remove its lock. */
    fd = lock_settings(&paths, 1, error, sizeof(error));
    assert(fd >= 0);
    inject_einval = 100000;
    unlock_settings(&paths, fd);
    inject_einval = 0;
    assert(lstat(lock, &st) == -1 && errno == ENOENT);

    /* 2. dead owner + transient EINVAL streak shorter than the window: acquisition succeeds. */
    fd = open(lock, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0);
    n = snprintf(buf, sizeof(buf), "%ld\n", dead_pid());
    assert(write(fd, buf, (size_t)n) == n);
    close(fd);
    inject_einval = 200;
    fd = lock_settings(&paths, 1, error, sizeof(error));
    assert(fd >= 0);
    inject_einval = 0;
    unlock_settings(&paths, fd);
    assert(lstat(lock, &st) == -1 && errno == ENOENT);

    /* 3. read_file rides out a transient EINVAL streak instead of reporting INVALID_VALUE. */
    assert(path_for(file, sizeof(file), root, "mibr-carplay111-compat-profile") == 0);
    fd = open(file, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    assert(fd >= 0 && write(fd, "mibr_legacy\n", 12) == 12);
    close(fd);
    inject_match = "compat-profile";
    inject_einval = 100;
    assert(read_file(file, buf, sizeof(buf), &size) == 0 && size == 12);
    assert(!memcmp(buf, "mibr_legacy\n", 12));

    /* 4. a streak longer than the window fails cleanly with the errno in the message. */
    inject_match = "lock-v2";
    fd = open(lock, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0);
    n = snprintf(buf, sizeof(buf), "%ld\n", (long)getpid());
    assert(write(fd, buf, (size_t)n) == n);
    close(fd);
    inject_einval = 100000;
    assert(lock_settings(&paths, 1, error, sizeof(error)) < 0);
    inject_einval = 0;
    assert(strstr(error, "APPLY_FAILED lock_stat errno=22") != NULL);
    assert(unlink(lock) == 0);

    assert(unlink(file) == 0 && rmdir(root) == 0);
    printf("ALT111_SETTINGS_SHMEM_ERRNO_TEST=PASS host_only=1\n");
    return 0;
}
