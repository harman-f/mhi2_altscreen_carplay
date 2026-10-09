/*
 * MU1440 Wireless CarPlay A3 credential bridge.
 *
 * Reads the stock ConnectionManager-generated /tmp/uaputl.cfg and emits a
 * canonical runtime state for the iAP2 0x5703 handoff / B0 transition.
 *
 * It never changes uap0, mlan0, uaputl, wpa_supplicant, dnsmasq, PF or routes.
 */

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#ifndef PATH_MAX
#define PATH_MAX 1024
#endif

struct wifi_state {
    char ssid[65];
    char psk[128];
    unsigned channel;
    unsigned security_type;
    int have_ssid;
    int have_psk;
    int have_channel;
    int have_wpa;
    int have_wpa2;
};

static char *trim(char *s)
{
    char *end;

    while (*s != '\0' && isspace((unsigned char)*s)) {
        ++s;
    }

    end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1])) {
        --end;
    }
    *end = '\0';
    return s;
}

static int copy_value(char *dst, size_t dst_size, const char *src)
{
    size_t n = strlen(src);
    if (n >= dst_size) {
        return -1;
    }
    memcpy(dst, src, n + 1);
    return 0;
}

static void unquote(char *s)
{
    size_t n = strlen(s);
    if (n >= 2 && s[0] == '"' && s[n - 1] == '"') {
        memmove(s, s + 1, n - 2);
        s[n - 2] = '\0';
    }
}

static int parse_channel(const char *value, unsigned *channel)
{
    char *end = NULL;
    unsigned long v = strtoul(value, &end, 10);

    if (end == value || v == 0 || v > 255) {
        return -1;
    }

    *channel = (unsigned)v;
    return 0;
}

static int parse_uaputl(const char *path, struct wifi_state *s)
{
    FILE *fp;
    char line[1024];

    fp = fopen(path, "r");
    if (fp == NULL) {
        fprintf(stderr, "A3_CRED_ERROR open=%s errno=%d\n", path, errno);
        return -1;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        char *p = trim(line);
        char *eq;
        char *key;
        char *value;

        if (*p == '\0' || *p == '#' || *p == ';') {
            continue;
        }

        eq = strchr(p, '=');
        if (eq == NULL) {
            continue;
        }

        *eq = '\0';
        key = trim(p);
        value = trim(eq + 1);

        if (strcmp(key, "SSID") == 0) {
            char tmp[sizeof(s->ssid)];
            if (copy_value(tmp, sizeof(tmp), value) != 0) {
                fclose(fp);
                return -1;
            }
            unquote(tmp);
            if (copy_value(s->ssid, sizeof(s->ssid), tmp) != 0) {
                fclose(fp);
                return -1;
            }
            s->have_ssid = 1;
        } else if (strcmp(key, "PSK") == 0) {
            char tmp[sizeof(s->psk)];
            if (copy_value(tmp, sizeof(tmp), value) != 0) {
                fclose(fp);
                return -1;
            }
            unquote(tmp);
            if (copy_value(s->psk, sizeof(s->psk), tmp) != 0) {
                fclose(fp);
                return -1;
            }
            s->have_psk = 1;
        } else if (strcmp(key, "Channel") == 0) {
            if (parse_channel(value, &s->channel) == 0) {
                s->have_channel = 1;
            }
        } else if (strcmp(key, "PwkCipherWPA2") == 0
                || strcmp(key, "ProtoWPA2") == 0) {
            s->have_wpa2 = 1;
        } else if (strcmp(key, "PwkCipherWPA") == 0
                || strcmp(key, "ProtoWPA") == 0) {
            s->have_wpa = 1;
        }
    }

    fclose(fp);

    if (s->have_wpa2 || s->have_wpa) {
        /* Exact stock iAP2 0x5703 mapping:
         * WPA / WPA2 / WPA2 Personal -> SecurityType 2.
         */
        s->security_type = 2;
    } else if (!s->have_psk) {
        s->security_type = 0;
    } else {
        /* A PSK without an identified WPA family is not safe to guess. */
        fprintf(stderr,
            "A3_CRED_ERROR reason=psk_without_supported_security_marker\n");
        return -1;
    }

    return 0;
}

static int validate(const struct wifi_state *s)
{
    size_t ssid_len;
    size_t psk_len;

    if (!s->have_ssid || !s->have_channel) {
        fprintf(stderr,
            "A3_CRED_ERROR reason=missing_required_field ssid=%d channel=%d\n",
            s->have_ssid, s->have_channel);
        return -1;
    }

    ssid_len = strlen(s->ssid);
    if (ssid_len == 0 || ssid_len > 32) {
        fprintf(stderr,
            "A3_CRED_ERROR reason=invalid_ssid_length length=%u\n",
            (unsigned)ssid_len);
        return -1;
    }

    if (s->security_type == 2) {
        if (!s->have_psk) {
            fprintf(stderr,
                "A3_CRED_ERROR reason=secured_ap_without_psk\n");
            return -1;
        }
        psk_len = strlen(s->psk);
        if (psk_len == 64) {
            fprintf(stderr,
                "A3_CRED_ERROR reason=raw_256bit_psk_not_verified_as_5703_passphrase length=64\n");
            return -1;
        }
        if (psk_len < 8 || psk_len > 63) {
            fprintf(stderr,
                "A3_CRED_ERROR reason=invalid_passphrase_length length=%u\n",
                (unsigned)psk_len);
            return -1;
        }
    }

    return 0;
}

static int write_state(const char *path, const struct wifi_state *s)
{
    char tmp[PATH_MAX + 8];
    FILE *fp;
    int fd;

    if (snprintf(tmp, sizeof(tmp), "%s.tmp", path) >= (int)sizeof(tmp)) {
        return -1;
    }

    fd = open(tmp, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) {
        fprintf(stderr, "A3_CRED_ERROR create=%s errno=%d\n", tmp, errno);
        return -1;
    }

    fp = fdopen(fd, "w");
    if (fp == NULL) {
        close(fd);
        unlink(tmp);
        return -1;
    }

    fprintf(fp, "SSID=%s\n", s->ssid);
    fprintf(fp, "Passphrase=%s\n", s->have_psk ? s->psk : "");
    fprintf(fp, "SecurityType=%u\n", s->security_type);
    fprintf(fp, "Channel=%u\n", s->channel);

    if (fclose(fp) != 0) {
        unlink(tmp);
        return -1;
    }

    (void)chmod(tmp, 0600);

    if (rename(tmp, path) != 0) {
        fprintf(stderr, "A3_CRED_ERROR rename=%s errno=%d\n", path, errno);
        unlink(tmp);
        return -1;
    }

    (void)chmod(path, 0600);
    return 0;
}

static void usage(const char *argv0)
{
    fprintf(stderr,
        "usage: %s [--input /tmp/uaputl.cfg] "
        "[--output /tmp/mhi2-wcp-a3-wifi.state]\n",
        argv0);
}

int main(int argc, char **argv)
{
    const char *input = "/tmp/uaputl.cfg";
    const char *output = "/tmp/mhi2-wcp-a3-wifi.state";
    struct wifi_state s;
    int i;

    memset(&s, 0, sizeof(s));

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--input") == 0 && i + 1 < argc) {
            input = argv[++i];
        } else if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
            output = argv[++i];
        } else if (strcmp(argv[i], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else {
            usage(argv[0]);
            return 64;
        }
    }

    if (parse_uaputl(input, &s) != 0 || validate(&s) != 0) {
        return 2;
    }

    if (write_state(output, &s) != 0) {
        return 3;
    }

    printf(
        "A3_CRED_READY ssid=%s channel=%u security=%u passphrase_len=%u state=%s\n",
        s.ssid,
        s.channel,
        s.security_type,
        (unsigned)(s.have_psk ? strlen(s.psk) : 0),
        output);

    return 0;
}
