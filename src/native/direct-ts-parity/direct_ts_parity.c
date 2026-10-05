/*
 * M.I.B. MU1440 Omonob-790 functional-parity transport bridge.
 *
 * Clean-room implementation from documented behavioral observations.
 * No third-party binary bytes or decompiler output are embedded here.
 *
 * Input:  M1AU v1 records from GEN2 over loopback TCP. Each record is exactly
 *         one complete Annex-B H.264 access unit plus the raw Stream-111
 *         32.32 source timestamp.
 * Output: continuous 12.288-Mbit/s MPEG-TS transport for /dev/mlb/isoTX2,
 *         written only as 64 x 188 = 12032-byte physical blocks.
 *
 * Reference topology / timing:
 *   PAT PID   0x0000
 *   PMT PID   0x0010
 *   PCR PID   0x1000
 *   H.264 PID 0x0011
 *   PCR/PAT/PMT cadence ~327 TS packets (~40 ms at 12.288 Mbit/s)
 *   PTS source = Stream-111 32.32 timestamp mapped to 90 kHz
 *   nominal PTS lead = PCR + 9000 (100 ms)
 *   minimum lead = PCR + 4500 (50 ms), then rebase
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 */

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>

#ifdef __QNXNTO__
#include <devctl.h>
#endif

#define TS_SIZE 188u
#define MOST_BLOCK_PACKETS 64u
#define MOST_BLOCK_BYTES (TS_SIZE * MOST_BLOCK_PACKETS)
#define TRANSPORT_BPS 12288000u
#define TRANSPORT_TICKS_NUM 705u
#define TRANSPORT_TICKS_DEN 64u
#define TRANSPORT_PCR_BASE 45000u
#define PSI_INTERVAL_PACKETS 327u
#define PCR_INTERVAL_PACKETS 327u
#define PTS_LEAD_90K 9000u
#define PTS_MIN_LEAD_90K 4500u
#define PID_PAT 0x0000u
#define PID_PMT 0x0010u
#define PID_PCR 0x1000u
#define PID_VIDEO 0x0011u
#define PROGRAM_NUMBER 1u
#define M1AU_HEADER_BYTES 56u
#define M1AU_MAX_PAYLOAD (3u * 1024u * 1024u)
#define M1AU_FLAG_IDR 0x00000001u
#define AU_QUEUE_CAP 64u
#define AU_QUEUE_PACKET_CAP 65536u
#define STATUS_PATH "/tmp/mibr-parity-ts.status"
#define KEYFRAME_MARKER "/tmp/mibr-alt111-keyframe-only"
#define DRIVER_DCMD_FLUSH 0x40040506
#define DRIVER_DCMD_START 0x80040509
#define DRIVER_DCMD_GET_INTERFACE 0x4004050c
#define DRIVER_DCMD_GET_PACKET_SIZE 0x4004050d
#define DRIVER_DCMD_GET_BLOCK_COUNT 0x40040510
#define PARITY_IDR_INTERVAL 20u
#define REFERENCE_PRODUCER_PAYLOAD_LIMIT 0x40000u
#define LOW_LATENCY_PACKET_LIMIT 1024u
#define WRITE_TIMEOUT_US 500000u
#define TRANSPORT_LATE_LIMIT_US 40000u

struct ts_au {
    uint8_t *packets;
    size_t packet_count;
    size_t packet_pos;
    uint64_t sequence;
    uint64_t pts90k;
    int idr;
};

struct au_queue {
    pthread_mutex_t lock;
    pthread_cond_t cv_nonempty;
    pthread_cond_t cv_space;
    struct ts_au q[AU_QUEUE_CAP];
    unsigned head;
    unsigned count;
    size_t packets_queued;
    int stop;
    int input_done;
};

struct clock_state {
    pthread_mutex_t lock;
    uint64_t physical_packets;
    uint64_t transport_pcr90k;
    uint64_t pts_origin90k;
    uint64_t last_pts90k;
    uint32_t origin_frac;
    uint32_t origin_sec;
    uint64_t local_origin_us;
    int have_origin;
    int origin_is_source;
    uint64_t pts_rebases;
    uint64_t source_rebases;
    uint64_t previous_source;
    uint64_t previous_arrival_us;
    int have_previous_source;
    uint64_t emitted_pts90k;
    uint64_t emission_shift90k;
};

struct bridge_stats {
    pthread_mutex_t lock;
    uint64_t input_records;
    uint64_t input_bytes;
    uint64_t input_idrs;
    uint64_t sequence_gaps;
    uint64_t dropped_wait_idr;
    uint64_t safe_recoveries;
    uint64_t generation_recoveries;
    uint64_t latency_recoveries;
    uint64_t safe_recovery_discarded_aus;
    uint64_t safe_recovery_discarded_packets;
    uint64_t safe_recovery_preserved_packets;
    uint64_t aus_queued;
    uint64_t pes_packets;
    uint64_t blocks_written;
    uint64_t bytes_written;
    uint64_t write_eagain;
    uint64_t write_errors;
    uint64_t null_packets;
    uint64_t pat_packets;
    uint64_t pmt_packets;
    uint64_t pcr_packets;
    uint64_t last_sequence;
    uint32_t last_frac;
    uint32_t last_sec;
    uint64_t last_pts;
    int waiting_idr;
    int driver_interface_rc;
    uint32_t driver_interface_value;
    int driver_packet_size_rc;
    uint32_t driver_packet_size_value;
    int driver_block_count_rc;
    uint32_t driver_block_count_value;
    int driver_flush_rc;
    int driver_start_rc;
};

struct writer_ctx {
    int fd;
    int regular_file;
    int input_fd;
    struct au_queue *queue;
    struct clock_state *clock;
    struct bridge_stats *stats;
    uint8_t cc_pat;
    uint8_t cc_pmt;
    uint8_t cc_video;
    uint8_t cc_null;
    uint64_t next_pat_packet;
    uint64_t next_pmt_packet;
    uint64_t next_pcr_packet;
};

static volatile sig_atomic_t g_stop;

static uint16_t be16(const uint8_t *p) {
    return (uint16_t)(((uint16_t)p[0] << 8) | p[1]);
}
static uint32_t be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}
static uint64_t be64(const uint8_t *p) {
    uint64_t v = 0; unsigned i;
    for (i = 0; i < 8u; ++i) v = (v << 8) | p[i];
    return v;
}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}

static void on_signal(int sig) { (void)sig; g_stop = 1; }

static uint32_t crc32_mpeg(const uint8_t *p, size_t n) {
    uint32_t crc = 0xffffffffu;
    size_t i; unsigned b;
    for (i = 0; i < n; ++i) {
        crc ^= (uint32_t)p[i] << 24;
        for (b = 0; b < 8u; ++b)
            crc = (crc & 0x80000000u) ? (crc << 1) ^ 0x04c11db7u : (crc << 1);
    }
    return crc;
}

static void put_crc(uint8_t *p, uint32_t crc) {
    p[0] = (uint8_t)(crc >> 24); p[1] = (uint8_t)(crc >> 16);
    p[2] = (uint8_t)(crc >> 8); p[3] = (uint8_t)crc;
}

static void make_null_packet(uint8_t p[TS_SIZE], uint8_t *cc) {
    memset(p, 0xff, TS_SIZE);
    p[0] = 0x47; p[1] = 0x1f; p[2] = 0xff;
    p[3] = (uint8_t)(0x10u | (*cc & 0x0fu));
    *cc = (uint8_t)((*cc + 1u) & 0x0fu);
}

static void make_psi_packet(uint8_t p[TS_SIZE], uint16_t pid, uint8_t *cc,
                            const uint8_t *section, size_t section_len) {
    if (section_len + 5u >= TS_SIZE) return;
    memset(p, 0xff, TS_SIZE);
    p[0] = 0x47;
    p[1] = (uint8_t)(0x40u | ((pid >> 8) & 0x1fu));
    p[2] = (uint8_t)pid;
    p[3] = (uint8_t)(0x10u | (*cc & 0x0fu));
    *cc = (uint8_t)((*cc + 1u) & 0x0fu);
    p[4] = 0;
    memcpy(p + 5, section, section_len);
}

static void make_pat(uint8_t p[TS_SIZE], uint8_t *cc) {
    uint8_t s[16]; uint32_t crc;
    memset(s, 0, sizeof(s));
    s[0] = 0x00; s[1] = 0xb0; s[2] = 0x0d;
    s[3] = 0x00; s[4] = 0x01; s[5] = 0xc1; s[6] = 0; s[7] = 0;
    s[8] = 0x00; s[9] = PROGRAM_NUMBER;
    s[10] = (uint8_t)(0xe0u | ((PID_PMT >> 8) & 0x1fu)); s[11] = (uint8_t)PID_PMT;
    crc = crc32_mpeg(s, 12); put_crc(s + 12, crc);
    make_psi_packet(p, PID_PAT, cc, s, sizeof(s));
}

static void make_pmt(uint8_t p[TS_SIZE], uint8_t *cc) {
    uint8_t s[21]; uint32_t crc;
    memset(s, 0, sizeof(s));
    s[0] = 0x02; s[1] = 0xb0; s[2] = 0x12;
    s[3] = 0x00; s[4] = PROGRAM_NUMBER; s[5] = 0xc1; s[6] = 0; s[7] = 0;
    s[8] = (uint8_t)(0xe0u | ((PID_PCR >> 8) & 0x1fu)); s[9] = (uint8_t)PID_PCR;
    s[10] = 0xf0; s[11] = 0x00;
    s[12] = 0x1b;
    s[13] = (uint8_t)(0xe0u | ((PID_VIDEO >> 8) & 0x1fu)); s[14] = (uint8_t)PID_VIDEO;
    s[15] = 0xf0; s[16] = 0x00;
    crc = crc32_mpeg(s, 17); put_crc(s + 17, crc);
    make_psi_packet(p, PID_PMT, cc, s, sizeof(s));
}

static void encode_pcr(uint8_t out[6], uint64_t base90k) {
    uint64_t b = base90k & ((1ull << 33) - 1ull);
    out[0] = (uint8_t)(b >> 25);
    out[1] = (uint8_t)(b >> 17);
    out[2] = (uint8_t)(b >> 9);
    out[3] = (uint8_t)(b >> 1);
    out[4] = (uint8_t)(((b & 1u) << 7) | 0x7e);
    out[5] = 0;
}

static void make_pcr_packet(uint8_t p[TS_SIZE], uint64_t pcr90k) {
    memset(p, 0xff, TS_SIZE);
    p[0] = 0x47;
    p[1] = (uint8_t)((PID_PCR >> 8) & 0x1fu);
    p[2] = (uint8_t)PID_PCR;
    p[3] = 0x20;
    p[4] = 183;
    p[5] = 0x10;
    encode_pcr(p + 6, pcr90k);
}

static void encode_pts(uint8_t out[5], uint64_t pts90k) {
    uint64_t v = pts90k & ((1ull << 33) - 1ull);
    out[0] = (uint8_t)(0x20u | (((v >> 30) & 0x07u) << 1) | 1u);
    out[1] = (uint8_t)(v >> 22);
    out[2] = (uint8_t)((((v >> 15) & 0x7fu) << 1) | 1u);
    out[3] = (uint8_t)(v >> 7);
    out[4] = (uint8_t)(((v & 0x7fu) << 1) | 1u);
}

static uint64_t source_delta_90k(uint32_t origin_frac, uint32_t origin_sec,
                                 uint32_t frac, uint32_t sec) {
    uint32_t borrow = frac < origin_frac ? 1u : 0u;
    uint32_t sec_delta = sec - origin_sec - borrow;
    uint32_t frac_delta = frac - origin_frac;
    uint64_t frac90 = ((uint64_t)frac_delta * 90000ull + 0x80000000ull) >> 32;
    return (uint64_t)sec_delta * 90000ull + frac90;
}

static uint64_t clock_pcr_now(struct clock_state *c) {
    uint64_t v;
    pthread_mutex_lock(&c->lock); v = c->transport_pcr90k; pthread_mutex_unlock(&c->lock);
    return v;
}

static uint64_t monotonic_us(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
    return (uint64_t)ts.tv_sec * 1000000ull + (uint64_t)ts.tv_nsec / 1000ull;
}

static uint64_t assign_pts(struct clock_state *c, uint32_t frac, uint32_t sec,
                           int *rebased) {
    uint64_t pcr, pts, floor, target, shift, now_us;
    uint64_t raw = ((uint64_t)sec << 32) | frac;
    int discontinuous = 0;
    int source_valid = (frac != 0u || sec != 0u);
    *rebased = 0;
    now_us = monotonic_us();
    pthread_mutex_lock(&c->lock);
    pcr = c->transport_pcr90k;
    if (source_valid && c->have_previous_source) {
        /* Unsigned 64-bit subtraction followed by signed interpretation also
         * handles the seconds-word rollover. Compare successive source times,
         * not the original session epoch. Idle time is allowed. */
        int64_t delta = (int64_t)(raw - c->previous_source);
        uint64_t wall_us = now_us - c->previous_arrival_us;
        uint64_t allowed = ((wall_us / 1000u + 500u) << 32) / 1000u;
        discontinuous = delta < 0 || (uint64_t)delta > allowed;
    }
    if (!c->have_origin || c->origin_is_source != source_valid ||
        discontinuous) {
        c->origin_frac = frac;
        c->origin_sec = sec;
        c->local_origin_us = now_us;
        c->pts_origin90k = pcr + PTS_LEAD_90K;
        if (c->pts_origin90k <= c->last_pts90k) c->pts_origin90k = c->last_pts90k + 1u;
        if (c->have_origin) ++c->source_rebases;
        c->have_origin = 1;
        c->origin_is_source = source_valid;
    }
    c->previous_source = raw;
    c->previous_arrival_us = now_us;
    c->have_previous_source = source_valid;
    if (source_valid) {
        pts = c->pts_origin90k + source_delta_90k(c->origin_frac, c->origin_sec, frac, sec);
        if (source_delta_90k(c->origin_frac, c->origin_sec, frac, sec) >
                ((now_us - c->local_origin_us) * 90u) / 1000u + 45000u) {
            c->origin_frac = frac; c->origin_sec = sec; c->local_origin_us = now_us;
            c->pts_origin90k = pcr + PTS_LEAD_90K;
            pts = c->pts_origin90k; ++c->source_rebases; *rebased = 1;
        }
    } else
        pts = c->pts_origin90k + ((now_us - c->local_origin_us) * 90ull) / 1000ull;
    floor = pcr + PTS_MIN_LEAD_90K;
    if (pts < floor) {
        target = pcr + PTS_LEAD_90K;
        if (target <= c->last_pts90k) target = c->last_pts90k + 1u;
        shift = target - pts;
        c->pts_origin90k += shift;
        pts += shift;
        ++c->pts_rebases;
        *rebased = 1;
    }
    if (pts <= c->last_pts90k) pts = c->last_pts90k + 1u;
    c->last_pts90k = pts;
    pthread_mutex_unlock(&c->lock);
    return pts;
}

static int annexb_nal_type(const uint8_t *p, size_t n, size_t *sc, size_t *nal) {
    size_t i;
    for (i = *sc; i + 3u < n; ++i) {
        if (p[i] == 0 && p[i+1] == 0 && p[i+2] == 1) {
            *sc = i; *nal = i + 3u; return p[*nal] & 31u;
        }
        if (i + 4u < n && p[i] == 0 && p[i+1] == 0 && p[i+2] == 0 && p[i+3] == 1) {
            *sc = i; *nal = i + 4u; return p[*nal] & 31u;
        }
    }
    return -1;
}

static int au_has_type(const uint8_t *p, size_t n, int want) {
    size_t sc = 0, nal = 0;
    int type;
    while ((type = annexb_nal_type(p, n, &sc, &nal)) >= 0) {
        if (type == want) return 1;
        sc = nal + 1u;
    }
    return 0;
}

static size_t annexb_find_next_start(const uint8_t *p, size_t n, size_t from) {
    size_t i;
    for (i = from; i + 3u < n; ++i) {
        if (p[i] == 0 && p[i+1] == 0 && p[i+2] == 1) return i;
        if (i + 4u < n && p[i] == 0 && p[i+1] == 0 && p[i+2] == 0 && p[i+3] == 1) return i;
    }
    return n;
}

static int extract_param_sets(const uint8_t *p, size_t n, uint8_t **out, size_t *out_n) {
    size_t sc = 0, nal = 0;
    uint8_t *buf = NULL; size_t used = 0;
    int type;
    int incoming_sps = au_has_type(p, n, 7);
    int incoming_pps = au_has_type(p, n, 8);
    /* A partial config update must retain the other parameter-set type. */
    while ((type = annexb_nal_type(*out, *out_n, &sc, &nal)) >= 0) {
        size_t next_sc = annexb_find_next_start(*out, *out_n, nal + 1u);
        if ((type == 7 && !incoming_sps) || (type == 8 && !incoming_pps)) {
            size_t len = next_sc - sc;
            uint8_t *nb = (uint8_t *)realloc(buf, used + len);
            if (!nb) { free(buf); return -1; }
            buf = nb; memcpy(buf + used, *out + sc, len); used += len;
        }
        if (next_sc == *out_n) break;
        sc = next_sc;
    }
    sc = 0; nal = 0;
    while ((type = annexb_nal_type(p, n, &sc, &nal)) >= 0) {
        size_t next_sc = annexb_find_next_start(p, n, nal + 1u);
        if (type == 7 || type == 8) {
            size_t len = next_sc - sc;
            uint8_t *nb = (uint8_t *)realloc(buf, used + len);
            if (!nb) { free(buf); return -1; }
            buf = nb; memcpy(buf + used, p + sc, len); used += len;
        }
        if (next_sc == n) break;
        sc = next_sc;
    }
    if (used) { free(*out); *out = buf; *out_n = used; }
    else free(buf);
    return 0;
}

static int normalize_au(const uint8_t *in, size_t in_n, int idr,
                        uint8_t **cache, size_t *cache_n,
                        uint8_t **out, size_t *out_n) {
    static const uint8_t aud[] = {0,0,0,1,0x09,0xf0};
    int has_sps = au_has_type(in, in_n, 7);
    int has_pps = au_has_type(in, in_n, 8);
    size_t extra = sizeof(aud), sc = 0, nal = 0;
    uint8_t *buf; size_t off = 0; int type;
    if (!in_n || (in[0] != 0) || !au_has_type(in, in_n, idr ? 5 : 1)) return -1;
    if ((has_sps || has_pps) && extract_param_sets(in, in_n, cache, cache_n) != 0) return -1;
    if (idr && (!au_has_type(*cache, *cache_n, 7) || !au_has_type(*cache, *cache_n, 8))) return -1;
    if (idr) extra += *cache_n;
    if (in_n > SIZE_MAX - extra) return -1;
    buf = (uint8_t *)malloc(in_n + extra);
    if (!buf) return -1;
    memcpy(buf, aud, sizeof(aud)); off += sizeof(aud);
    if (idr) {
        /* Canonical ordering: AUD, all SPS, all PPS, then SEI/VCL. */
        int wanted;
        for (wanted = 7; wanted <= 8; ++wanted) {
            sc = 0; nal = 0;
            while ((type = annexb_nal_type(*cache, *cache_n, &sc, &nal)) >= 0) {
                size_t next = annexb_find_next_start(*cache, *cache_n, nal + 1u);
                if (type == wanted) { memcpy(buf + off, *cache + sc, next - sc); off += next - sc; }
                if (next == *cache_n) break;
                sc = next;
            }
        }
    }
    sc = 0; nal = 0;
    while ((type = annexb_nal_type(in, in_n, &sc, &nal)) >= 0) {
        size_t next = annexb_find_next_start(in, in_n, nal + 1u);
        if (type != 9 && (!idr || (type != 7 && type != 8))) {
            memcpy(buf + off, in + sc, next - sc); off += next - sc;
        }
        if (next == in_n) break;
        sc = next;
    }
    *out = buf; *out_n = off;
    return 0;
}

static int packetize_pes(const uint8_t *au, size_t au_n, uint64_t pts90k, int idr,
                         int discontinuity, uint8_t *cc_video,
                         uint8_t **out_packets, size_t *out_count) {
    uint8_t *pes, *pkts; size_t pes_n, off = 0, count, idx = 0;
    uint8_t pts[5];
    if (au_n > SIZE_MAX - 14u) return -1;
    pes_n = 14u + au_n;
    pes = (uint8_t *)malloc(pes_n);
    if (!pes) return -1;
    pes[0]=0; pes[1]=0; pes[2]=1; pes[3]=0xe0; pes[4]=0; pes[5]=0;
    pes[6]=0x80; pes[7]=0x80; pes[8]=5;
    encode_pts(pts, pts90k); memcpy(pes + 9, pts, 5); memcpy(pes + 14, au, au_n);
    count = (pes_n + 181u) / 182u + 1u;
    pkts = (uint8_t *)malloc(count * TS_SIZE);
    if (!pkts) { free(pes); return -1; }
    while (off < pes_n) {
        uint8_t *p = pkts + idx * TS_SIZE;
        size_t rem = pes_n - off, payload_cap = 184u, payload, adapt_len = 0;
        int first = idx == 0;
        memset(p, 0xff, TS_SIZE);
        p[0] = 0x47;
        p[1] = (uint8_t)((first ? 0x40u : 0u) | ((PID_VIDEO >> 8) & 0x1fu));
        p[2] = (uint8_t)PID_VIDEO;
        /* Omonob parity: every PES-start TS packet has an adaptation field,
         * even when neither discontinuity nor random-access is asserted. */
        if (first) payload_cap = 182u;
        payload = rem < payload_cap ? rem : payload_cap;
        if (first || payload < 184u) {
            adapt_len = 183u - payload;
            if (first && adapt_len < 1u) { payload = 182u; adapt_len = 1u; }
            p[3] = (uint8_t)(0x30u | (*cc_video & 0x0fu));
            p[4] = (uint8_t)adapt_len;
            if (adapt_len) {
                p[5] = (uint8_t)((first && discontinuity ? 0x80u : 0u) |
                                 (first && idr ? 0x40u : 0u));
                if (adapt_len > 1u) memset(p + 6, 0xff, adapt_len - 1u);
            }
            memcpy(p + 5u + adapt_len, pes + off, payload);
        } else {
            p[3] = (uint8_t)(0x10u | (*cc_video & 0x0fu));
            memcpy(p + 4, pes + off, payload);
        }
        *cc_video = (uint8_t)((*cc_video + 1u) & 0x0fu);
        off += payload; ++idx;
    }
    free(pes);
    *out_packets = pkts; *out_count = idx;
    return 0;
}

static void queue_init(struct au_queue *q) {
    memset(q, 0, sizeof(*q));
    pthread_mutex_init(&q->lock, NULL);
    pthread_cond_init(&q->cv_nonempty, NULL);
    pthread_cond_init(&q->cv_space, NULL);
}

static void queue_stop(struct au_queue *q) {
    pthread_mutex_lock(&q->lock); q->stop = 1;
    pthread_cond_broadcast(&q->cv_nonempty); pthread_cond_broadcast(&q->cv_space);
    pthread_mutex_unlock(&q->lock);
}

static void queue_destroy(struct au_queue *q) {
    unsigned i;
    for (i=0;i<AU_QUEUE_CAP;++i) free(q->q[i].packets);
    pthread_cond_destroy(&q->cv_nonempty); pthread_cond_destroy(&q->cv_space);
    pthread_mutex_destroy(&q->lock);
}

static size_t queue_packet_depth(struct au_queue *q) {
    size_t packets;
    pthread_mutex_lock(&q->lock);
    packets=q->packets_queued;
    pthread_mutex_unlock(&q->lock);
    return packets;
}

/*
 * Unlike the reference packet-level queue flush, discard only whole AUs that
 * have not started physical presentation. If the writer has consumed any
 * packet from the head AU, preserve its remaining tail to avoid truncating an
 * in-flight PES.
 */
static void queue_recover_au_boundary(struct au_queue *q,
                                      uint64_t *discarded_aus,
                                      uint64_t *discarded_packets,
                                      uint64_t *preserved_packets) {
    unsigned i, keep_head=0, old_count;
    uint64_t da=0, dp=0, pp=0;
    pthread_mutex_lock(&q->lock);
    old_count=q->count;
    if(old_count && q->q[q->head].packet_pos>0u) {
        keep_head=1u;
        pp=(uint64_t)(q->q[q->head].packet_count-q->q[q->head].packet_pos);
    }
    for(i=keep_head;i<old_count;++i) {
        unsigned idx=(q->head+i)%AU_QUEUE_CAP;
        struct ts_au *a=&q->q[idx];
        dp+=(uint64_t)(a->packet_count-a->packet_pos);
        ++da;
        free(a->packets);
        memset(a,0,sizeof(*a));
    }
    q->count=keep_head;
    q->packets_queued=(size_t)pp;
    pthread_cond_broadcast(&q->cv_space);
    pthread_mutex_unlock(&q->lock);
    if(discarded_aus)*discarded_aus=da;
    if(discarded_packets)*discarded_packets=dp;
    if(preserved_packets)*preserved_packets=pp;
}

static void record_safe_recovery(struct bridge_stats *s, const char *reason,
                                 uint64_t discarded_aus,
                                 uint64_t discarded_packets,
                                 uint64_t preserved_packets) {
    pthread_mutex_lock(&s->lock);
    ++s->safe_recoveries;
    if(reason && strcmp(reason,"generation")==0) ++s->generation_recoveries;
    if(reason && strcmp(reason,"latency")==0) ++s->latency_recoveries;
    s->safe_recovery_discarded_aus+=discarded_aus;
    s->safe_recovery_discarded_packets+=discarded_packets;
    s->safe_recovery_preserved_packets+=preserved_packets;
    pthread_mutex_unlock(&s->lock);
    fprintf(stderr,
            "PARITY_SAFE_RECOVERY reason=%s discarded_aus=%llu discarded_packets=%llu preserved_head_packets=%llu\n",
            reason?reason:"unknown",
            (unsigned long long)discarded_aus,
            (unsigned long long)discarded_packets,
            (unsigned long long)preserved_packets);
}

static int queue_push(struct au_queue *q, struct ts_au *au) {
    unsigned idx;
    pthread_mutex_lock(&q->lock);
    while (!q->stop && !g_stop && (q->count == AU_QUEUE_CAP ||
           q->packets_queued + au->packet_count > AU_QUEUE_PACKET_CAP))
        pthread_cond_wait(&q->cv_space, &q->lock);
    if (q->stop || g_stop) { pthread_mutex_unlock(&q->lock); return -1; }
    idx = (q->head + q->count) % AU_QUEUE_CAP;
    q->q[idx] = *au; ++q->count; q->packets_queued += au->packet_count;
    memset(au, 0, sizeof(*au));
    pthread_cond_signal(&q->cv_nonempty); pthread_mutex_unlock(&q->lock);
    return 0;
}

static int queue_take_packet_at(struct au_queue *q, uint8_t p[TS_SIZE],
                                struct clock_state *clock, uint64_t pcr) {
    struct ts_au *a;
    pthread_mutex_lock(&q->lock);
    if (!q->count) { pthread_mutex_unlock(&q->lock); return 0; }
    a = &q->q[q->head];
    if (clock && a->packet_pos == 0) {
        /* Guard the complete PES deadline at emission, including PSI/PCR
         * slots and two physical blocks of scheduling/driver margin. */
        uint64_t budget = a->packet_count + (a->packet_count / 300u + 1u) * 3u + 128u;
        uint64_t floor = pcr + (budget * TRANSPORT_TICKS_NUM + 63u) / 64u + PTS_MIN_LEAD_90K;
        uint64_t pts;
        size_t offset = 5u + a->packets[4];
        pthread_mutex_lock(&clock->lock);
        pts = a->pts90k + clock->emission_shift90k;
        if (pts < floor) { clock->emission_shift90k += floor - pts; pts = floor; ++clock->pts_rebases; }
        if (pts <= clock->emitted_pts90k) pts = clock->emitted_pts90k + 1u;
        clock->emitted_pts90k = pts;
        pthread_mutex_unlock(&clock->lock);
        encode_pts(a->packets + offset + 9u, pts);
    }
    memcpy(p, a->packets + a->packet_pos * TS_SIZE, TS_SIZE);
    ++a->packet_pos; --q->packets_queued;
    if (a->packet_pos == a->packet_count) {
        free(a->packets); memset(a, 0, sizeof(*a));
        q->head = (q->head + 1u) % AU_QUEUE_CAP; --q->count;
    }
    pthread_cond_signal(&q->cv_space); pthread_mutex_unlock(&q->lock);
    return 1;
}

static int queue_take_packet(struct au_queue *q, uint8_t p[TS_SIZE]) {
    return queue_take_packet_at(q, p, NULL, 0);
}

static int queue_wait_empty(struct au_queue *q, unsigned max_ms) {
    unsigned waited = 0;
    for (;;) {
        unsigned count;
        size_t packets;
        pthread_mutex_lock(&q->lock);
        count = q->count;
        packets = q->packets_queued;
        pthread_mutex_unlock(&q->lock);
        if (!count && !packets) return 0;
        if (g_stop || waited >= max_ms) return -1;
        usleep(1000);
        ++waited;
    }
}

static int queue_finished(struct au_queue *q) {
    int done;
    pthread_mutex_lock(&q->lock); done = q->input_done && !q->count; pthread_mutex_unlock(&q->lock);
    return done;
}

static void stats_add_u64(uint64_t *v, pthread_mutex_t *m, uint64_t add) {
    pthread_mutex_lock(m); *v += add; pthread_mutex_unlock(m);
}

static void publish_status(struct bridge_stats *s, struct clock_state *c,
                           struct au_queue *q, const char *state) {
    char tmp[128]; FILE *f; unsigned qcount; size_t qpkts;
    struct bridge_stats snap; uint64_t pcr, rebase, source_rebase;
    snprintf(tmp, sizeof(tmp), "%s.tmp", STATUS_PATH);
    pthread_mutex_lock(&s->lock); snap = *s; pthread_mutex_unlock(&s->lock);
    pthread_mutex_lock(&c->lock); pcr=c->transport_pcr90k; rebase=c->pts_rebases; source_rebase=c->source_rebases; pthread_mutex_unlock(&c->lock);
    pthread_mutex_lock(&q->lock); qcount=q->count; qpkts=q->packets_queued; pthread_mutex_unlock(&q->lock);
    f=fopen(tmp,"w"); if(!f)return;
    fprintf(f,"state=%s\n",state);
    fprintf(f,"architecture=omonob790-functional-parity-cleanroom\n");
    fprintf(f,"input_mode=m1au-complete-au\n");
    fprintf(f,"source_clock=stream111-32.32\n");
    fprintf(f,"pts_clock=source-derived-90khz\n");
    fprintf(f,"frame_pacer=none\n");
    fprintf(f,"transport_pacer=absolute_monotonic_all_outputs\n");
    fprintf(f,"transport_clock_model=scheduled_cbr_accepted_blocks\n");
    fprintf(f,"hardware_drain_validation=required\n");
    pthread_mutex_lock(&c->lock);
    fprintf(f,"last_emitted_pts90k=%llu\nemission_shift90k=%llu\n",
        (unsigned long long)c->emitted_pts90k,(unsigned long long)c->emission_shift90k);
    pthread_mutex_unlock(&c->lock);
    fprintf(f,"transport_bps=%u\n",TRANSPORT_BPS);
    fprintf(f,"pat_pid=0x%04x\npmt_pid=0x%04x\npcr_pid=0x%04x\nvideo_pid=0x%04x\n",PID_PAT,PID_PMT,PID_PCR,PID_VIDEO);
    fprintf(f,"most_block_bytes=%u\n",MOST_BLOCK_BYTES);
    fprintf(f,"device_open_mode=write_only_nonblock\n");
    fprintf(f,"reference_producer_payload_limit=%u\n",REFERENCE_PRODUCER_PAYLOAD_LIMIT);
    fprintf(f,"bridge_safety_payload_limit=%u\n",M1AU_MAX_PAYLOAD);
    fprintf(f,"driver_interface_rc=%d\ndriver_interface_value=%u\n",snap.driver_interface_rc,snap.driver_interface_value);
    fprintf(f,"driver_packet_size_rc=%d\ndriver_packet_size_value=%u\n",snap.driver_packet_size_rc,snap.driver_packet_size_value);
    fprintf(f,"driver_block_count_rc=%d\ndriver_block_count_value=%u\n",snap.driver_block_count_rc,snap.driver_block_count_value);
    fprintf(f,"driver_flush_rc=%d\ndriver_start_rc=%d\n",snap.driver_flush_rc,snap.driver_start_rc);
    fprintf(f,"transport_pcr90k=%llu\n",(unsigned long long)pcr);
    fprintf(f,"pts_rebases=%llu\nsource_rebases=%llu\n",(unsigned long long)rebase,(unsigned long long)source_rebase);
    fprintf(f,"input_records=%llu\ninput_bytes=%llu\ninput_idrs=%llu\nsequence_gaps=%llu\n",
        (unsigned long long)snap.input_records,(unsigned long long)snap.input_bytes,
        (unsigned long long)snap.input_idrs,(unsigned long long)snap.sequence_gaps);
    fprintf(f,"dropped_wait_idr=%llu\n",(unsigned long long)snap.dropped_wait_idr);
    fprintf(f,"safe_recoveries=%llu\ngeneration_recoveries=%llu\nlatency_recoveries=%llu\n",
        (unsigned long long)snap.safe_recoveries,
        (unsigned long long)snap.generation_recoveries,
        (unsigned long long)snap.latency_recoveries);
    fprintf(f,"safe_recovery_discarded_aus=%llu\nsafe_recovery_discarded_packets=%llu\nsafe_recovery_preserved_packets=%llu\n",
        (unsigned long long)snap.safe_recovery_discarded_aus,
        (unsigned long long)snap.safe_recovery_discarded_packets,
        (unsigned long long)snap.safe_recovery_preserved_packets);
    fprintf(f,"latency_packet_limit=%u\n",LOW_LATENCY_PACKET_LIMIT);
    fprintf(f,"aus_queued=%llu\npes_packets=%llu\n",
        (unsigned long long)snap.aus_queued,(unsigned long long)snap.pes_packets);
    fprintf(f,"blocks_written=%llu\nbytes_written=%llu\nwrite_eagain=%llu\nwrite_errors=%llu\n",
        (unsigned long long)snap.blocks_written,(unsigned long long)snap.bytes_written,
        (unsigned long long)snap.write_eagain,(unsigned long long)snap.write_errors);
    fprintf(f,"null_packets=%llu\npat_packets=%llu\npmt_packets=%llu\npcr_packets=%llu\n",
        (unsigned long long)snap.null_packets,(unsigned long long)snap.pat_packets,
        (unsigned long long)snap.pmt_packets,(unsigned long long)snap.pcr_packets);
    fprintf(f,"queue_aus=%u\nqueue_packets=%lu\n",qcount,(unsigned long)qpkts);
    fprintf(f,"last_sequence=%llu\nlast_source_frac=0x%08x\nlast_source_sec=0x%08x\nlast_pts90k=%llu\nwaiting_idr=%d\n",
        (unsigned long long)snap.last_sequence,snap.last_frac,snap.last_sec,
        (unsigned long long)snap.last_pts,snap.waiting_idr);
    fclose(f); rename(tmp,STATUS_PATH);
}

static int write_full(int fd, const uint8_t *p, size_t n, struct bridge_stats *s) {
    size_t off=0;
    uint64_t deadline = monotonic_us() + WRITE_TIMEOUT_US;
    while(off<n) {
        ssize_t w=write(fd,p+off,n-off);
        if(w>0) {
            /* An isoTX2 short acceptance breaks the 64-packet syscall
             * contract. Fail rather than silently submit a partial block. */
            if ((size_t)w != n) { stats_add_u64(&s->write_errors,&s->lock,1); return -1; }
            off+=(size_t)w; continue;
        }
        if(w<0 && errno==EINTR)continue;
        if(w<0 && (errno==EAGAIN||errno==EWOULDBLOCK)){
            if (monotonic_us() >= deadline) { stats_add_u64(&s->write_errors,&s->lock,1); return -1; }
            stats_add_u64(&s->write_eagain,&s->lock,1); usleep(1000); continue;
        }
        stats_add_u64(&s->write_errors,&s->lock,1); return -1;
    }
    return off==n?0:-1;
}

static void update_transport_clock(struct clock_state *c, uint64_t packets) {
    pthread_mutex_lock(&c->lock);
    c->physical_packets = packets;
    c->transport_pcr90k = TRANSPORT_PCR_BASE + (packets * TRANSPORT_TICKS_NUM) / TRANSPORT_TICKS_DEN;
    pthread_mutex_unlock(&c->lock);
}

static void *writer_main(void *arg) {
    struct writer_ctx *w=(struct writer_ctx*)arg;
    uint8_t block[MOST_BLOCK_BYTES]; uint64_t packet_index=0;
    uint64_t epoch = monotonic_us();
    w->next_pat_packet=0; w->next_pmt_packet=1; w->next_pcr_packet=2;
    for (;;) {
        unsigned i;
        uint64_t due = epoch + (packet_index * TS_SIZE * 8ull * 1000000ull) / TRANSPORT_BPS;
        uint64_t now = monotonic_us();
        while (now < due) { usleep((unsigned)((due - now) > 1000u ? 1000u : due - now)); now = monotonic_us(); }
        if (now > due + TRANSPORT_LATE_LIMIT_US) {
            fprintf(stderr,"ERROR transport deadline exceeded late_us=%llu\n",(unsigned long long)(now-due));
            stats_add_u64(&w->stats->write_errors,&w->stats->lock,1); goto failed;
        }
        for(i=0;i<MOST_BLOCK_PACKETS;++i) {
            uint8_t *p=block+i*TS_SIZE;
            uint64_t pcr=TRANSPORT_PCR_BASE + (packet_index * TRANSPORT_TICKS_NUM) / TRANSPORT_TICKS_DEN;
            if(packet_index>=w->next_pat_packet){make_pat(p,&w->cc_pat);w->next_pat_packet+=PSI_INTERVAL_PACKETS;stats_add_u64(&w->stats->pat_packets,&w->stats->lock,1);}
            else if(packet_index>=w->next_pmt_packet){make_pmt(p,&w->cc_pmt);w->next_pmt_packet+=PSI_INTERVAL_PACKETS;stats_add_u64(&w->stats->pmt_packets,&w->stats->lock,1);}
            else if(packet_index>=w->next_pcr_packet){make_pcr_packet(p,pcr);w->next_pcr_packet+=PCR_INTERVAL_PACKETS;stats_add_u64(&w->stats->pcr_packets,&w->stats->lock,1);}
            else if(!queue_take_packet_at(w->queue,p,w->clock,pcr)){make_null_packet(p,&w->cc_null);stats_add_u64(&w->stats->null_packets,&w->stats->lock,1);}
            ++packet_index;
        }
        if(write_full(w->fd,block,sizeof(block),w->stats)!=0) goto failed;
        if (monotonic_us() > due + 7834u + TRANSPORT_LATE_LIMIT_US) {
            fprintf(stderr,"ERROR driver acceptance exceeded transport deadline\n");
            stats_add_u64(&w->stats->write_errors,&w->stats->lock,1); goto failed;
        }
        update_transport_clock(w->clock,packet_index);
        pthread_mutex_lock(&w->stats->lock); ++w->stats->blocks_written; w->stats->bytes_written+=MOST_BLOCK_BYTES; pthread_mutex_unlock(&w->stats->lock);
        /* EOF is acknowledged only after the writer-local block is committed. */
        if (queue_finished(w->queue)) break;
    }
    return NULL;
failed:
    g_stop=1; queue_stop(w->queue); shutdown(w->input_fd,SHUT_RDWR);
    return NULL;
}

static int parse_tcp_url(const char *url, struct sockaddr_in *sa) {
    const char *pfx="tcp://127.0.0.1:"; char *end=NULL; long port;
    if(strncmp(url,pfx,strlen(pfx))!=0)return -1;
    port=strtol(url+strlen(pfx),&end,10);
    if(!end||*end||port<1||port>65535)return -1;
    memset(sa,0,sizeof(*sa));sa->sin_family=AF_INET;sa->sin_port=htons((uint16_t)port);sa->sin_addr.s_addr=htonl(INADDR_LOOPBACK);return 0;
}

static int connect_input(const char *url) {
    struct sockaddr_in sa; int fd,attempt;
    if(parse_tcp_url(url,&sa)!=0)return -1;
    for(attempt=0;attempt<30&&!g_stop;++attempt){
        fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)return -1;
        if(connect(fd,(struct sockaddr*)&sa,sizeof(sa))==0)return fd;
        close(fd);sleep(1);
    }
    return -1;
}

static int recv_exact(int fd, void *buf, size_t n) {
    uint8_t *p=(uint8_t*)buf; size_t off=0;
    while(off<n&&!g_stop){ssize_t r=recv(fd,p+off,n-off,0);if(r>0){off+=(size_t)r;continue;}if(r==0)return off ? -1 : 0;if(errno==EINTR)continue;if(errno==EAGAIN||errno==EWOULDBLOCK){usleep(5000);continue;}return -1;}
    return off==n?1:-1;
}

static void request_keyframe(void) {
    int fd=open(KEYFRAME_MARKER,O_WRONLY|O_CREAT|O_TRUNC,0644);if(fd>=0)close(fd);
}

static int driver_init(int fd, int regular_file, struct bridge_stats *s) {
#ifdef __QNXNTO__
    uint32_t value=0, packets=MOST_BLOCK_PACKETS;
    int irc, prc, brc, frc, src;
    if(regular_file)return 0;

    value=0;
    irc=devctl(fd,DRIVER_DCMD_GET_INTERFACE,&value,sizeof(value),NULL);
    pthread_mutex_lock(&s->lock); s->driver_interface_rc=irc; s->driver_interface_value=value; pthread_mutex_unlock(&s->lock);
    fprintf(stderr,"PARITY_DRIVER interface status=%d value=%u\n",irc,value);

    value=0;
    prc=devctl(fd,DRIVER_DCMD_GET_PACKET_SIZE,&value,sizeof(value),NULL);
    pthread_mutex_lock(&s->lock); s->driver_packet_size_rc=prc; s->driver_packet_size_value=value; pthread_mutex_unlock(&s->lock);
    fprintf(stderr,"PARITY_DRIVER packet_size status=%d value=%u\n",prc,value);

    value=0;
    brc=devctl(fd,DRIVER_DCMD_GET_BLOCK_COUNT,&value,sizeof(value),NULL);
    pthread_mutex_lock(&s->lock); s->driver_block_count_rc=brc; s->driver_block_count_value=value; pthread_mutex_unlock(&s->lock);
    fprintf(stderr,"PARITY_DRIVER block_count status=%d value=%u\n",brc,value);

    frc=devctl(fd,DRIVER_DCMD_FLUSH,NULL,0,NULL);
    pthread_mutex_lock(&s->lock); s->driver_flush_rc=frc; pthread_mutex_unlock(&s->lock);
    fprintf(stderr,"PARITY_DRIVER queue_flush status=%d\n",frc);

    src=devctl(fd,DRIVER_DCMD_START,&packets,sizeof(packets),NULL);
    pthread_mutex_lock(&s->lock); s->driver_start_rc=src; pthread_mutex_unlock(&s->lock);
    fprintf(stderr,"PARITY_DRIVER start status=%d packets=%u\n",src,packets);
    if(irc!=0 || prc!=0 || brc!=0 || frc!=0 || src!=0)return -1;
#else
    (void)fd; (void)regular_file; (void)s;
#endif
    return 0;
}

static int host_self_test(void) {
    uint64_t d;
    uint8_t pat[TS_SIZE],pmt[TS_SIZE],pcr[TS_SIZE],cc=0;
    uint8_t au[]={0,0,0,1,0x65,0x88,0x84};
    uint8_t *pkts=NULL;size_t n=0;uint8_t ccv=0;
    struct clock_state c; int rb=0; uint64_t p1,p2;
    struct au_queue tq;
    struct ts_au qa,qb;
    uint8_t one[TS_SIZE];
    uint64_t da=0,dp=0,pp=0;
    d=source_delta_90k(0,100,0x40000000u,100);if(d!=22500u){fprintf(stderr,"SELFTEST delta quarter=%llu\n",(unsigned long long)d);return 1;}
    d=source_delta_90k(0xc0000000u,100,0x40000000u,101);if(d!=45000u){fprintf(stderr,"SELFTEST borrow=%llu\n",(unsigned long long)d);return 2;}
    if(((uint64_t)MOST_BLOCK_BYTES*8u*90000u)/TRANSPORT_BPS!=705u){fprintf(stderr,"SELFTEST transport\n");return 3;}
    make_pat(pat,&cc); if(pat[0]!=0x47||(((pat[1]&0x1f)<<8)|pat[2])!=PID_PAT)return 4;
    cc=0;make_pmt(pmt,&cc);if(pmt[0]!=0x47||(((pmt[1]&0x1f)<<8)|pmt[2])!=PID_PMT)return 5;
    make_pcr_packet(pcr,45000);if(pcr[0]!=0x47||(((pcr[1]&0x1f)<<8)|pcr[2])!=PID_PCR||pcr[3]!=0x20)return 6;
    if(packetize_pes(au,sizeof(au),54000,1,1,&ccv,&pkts,&n)!=0||!n)return 7;
    if(pkts[0]!=0x47||!(pkts[1]&0x40)||(((pkts[1]&0x1f)<<8)|pkts[2])!=PID_VIDEO){free(pkts);return 8;}
    free(pkts);
    memset(&c,0,sizeof(c)); pthread_mutex_init(&c.lock,NULL); c.transport_pcr90k=45000;
    p1=assign_pts(&c,0x80000000u,100,&rb); if(p1!=54000u)return 9;
    c.transport_pcr90k=45705; p2=assign_pts(&c,0xc0000000u,100,&rb); if(p2-p1!=22500u)return 10;
    c.transport_pcr90k=90000; p2=assign_pts(&c,0x10000000u,99,&rb); if(!rb && c.source_rebases==0)return 11;
    pthread_mutex_destroy(&c.lock);

    memset(&qa,0,sizeof(qa)); memset(&qb,0,sizeof(qb)); queue_init(&tq);
    qa.packet_count=4u; qa.packets=(uint8_t*)calloc(qa.packet_count,TS_SIZE);
    qb.packet_count=3u; qb.packets=(uint8_t*)calloc(qb.packet_count,TS_SIZE);
    if(!qa.packets || !qb.packets){ free(qa.packets); free(qb.packets); queue_destroy(&tq); return 12; }
    if(queue_push(&tq,&qa)!=0 || queue_push(&tq,&qb)!=0){ free(qa.packets); free(qb.packets); queue_destroy(&tq); return 13; }
    if(!queue_take_packet(&tq,one)){ queue_destroy(&tq); return 14; }
    queue_recover_au_boundary(&tq,&da,&dp,&pp);
    if(tq.count!=1u || tq.packets_queued!=3u || da!=1u || dp!=3u || pp!=3u){ queue_destroy(&tq); return 15; }
    queue_destroy(&tq);

    fprintf(stdout,"PARITY_SELFTEST=PASS\n");return 0;
}

int main(int argc,char **argv) {
    const char *input,*output;int in_fd=-1,out_fd=-1,regular_file=0,rc=1;
    struct stat st;pthread_t writer;int writer_started=0;
    struct au_queue queue;struct clock_state clock;struct bridge_stats stats;struct writer_ctx wctx;
    uint8_t *param_cache=NULL;size_t param_cache_n=0;uint64_t prev_seq=0;
    uint64_t prev_stream=0,prev_codec=0,prev_consumer=0;
    int waiting_idr=1;int discontinuity=1;
    uint8_t cc_video=0;

    if(argc==2 && !strcmp(argv[1],"--self-test"))return host_self_test();
    if(argc!=3){fprintf(stderr,"usage: %s tcp://127.0.0.1:PORT OUTPUT\n",argv[0]);return 64;}
    input=argv[1];output=argv[2];
    signal(SIGINT,on_signal);signal(SIGTERM,on_signal);signal(SIGHUP,on_signal);
    memset(&clock,0,sizeof(clock));pthread_mutex_init(&clock.lock,NULL);clock.transport_pcr90k=TRANSPORT_PCR_BASE;
    memset(&stats,0,sizeof(stats));pthread_mutex_init(&stats.lock,NULL);stats.waiting_idr=1;
    queue_init(&queue);
    if (!strncmp(output, "/dev/", 5)) out_fd=open(output,O_WRONLY|O_NONBLOCK);
    else out_fd=open(output,O_WRONLY|O_CREAT|O_TRUNC,0644);
    if(out_fd<0){perror("open output");goto done;}
    if(fstat(out_fd,&st)==0 && S_ISREG(st.st_mode))regular_file=1;
    if(driver_init(out_fd,regular_file,&stats)!=0){fprintf(stderr,"ERROR driver start failed errno=%d\n",errno);goto done;}
    in_fd=connect_input(input);if(in_fd<0){fprintf(stderr,"ERROR cannot connect input %s\n",input);goto done;}
    {
        struct timeval tv; tv.tv_sec=0; tv.tv_usec=100000;
        if(setsockopt(in_fd,SOL_SOCKET,SO_RCVTIMEO,&tv,sizeof(tv))!=0){perror("input timeout");goto done;}
    }
    memset(&wctx,0,sizeof(wctx));wctx.fd=out_fd;wctx.input_fd=in_fd;wctx.regular_file=regular_file;wctx.queue=&queue;wctx.clock=&clock;wctx.stats=&stats;
    if(pthread_create(&writer,NULL,writer_main,&wctx)!=0){fprintf(stderr,"ERROR writer thread\n");goto done;}writer_started=1;
    request_keyframe();
    publish_status(&stats,&clock,&queue,"running");
    fprintf(stderr,"PARITY_START input=%s output=%s transport_bps=%u block=%u pids=pat:0x0,pmt:0x10,pcr:0x1000,video:0x11\n",input,output,TRANSPORT_BPS,MOST_BLOCK_BYTES);

    while(!g_stop){
        uint8_t h[M1AU_HEADER_BYTES];uint32_t flags,payload_n,frac,sec;uint64_t stream,codec,consumer,seq,pts;uint8_t *payload=NULL,*norm=NULL,*packets=NULL;size_t norm_n=0,packet_count=0;int rr,idr,rebased=0;struct ts_au au;
        rr=recv_exact(in_fd,h,sizeof(h));if(rr<=0){if(rr==0&&!g_stop)rc=0;break;}
        if(memcmp(h,"M1AU",4)||be16(h+4)!=1u||be16(h+6)!=M1AU_HEADER_BYTES){fprintf(stderr,"ERROR invalid M1AU header\n");break;}
        flags=be32(h+8);payload_n=be32(h+12);stream=be64(h+16);codec=be64(h+24);consumer=be64(h+32);seq=be64(h+40);frac=le32(h+48);sec=le32(h+52);idr=(flags&M1AU_FLAG_IDR)?1:0;
        if(!payload_n||payload_n>M1AU_MAX_PAYLOAD){fprintf(stderr,"ERROR invalid M1AU payload=%u\n",payload_n);break;}
        payload=(uint8_t*)malloc(payload_n);if(!payload)break;
        rr=recv_exact(in_fd,payload,payload_n);if(rr<=0){free(payload);break;}
        if(payload_n>REFERENCE_PRODUCER_PAYLOAD_LIMIT) {
            free(payload); waiting_idr=1; discontinuity=1; request_keyframe();
            fprintf(stderr,"PARITY_DROP oversized AU bytes=%u\n",payload_n);
            continue;
        }
        pthread_mutex_lock(&stats.lock);++stats.input_records;stats.input_bytes+=payload_n;stats.input_idrs+=idr;stats.last_sequence=seq;stats.last_frac=frac;stats.last_sec=sec;pthread_mutex_unlock(&stats.lock);
        if ((prev_stream && stream != prev_stream) || (prev_codec && codec != prev_codec) ||
            (prev_consumer && consumer != prev_consumer)) {
            uint64_t da=0,dp=0,pp=0;
            queue_recover_au_boundary(&queue,&da,&dp,&pp);
            record_safe_recovery(&stats,"generation",da,dp,pp);
            pthread_mutex_lock(&clock.lock); clock.have_origin=0; clock.have_previous_source=0; ++clock.source_rebases; pthread_mutex_unlock(&clock.lock);
            free(param_cache); param_cache=NULL; param_cache_n=0;
            prev_seq=0;
            waiting_idr=1; discontinuity=1; request_keyframe();
            pthread_mutex_lock(&stats.lock); stats.waiting_idr=1; pthread_mutex_unlock(&stats.lock);
        }
        prev_stream=stream; prev_codec=codec; prev_consumer=consumer;
        if(prev_seq && seq!=prev_seq+1u){
            uint64_t da=0,dp=0,pp=0;
            pthread_mutex_lock(&stats.lock);++stats.sequence_gaps;stats.waiting_idr=1;pthread_mutex_unlock(&stats.lock);
            queue_recover_au_boundary(&queue,&da,&dp,&pp);
            record_safe_recovery(&stats,"sequence",da,dp,pp);
            waiting_idr=1;discontinuity=1;request_keyframe();
        }
        prev_seq=seq;
        if(!waiting_idr && queue_packet_depth(&queue)>LOW_LATENCY_PACKET_LIMIT) {
            uint64_t da=0,dp=0,pp=0;
            queue_recover_au_boundary(&queue,&da,&dp,&pp);
            record_safe_recovery(&stats,"latency",da,dp,pp);
            waiting_idr=1;discontinuity=1;request_keyframe();
            pthread_mutex_lock(&stats.lock);stats.waiting_idr=1;pthread_mutex_unlock(&stats.lock);
        }
        /* Periodic reference requests are made in GEN2 before consumer/drop
         * decisions. This bridge requests only startup/gap/latency recovery. */
        if(waiting_idr&&!idr){pthread_mutex_lock(&stats.lock);++stats.dropped_wait_idr;pthread_mutex_unlock(&stats.lock);free(payload);publish_status(&stats,&clock,&queue,"waiting_idr");continue;}
        if(idr&&waiting_idr){waiting_idr=0;pthread_mutex_lock(&stats.lock);stats.waiting_idr=0;pthread_mutex_unlock(&stats.lock);}
        if(normalize_au(payload,payload_n,idr,&param_cache,&param_cache_n,&norm,&norm_n)!=0){free(payload);break;}free(payload);
        pts=assign_pts(&clock,frac,sec,&rebased);
        if(packetize_pes(norm,norm_n,pts,idr,discontinuity,&cc_video,&packets,&packet_count)!=0){free(norm);break;}free(norm);discontinuity=0;
        memset(&au,0,sizeof(au));au.packets=packets;au.packet_count=packet_count;au.sequence=seq;au.pts90k=pts;au.idr=idr;
        if(queue_push(&queue,&au)!=0){free(au.packets);break;}
        pthread_mutex_lock(&stats.lock);++stats.aus_queued;stats.pes_packets+=packet_count;stats.last_pts=pts;pthread_mutex_unlock(&stats.lock);
        if(rebased)fprintf(stderr,"PARITY_PTS_REBASE seq=%llu pcr=%llu pts=%llu\n",(unsigned long long)seq,(unsigned long long)clock_pcr_now(&clock),(unsigned long long)pts);
        publish_status(&stats,&clock,&queue,"running");
    }
    /* A clean input EOF must not discard complete AUs that are already queued.
     * Drain the AU/PES queue before stopping the continuous writer. */
    if (!g_stop && queue_wait_empty(&queue, 10000u) != 0) {
        fprintf(stderr,"ERROR graceful queue drain timeout\n");
        rc=1;
    }

done:
    if (g_stop && rc==0) rc=130;
    if (rc!=0) queue_recover_au_boundary(&queue,NULL,NULL,NULL);
    pthread_mutex_lock(&queue.lock); queue.input_done=1; pthread_mutex_unlock(&queue.lock);
    g_stop=1;
    queue_stop(&queue);
    if(writer_started)pthread_join(writer,NULL);
    if(stats.write_errors)rc=1;
    publish_status(&stats,&clock,&queue,rc==0?"done":"error");
    if(in_fd>=0)close(in_fd);
    if(out_fd>=0)close(out_fd);
    free(param_cache);
    queue_destroy(&queue);
    pthread_mutex_destroy(&clock.lock);
    pthread_mutex_destroy(&stats.lock);
    unlink(KEYFRAME_MARKER);
    fprintf(stderr,"PARITY_DONE rc=%d\n",rc);
    return rc;
}
