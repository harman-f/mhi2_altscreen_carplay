/*
 * Minimal tee compatibility utility for MU1440/QNX 6.5.
 *
 * Runtime role: project-owned replacement for the M.I.B. apps/sbin/tee
 * dependency used by the original logging helpers.
 *
 * Supported subset:
 *   tee [-a] [-i] FILE [FILE ...]
 *
 * -a: append instead of truncate
 * -i: ignore SIGINT
 *
 * Input is copied byte-for-byte from stdin to stdout and to every file.
 */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>

#define BUF_SIZE 4096
#define MAX_OUT 64

static int copy_stream(FILE **outs, int count)
{
    unsigned char buf[BUF_SIZE];
    size_t n;
    int i, rc = 0;

    while ((n = fread(buf, 1, sizeof(buf), stdin)) > 0) {
        if (fwrite(buf, 1, n, stdout) != n) {
            fprintf(stderr, "tee: stdout: write error\n");
            rc = 1;
        }
        for (i = 0; i < count; ++i) {
            if (outs[i] && fwrite(buf, 1, n, outs[i]) != n) {
                fprintf(stderr, "tee: write error\n");
                rc = 1;
            }
        }
    }

    if (ferror(stdin)) {
        fprintf(stderr, "tee: stdin: read error\n");
        rc = 1;
    }

    if (fflush(stdout) != 0) rc = 1;
    for (i = 0; i < count; ++i)
        if (outs[i] && fflush(outs[i]) != 0) rc = 1;

    return rc;
}

int main(int argc, char **argv)
{
    FILE *outs[MAX_OUT];
    int append = 0, ignore_int = 0;
    int first = 1, count = 0, i, rc = 0, open_rc = 0;
    const char *mode;

    for (i = 0; i < MAX_OUT; ++i) outs[i] = NULL;

    while (first < argc && argv[first][0] == '-' && argv[first][1] != '\0') {
        const char *p = argv[first] + 1;
        if (strcmp(argv[first], "--") == 0) {
            ++first;
            break;
        }
        while (*p) {
            if (*p == 'a') append = 1;
            else if (*p == 'i') ignore_int = 1;
            else {
                fprintf(stderr, "usage: tee [-a] [-i] FILE [FILE ...]\n");
                return 2;
            }
            ++p;
        }
        ++first;
    }

    if (ignore_int)
        signal(SIGINT, SIG_IGN);

    mode = append ? "ab" : "wb";
    for (i = first; i < argc; ++i) {
        if (count >= MAX_OUT) {
            fprintf(stderr, "tee: too many output files\n");
            return 2;
        }
        outs[count] = fopen(argv[i], mode);
        if (!outs[count]) {
            fprintf(stderr, "tee: %s: %s\n", argv[i], strerror(errno));
            open_rc = 1;
        }
        ++count;
    }

    rc = copy_stream(outs, count);
    if (open_rc) rc = 1;

    for (i = 0; i < count; ++i)
        if (outs[i] && fclose(outs[i]) != 0) rc = 1;

    return rc;
}
