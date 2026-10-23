/* Host test for the VehicleStatus core with a mocked libstrm/HARMAN API. */
#include "../src/native/vehicle-data/mibr_vstatus.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(c) do { if (!(c)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #c); exit(1); } } while (0)

static uint64_t g_now = 100000, g_age = 1000;
static int g_present = 1;
static uint64_t mono(void) { return g_now; }
static int fage(const char *p, uint64_t *a) { (void)p; if (!g_present) return -1; *a = g_age; return 0; }
static const struct vdata_clock CLK = { mono, fage };

/* mock dictionary: a flat text buffer */
struct mdict { char text[256]; };
static struct mdict g_dicts[8];
static unsigned g_dict_used;
static unsigned g_destroyed, g_updates, g_fail_update;
static char g_last_text[256];
static void *g_last_handle_seen;
static void *d_new(void) { struct mdict *d = &g_dicts[g_dict_used++ % 8]; d->text[0] = 0; return d; }
static void *d_set(void *dd, const char *k, const char *v) {
    struct mdict *d = (struct mdict *)dd;
    size_t n = strlen(d->text);
    snprintf(d->text + n, sizeof(d->text) - n, "%s=%s;", k, v);
    return d;
}
static void d_destroy(void *dd) { (void)dd; g_destroyed++; }
static int upd(void *h, void *dd) {
    g_updates++; g_last_handle_seen = h;
    snprintf(g_last_text, sizeof(g_last_text), "%s", ((struct mdict *)dd)->text);
    return g_fail_update ? -1 : 0;
}
static const struct vstatus_api API = { d_new, d_set, d_destroy, upd };

static const char *DIR_ = "vstatus-test";
static char modep[100], srcp[100];
static void wr(const char *p, const char *t) { FILE *f = fopen(p, "w"); CHECK(f); fputs(t, f); fclose(f); }

int main(void) {
    struct vstatus s;
    int h1, h2;
    char line[512];
    snprintf(modep, sizeof(modep), "%s.mode", DIR_);
    snprintf(srcp, sizeof(srcp), "%s.src", DIR_);
    remove(modep); remove(srcp);
    vstatus_init(&s, modep, srcp);

    /* default off */
    wr(srcp, "range=350\noutsidetemp=12\nrangewarn=0\nseq=1\n");
    CHECK(vstatus_poll(&s, &CLK, &h1, &API) == 0 && s.polls == 0 && g_updates == 0);

    /* shadow: counts, never calls the driver */
    wr(modep, "shadow\n");
    g_now += 4000;
    CHECK(vstatus_poll(&s, &CLK, &h1, &API) == 0);
    CHECK(s.mode == VSTATUS_SHADOW && s.would_send == 1 && g_updates == 0);
    CHECK(strstr(s.last_dict, "range=350"));

    /* send: first update carries all three fields */
    wr(modep, "send\n");
    g_now += 4000;
    CHECK(vstatus_poll(&s, &CLK, &h1, &API) == 1);
    CHECK(g_updates == 1 && g_last_handle_seen == &h1);
    CHECK(strstr(g_last_text, "range=350;") && strstr(g_last_text, "outsidetemp=12;") && strstr(g_last_text, "rangewarn=false;"));
    CHECK(g_destroyed == 1);

    /* unchanged, within the refresh interval: nothing */
    g_now += 3000;
    CHECK(vstatus_poll(&s, &CLK, &h1, &API) == 0 && g_updates == 1);
    /* unchanged, after the refresh interval: resend */
    g_now += 8000;
    CHECK(vstatus_poll(&s, &CLK, &h1, &API) == 1 && g_updates == 2);
    /* a change goes out at once */
    wr(srcp, "range=340\noutsidetemp=12\nrangewarn=1\nseq=2\n");
    g_now += 1000;
    CHECK(vstatus_poll(&s, &CLK, &h1, &API) == 1 && strstr(g_last_text, "range=340;") && strstr(g_last_text, "rangewarn=true;"));
    /* a new handle (new phone session) resends immediately */
    g_now += 1000;
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 1 && g_last_handle_seen == &h2 && s.handle_changes == 1);

    /* partial data: absent fields are left out, never invented */
    wr(srcp, "range=300\nseq=3\n");
    g_now += 1000;
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 1);
    CHECK(strstr(g_last_text, "range=300;") && !strstr(g_last_text, "outsidetemp") && !strstr(g_last_text, "rangewarn"));

    /* stale file: silence */
    g_age = 100000;
    g_now += 20000;
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 0 && s.src_stale >= 1);
    g_age = 1000;

    /* missing / garbage / out of range */
    g_present = 0;
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 0 && s.src_missing >= 1);
    g_present = 1;
    wr(srcp, "range=99999\n");
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 0 && s.src_bad >= 1);
    wr(srcp, "weird\n");
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 0 && s.src_bad >= 2);
    wr(srcp, "outsidetemp=500\n");
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 0 && s.src_bad >= 3);

    /* driver refusal is counted, state not advanced */
    wr(srcp, "range=250\nseq=9\n");
    g_fail_update = 1;
    g_now += 1000;
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 0 && s.errors == 1);
    g_fail_update = 0;
    g_now += 1000;
    CHECK(vstatus_poll(&s, &CLK, &h2, &API) == 1);

    /* no handle: no call */
    wr(srcp, "range=200\nseq=10\n");
    g_now += 1000;
    {
        unsigned before = g_updates;
        CHECK(vstatus_poll(&s, &CLK, NULL, &API) == 0 && g_updates == before);
    }
    CHECK(vstatus_format(&s, line, sizeof(line)) > 20 && strstr(line, "vstatus_mode=send"));
    remove(modep); remove(srcp);
    printf("VSTATUS_CORE_HOST_PASS off/shadow/send, change+refresh+new handle, partial fields, stale/missing/garbage, driver error\n");
    return 0;
}
