/* SPDX-License-Identifier: GPL-3.0-or-later
 * MU1440/QNX /tmp -> /dev/shmem syscall probe.
 * Diagnostic only: creates and removes /tmp/mibr-shmem-probe.{new,status}.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static void report(const char *op, long rc, int err)
{
    printf("%s rc=%ld errno=%d strerror=%s\n", op, rc, err,
           err ? strerror(err) : "OK");
}

int main(void)
{
    static const char *tmp = "/tmp/mibr-shmem-probe.new";
    static const char *dst = "/tmp/mibr-shmem-probe.status";
    static const char payload[] = "MIBR_SHMEM_PROBE\n";
    char buf[64];
    struct flock lk;
    int fd, fd2, e;
    ssize_t n;

    (void)unlink(tmp);
    (void)unlink(dst);

    errno = 0;
    fd = open(tmp, O_RDWR | O_CREAT | O_EXCL, 0600);
    e = errno; report("open_excl_create", fd, fd < 0 ? e : 0);
    if (fd < 0) return 10;

    errno = 0;
    fd2 = open(tmp, O_RDWR | O_CREAT | O_EXCL, 0600);
    e = errno; report("open_excl_collision", fd2, fd2 < 0 ? e : 0);
    if (fd2 >= 0) close(fd2);

    errno = 0;
    n = write(fd, payload, sizeof(payload) - 1u);
    e = errno; report("write", (long)n, n < 0 ? e : 0);

    memset(&lk, 0, sizeof(lk));
    lk.l_type = F_WRLCK;
    lk.l_whence = SEEK_SET;
    errno = 0;
    e = fcntl(fd, F_SETLK, &lk);
    {
        int saved = errno;
        report("fcntl_F_SETLK", e, e < 0 ? saved : 0);
    }

    errno = 0;
    e = fsync(fd);
    {
        int saved = errno;
        report("fsync", e, e < 0 ? saved : 0);
    }

    errno = 0;
    e = close(fd);
    {
        int saved = errno;
        report("close_write_fd", e, e < 0 ? saved : 0);
    }

    errno = 0;
    e = rename(tmp, dst);
    {
        int saved = errno;
        report("rename", e, e < 0 ? saved : 0);
    }

    errno = 0;
    fd = open(dst, O_RDONLY);
    e = errno; report("open_readback", fd, fd < 0 ? e : 0);
    if (fd >= 0) {
        errno = 0;
        n = read(fd, buf, sizeof(buf) - 1u);
        e = errno; report("readback", (long)n, n < 0 ? e : 0);
        if (n >= 0) {
            buf[n] = 0;
            printf("payload=%s", buf);
            if (!n || buf[n-1] != '\n') putchar('\n');
        }
        errno = 0;
        e = close(fd);
        {
            int saved = errno;
            report("close_read_fd", e, e < 0 ? saved : 0);
        }
    }

    errno = 0;
    e = unlink(dst);
    {
        int saved = errno;
        report("unlink_final", e, e < 0 ? saved : 0);
    }
    (void)unlink(tmp);

    puts("PROBE_DONE=YES");
    return 0;
}
