/* SPDX-License-Identifier: GPL-3.0-or-later
 * CPVC profile transaction using the PINNED original settings validator.
 * Flash mount guard is mandatory; this library NEVER remounts by itself.
 */
#ifndef MIBR_V3_PROFILE_STORE_H
#define MIBR_V3_PROFILE_STORE_H
#include "alt111_settings.h"
#include <stdint.h>
struct mibr_v3_mount_guard {
    /* Must independently verify expected physical media and RW/RO state. */
    int (*enter_rw)(void *context);
    int (*restore_verified_ro)(void *context);
    void *context;
};
/* Meaning of result: -1 no verified commit, -2 commit may have happened;
 * 0 verified unchanged, 1 durable verified and TEMP materialized,
 * 2 durable verified but TEMP not yet materialized (pending boot replay).
 * No result proves effective AirPlay state. */
/* Read-only boot gate: all 45 durable values must equal the resolved core. */
int mibr_v3_profile_parity(const char *path,const struct alt111_settings *observed);
int mibr_v3_profile_set(const struct alt111_settings_paths *paths,
    const char *profile_path, const struct alt111_settings *observed,
    unsigned id,const char *value,uint64_t expected_revision,
    const struct mibr_v3_mount_guard *guard, char *error,size_t error_cap);
/* r13: volatile TEMP write before the slow flash transaction (0 = applied). */
int mibr_v3_live_apply(const struct alt111_settings_paths *paths,const struct alt111_settings *observed,
    unsigned id,const char *value,uint64_t *revision_out);
int mibr_v3_live_revert(const struct alt111_settings_paths *paths,unsigned id,const char *old_value,
    uint64_t revision);
#endif
