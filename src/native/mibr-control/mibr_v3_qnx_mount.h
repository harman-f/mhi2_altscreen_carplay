/* SPDX-License-Identifier: GPL-3.0-or-later
 * QNX6.5 target storage preflight/mount adapter. Actual vehicle qualification
 * (source, filesystem, fault/reboot/powerloss, legacy-writer migration) required.
 */
#ifndef MIBR_V3_QNX_MOUNT_H
#define MIBR_V3_QNX_MOUNT_H
#include "mibr_v3_profile_store.h"
#include "mibr_display_scaling.h"
#include "mibr_menu_language.h"
#include "mibr_durable_switch.h"
#include <sys/types.h>
struct mibr_v3_qnx_store {
    const char *profile;
    const char *scaling_path;
    const char *menu_language_path;
    int switch_ready[MIBR_SWITCH_COUNT];
    dev_t mount_device;
    int degraded;
};
/* Retries the read-only remount after a failed restore; writes stay disabled. */
int mibr_v3_qnx_heal(struct mibr_v3_qnx_store *state);
int mibr_v3_qnx_preflight(struct mibr_v3_qnx_store *state,const char *profile,const struct alt111_settings *observed);
int mibr_v3_qnx_set(void *context,const struct alt111_settings_paths *paths,
    const struct alt111_settings *observed,unsigned id,const char *value,
    uint64_t revision,char *error,size_t cap);
int mibr_v3_qnx_scaling_preflight(struct mibr_v3_qnx_store *state,const char *path);
int mibr_v3_qnx_scaling_set(void *context,const char *path,
    const struct mibr_display_scaling_state *observed,const char *id,const char *value,
    uint64_t revision,char *error,size_t cap);
int mibr_v3_qnx_menu_language_preflight(struct mibr_v3_qnx_store *state,const char *path);
int mibr_v3_qnx_menu_language_set(void *context,const char *path,
    const struct mibr_menu_language *observed,const char *value,
    uint64_t revision,char *error,size_t cap);
int mibr_v3_qnx_switch_preflight(struct mibr_v3_qnx_store *state,const struct mibr_switch_def *def,const char *path);
int mibr_v3_qnx_switch_set(void *context,const struct mibr_switch_def *def,const char *path,
    const struct mibr_switch *observed,const char *value,
    uint64_t revision,char *error,size_t cap);
#endif
