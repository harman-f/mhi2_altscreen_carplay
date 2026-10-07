/*
 * Minimal QNX TCP capture helper for diagnostic Stream-111 mirrors.
 *
 * Connects to an IPv4 TCP endpoint and writes the received byte stream
 * verbatim to a file. No protocol bytes are transmitted.
 *
 * Usage:
 *   tcp-capture HOST PORT OUTPUT [SECONDS]
 *
 * SECONDS=0 or omitted means run until EOF/SIGINT/SIGTERM.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

static volatile sig_atomic_t g_stop;

static void on_signal(int sig)
{
    (void)sig;
    g_stop = 1;
}

static uint64_t monotonic_ms(void)
{
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
    return (uint64_t)ts.tv_sec * 1000ull + (uint64_t)ts.tv_nsec / 1000000ull;
}

static int write_full(int fd, const uint8_t *p, size_t n)
{
    size_t off = 0;
    while (off < n) {
        ssize_t w = write(fd, p + off, n - off);
        if (w > 0) {
            off += (size_t)w;
            continue;
        }
        if (w < 0 && errno == EINTR) continue;
        return -1;
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *host, *out_path;
    char *end = NULL;
    long port_l, seconds_l = 0;
    int s = -1, out = -1, rc = 1;
    struct sockaddr_in addr;
    uint8_t buf[65536];
    uint64_t bytes = 0, chunks = 0, start_ms, deadline_ms = 0;

    if (argc != 4 && argc != 5) {
        fprintf(stderr, "usage: %s HOST PORT OUTPUT [SECONDS]\n", argv[0]);
        return 64;
    }

    host = argv[1];
    errno = 0;
    port_l = strtol(argv[2], &end, 10);
    if (errno || !end || *end || port_l < 1 || port_l > 65535) {
        fprintf(stderr, "TCP_CAPTURE=FAIL invalid_port\n");
        return 64;
    }

    if (argc == 5) {
        errno = 0;
        seconds_l = strtol(argv[4], &end, 10);
        if (errno || !end || *end || seconds_l < 0 || seconds_l > 7200) {
            fprintf(stderr, "TCP_CAPTURE=FAIL invalid_seconds\n");
            return 64;
        }
    }

    out_path = argv[3];
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);
    signal(SIGHUP, on_signal);
    signal(SIGPIPE, SIG_IGN);

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons((uint16_t)port_l);
    if (inet_aton(host, &addr.sin_addr) == 0) {
        fprintf(stderr, "TCP_CAPTURE=FAIL invalid_ipv4=%s\n", host);
        return 65;
    }

    s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) {
        fprintf(stderr, "TCP_CAPTURE=FAIL socket errno=%d\n", errno);
        goto done;
    }
    if (connect(s, (struct sockaddr *)&addr, sizeof(addr)) != 0) {
        fprintf(stderr, "TCP_CAPTURE=FAIL connect errno=%d\n", errno);
        goto done;
    }

    out = open(out_path, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (out < 0) {
        fprintf(stderr, "TCP_CAPTURE=FAIL open_output errno=%d path=%s\n", errno, out_path);
        goto done;
    }

    start_ms = monotonic_ms();
    if (seconds_l > 0) deadline_ms = start_ms + (uint64_t)seconds_l * 1000ull;

    fprintf(stderr,
            "TCP_CAPTURE=START host=%s port=%ld output=%s seconds=%ld\n",
            host, port_l, out_path, seconds_l);

    while (!g_stop) {
        fd_set rfds;
        struct timeval tv;
        int sr;
        ssize_t n;

        if (deadline_ms && monotonic_ms() >= deadline_ms) {
            rc = 0;
            break;
        }

        FD_ZERO(&rfds);
        FD_SET(s, &rfds);
        tv.tv_sec = 1;
        tv.tv_usec = 0;
        sr = select(s + 1, &rfds, NULL, NULL, &tv);
        if (sr < 0) {
            if (errno == EINTR) continue;
            fprintf(stderr, "TCP_CAPTURE=FAIL select errno=%d\n", errno);
            goto done;
        }
        if (sr == 0) continue;

        n = recv(s, buf, sizeof(buf), 0);
        if (n > 0) {
            if (write_full(out, buf, (size_t)n) != 0) {
                fprintf(stderr, "TCP_CAPTURE=FAIL write errno=%d\n", errno);
                goto done;
            }
            bytes += (uint64_t)n;
            ++chunks;
            continue;
        }
        if (n == 0) {
            rc = 0;
            break;
        }
        if (errno == EINTR) continue;
        fprintf(stderr, "TCP_CAPTURE=FAIL recv errno=%d\n", errno);
        goto done;
    }

    if (g_stop) rc = 0;

done:
    if (out >= 0) {
        (void)fsync(out);
        (void)close(out);
    }
    if (s >= 0) close(s);

    fprintf(stderr,
            "TCP_CAPTURE=%s bytes=%llu chunks=%llu elapsed_ms=%llu\n",
            rc == 0 ? "PASS" : "FAIL",
            (unsigned long long)bytes,
            (unsigned long long)chunks,
            (unsigned long long)(monotonic_ms() - start_ms));
    return rc;
}
