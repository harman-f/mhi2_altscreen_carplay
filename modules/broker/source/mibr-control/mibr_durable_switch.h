/* MIBR-owned durable choices (on/off or a short value list): one table row per switch, all served by the same store and
 * the same broker verbs. The file format is "<magic>\nrevision=N\nvalue=<value>\n". */
#ifndef MIBR_DURABLE_SWITCH_H
#define MIBR_DURABLE_SWITCH_H
#include <stdint.h>
#include <stddef.h>
#define MIBR_SWITCH_COUNT 13u
struct mibr_switch {char value[20];uint64_t revision;int stored;};
struct mibr_switch_guard {
    int (*enter_rw)(void *);
    int (*restore_ro)(void *);
    void *context;
};
struct mibr_switch_def {
    const char *magic;
    const char *values;         /* '|' separated, each shorter than mibr_switch.value; NULL = a rectangle "x,y,w,h" */
    const char *default_value;  /* a missing file means this */
    const char *path;
    const char *get_op;
    const char *set_op;
    const char *capability;
    const char *host_env;       /* host builds only: path override that also grants the writer */
    const char *host_readonly;  /* host builds only: path without the override */
};
extern const struct mibr_switch_def mibr_switch_defs[MIBR_SWITCH_COUNT];
/* Per-platform defaults, one "<capability>=<value>" per line. A missing file or an invalid value means the
 * compiled default, so a port to another car changes this file instead of the code. */
extern const char *mibr_switch_platform_path;
const struct mibr_switch_def *mibr_switch_for_op(const char *op,int *set);
int mibr_switch_valid(const struct mibr_switch_def *,const char *);
/* Writes the platform default, or else the compiled one. */
void mibr_switch_default(const struct mibr_switch_def *,char *,size_t);
int mibr_switch_load(const struct mibr_switch_def *,const char *,struct mibr_switch *,char *,size_t);
int mibr_switch_set(const struct mibr_switch_def *,const char *,const struct mibr_switch *,
 const char *,uint64_t,const struct mibr_switch_guard *,char *,size_t);
/* navigation and safe-area switches are stored in the shared view profile
 * (MIBR_NAV_VIEW_PROFILES/3, also written by the HTML configurator). Same verbs/values as before. */
extern const char *mibr_view_profile_path;
int mibr_switch_profile_backed(const struct mibr_switch_def *);
uint32_t mibr_view_profile_crc32(const char *,size_t);
/* Profile-only keys (no legacy file): view.<wide|full|center>.geometry.zoom, global.transition.*.
 * values "#min..max" = canonical decimal range. Served by VIEW_PROFILE_GET/SET key=<profile key>. */
#define MIBR_VIEW_KEY_COUNT 7u
extern const struct mibr_switch_def mibr_view_key_defs[MIBR_VIEW_KEY_COUNT];
const struct mibr_switch_def *mibr_view_key_for(const char *profile_key);
const char *mibr_view_key_name(const struct mibr_switch_def *);
#endif
