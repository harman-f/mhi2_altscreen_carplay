/* SPDX-License-Identifier: GPL-3.0-or-later
 * QNX6.5 target storage preflight/mount adapter. Actual vehicle qualification
 * (source, filesystem, fault/reboot/powerloss, legacy-writer migration) required.
 */
#ifndef MIBR_V3_QNX_MOUNT_H
#define MIBR_V3_QNX_MOUNT_H
#include "mibr_v3_profile_store.h"
#include <sys/types.h>
struct mibr_v3_qnx_store {
    const char *profile;
    dev_t mount_device;
    int degraded;
};
int mibr_v3_qnx_preflight(struct mibr_v3_qnx_store *state,const char *profile,const struct alt111_settings *observed);
int mibr_v3_qnx_set(void *context,const struct alt111_settings_paths *paths,
    const struct alt111_settings *observed,unsigned id,const char *value,
    uint64_t revision,char *error,size_t cap);
#endif
