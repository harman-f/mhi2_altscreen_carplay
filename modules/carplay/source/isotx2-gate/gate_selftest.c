/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/uio.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    struct iovec v[2];
    int fd;
    ssize_t n;
    if (argc != 2) return 2;
    fd = open(argv[1], O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) return 3;
    v[0].iov_base = (void *)"abc";
    v[0].iov_len = 3;
    v[1].iov_base = (void *)"DEF";
    v[1].iov_len = 3;
    n = writev(fd, v, 2);
    close(fd);
    printf("writev_rc=%ld\n", (long)n);
    return n == 6 ? 0 : 4;
}
