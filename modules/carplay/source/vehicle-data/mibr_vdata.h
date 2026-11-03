/* SPDX-License-Identifier: GPL-3.0-or-later
 * MIBR vehicle data towards CarPlay: host-testable core (no OS hooks here).
 *
 * The hook (mibr_vdata_hook.c) interposes iap2_gps_data_send inside dio_manager. This core only
 *   - classifies every stock NMEA sentence the original worker sends (counters, no coordinates kept),
 *   - latches a stock $PASCD (then the extension stays silent),
 *   - reads the speed ring file written by the HMI-side DSI source,
 *   - turns fresh genuine samples into at most one $PASCD sentence per call group (mvs_core, R0).
 * Modes (config file, re-read every few seconds): off (default) | shadow (compute, never send) | send.
 */
#ifndef MIBR_VDATA_H
#define MIBR_VDATA_H
#include <stddef.h>
#include <stdint.h>
#include "mvs_core.h"

enum vdata_mode { VDATA_OFF = 0, VDATA_SHADOW = 1, VDATA_SEND = 2 };

#define VDATA_RING_MAX 8u                 /* records in the source ring file (8 x 24 bytes) */
#define VDATA_PATH_CAP 160u

struct vdata_paths {
    char mode_file[VDATA_PATH_CAP];       /* first line: off | shadow | send */
    char source_file[VDATA_PATH_CAP];     /* 0..8 MVS1 records, oldest first, replaced atomically */
    char status_file[VDATA_PATH_CAP];     /* human readable counters, no positions */
};

struct vdata {
    struct vdata_paths paths;
    enum vdata_mode mode;
    mvs_engine eng;
    uint32_t last_seq;                    /* highest source sequence already ingested */
    int have_seq;
    uint64_t mode_checked_ms, status_written_ms;
    /* counters (all start at zero) */
    unsigned long calls, gga, rmc, pascd_stock, other;
    unsigned long src_reads, src_missing, src_stale, src_records, src_bad;
    unsigned long would_send, sent_requested;
    char last_sentence[MVS_SENTENCE_BYTES + 1];
    char last_stock_kind[8];
};

/* Time access is injected so tests and the hook share the logic. */
struct vdata_clock {
    uint64_t (*mono_ms)(void);            /* CLOCK_MONOTONIC in milliseconds */
    int (*file_age_ms)(const char *path, uint64_t *age_ms); /* wall-clock age of the file, <0 if missing */
};

void vdata_init(struct vdata *v, const char *mode_file, const char *source_file, const char *status_file);
/* Called with every sentence the ORIGINAL worker is about to send (before forwarding it unchanged). */
void vdata_observe_stock(struct vdata *v, const char *nmea, const struct vdata_clock *clk);
/* Called after the stock send. Returns the length of a NUL-terminated $PASCD sentence in `out` that the
 * caller may send in the same worker context (mode send only), else 0. Never blocks. */
int vdata_next_sentence(struct vdata *v, const struct vdata_clock *clk, char *out, size_t cap);
/* Call after a sentence returned by vdata_next_sentence was actually handed to the driver. */
void vdata_note_sent(struct vdata *v);
/* Writes the status file if the interval elapsed (cheap otherwise). */
void vdata_status_tick(struct vdata *v, const struct vdata_clock *clk);

#endif
