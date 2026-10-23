/* SPDX-License-Identifier: GPL-3.0-or-later
 * Interposer for the HARMAN iAP2 client call the stock DIO worker uses for every NMEA sentence
 * (libiap2client.so.1: iap2_gps_data_send(handle, NUL-terminated NMEA), QNX command 0x2700).
 * It lives in the library that is already LD_PRELOADed into dio_manager (smartphone_integrator.json),
 * so there is no second process, no second iAP2 connection and no foreign thread: every original call
 * is forwarded unchanged first, and the optional $PASCD sentence is sent from the SAME call with the
 * SAME handle. Any failure of the extension falls back to pure pass-through.
 * Project-authored hook adapter; optional producers remain controlled by existing mode files.
 */
#define _POSIX_C_SOURCE 200809L
#include "mibr_vdata.h"
#include "mibr_vstatus.h"
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>

#define VDATA_MODE_FILE   "/mnt/app/root/altscreen-u2/config/vdata.mode"
#define VDATA_SOURCE_FILE "/tmp/mibr-vdata-speed.ring"
#define VDATA_STATUS_FILE "/tmp/mibr-vdata.status"
#define VSTATUS_MODE_FILE   "/mnt/app/root/altscreen-u2/config/vstatus.mode"
#define VSTATUS_SOURCE_FILE "/tmp/mibr-vdata-status.vss"
#define VSTATUS_STATUS_FILE "/tmp/mibr-vstatus.status"

typedef int (*gps_send_fn)(void *, const char *);
static gps_send_fn g_real;
static int g_resolved;
static struct vdata g_vdata;
static int g_vdata_ready;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static struct vstatus g_vstatus;
static struct vstatus_api g_vapi;
static int g_vapi_resolved;
static uint64_t g_vstatus_written_ms;

/* HARMAN client + libstrm entry points (both already loaded in dio_manager); a missing one disables the update. */
static void resolve_vapi(void) {
    void *u, *n, *st, *d;
    if (g_vapi_resolved) return;
    g_vapi_resolved = 1;
    u = dlsym(RTLD_DEFAULT, "iap2_vehicle_update");
    n = dlsym(RTLD_DEFAULT, "strm_dict_new");
    st = dlsym(RTLD_DEFAULT, "strm_dict_set");
    d = dlsym(RTLD_DEFAULT, "strm_dict_destroy");
    if (u && n && st && d) {
        g_vapi.update = (int (*)(void *, void *))u;
        g_vapi.dict_new = (void *(*)(void))n;
        g_vapi.dict_set = (void *(*)(void *, const char *, const char *))st;
        g_vapi.dict_destroy = (void (*)(void *))d;
    }
}

static void vstatus_status_tick(uint64_t now) {
    FILE *f;
    char text[512];
    if (g_vstatus_written_ms && now - g_vstatus_written_ms < 5000ull) return;
    g_vstatus_written_ms = now ? now : 1u;
    (void)vstatus_format(&g_vstatus, text, sizeof(text));
    f = fopen(VSTATUS_STATUS_FILE, "w");
    if (!f) return;
    (void)fprintf(f, "%sapi_resolved=%d\n", text, g_vapi.update != NULL);
    (void)fclose(f);
}

static uint64_t clock_mono_ms(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec * 1000ull + (uint64_t)(t.tv_nsec / 1000000L);
}

static int clock_file_age_ms(const char *path, uint64_t *age) {
    struct stat st;
    struct timespec now;
    long long d;
    if (stat(path, &st) || !age) return -1;
    if (clock_gettime(CLOCK_REALTIME, &now)) return -1;
    d = ((long long)now.tv_sec - (long long)st.st_mtime) * 1000LL;
    if (d < 0) d = 0;                         /* wall clock stepped: treat as fresh, ingest still checks the sequence */
    *age = (uint64_t)d;
    return 0;
}

static const struct vdata_clock g_clock = { clock_mono_ms, clock_file_age_ms };

static gps_send_fn resolve_real(void) {
    if (!g_resolved) {
        void *p = dlsym(RTLD_NEXT, "iap2_gps_data_send");
        if (!p) {
            void *h = dlopen("libiap2client.so.1", RTLD_LAZY | RTLD_NOLOAD);
            if (h) p = dlsym(h, "iap2_gps_data_send");
        }
        g_real = (gps_send_fn)p;
        g_resolved = 1;
    }
    return g_real;
}

int iap2_gps_data_send(void *handle, const char *nmea) {
    gps_send_fn real = resolve_real();
    char extra[MVS_SENTENCE_BYTES + 1];
    int rc, len = 0, locked = 0;
    if (!real) return -1;                     /* cannot happen while the client library is loaded */
    if (nmea && pthread_mutex_trylock(&g_lock) == 0) {
        locked = 1;
        if (!g_vdata_ready) {
            vdata_init(&g_vdata, VDATA_MODE_FILE, VDATA_SOURCE_FILE, VDATA_STATUS_FILE);
            vstatus_init(&g_vstatus, VSTATUS_MODE_FILE, VSTATUS_SOURCE_FILE);
            resolve_vapi();
            g_vdata_ready = 1;
        }
        vdata_observe_stock(&g_vdata, nmea, &g_clock);
    }
    rc = real(handle, nmea);                  /* the original sentence always goes out first, unchanged */
    if (locked) {
        len = vdata_next_sentence(&g_vdata, &g_clock, extra, sizeof(extra));
        if (len > 0) {
            (void)real(handle, extra);        /* same worker, same handle; the driver filters unrequested types */
            vdata_note_sent(&g_vdata);
        }
        /* VehicleStatus (range/outside temperature/range warning): same worker, same handle, never before the
         * original sentence. The driver drops it unless Identify advertised it and the phone requested it. */
        (void)vstatus_poll(&g_vstatus, &g_clock, handle, &g_vapi);
        vstatus_status_tick(clock_mono_ms());
        (void)pthread_mutex_unlock(&g_lock);
    }
    return rc;
}
