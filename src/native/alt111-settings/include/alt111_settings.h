#ifndef MIBR_ALT111_SETTINGS_H
#define MIBR_ALT111_SETTINGS_H
#include <stddef.h>
#include <stdint.h>
#include "alt111_policy.h"
#include "registry_generated.h"

#define ALT111_SETTING_VALUE_CAP 192u
#define ALT111_SETTING_GROUP_CAP 2048u
#define ALT111_SETTING_BATCH_CAP 8192u
void mibr_sha256_bytes(const void *data, size_t size, char hex[65]);
enum alt111_settings_layer { ALT111_PROFILE, ALT111_PERSISTENT, ALT111_TEMP };
struct alt111_setting_descriptor {
    const char *key, *basename, *field, *type, *allowed;
    const char *reference, *dual, *legacy, *apply, *hmi;
    unsigned minimum, maximum, group, read_only;
};
struct alt111_settings {
    char value[ALTSET_COUNT][ALT111_SETTING_VALUE_CAP];
    unsigned layer[ALTSET_COUNT];
    uint64_t revision;
    unsigned reference_match;
};
struct alt111_settings_paths {
    const char *temp, *persistent;
};
const struct alt111_setting_descriptor *alt111_setting(unsigned id);
int alt111_setting_find(const char *key);
int alt111_settings_defaults(struct alt111_settings *s, const char *preset);
int alt111_setting_validate(unsigned id, const char *value);
int alt111_settings_set(struct alt111_settings *s, unsigned id,
                        const char *value, unsigned layer);
int alt111_settings_validate(struct alt111_settings *s, char *error, size_t cap);
int alt111_settings_parse_group(struct alt111_settings *s, unsigned group,
                                const char *data, size_t size, unsigned layer,
                                unsigned allow_legacy, char *error, size_t cap);
int alt111_settings_render_group(const struct alt111_settings *s, unsigned group,
                                 char *out, size_t cap);
unsigned alt111_setting_integer(const struct alt111_settings *s, unsigned id);
void alt111_settings_policy(const struct alt111_settings *s,
                            struct alt111_policy_config *config);
/* Keep negotiated/session fields frozen. selected is committed only by a
 * successful generation-bound VIEW/SHOW acknowledgement, never by polling. */
enum alt111_runtime_overlay { ALT111_OVERLAY_LIVE=1u, ALT111_OVERLAY_PRESENTATION=2u };
void alt111_settings_runtime_overlay(struct alt111_settings *active,
                                    const struct alt111_settings *desired,
                                    unsigned classes);
/* POSIX implementation; these operations hold the same advisory lock.
 * A process must additionally serialize its threads around these calls. */
int alt111_settings_load(const struct alt111_settings_paths *paths,
                         struct alt111_settings *out, char *error, size_t cap);
int alt111_settings_mutate(const struct alt111_settings_paths *paths,
                           unsigned layer, const unsigned *ids,
                           const char *const *values, size_t count,
                           uint64_t expected_revision,
                           struct alt111_settings *out, char *error, size_t cap);
int alt111_settings_clear(const struct alt111_settings_paths *paths,
                          unsigned layer, unsigned id, uint64_t expected_revision,
                          struct alt111_settings *out, char *error, size_t cap);
int alt111_settings_reconcile(const struct alt111_settings_paths *paths,
                              char *error, size_t cap);
int alt111_settings_preset(const struct alt111_settings_paths *paths,
                           const char *preset, uint64_t expected_revision,
                           struct alt111_settings *out, char *error, size_t cap);
#endif
