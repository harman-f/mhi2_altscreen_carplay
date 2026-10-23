/* SPDX-License-Identifier: GPL-3.0-or-later
 * Passive GEN2 status observer. Never commands an owner and NEVER certifies
 * per-key ACTIVE from aggregate revisions.
 */
#ifndef MIBR_V3_RUNTIME_OBSERVER_H
#define MIBR_V3_RUNTIME_OBSERVER_H
#include <stdint.h>
struct mibr_v3_runtime_observation {
    int observed;
    uint64_t session,stream_gen,active_revision,desired_revision;
    int confirmed;
};
int mibr_v3_runtime_read(const char *path,struct mibr_v3_runtime_observation *out);
#endif
