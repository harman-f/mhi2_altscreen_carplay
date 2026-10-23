/* SPDX-License-Identifier: GPL-3.0-or-later
 * Creates one MIBR/3 credential file: 64 lowercase hex characters plus LF,
 * mode 0600, owned by the caller. The file must not exist (O_EXCL), so an
 * existing credential is never overwritten. MU1440 has no od/hexdump, hence
 * this helper. The token is never printed.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int read_full(int fd, unsigned char *p, size_t n) {
    size_t used = 0;
    while (used < n) {
        ssize_t k = read(fd, p + used, n - used);
        if (k < 0 && errno == EINTR) continue;
        if (k <= 0) return -1;
        used += (size_t)k;
    }
    return 0;
}

int main(int argc, char **argv) {
    static const char hex[] = "0123456789abcdef";
    unsigned char raw[32];
    char text[65];
    int in, out;
    size_t i;
    ssize_t w;
    if (argc != 2 || argv[1][0] != '/') { fprintf(stderr, "usage: %s /absolute/path\n", argv[0]); return 2; }
    in = open("/dev/urandom", O_RDONLY);
    if (in < 0) in = open("/dev/random", O_RDONLY);
    if (in < 0 || read_full(in, raw, sizeof(raw))) { fprintf(stderr, "MIBR_V3_GENKEY=NO_ENTROPY\n"); return 3; }
    close(in);
    for (i = 0; i < sizeof(raw); i++) { text[2 * i] = hex[raw[i] >> 4]; text[2 * i + 1] = hex[raw[i] & 15]; }
    text[64] = '\n';
    memset(raw, 0, sizeof(raw));
    umask(077);
    out = open(argv[1], O_WRONLY | O_CREAT | O_EXCL, 0600);
    if (out < 0) { memset(text, 0, sizeof(text)); fprintf(stderr, "MIBR_V3_GENKEY=EXISTS_OR_UNWRITABLE\n"); return 4; }
    w = write(out, text, sizeof(text));
    memset(text, 0, sizeof(text));
    /* No fsync: the credential is a RAM file (/tmp) by design; MU1440's /tmp
     * rejected fsync on the first vehicle run (2026-10-20). */
    if (w != (ssize_t)sizeof(text) || fchmod(out, 0600) || close(out)) {
        unlink(argv[1]);
        fprintf(stderr, "MIBR_V3_GENKEY=WRITE_FAILED\n");
        return 5;
    }
    printf("MIBR_V3_GENKEY=CREATED mode=0600\n");
    return 0;
}
