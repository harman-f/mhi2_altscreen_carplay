/* SPDX-License-Identifier: GPL-3.0-or-later
 * Classic iAP2 VehicleStatus (0xA100/0xA101: range km, outside temperature, range warning) towards CarPlay.
 *
 * The HMI-side Java source writes a tiny key=value file with the latest genuine OEM values. This core turns it
 * into one HARMAN iap2_vehicle_update(handle, strm_dict) call that the interposer (mibr_vdata_hook.c) issues in
 * the SAME worker context as the stock NMEA send. The HARMAN driver filters: it only emits 0xA101 for the
 * fields advertised in the Identify ([vehicle] section of /etc/mm/iap2.cfg) and requested by the phone (0xA100);
 * otherwise it drops the update ("Apple device is not accepting Vehicle updates").
 * Never invents values: a field that is unknown or stale is left out; nothing is replayed after the file ages out.
 */
#ifndef MIBR_VSTATUS_H
#define MIBR_VSTATUS_H
#include <stddef.h>
#include <stdint.h>
#include "mibr_vdata.h"

#define VSTATUS_PATH_CAP 160u

enum vstatus_mode { VSTATUS_OFF = 0, VSTATUS_SHADOW = 1, VSTATUS_SEND = 2 };

/* libstrm dictionary + HARMAN client entry points, resolved by the hook (injected for tests). */
struct vstatus_api {
    void *(*dict_new)(void);
    void *(*dict_set)(void *dict, const char *key, const char *value);   /* returns the (possibly new) dict, NULL on error */
    void (*dict_destroy)(void *dict);
    int (*update)(void *handle, void *dict);                              /* 0 = ok, -1 = error */
};

struct vstatus {
    char mode_file[VSTATUS_PATH_CAP];
    char source_file[VSTATUS_PATH_CAP];
    enum vstatus_mode mode;
    uint64_t mode_checked_ms, last_send_ms;
    void *last_handle;
    int have_sent;
    int sent_range, sent_temp, sent_warn;          /* last values handed to the driver (-9999 = field was absent) */
    unsigned long polls, src_missing, src_stale, src_bad, would_send, sent, errors, handle_changes;
    char last_dict[96];                            /* human readable copy of the last dictionary, no secrets */
};

#define VSTATUS_ABSENT (-9999)

void vstatus_init(struct vstatus *s, const char *mode_file, const char *source_file);
/* Called after the stock NMEA send with the SAME handle. Returns 1 if an update was handed to the driver. */
int vstatus_poll(struct vstatus *s, const struct vdata_clock *clk, void *handle, const struct vstatus_api *api);
/* One line of counters for the status file. */
int vstatus_format(const struct vstatus *s, char *out, size_t cap);

#endif
