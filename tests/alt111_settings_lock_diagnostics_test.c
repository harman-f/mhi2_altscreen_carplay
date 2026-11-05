/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <sys/stat.h>
#include "../modules/carplay/source/alt111-settings/settings_posix.c"

int main(void)
{
    char root[] = "/tmp/mibr-lock-diagnostics-XXXXXX";
    char lock[512], error[512];
    struct alt111_settings_paths paths;
    struct stat before, after;
    int fd, out;
    assert(mkdtemp(root) != NULL);
    paths.temp = root;
    paths.persistent = root;
    assert(path_for(lock, sizeof(lock), root, "mibr-alt111-settings.lock-v2") == 0);

    /* Live owner: diagnostics are bounded and acquisition remains fail-closed. */
    fd = open(lock, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0);
    { char pid[64]; int n = snprintf(pid, sizeof(pid), "%ld\n", (long)getpid());
      assert(write(fd, pid, (size_t)n) == n); }
    assert(!fstat(fd, &before));
    assert(lock_settings(&paths, 0, error, sizeof(error)) < 0);
    assert(strstr(error, "BUSY settings_lock waiter_pid=") == error);
    assert(strstr(error, "owner_state=readable") != NULL);
    assert(strstr(error, "owner_liveness=live") != NULL);
    assert(strstr(error, "wait_ms=") != NULL && strstr(error, "attempts=100") != NULL);
    assert(strstr(error, "lock_dev=") != NULL && strstr(error, "lock_ino=") != NULL);
    assert(!fstat(fd, &after) && before.st_ino == after.st_ino);
    assert(!lstat(lock, &after) && before.st_ino == after.st_ino);
    close(fd);
    printf("held-lock: %s\n", error);

    /* Malformed owner remains BUSY and is not reclaimed. */
    assert(unlink(lock) == 0);
    fd = open(lock, O_WRONLY | O_CREAT | O_EXCL, 0600);
    assert(fd >= 0 && write(fd, "not-a-pid\n", 10) == 10 && close(fd) == 0);
    assert(lock_settings(&paths, 0, error, sizeof(error)) < 0);
    assert(strstr(error, "owner_state=invalid") != NULL);
    assert(strstr(error, "owner_liveness=unknown") != NULL);
    assert(!lstat(lock, &after));
    printf("malformed-owner: %s\n", error);

    /* Once the prior lock disappears, normal exclusive acquisition recovers. */
    assert(unlink(lock) == 0);
    out = lock_settings(&paths, 0, error, sizeof(error));
    assert(out >= 0);
    unlock_settings(&paths, out);
    assert(lstat(lock, &after) == -1);
    assert(rmdir(root) == 0);
    puts("release-recovery: PASS");
    return 0;
}
