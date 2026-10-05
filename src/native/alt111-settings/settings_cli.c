/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "alt111_settings.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char *layer_name(unsigned layer)
{
    return layer == ALT111_TEMP ? "temp" : layer == ALT111_PERSISTENT ? "persistent" : "profile";
}

static void print_entry(const struct alt111_settings *s, unsigned id)
{
    const struct alt111_setting_descriptor *d = alt111_setting(id);
    printf("%s.value=%s\n%s.source=%s\n%s.apply=%s\n", d->key, s->value[id],
           d->key, layer_name(s->layer[id]), d->key, d->apply);
}

static int error_result(const char *error)
{
    printf("result=%s\n", error && *error ? error : "APPLY_FAILED unspecified");
    return 1;
}

static void stored_result(const struct alt111_settings *s, const unsigned *ids, size_t count)
{
    size_t i;
    int reconnect = 0, session = 0, presentation = 0;
    for (i = 0; i < count; ++i) {
        const char *a = alt111_setting(ids[i])->apply;
        reconnect |= !strcmp(a, "reconnect");
        session |= !strcmp(a, "session");
        presentation |= !strcmp(a, "presentation");
    }
    /* Persistence/storage never impersonates a runtime completion ack. */
    printf("result=%s\nrevision=%" PRIu64 "\n",
           reconnect ? "RECONNECT_REQUIRED" : session ? "SESSION_TRANSITION_REQUIRED" :
           presentation ? "PRESENTATION_REFRESH_REQUIRED" : "QUEUED", s->revision);
    for (i = 0; i < count; ++i) print_entry(s, ids[i]);
}

int main(int argc, char **argv)
{
    struct alt111_settings_paths paths = {"/tmp", "/mnt/app/root"};
    struct alt111_settings *s;
    char error[256] = {0}, *batch = NULL;
    const char *key = NULL, *value = NULL, *input = NULL, *preset = NULL;
    unsigned layer = ALT111_TEMP, ids[ALTSET_COUNT];
    const char *values[ALTSET_COUNT];
    uint64_t expected = 0;
    size_t count = 0;
    int i, id, rc = 0, seen_layer = 0, seen_revision = 0;
#ifdef ALT111_SETTINGS_TEST
    /* Compiled out of the target helper. Host tests do not touch real /tmp
     * or /mnt/app settings and need no production environment overrides. */
    paths.temp = getenv("ALT111_SETTINGS_TEMP_ROOT");
    paths.persistent = getenv("ALT111_SETTINGS_PERSISTENT_ROOT");
    if (!paths.temp || !paths.persistent) return error_result("INVALID_VALUE test_roots");
#endif
    if (argc < 2) return error_result("INVALID_VALUE command_required");
    for (i = 2; i < argc; i += 2) {
        if (i + 1 >= argc) return error_result("INVALID_VALUE argument_pair");
        if (!strcmp(argv[i], "--key") && !key) key = argv[i + 1];
        else if (!strcmp(argv[i], "--value") && !value) value = argv[i + 1];
        else if (!strcmp(argv[i], "--input") && !input) input = argv[i + 1];
        else if (!strcmp(argv[i], "--preset") && !preset) preset = argv[i + 1];
        else if (!strcmp(argv[i], "--layer") && !seen_layer++) {
            if (!strcmp(argv[i + 1], "temp")) layer = ALT111_TEMP;
            else if (!strcmp(argv[i + 1], "persistent")) layer = ALT111_PERSISTENT;
            else return error_result("INVALID_VALUE layer");
        } else if (!strcmp(argv[i], "--expected-revision") && !seen_revision++) {
            char *end;
            errno = 0; expected = strtoull(argv[i + 1], &end, 10);
            if (errno || !argv[i + 1][0] || argv[i + 1][0] == '-' || *end || !expected)
                return error_result("INVALID_VALUE revision");
        } else return error_result("INVALID_VALUE unknown_or_duplicate_argument");
    }
    s = malloc(sizeof(*s));
    if (!s) return error_result("APPLY_FAILED allocation");
    if (!strcmp(argv[1], "list")) {
        for (i = 0; i < ALTSET_COUNT; ++i) {
            const struct alt111_setting_descriptor *d = alt111_setting((unsigned)i);
            printf("key=%s basename=%s field=%s type=%s allowed=%s min=%u max=%u apply=%s hmi=%s read_only=%u\n",
                   d->key, d->basename, d->field, d->type, d->allowed,
                   d->minimum, d->maximum, d->apply, d->hmi, d->read_only);
        }
    } else if (!strcmp(argv[1], "status") || !strcmp(argv[1], "get")) {
        if (alt111_settings_load(&paths, s, error, sizeof(error))) { rc = error_result(error); goto done; }
        printf("result=VALID\nrevision=%" PRIu64 "\nreference_match=%u\n", s->revision, s->reference_match);
        if (!strcmp(argv[1], "get")) {
            id = alt111_setting_find(key);
            if (id < 0) { rc = error_result("INVALID_VALUE key"); goto done; }
            print_entry(s, (unsigned)id);
        } else for (i = 0; i < ALTSET_COUNT; ++i) print_entry(s, (unsigned)i);
    } else if (!strcmp(argv[1], "reconcile")) {
        if (alt111_settings_reconcile(&paths, error, sizeof(error))) rc = error_result(error);
        else puts("result=RECONCILED\nactive_apply=not_claimed");
    } else if (!strcmp(argv[1], "preset")) {
        if (layer != ALT111_TEMP) { rc = error_result("POLICY_BLOCKED persistent_backup_powerloss_gate"); goto done; }
        if (!preset || alt111_settings_preset(&paths, preset, expected, s, error, sizeof(error)))
            rc = error_result(error[0] ? error : "INVALID_VALUE preset");
        else printf("result=RECONNECT_REQUIRED\nrevision=%" PRIu64 "\npreset=%s\n", s->revision, preset);
    } else if (!strcmp(argv[1], "clear-temp")) {
        if(layer!=ALT111_TEMP)rc=error_result("POLICY_BLOCKED persistent_backup_powerloss_gate");
        else if(alt111_settings_clear_temp(&paths,expected,s,error,sizeof(error)))rc=error_result(error);
        else printf("result=RECONNECT_REQUIRED\nrevision=%" PRIu64 "\nclear_scope=complete_temp_layer\n",s->revision);
    } else if (!strcmp(argv[1], "clear")) {
        id = alt111_setting_find(key);
        if (id < 0) { rc = error_result("INVALID_VALUE key"); goto done; }
        if (alt111_settings_clear(&paths, layer, (unsigned)id, expected, s, error, sizeof(error))) rc = error_result(error);
        else {
            ids[0] = (unsigned)id;
            puts("clear_scope=whole_file"); stored_result(s, ids, 1);
        }
    } else if (!strcmp(argv[1], "set") || !strcmp(argv[1], "batch")) {
        if (!strcmp(argv[1], "set")) {
            id = alt111_setting_find(key);
            if (id < 0 || !value) { rc = error_result("INVALID_VALUE key_or_value"); goto done; }
            ids[0] = (unsigned)id; values[0] = value; count = 1;
        } else {
            FILE *file;
            size_t size;
            char *p;
            if (!input || !(file = !strcmp(input, "-") ? stdin : fopen(input, "rb"))) {
                rc = error_result("INVALID_VALUE input"); goto done;
            }
            batch = malloc(ALT111_SETTING_BATCH_CAP + 2u);
            if (!batch) { fclose(file); rc = error_result("APPLY_FAILED allocation"); goto done; }
            size = fread(batch, 1, ALT111_SETTING_BATCH_CAP + 1u, file);
            if (ferror(file) || size > ALT111_SETTING_BATCH_CAP || !size || memchr(batch, 0, size) || batch[size - 1] != '\n') {
                fclose(file); rc = error_result("INVALID_VALUE batch_size_or_format"); goto done;
            }
            fclose(file); batch[size] = 0; p = batch;
            while (*p) {
                char *end = strchr(p, '\n'), *equals;
                if (!end || end == p || count == ALTSET_COUNT) { rc = error_result("INVALID_VALUE batch_line"); goto done; }
                *end = 0; if (end > p && end[-1] == '\r') end[-1] = 0;
                equals = strchr(p, '='); if (!equals) { rc = error_result("INVALID_VALUE batch_key"); goto done; }
                *equals++ = 0; id = alt111_setting_find(p);
                if (id < 0) { rc = error_result("INVALID_VALUE batch_key"); goto done; }
                ids[count] = (unsigned)id; values[count++] = equals; p = end + 1;
            }
        }
        for (i = 0; i < (int)count; ++i) if (alt111_setting(ids[i])->read_only) {
            rc = error_result("POLICY_BLOCKED read_only_setting"); goto done;
        }
        if (alt111_settings_mutate(&paths, layer, ids, values, count, expected, s, error, sizeof(error)))
            rc = error_result(error);
        else stored_result(s, ids, count);
    } else rc = error_result("INVALID_VALUE command");
done:
    free(batch); free(s); return rc;
}
