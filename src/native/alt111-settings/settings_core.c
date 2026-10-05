/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "alt111_settings.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include "registry_table_generated.h"

static int failure(char *out, size_t cap, const char *format, ...)
{
    va_list ap;
    if (out && cap) {
        va_start(ap, format); vsnprintf(out, cap, format, ap); va_end(ap);
    }
    return -1;
}

const struct alt111_setting_descriptor *alt111_setting(unsigned id)
{
    return id < ALTSET_COUNT ? &registry[id] : NULL;
}

int alt111_setting_find(const char *key)
{
    unsigned i;
    for (i = 0; key && i < ALTSET_COUNT; ++i)
        if (!strcmp(registry[i].key, key)) return (int)i;
    return -1;
}

static int token_in(const char *list, const char *value)
{
    size_t n = strlen(value);
    const char *p = list;
    while (*p) {
        const char *end = strchr(p, '|');
        size_t length = end ? (size_t)(end - p) : strlen(p);
        if (length == n && !memcmp(p, value, n)) return 1;
        if (!end) break;
        p = end + 1;
    }
    return 0;
}

static int decimal(const char *v, unsigned max, unsigned *out)
{
    unsigned value = 0;
    const unsigned char *p = (const unsigned char *)v;
    if (!*p || (*p == '0' && p[1])) return 0;
    while (*p) {
        unsigned digit;
        if (*p < '0' || *p > '9') return 0;
        digit = (unsigned)(*p++ - '0');
        if (digit > max || value > (max - digit) / 10u) return 0;
        value = value * 10u + digit;
    }
    *out = value; return 1;
}

static int version_valid(const char *v)
{
    char part[6];
    unsigned components = 0, value;
    const char *p = v;
    if (!strcmp(v, "stock")) return 1;
    if (strlen(v) > 23) return 0;
    while (*p) {
        const char *end = strchr(p, '.');
        size_t n = end ? (size_t)(end - p) : strlen(p);
        if (!n || n >= sizeof(part)) return 0;
        memcpy(part, p, n); part[n] = 0;
        if (!decimal(part, 65535, &value) || ++components > 4) return 0;
        if (!end) break;
        p = end + 1; if (!*p) return 0;
    }
    return components >= 2;
}

static int url_valid(const char *v, int allow_auto)
{
    const char *query;
    char base[64], copy[192];
    size_t n;
    uint32_t seen = 0;
    if (allow_auto && !strcmp(v, "auto")) return 1;
    query = strchr(v, '?'); n = query ? (size_t)(query - v) : strlen(v);
    if (n >= sizeof(base)) return 0;
    memcpy(base, v, n); base[n] = 0;
    if (!token_in("maps:/car/instrumentcluster|maps:/car/instrumentcluster/map|maps:/car/instrumentcluster/instructioncard", base)) return 0;
    if (query) {
        char *p;
        if (!query[1]) return 0;
        strcpy(copy, query + 1); p = copy;
        while (*p) {
            char *next = strchr(p, '&'), *equals;
            unsigned bit = 0;
            if (next) *next = 0;
            equals = strchr(p, '='); if (!equals || strchr(equals + 1, '=')) return 0;
            *equals++ = 0;
            if (!strcmp(p, "showETA")) bit = 1;
            else if (!strcmp(p, "showSpeedLimit")) bit = 2;
            else if (!strcmp(p, "showCompass")) bit = 4;
            else if (!strcmp(p, "maneuverLayout")) bit = 8;
            if (!bit || (seen & bit)) return 0;
            if (bit == 8 ? !token_in("none|leftAligned|rightAligned|topAligned", equals)
                         : !token_in("yes|no|user", equals)) return 0;
            seen |= bit;
            if (!next) break;
            p = next + 1; if (!*p) return 0;
        }
    }
    return 1;
}

int alt111_setting_validate(unsigned id, const char *v)
{
    const struct alt111_setting_descriptor *d = alt111_setting(id);
    unsigned value, i;
    size_t n;
    if (!d || !v || !(n = strlen(v)) || n >= ALT111_SETTING_VALUE_CAP) return -1;
    for (i = 0; i < n; ++i)
        if ((unsigned char)v[i] < 32 || (unsigned char)v[i] > 126) return -1;
    if (!strcmp(d->type, "integer"))
        return decimal(v, d->maximum, &value) && value >= d->minimum ? 0 : -1;
    if (!strcmp(d->type, "enum")) return token_in(d->allowed, v) ? 0 : -1;
    if (!strcmp(d->type, "version")) return version_valid(v) ? 0 : -1;
    if (!strcmp(d->type, "uuid")) {
        if (n != 36) return -1;
        for (i = 0; i < n; ++i) {
            if (i == 8 || i == 13 || i == 18 || i == 23) { if (v[i] != '-') return -1; }
            else if (!((v[i] >= '0' && v[i] <= '9') ||
                       (v[i] >= 'a' && v[i] <= 'f') || (v[i] >= 'A' && v[i] <= 'F'))) return -1;
        }
        return 0;
    }
    if (!strcmp(d->type, "url")) return url_valid(v, 1) ? 0 : -1;
    if (!strcmp(d->type, "urls")) {
        char copy[192], *p; unsigned count = 0;
        strcpy(copy, v); p = copy;
        while (*p) {
            char *end = strchr(p, '|'); if (end) *end = 0;
            if (!url_valid(p, 0) || ++count > 8) return -1;
            if (!end) return 0;
            p = end + 1;
        }
    }
    return -1;
}

int alt111_settings_defaults(struct alt111_settings *s, const char *preset)
{
    unsigned i;
    int mode;
    if (!s || !preset) return -1;
    mode = !strcmp(preset, "omonob790") ? 0 : !strcmp(preset, "mibr_dual_view") ? 1 :
           (!strcmp(preset, "mibr_legacy") || !strcmp(preset, "mibr")) ? 2 : -1;
    if (mode < 0) return -1;
    memset(s, 0, sizeof(*s));
    for (i = 0; i < ALTSET_COUNT; ++i) {
        const char *v = mode == 0 ? registry[i].reference : mode == 1 ? registry[i].dual : registry[i].legacy;
        if (alt111_setting_validate(i, v)) return -1;
        strcpy(s->value[i], v);
    }
    s->reference_match = mode == 0;
    return 0;
}

int alt111_settings_set(struct alt111_settings *s, unsigned id,
                        const char *value, unsigned layer)
{
    if (!s || layer > ALT111_TEMP || alt111_setting_validate(id, value)) return -1;
    strcpy(s->value[id], value); s->layer[id] = layer;
    return 0;
}

unsigned alt111_setting_integer(const struct alt111_settings *s, unsigned id)
{
    unsigned value = 0;
    if (s && id < ALTSET_COUNT) (void)decimal(s->value[id], UINT32_MAX, &value);
    return value;
}

int alt111_settings_validate(struct alt111_settings *s, char *error, size_t cap)
{
    unsigned i, count, initial, selected, canvas_w, canvas_h;
    if (!s) return failure(error, cap, "INVALID_VALUE null_snapshot");
    s->reference_match = 1;
    for (i = 0; i < ALTSET_COUNT; ++i) {
        if (alt111_setting_validate(i, s->value[i]))
            return failure(error, cap, "INVALID_VALUE key=%s", registry[i].key);
        if (strcmp(s->value[i], registry[i].reference)) s->reference_match = 0;
    }
    count = alt111_setting_integer(s, ALTSET_VIEWAREAS_COUNT);
    initial = alt111_setting_integer(s, ALTSET_VIEWAREAS_INITIAL);
    selected = alt111_setting_integer(s, ALTSET_VIEWAREA_SELECTED);
    if (initial >= count || selected >= count)
        return failure(error, cap, "INVALID_VALUE view_index_outside_count");
    if (!strcmp(s->value[ALTSET_PRESET_ID], "mibr_dual_view") && count != 2)
        return failure(error, cap, "INVALID_VALUE dual_profile_requires_two_areas");
    canvas_w = alt111_setting_integer(s, ALTSET_DISPLAY_WIDTHPIXELS);
    canvas_h = alt111_setting_integer(s, ALTSET_DISPLAY_HEIGHTPIXELS);
    for (i = 0; i < count; ++i) {
        unsigned base = i ? ALTSET_VIEWAREA_1_X : ALTSET_VIEWAREA_0_X;
        unsigned x = alt111_setting_integer(s, base), y = alt111_setting_integer(s, base + 1);
        unsigned w = alt111_setting_integer(s, base + 2), h = alt111_setting_integer(s, base + 3);
        unsigned sx = alt111_setting_integer(s, base + 4), sy = alt111_setting_integer(s, base + 5);
        unsigned sw = alt111_setting_integer(s, base + 6), sh = alt111_setting_integer(s, base + 7);
        unsigned adjacent = alt111_setting_integer(s, base + 8);
        if (x > canvas_w || y > canvas_h || w > canvas_w - x || h > canvas_h - y ||
            sx > w || sy > h || sw > w - sx || sh > h - sy ||
            adjacent != (count == 1 ? i : 1u - i))
            return failure(error, cap, "INVALID_VALUE area=%u geometry_or_adjacency", i);
    }
    if (error && cap) error[0] = 0;
    return 0;
}

int alt111_settings_parse_group(struct alt111_settings *s, unsigned group,
                                const char *data, size_t size, unsigned layer,
                                unsigned legacy, char *error, size_t cap)
{
    struct alt111_settings *candidate;
    char blob[ALT111_SETTING_GROUP_CAP + 1];
    unsigned i, first = ALTSET_COUNT, schema = 0, seen[ALTSET_COUNT];
    char *p;
    int result = -1;
    if (!s || !data || !size || size > ALT111_SETTING_GROUP_CAP || group >= ALTSET_GROUP_COUNT ||
        memchr(data, 0, size) || data[size - 1] != '\n')
        return failure(error, cap, "INVALID_VALUE group=%u truncated_or_malformed", group);
    for (i = 0; i < ALTSET_COUNT; ++i) if (registry[i].group == group) { first = i; break; }
    if (first == ALTSET_COUNT) return -1;
    memcpy(blob, data, size); blob[size] = 0;
    if (!registry[first].field[0]) {
        size_t n = size - 1;
        if (n && blob[n - 1] == '\r') --n;
        blob[n] = 0;
        if (alt111_settings_set(s, first, blob, layer))
            return failure(error, cap, "INVALID_VALUE key=%s", registry[first].key);
        return 0;
    }
    candidate = malloc(sizeof(*candidate));
    if (!candidate) return failure(error, cap, "APPLY_FAILED allocation");
    *candidate = *s; memset(seen, 0, sizeof(seen)); p = blob;
    while (*p) {
        char *end = strchr(p, '\n'), *equals;
        if (!end || end == p) goto malformed;
        *end = 0; if (end > p && end[-1] == '\r') end[-1] = 0;
        equals = strchr(p, '='); if (!equals) goto malformed;
        *equals++ = 0;
        if (!strcmp(p, "schema")) {
            if (schema || strcmp(equals, "2")) goto malformed;
            schema = 2;
        } else {
            for (i = 0; i < ALTSET_COUNT; ++i)
                if (registry[i].group == group && !strcmp(registry[i].field, p)) break;
            if (i == ALTSET_COUNT || seen[i] || alt111_settings_set(candidate, i, equals, layer)) goto malformed;
            seen[i] = 1;
        }
        p = end + 1;
    }
    if (!schema && !legacy) goto malformed;
    for (i = 0; i < ALTSET_COUNT; ++i) {
        if (registry[i].group != group) continue;
        /* Legacy single-area dictionaries legitimately omit unused view1. */
        if (!seen[i] && !(legacy && !schema &&
            alt111_setting_integer(candidate, ALTSET_VIEWAREAS_COUNT) == 1 &&
            !strncmp(registry[i].field, "view1.", 6))) goto malformed;
        candidate->layer[i] = layer;
    }
    *s = *candidate; result = 0;
    goto done;
malformed:
    result = failure(error, cap, "INVALID_VALUE basename=%s duplicate_unknown_missing_or_bad_field", registry[first].basename);
done:
    free(candidate); return result;
}

int alt111_settings_render_group(const struct alt111_settings *s, unsigned group,
                                 char *out, size_t cap)
{
    unsigned i; size_t used = 0;
    if (!s || !out || !cap || group >= ALTSET_GROUP_COUNT) return -1;
    out[0] = 0;
    for (i = 0; i < ALTSET_COUNT; ++i) {
        int n;
        if (registry[i].group != group) continue;
        if (!used && registry[i].field[0]) {
            n = snprintf(out, cap, "schema=2\n");
            if (n < 0 || (size_t)n >= cap) return -1;
            used = (size_t)n;
        }
        n = registry[i].field[0] ? snprintf(out + used, cap - used, "%s=%s\n", registry[i].field, s->value[i]) :
                                 snprintf(out + used, cap - used, "%s\n", s->value[i]);
        if (n < 0 || (size_t)n >= cap - used) return -1;
        used += (size_t)n;
    }
    return (int)used;
}

void alt111_settings_policy(const struct alt111_settings *s, struct alt111_policy_config *c)
{
    const char *mode = s->value[ALTSET_KEYFRAME_MODE];
    alt111_policy_defaults(c);
    c->mode = !strcmp(mode, "source_frames") ? ALT111_SOURCE_FRAMES :
              !strcmp(mode, "source_time") ? ALT111_SOURCE_TIME :
              !strcmp(mode, "event_only") ? ALT111_EVENT_ONLY : ALT111_PERIODIC_OFF;
    c->interval_frames = alt111_setting_integer(s, ALTSET_KEYFRAME_INTERVAL_FRAMES);
    c->interval_ms = alt111_setting_integer(s, ALTSET_KEYFRAME_INTERVAL_MS);
    c->showui = alt111_setting_integer(s, ALTSET_KEYFRAME_SHOWUI);
    c->gap_recovery = alt111_setting_integer(s, ALTSET_KEYFRAME_GAP_RECOVERY);
    c->latency_recovery = alt111_setting_integer(s, ALTSET_KEYFRAME_LATENCY_RECOVERY);
}
