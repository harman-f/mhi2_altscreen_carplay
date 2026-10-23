/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "mibr_vdata.h"
#include <stdio.h>
#include <string.h>

#define MODE_RECHECK_MS 3000ull
#define STATUS_EVERY_MS 5000ull
#define SOURCE_FRESH_MS 1500ull          /* a source file older than this has no new genuine event */

static void copy_path(char *dst, const char *src) {
    size_t n = src ? strlen(src) : 0;
    if (n >= VDATA_PATH_CAP) n = VDATA_PATH_CAP - 1u;
    if (n) memcpy(dst, src, n);
    dst[n] = 0;
}

void vdata_init(struct vdata *v, const char *mode_file, const char *source_file, const char *status_file) {
    if (!v) return;
    memset(v, 0, sizeof(*v));
    copy_path(v->paths.mode_file, mode_file);
    copy_path(v->paths.source_file, source_file);
    copy_path(v->paths.status_file, status_file);
    v->mode = VDATA_OFF;
    mvs_reset(&v->eng);
    /* Capability and request are enforced by the original HARMAN driver (it drops any sentence the phone
     * did not request and that Identify did not advertise), so the engine gates are held open here. */
    mvs_set_identify_speed(&v->eng, 1);
    v->eng.phone_wants_speed = 1;
    snprintf(v->last_stock_kind, sizeof(v->last_stock_kind), "none");
}

static void refresh_mode(struct vdata *v, uint64_t now) {
    FILE *f;
    char line[24] = {0};
    enum vdata_mode m = VDATA_OFF;
    if (v->mode_checked_ms && now - v->mode_checked_ms < MODE_RECHECK_MS) return;
    v->mode_checked_ms = now ? now : 1u;
    f = fopen(v->paths.mode_file, "r");
    if (f) {
        if (fgets(line, sizeof(line), f)) {
            if (!strncmp(line, "send", 4)) m = VDATA_SEND;
            else if (!strncmp(line, "shadow", 6)) m = VDATA_SHADOW;
        }
        (void)fclose(f);
    }
    if (m != v->mode) {
        v->mode = m;
        /* A mode change never carries a half-built batch over. */
        v->eng.count = 0;
        v->eng.have_last = 0;
        v->have_seq = 0;
    }
}

void vdata_observe_stock(struct vdata *v, const char *nmea, const struct vdata_clock *clk) {
    uint64_t now;
    if (!v || !nmea || !clk) return;
    now = clk->mono_ms();
    refresh_mode(v, now);
    v->calls++;
    if (!strncmp(nmea, "$GPGGA", 6) || !strncmp(nmea, "$GNGGA", 6)) {
        v->gga++; snprintf(v->last_stock_kind, sizeof(v->last_stock_kind), "GGA");
    } else if (!strncmp(nmea, "$GPRMC", 6) || !strncmp(nmea, "$GNRMC", 6)) {
        v->rmc++; snprintf(v->last_stock_kind, sizeof(v->last_stock_kind), "RMC");
    } else if (!strncmp(nmea, "$PASCD", 6)) {
        v->pascd_stock++; snprintf(v->last_stock_kind, sizeof(v->last_stock_kind), "PASCD");
        mvs_stock_pascd_observed(&v->eng);   /* the stock produces speed itself: stay silent */
    } else {
        v->other++; snprintf(v->last_stock_kind, sizeof(v->last_stock_kind), "other");
    }
    vdata_status_tick(v, clk);
}

/* Reads the ring file. Returns number of records (0..8) or -1 if absent/unusable. */
static int read_ring(struct vdata *v, uint8_t buf[VDATA_RING_MAX * MVS_WIRE_BYTES + 1u]) {
    FILE *f = fopen(v->paths.source_file, "rb");
    size_t n;
    if (!f) return -1;
    n = fread(buf, 1, VDATA_RING_MAX * MVS_WIRE_BYTES + 1u, f);
    (void)fclose(f);
    if (n == 0 || n > VDATA_RING_MAX * MVS_WIRE_BYTES || n % MVS_WIRE_BYTES) { v->src_bad++; return -1; }
    return (int)(n / MVS_WIRE_BYTES);
}

int vdata_next_sentence(struct vdata *v, const struct vdata_clock *clk, char *out, size_t cap) {
    uint8_t ring[VDATA_RING_MAX * MVS_WIRE_BYTES + 1u];   /* +1: detects an oversized file */
    mvs_sample rec[VDATA_RING_MAX];
    uint64_t now, age = 0, base;
    int n, i, produced = 0;
    char sentence[MVS_SENTENCE_BYTES + 1];
    if (!v || !clk || !out || cap < 2u) return 0;
    now = clk->mono_ms();
    refresh_mode(v, now);
    if (v->mode == VDATA_OFF) return 0;
    v->src_reads++;
    if (clk->file_age_ms(v->paths.source_file, &age) < 0) { v->src_missing++; return 0; }
    if (age > SOURCE_FRESH_MS) { v->src_stale++; return 0; }
    n = read_ring(v, ring);
    if (n < 0) return 0;
    for (i = 0; i < n; i++)
        if (mvs_wire_decode(ring + (size_t)i * MVS_WIRE_BYTES, MVS_WIRE_BYTES, &rec[i])) { v->src_bad++; return 0; }
    /* Source timestamps are relative: the HMI process and this process need not share a clock domain.
     * The newest record is placed at (now - file age); older records keep their exact spacing. */
    if (now < age) return 0;
    base = now - age;
    for (i = 0; i < n; i++) {
        uint8_t wire[MVS_WIRE_BYTES];
        mvs_sample s = rec[i];
        uint64_t back = rec[n - 1].sample_ms - rec[i].sample_ms;
        int len;
        if (rec[i].sample_ms > rec[n - 1].sample_ms || back > base) continue;
        if (v->have_seq) {
            uint32_t d = (uint32_t)(s.source_seq - v->last_seq);
            if (!d || (d & 0x80000000u)) continue;       /* already ingested or replayed */
        }
        v->last_seq = s.source_seq; v->have_seq = 1;
        v->src_records++;
        s.sample_ms = base - back;
        if (mvs_wire_encode(&s, wire, sizeof(wire))) { v->src_bad++; continue; }
        len = mvs_ingest(&v->eng, wire, sizeof(wire), now, sentence, sizeof(sentence));
        if (len > 0 && !produced) {
            snprintf(v->last_sentence, sizeof(v->last_sentence), "%s", sentence);
            v->would_send++;
            if (v->mode == VDATA_SEND && (size_t)len < cap) {
                memcpy(out, sentence, (size_t)len + 1u);
                produced = len;
            }
        }
    }
    return produced;
}

void vdata_note_sent(struct vdata *v) { if (v) v->sent_requested++; }

void vdata_status_tick(struct vdata *v, const struct vdata_clock *clk) {
    uint64_t now;
    FILE *f;
    static const char *const names[] = {"off", "shadow", "send"};
    if (!v || !clk) return;
    now = clk->mono_ms();
    if (v->status_written_ms && now - v->status_written_ms < STATUS_EVERY_MS) return;
    v->status_written_ms = now ? now : 1u;
    f = fopen(v->paths.status_file, "w");
    if (!f) return;
    (void)fprintf(f,
        "mode=%s\ncalls=%lu\ngga=%lu\nrmc=%lu\npascd_stock=%lu\nother=%lu\nlast_stock=%s\n"
        "src_reads=%lu\nsrc_missing=%lu\nsrc_stale=%lu\nsrc_records=%lu\nsrc_bad=%lu\n"
        "would_send=%lu\nsent=%lu\nstock_pascd_latched=%d\nlast_sentence=%s\n",
        names[v->mode], v->calls, v->gga, v->rmc, v->pascd_stock, v->other, v->last_stock_kind,
        v->src_reads, v->src_missing, v->src_stale, v->src_records, v->src_bad,
        v->would_send, v->sent_requested, v->eng.stock_pascd_seen, v->last_sentence);
    (void)fclose(f);
}
