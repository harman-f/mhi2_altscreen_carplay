/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_vstatus.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MODE_RECHECK_MS 3000ull
#define SOURCE_FRESH_MS 90000ull   /* the Java side rewrites the file at least every 30 s */
#define REFRESH_MS 10000ull        /* resend unchanged values this often (new phone sessions need a first value) */

static void copy_path(char *dst, const char *src) {
    size_t n = src ? strlen(src) : 0;
    if (n >= VSTATUS_PATH_CAP) n = VSTATUS_PATH_CAP - 1u;
    if (n) memcpy(dst, src, n);
    dst[n] = 0;
}

void vstatus_init(struct vstatus *s, const char *mode_file, const char *source_file) {
    if (!s) return;
    memset(s, 0, sizeof(*s));
    copy_path(s->mode_file, mode_file);
    copy_path(s->source_file, source_file);
    s->mode = VSTATUS_OFF;
    s->sent_range = s->sent_temp = s->sent_warn = VSTATUS_ABSENT;
}

static void refresh_mode(struct vstatus *s, uint64_t now) {
    FILE *f;
    char line[24] = {0};
    enum vstatus_mode m = VSTATUS_OFF;
    if (s->mode_checked_ms && now - s->mode_checked_ms < MODE_RECHECK_MS) return;
    s->mode_checked_ms = now ? now : 1u;
    f = fopen(s->mode_file, "r");
    if (f) {
        if (fgets(line, sizeof(line), f)) {
            if (!strncmp(line, "send", 4)) m = VSTATUS_SEND;
            else if (!strncmp(line, "shadow", 6)) m = VSTATUS_SHADOW;
        }
        (void)fclose(f);
    }
    if (m != s->mode) { s->mode = m; s->have_sent = 0; }
}

/* key=value lines; returns 0 and the fields (VSTATUS_ABSENT when missing), -1 on garbage */
static int parse_source(const char *text, int *range, int *temp, int *warn) {
    const char *p = text;
    *range = *temp = *warn = VSTATUS_ABSENT;
    while (*p) {
        const char *eol = strchr(p, '\n');
        size_t n = eol ? (size_t)(eol - p) : strlen(p);
        char line[48];
        char *eq, *end;
        long v;
        if (n >= sizeof(line)) return -1;
        memcpy(line, p, n); line[n] = 0;
        p += n + (eol ? 1u : 0u);
        if (!line[0]) continue;
        eq = strchr(line, '=');
        if (!eq || eq == line || !eq[1]) return -1;
        *eq = 0;
        v = strtol(eq + 1, &end, 10);
        if (*end) return -1;
        if (!strcmp(line, "range")) { if (v < 0 || v > 2000) return -1; *range = (int)v; }
        else if (!strcmp(line, "outsidetemp")) { if (v < -60 || v > 80) return -1; *temp = (int)v; }
        else if (!strcmp(line, "rangewarn")) { if (v != 0 && v != 1) return -1; *warn = (int)v; }
        else if (!strcmp(line, "seq")) { /* informational */ }
        else return -1;
    }
    return 0;
}

int vstatus_poll(struct vstatus *s, const struct vdata_clock *clk, void *handle, const struct vstatus_api *api) {
    char text[256];
    uint64_t now, age = 0;
    int range, temp, warn, changed, result;
    FILE *f;
    size_t n;
    void *dict;
    char v[16];
    if (!s || !clk || !api) return 0;
    now = clk->mono_ms();
    refresh_mode(s, now);
    if (s->mode == VSTATUS_OFF) return 0;
    s->polls++;
    if (clk->file_age_ms(s->source_file, &age) < 0) { s->src_missing++; return 0; }
    if (age > SOURCE_FRESH_MS) { s->src_stale++; return 0; }
    f = fopen(s->source_file, "rb");
    if (!f) { s->src_missing++; return 0; }
    n = fread(text, 1, sizeof(text) - 1u, f);
    (void)fclose(f);
    text[n] = 0;
    if (parse_source(text, &range, &temp, &warn)) { s->src_bad++; return 0; }
    if (range == VSTATUS_ABSENT && temp == VSTATUS_ABSENT && warn == VSTATUS_ABSENT) return 0;
    if (handle != s->last_handle) { if (s->last_handle) s->handle_changes++; s->last_handle = handle; s->have_sent = 0; }
    changed = !s->have_sent || range != s->sent_range || temp != s->sent_temp || warn != s->sent_warn;
    if (!changed && s->last_send_ms && now - s->last_send_ms < REFRESH_MS) return 0;
    if (changed || s->last_send_ms == 0) {
        snprintf(s->last_dict, sizeof(s->last_dict), "range=%d outsidetemp=%d rangewarn=%d",
                 range, temp, warn);
    }
    s->would_send++;
    if (s->mode == VSTATUS_SHADOW) {
        s->last_send_ms = now;
        s->have_sent = 1; s->sent_range = range; s->sent_temp = temp; s->sent_warn = warn;
        return 0;
    }
    if (!api->dict_new || !api->dict_set || !api->dict_destroy || !api->update || !handle) { s->errors++; return 0; }
    dict = api->dict_new();
    if (range != VSTATUS_ABSENT) { snprintf(v, sizeof(v), "%d", range); dict = api->dict_set(dict, "range", v); }
    if (dict && temp != VSTATUS_ABSENT) { snprintf(v, sizeof(v), "%d", temp); dict = api->dict_set(dict, "outsidetemp", v); }
    if (dict && warn != VSTATUS_ABSENT) { snprintf(v, sizeof(v), "%s", warn ? "true" : "false"); dict = api->dict_set(dict, "rangewarn", v); }
    if (!dict) { s->errors++; return 0; }
    result = api->update(handle, dict);
    api->dict_destroy(dict);
    s->last_send_ms = now;
    if (result == 0) {
        s->sent++;
        s->have_sent = 1; s->sent_range = range; s->sent_temp = temp; s->sent_warn = warn;
        return 1;
    }
    s->errors++;
    return 0;
}

int vstatus_format(const struct vstatus *s, char *out, size_t cap) {
    static const char *const names[] = {"off", "shadow", "send"};
    if (!s || !out || !cap) return 0;
    return snprintf(out, cap,
        "vstatus_mode=%s\nvstatus_polls=%lu\nvstatus_src_missing=%lu\nvstatus_src_stale=%lu\nvstatus_src_bad=%lu\n"
        "vstatus_would_send=%lu\nvstatus_sent=%lu\nvstatus_errors=%lu\nvstatus_handle_changes=%lu\nvstatus_last=%s\n",
        names[s->mode], s->polls, s->src_missing, s->src_stale, s->src_bad, s->would_send, s->sent, s->errors,
        s->handle_changes, s->last_dict);
}
