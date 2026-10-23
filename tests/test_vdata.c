/* Host test for the vehicle-data core (mibr_vdata.c + R0 mvs_core.c). No hook, no OS interposition. */
#include "../src/native/vehicle-data/mibr_vdata.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); exit(1); } } while (0)

static uint64_t g_now = 100000;
static uint64_t g_age = 100;
static int g_file_present = 1;
static uint64_t mono(void) { return g_now; }
static int file_age(const char *p, uint64_t *a) { (void)p; if (!g_file_present) return -1; *a = g_age; return 0; }
static const struct vdata_clock CLK = { mono, file_age };

static const char *DIR_ = "vdata-test-tmp";
static char modep[200], srcp[200], statp[200];

static void write_file(const char *p, const void *d, size_t n) {
    FILE *f = fopen(p, "wb");
    CHECK(f);
    CHECK(fwrite(d, 1, n, f) == n);
    fclose(f);
}
static void set_mode(const char *m) { write_file(modep, m, strlen(m)); }
static void put_ring(const mvs_sample *s, unsigned n) {
    uint8_t buf[VDATA_RING_MAX * MVS_WIRE_BYTES];
    unsigned i;
    for (i = 0; i < n; i++) CHECK(mvs_wire_encode(&s[i], buf + i * MVS_WIRE_BYTES, MVS_WIRE_BYTES) == 0);
    write_file(srcp, buf, n * MVS_WIRE_BYTES);
}
static mvs_sample smp(uint64_t ms, uint32_t mmps, uint32_t seq) {
    mvs_sample s; memset(&s, 0, sizeof(s));
    s.sample_ms = ms; s.speed_mmps = mmps; s.source_seq = seq;
    s.flags = (uint8_t)(MVS_VALID_SPEED | MVS_GEAR_VALID | (mmps ? 0 : MVS_STANDSTILL));
    return s;
}

int main(void) {
    struct vdata v;
    char out[MVS_SENTENCE_BYTES + 1];
    mvs_sample ring[VDATA_RING_MAX];
    int len;
    unsigned i;
    snprintf(modep, sizeof(modep), "%s.mode", DIR_);
    snprintf(srcp, sizeof(srcp), "%s.ring", DIR_);
    snprintf(statp, sizeof(statp), "%s.status", DIR_);
    remove(modep); remove(srcp); remove(statp);

    vdata_init(&v, modep, srcp, statp);
    /* default OFF: stock classification works, nothing is produced */
    vdata_observe_stock(&v, "$GPGGA,000000.00,0000.0,N,00000.0,E,6,14,1.0,0.0,M,,M,,*00", &CLK);
    vdata_observe_stock(&v, "$GPRMC,000000.00,A,0000.0,N,00000.0,E,0.0,0.0,010100,,,E*00", &CLK);
    CHECK(v.calls == 2 && v.gga == 1 && v.rmc == 1 && v.mode == VDATA_OFF);
    CHECK(vdata_next_sentence(&v, &CLK, out, sizeof(out)) == 0 && v.src_reads == 0);

    /* shadow: computes, never returns a sentence */
    set_mode("shadow\n");
    g_now += 4000;                                         /* past the mode recheck interval */
    for (i = 0; i < 6; i++) ring[i] = smp(5000 + i * 200u, 10000u + i * 100u, 1u + i);
    put_ring(ring, 6);
    g_age = 120;
    vdata_observe_stock(&v, "$GPRMC,x", &CLK);
    CHECK(v.mode == VDATA_SHADOW);
    len = vdata_next_sentence(&v, &CLK, out, sizeof(out));
    CHECK(len == 0);
    CHECK(v.src_records == 6);
    CHECK(v.would_send == 1 && !strncmp(v.last_sentence, "$PASCD,", 7));
    CHECK(v.sent_requested == 0);

    /* send: only a NEW genuine event after the watermark produces output, nothing is replayed */
    set_mode("send\n");
    g_now += 4000;
    vdata_observe_stock(&v, "$GPRMC,x", &CLK);
    CHECK(v.mode == VDATA_SEND);
    for (i = 0; i < 6; i++) ring[i] = smp(9000 + i * 200u, 8000u, 10u + i);
    put_ring(ring, 6);
    g_age = 60;
    len = vdata_next_sentence(&v, &CLK, out, sizeof(out));
    CHECK(len > 12 && !strncmp(out, "$PASCD,", 7) && out[len - 3] == '*');
    {   /* validates through the R0 TLV builder: correct checksum and length */
        uint8_t tlv[256];
        CHECK(mvs_location_tlv(out, tlv, sizeof(tlv)) == (size_t)len + 5u);
    }
    CHECK(vdata_next_sentence(&v, &CLK, out, sizeof(out)) == 0);   /* same ring again: no replay */

    /* stale file: silence, counted */
    g_age = 3000;
    put_ring(ring, 6);
    CHECK(vdata_next_sentence(&v, &CLK, out, sizeof(out)) == 0 && v.src_stale >= 1);

    /* missing file */
    g_file_present = 0;
    CHECK(vdata_next_sentence(&v, &CLK, out, sizeof(out)) == 0 && v.src_missing >= 1);
    g_file_present = 1;

    /* corrupt ring (not a multiple of 24 bytes) is rejected, no output */
    g_age = 50;
    write_file(srcp, "MVS1garbage", 11);
    CHECK(vdata_next_sentence(&v, &CLK, out, sizeof(out)) == 0 && v.src_bad >= 1);

    /* a stock $PASCD latches: the extension stays silent for good */
    vdata_observe_stock(&v, "$PASCD,1.000,C,D,0,1,0.00,1.000*00", &CLK);
    CHECK(v.pascd_stock == 1 && v.eng.stock_pascd_seen);
    for (i = 0; i < 6; i++) ring[i] = smp(20000 + i * 200u, 7000u, 100u + i);
    put_ring(ring, 6);
    CHECK(vdata_next_sentence(&v, &CLK, out, sizeof(out)) == 0);

    /* status file contains counters but never an NMEA position */
    vdata_status_tick(&v, &CLK);
    g_now += 6000;
    vdata_status_tick(&v, &CLK);
    {
        char text[2048]; size_t n; FILE *f = fopen(statp, "rb");
        CHECK(f);
        n = fread(text, 1, sizeof(text) - 1, f); text[n] = 0; fclose(f);
        CHECK(strstr(text, "mode=send") && strstr(text, "stock_pascd_latched=1"));
        CHECK(!strstr(text, "0000.0") && !strstr(text, "00000.0"));
    }
    remove(modep); remove(srcp); remove(statp);
    printf("VDATA_CORE_HOST_PASS off/shadow/send, no replay, stale/missing/corrupt, stock PASCD latch, no positions in status\n");
    return 0;
}
