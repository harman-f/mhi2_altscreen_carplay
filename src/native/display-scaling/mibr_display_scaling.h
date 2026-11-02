/* SPDX-License-Identifier: GPL-3.0-or-later
 * Finite per-display ZoomFactor and physical-size presets shared by MIBR and GEN2.
 */
#ifndef MIBR_DISPLAY_SCALING_H
#define MIBR_DISPLAY_SCALING_H
#include <stddef.h>
#include <stdint.h>

#define MIBR_DISPLAY_SCALING_VALUE_CAP 8u
struct mibr_display_scaling_state {
    uint64_t revision;
    char main[MIBR_DISPLAY_SCALING_VALUE_CAP];
    char cluster[MIBR_DISPLAY_SCALING_VALUE_CAP];
    char physical[MIBR_DISPLAY_SCALING_VALUE_CAP]; /* BASE / P20 / P30 / P50 */
    char main_physical[MIBR_DISPLAY_SCALING_VALUE_CAP]; /* Type110; BASE preserves OEM dimensions */
    int stored; /* 0 = compiled AUTO/AUTO defaults, 1 = exact persisted file */
};
struct mibr_display_scaling_guard {
    int (*enter_rw)(void *context);
    int (*restore_verified_ro)(void *context);
    void *context;
};

/* Strictly read legacy /1 and /2 or current /3. Legacy files default
 * main_physical=BASE; missing file is AUTO/AUTO/BASE/BASE, revision 0. */
int mibr_display_scaling_load(const char *path,
    struct mibr_display_scaling_state *out,char *error,size_t error_cap);

/* Optional GEN2 /info descriptor receipt. Returns 1 only for a strict
 * receipt matching desired revision and all scaling values, 0 if absent/stale/bad. */
int mibr_display_scaling_advertised_load(const char *path,
    const struct mibr_display_scaling_state *desired,
    struct mibr_display_scaling_state *advertised);

/* CAS update of one allowlisted display. 0 = verified durable update, 1 =
 * verified unchanged, -1 = proven no commit, -2 = uncertain commit/RO state.
 * Caller must reload after success. The guard is required for every write. */
int mibr_display_scaling_set(const char *path,
    const struct mibr_display_scaling_state *observed,const char *id,
    const char *value,uint64_t expected_revision,
    const struct mibr_display_scaling_guard *guard,
    char *error,size_t error_cap);

int mibr_display_scaling_id_valid(const char *id);
int mibr_display_scaling_value_valid(const char *value);
int mibr_display_physical_value_valid(const char *value);
int mibr_display_physical_dimensions(const char *value,int *width_mm,int *height_mm);
int mibr_display_main_physical_dimensions(const char *value,int original_width_mm,int original_height_mm,
    int *width_mm,int *height_mm);
#endif
