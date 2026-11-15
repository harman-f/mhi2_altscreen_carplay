/* SPDX-License-Identifier: GPL-3.0-or-later
 * Steering-wheel key map: logical function -> keyboard/key code, read from the per-profile platform
 * defaults MIBR_KEYMAP_PATH ("<config>/platform/defaults.conf"), the one configurable mapping file
 * (key.menu and zoom.* live there too and are read by their own consumers). Header-only, C99, QNX 6.5 safe.
 *
 * Lines "key.<name>=keyboard/key" (decimal 0..65535), '#' starts a comment, blank lines ok.
 *   key.view_step=4/40            cockpit view step (press start)
 *   key.view_resync_long=4/40     long press: resync the view counter
 *   key.carplay_switch_long=4/44  long press: CarPlay <-> native
 * Every other line (safe_*, zoom.*, key.menu, unknown key.* names) is ignored without a log line;
 * malformed key.<name> values are ignored (reported through log). Missing entries and a missing or
 * oversized file keep the compiled defaults, which are the Skoda MU1440 values measured on the car.
 */
#ifndef MIBR_KEYMAP_H
#define MIBR_KEYMAP_H
#include "mibr_paths.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MIBR_KEYMAP_PATH MIBR_CONFIG_DIR "/platform/defaults.conf"
#define MIBR_KEYMAP_PREFIX "key."
#define MIBR_KEYMAP_MAX_BYTES 4096u
#if defined(__GNUC__)
#define MIBR_KM_FN static __attribute__((unused))
#else
#define MIBR_KM_FN static
#endif

enum { MIBR_KM_VIEW_STEP, MIBR_KM_VIEW_RESYNC_LONG, MIBR_KM_CARPLAY_SWITCH_LONG, MIBR_KM_COUNT };
struct mibr_keymap { int kbd[MIBR_KM_COUNT]; int key[MIBR_KM_COUNT]; };
typedef void (*mibr_keymap_log_fn)(const char *msg);

static const char *const mibr_keymap_names[MIBR_KM_COUNT] = {
    "view_step", "view_resync_long", "carplay_switch_long" };

MIBR_KM_FN void mibr_keymap_defaults(struct mibr_keymap *m){
    static const int k[MIBR_KM_COUNT] = { 40, 40, 44 };
    int i;
    for (i = 0; i < MIBR_KM_COUNT; i++) { m->kbd[i] = 4; m->key[i] = k[i]; }
}

/* Parses NUL-terminated text over *m (call mibr_keymap_defaults first).
 * Returns the number of entries applied. */
MIBR_KM_FN int mibr_keymap_parse(struct mibr_keymap *m, const char *text, mibr_keymap_log_fn log){
    int applied = 0;
    while (*text) {
        char line[96], *eq, *sl, *e1, *e2;
        size_t n = 0;
        long a, b;
        int i, bad = 0;
        while (*text && *text != '\n') { if (n < sizeof(line) - 1) line[n++] = *text; else bad = 1; text++; }
        if (*text == '\n') text++;
        line[n] = 0;
        { char *h = strchr(line, '#'); if (h) { *h = 0; bad = 0; } } /* long comments are fine */
        for (eq = line; *eq == ' ' || *eq == '\t' || *eq == '\r'; eq++) {}
        if (!*eq && !bad) continue;
        n = strlen(eq);
        while (n && (eq[n - 1] == ' ' || eq[n - 1] == '\t' || eq[n - 1] == '\r')) eq[--n] = 0;
        if (!n && !bad) continue;
        sl = strchr(eq, '=');
        if (bad || !sl) { if (log && !strncmp(eq, MIBR_KEYMAP_PREFIX, sizeof(MIBR_KEYMAP_PREFIX) - 1)) log("keymap: malformed line ignored"); continue; }
        *sl++ = 0;
        { size_t q = strlen(eq); while (q && (eq[q - 1] == ' ' || eq[q - 1] == '\t')) eq[--q] = 0; }
        while (*sl == ' ' || *sl == '\t') sl++;
        if (strncmp(eq, MIBR_KEYMAP_PREFIX, sizeof(MIBR_KEYMAP_PREFIX) - 1)) continue; /* not ours */
        eq += sizeof(MIBR_KEYMAP_PREFIX) - 1;
        for (i = 0; i < MIBR_KM_COUNT; i++) if (!strcmp(eq, mibr_keymap_names[i])) break;
        if (i == MIBR_KM_COUNT) continue; /* key.menu and other names: not a keyboard/key pair */
        a = strtol(sl, &e1, 10);
        if (e1 == sl || *e1 != '/') { if (log) log("keymap: malformed value ignored"); continue; }
        b = strtol(e1 + 1, &e2, 10);
        if (e2 == e1 + 1 || *e2 || a < 0 || a > 65535 || b < 0 || b > 65535) {
            if (log) log("keymap: malformed value ignored");
            continue;
        }
        m->kbd[i] = (int)a; m->key[i] = (int)b; applied++;
    }
    return applied;
}

/* Defaults, then the file if present and <= MIBR_KEYMAP_MAX_BYTES. Returns entries applied (-1: no file). */
MIBR_KM_FN int mibr_keymap_load(struct mibr_keymap *m, const char *path, mibr_keymap_log_fn log){
    char buf[MIBR_KEYMAP_MAX_BYTES + 1u];
    size_t n;
    FILE *f;
    mibr_keymap_defaults(m);
    f = fopen(path, "r");
    if (!f) return -1;
    n = fread(buf, 1, sizeof(buf), f);
    fclose(f);
    if (n > MIBR_KEYMAP_MAX_BYTES) { if (log) log("keymap: file too large, defaults used"); return 0; }
    buf[n] = 0;
    if (memchr(buf, 0, n)) { if (log) log("keymap: binary file, defaults used"); return 0; }
    return mibr_keymap_parse(m, buf, log);
}

/* One-line effective mapping for the log. */
MIBR_KM_FN void mibr_keymap_describe(const struct mibr_keymap *m, char *out, size_t cap){
    int i; size_t used = 0;
    out[0] = 0;
    for (i = 0; i < MIBR_KM_COUNT; i++) {
        int w = snprintf(out + used, cap - used, "%s" MIBR_KEYMAP_PREFIX "%s=%d/%d", i ? " " : "",
                         mibr_keymap_names[i], m->kbd[i], m->key[i]);
        if (w < 0 || (size_t)w >= cap - used) return;
        used += (size_t)w;
    }
}
#endif
