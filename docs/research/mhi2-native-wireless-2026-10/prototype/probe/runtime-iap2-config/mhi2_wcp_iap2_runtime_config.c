/*
 * MU1440 Wireless CarPlay runtime iAP2 configuration generator.
 *
 * Copies the stock iAP2 configuration to a temporary runtime file and replaces
 * only the [WiFi] section with the live A3 state. It never edits the stock
 * configuration and never logs the passphrase.
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
    char passphrase[128];
    unsigned security_type;
    unsigned channel;
    int have_ssid;
    int have_passphrase;
    int have_security_type;
    int have_channel;
};

static char *trim(char *s)
{
    char *end;

    while (*s != '\0' && isspace((unsigned char)*s))
        ++s;

    end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1]))
        --end;
    *end = '\0';
    return s;
}

static int copy_value(char *dst, size_t cap, const char *src)
{
    size_t n = strlen(src);
    if (n >= cap)
        return -1;
    memcpy(dst, src, n + 1);
    return 0;
}

static int has_line_break(const char *s)
{
    for (; *s != '\0'; ++s) {
        if (*s == '\r' || *s == '\n')
            return 1;
    }
    return 0;
}

static int parse_uint(const char *s, unsigned *out)
{
    char *end = NULL;
    unsigned long v;

    if (s == NULL || *s == '\0')
        return -1;
    errno = 0;
    v = strtoul(s, &end, 10);
    if (errno != 0 || end == s || *end != '\0' || v > 0xffffffffUL)
        return -1;
    *out = (unsigned)v;
    return 0;
}

static int load_state(const char *path, struct wifi_state *state)
{
    FILE *fp;
    char line[1024];

    fp = fopen(path, "r");
    if (fp == NULL) {
        fprintf(stderr, "IAP2_CFG_ERROR open_state=%s errno=%d\n", path, errno);
        return -1;
    }

    while (fgets(line, sizeof(line), fp) != NULL) {
        char *p = trim(line);
        char *eq;
        char *key;
        char *value;

        if (*p == '\0' || *p == '#' || *p == ';')
            continue;

        eq = strchr(p, '=');
        if (eq == NULL)
            continue;
        *eq = '\0';
        key = trim(p);
        value = trim(eq + 1);

        if (strcmp(key, "SSID") == 0) {
            if (copy_value(state->ssid, sizeof(state->ssid), value) != 0) {
                fclose(fp);
                return -1;
            }
            state->have_ssid = 1;
        } else if (strcmp(key, "Passphrase") == 0) {
            if (copy_value(state->passphrase, sizeof(state->passphrase), value) != 0) {
                fclose(fp);
                return -1;
            }
            state->have_passphrase = 1;
        } else if (strcmp(key, "SecurityType") == 0) {
            if (parse_uint(value, &state->security_type) != 0) {
                fclose(fp);
                return -1;
            }
            state->have_security_type = 1;
        } else if (strcmp(key, "Channel") == 0) {
            if (parse_uint(value, &state->channel) != 0) {
                fclose(fp);
                return -1;
            }
            state->have_channel = 1;
        }
    }

    fclose(fp);
    return 0;
}

static int validate_state(const struct wifi_state *state)
{
    size_t ssid_len;
    size_t pass_len;

    if (!state->have_ssid || !state->have_security_type || !state->have_channel) {
        fprintf(stderr,
            "IAP2_CFG_ERROR reason=missing_state_field ssid=%d security=%d channel=%d\n",
            state->have_ssid, state->have_security_type, state->have_channel);
        return -1;
    }

    ssid_len = strlen(state->ssid);
    if (ssid_len == 0 || ssid_len > 32 || has_line_break(state->ssid)) {
        fprintf(stderr, "IAP2_CFG_ERROR reason=invalid_ssid\n");
        return -1;
    }

    if (state->channel == 0 || state->channel > 255) {
        fprintf(stderr, "IAP2_CFG_ERROR reason=invalid_channel channel=%u\n",
            state->channel);
        return -1;
    }

    if (state->security_type != 0 && state->security_type != 2) {
        fprintf(stderr,
            "IAP2_CFG_ERROR reason=unsupported_security_type security=%u\n",
            state->security_type);
        return -1;
    }

    pass_len = strlen(state->passphrase);
    if (has_line_break(state->passphrase)) {
        fprintf(stderr, "IAP2_CFG_ERROR reason=invalid_passphrase\n");
        return -1;
    }

    if (state->security_type == 2) {
        if (!state->have_passphrase || pass_len < 8 || pass_len > 63) {
            fprintf(stderr,
                "IAP2_CFG_ERROR reason=invalid_wpa_passphrase_length length=%u\n",
                (unsigned)pass_len);
            return -1;
        }
    } else if (pass_len != 0) {
        fprintf(stderr,
            "IAP2_CFG_ERROR reason=open_network_with_passphrase\n");
        return -1;
    }

    return 0;
}

static int section_name(const char *line, char *name, size_t cap)
{
    const char *p = line;
    const char *end;
    size_t n;

    while (*p != '\0' && isspace((unsigned char)*p))
        ++p;
    if (*p != '[')
        return 0;
    ++p;
    end = strchr(p, ']');
    if (end == NULL)
        return 0;

    while (end > p && isspace((unsigned char)end[-1]))
        --end;
    while (p < end && isspace((unsigned char)*p))
        ++p;

    n = (size_t)(end - p);
    if (n == 0 || n >= cap)
        return 0;
    memcpy(name, p, n);
    name[n] = '\0';
    return 1;
}

static int ascii_equal_ci(const char *a, const char *b)
{
    while (*a != '\0' && *b != '\0') {
        if (tolower((unsigned char)*a) != tolower((unsigned char)*b))
            return 0;
        ++a;
        ++b;
    }
    return *a == '\0' && *b == '\0';
}

static int write_runtime_config(const char *base_path,
                                const char *output_path,
                                const struct wifi_state *state)
{
    FILE *in = NULL;
    FILE *out = NULL;
    int fd = -1;
    char tmp_path[PATH_MAX];
    char line[2048];
    int skip_wifi = 0;
    int wrote_any = 0;
    int last_had_newline = 1;
    int rc = -1;

    if (snprintf(tmp_path, sizeof(tmp_path), "%s.tmp.%ld",
                 output_path, (long)getpid()) >= (int)sizeof(tmp_path)) {
        fprintf(stderr, "IAP2_CFG_ERROR reason=output_path_too_long\n");
        return -1;
    }

    in = fopen(base_path, "r");
    if (in == NULL) {
        fprintf(stderr, "IAP2_CFG_ERROR open_base=%s errno=%d\n", base_path, errno);
        goto out;
    }

    fd = open(tmp_path, O_WRONLY | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) {
        fprintf(stderr, "IAP2_CFG_ERROR create=%s errno=%d\n", tmp_path, errno);
        goto out;
    }

    out = fdopen(fd, "w");
    if (out == NULL) {
        fprintf(stderr, "IAP2_CFG_ERROR fdopen errno=%d\n", errno);
        goto out;
    }
    fd = -1;

    while (fgets(line, sizeof(line), in) != NULL) {
        char name[64];
        if (section_name(line, name, sizeof(name))) {
            skip_wifi = ascii_equal_ci(name, "WiFi");
            if (skip_wifi)
                continue;
        }

        if (!skip_wifi) {
            size_t n = strlen(line);
            if (fputs(line, out) == EOF)
                goto out;
            wrote_any = 1;
            last_had_newline = n > 0 && line[n - 1] == '\n';
        }
    }
    if (ferror(in))
        goto out;

    if (wrote_any && !last_had_newline && fputc('\n', out) == EOF)
        goto out;
    if (wrote_any && fputc('\n', out) == EOF)
        goto out;

    if (fprintf(out,
            "# Runtime-only Wireless CarPlay WiFi section; generated from A3 state.\n"
            "[WiFi]\n"
            "enable=yes\n"
            "name=wifi\n"
            "carplay=yes\n"
            "SSID=%s\n",
            state->ssid) < 0)
        goto out;

    if (state->security_type == 2) {
        if (fprintf(out, "Passphrase=%s\n", state->passphrase) < 0)
            goto out;
    }

    if (fprintf(out,
            "SecurityType=%u\n"
            "Channel=%u\n",
            state->security_type, state->channel) < 0)
        goto out;

    if (fflush(out) != 0)
        goto out;
    if (fsync(fileno(out)) != 0)
        goto out;
    if (fclose(out) != 0) {
        out = NULL;
        goto out;
    }
    out = NULL;

    (void)chmod(tmp_path, 0600);
    if (rename(tmp_path, output_path) != 0) {
        fprintf(stderr, "IAP2_CFG_ERROR rename=%s errno=%d\n", output_path, errno);
        goto out;
    }
    (void)chmod(output_path, 0600);
    rc = 0;

out:
    if (in != NULL)
        fclose(in);
    if (out != NULL)
        fclose(out);
    else if (fd >= 0)
        close(fd);
    if (rc != 0)
        unlink(tmp_path);
    return rc;
}

static void usage(const char *argv0)
{
    fprintf(stderr,
        "usage: %s [--base /etc/mm/iap2.cfg] "
        "[--state /tmp/mhi2-wcp-a3-wifi.state] "
        "[--output /tmp/mhi2-wcp-iap2.cfg]\n",
        argv0);
}

int main(int argc, char **argv)
{
    const char *base = "/etc/mm/iap2.cfg";
    const char *state_path = "/tmp/mhi2-wcp-a3-wifi.state";
    const char *output = "/tmp/mhi2-wcp-iap2.cfg";
    struct wifi_state state;
    int i;

    memset(&state, 0, sizeof(state));

    for (i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--base") == 0 && i + 1 < argc) {
            base = argv[++i];
        } else if (strcmp(argv[i], "--state") == 0 && i + 1 < argc) {
            state_path = argv[++i];
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

    if (load_state(state_path, &state) != 0 || validate_state(&state) != 0)
        return 2;

    if (write_runtime_config(base, output, &state) != 0)
        return 3;

    printf("IAP2_RUNTIME_CONFIG_READY output=%s ssid_len=%u channel=%u security=%u\n",
        output, (unsigned)strlen(state.ssid), state.channel, state.security_type);
    return 0;
}
