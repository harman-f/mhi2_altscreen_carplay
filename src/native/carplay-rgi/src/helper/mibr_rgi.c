/* SPDX-License-Identifier: GPL-3.0-or-later
 * mibr-rgi: route guidance helper for MU1440.
 *
 * Started next to mm-ipod by the mm-ipod-rgi wrapper (its parent is mm-ipod after the exec) and
 * ends when mm-ipod ends. It owns nothing of the iAP2 link:
 *  - the HMI says with WANT_FILE ("1") whether the user's "CarPlay-Navigation" is on and the
 *    cockpit shows CarPlay. While it is wanted and the mm-ipod library offered group 30
 *    (READY_FILE), the helper opens a short-lived client on /dev/ipod0 and sends
 *    StartRouteGuidanceUpdates (0x5200) with iap2_raw_msg_send, retrying every 2 s (10x), then
 *    every 30 s, until the first 0x52xx arrives. When it is no longer wanted it sends
 *    StopRouteGuidanceUpdates (0x5203) once and clears the guidance;
 *  - it follows the driver log /dev/shmem/iap2.log, decodes 0x5201/0x5202/0x5204 with the
 *    vendored luka-dev parser, merges them and writes the snapshot GUIDANCE for the HMI (one
 *    buffer in one write: renaming fails on /dev/shmem, and the reader checks the first and last
 *    line; heartbeat every second), plus one log line per message to OUT_LOG.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

#include "mibr_rgi_guidance.h"
#include "mibr_rgi_wire.h"
#include "routeguidance/rgd_tlv.h"

#define ENABLE_FILE "/mnt/app/root/mibr-rgi/rgi.on"
#define READY_FILE  "/dev/shmem/mibr-rgi-ready"
#define WANT_FILE   "/dev/shmem/mibr-rgi.want"
#define GUIDANCE    "/dev/shmem/mibr-rgi.guidance"
#define IAP2_LOG    "/dev/shmem/iap2.log"
#define IAP2_DEVICE "/dev/ipod0"
#define OUT_LOG     "/tmp/mibr-rgi.log"
#define OUT_STATE   "/tmp/mibr-rgi.state"
#define OUT_LOG_MAX (512 * 1024)

void *iap2_connect(const char *path, int flags);
int iap2_disconnect(void *dev);
int iap2_raw_msg_send(void *dev, const void *buf, size_t len);

struct helper {
    struct mibr_rgi_scan scan;
    unsigned updates, maneuvers, lanes, garbled;
    int wanted;
    struct mibr_rgi_guidance g;
};

static void out(const char *fmt, ...)
{
    struct stat st;
    va_list ap;
    FILE *f;

    if (stat(OUT_LOG, &st) == 0 && st.st_size > OUT_LOG_MAX) {
        (void)unlink(OUT_LOG);
    }
    f = fopen(OUT_LOG, "a");
    if (!f) {
        return;
    }
    fprintf(f, "%ld ", (long)time(NULL));
    va_start(ap, fmt);
    vfprintf(f, fmt, ap);
    va_end(ap);
    fputc('\n', f);
    fclose(f);
}

static void write_state(const struct helper *h)
{
    FILE *f = fopen(OUT_STATE, "w");

    if (!f) {
        return;
    }
    fprintf(f, "updates=%u\nmaneuvers=%u\nlanes=%u\ngarbled=%u\n", h->updates, h->maneuvers, h->lanes,
            h->garbled);
    fprintf(f, "wanted=%d\nroute_state=%u\nmaneuver_state=%u\nroad=%s\ndestination=%s\n"
               "distance_remaining=%u\ndistance_to_maneuver=%u\n",
            h->wanted, h->g.route_state, h->g.maneuver_state, h->g.road, h->g.destination,
            (unsigned)h->g.distance_remaining, (unsigned)h->g.dist_to_maneuver);
    fclose(f);
}

static void on_message(void *ctx, const uint8_t *msg, size_t len)
{
    struct helper *h = ctx;
    unsigned id = (unsigned)(msg[4] << 8 | msg[5]);

    if (id == MIBR_RGI_MSG_UPDATE) {
        rgd_update_t u;

        if (!rgd_parse_update(msg, len, &u) || !u.present) {
            h->garbled++;
            return;
        }
        h->updates++;
        out("5201 state=%u man_state=%u road=\"%s\" dest=\"%s\" dist_rem=%u dist_man=%u list=%u",
            (unsigned)u.route_state, (unsigned)u.maneuver_state, u.current_road, u.destination,
            (unsigned)u.distance_remaining, (unsigned)u.dist_to_maneuver, (unsigned)u.maneuver_list_count);
        mibr_rgi_guidance_update(&h->g, &u);
    } else if (id == MIBR_RGI_MSG_MANEUVER) {
        rgd_maneuver_t m;

        if (!rgd_parse_maneuver(msg, len, &m) || !m.present) {
            h->garbled++;
            return;
        }
        h->maneuvers++;
        out("5202 index=%u type=%u after=\"%s\" dist=%u side=%u junction=%u exit_angle=%d",
            (unsigned)m.index, (unsigned)m.maneuver_type, m.after_road_name, (unsigned)m.distance_between,
            (unsigned)m.driving_side, (unsigned)m.junction_type, (int)m.exit_angle);
        mibr_rgi_guidance_maneuver(&h->g, &m);
    } else if (id == MIBR_RGI_MSG_LANES) {
        rgd_lane_guidance_t l;

        if (!rgd_parse_lane_guidance(msg, len, &l) || !l.present) {
            h->garbled++;
            return;
        }
        h->lanes++;
        out("5204 index=%u lanes=%u complete=%u", (unsigned)l.lane_guidance_index, (unsigned)l.lane_count,
            (unsigned)l.lane_complete);
        mibr_rgi_guidance_lanes(&h->g, &l);
    } else {
        out("%04x len=%u (not decoded)", id, (unsigned)len);
    }
}

static int send_control(int start)
{
    uint8_t msg[32];
    size_t n = start ? mibr_rgi_start_message(msg, sizeof(msg)) : mibr_rgi_stop_message(msg, sizeof(msg));
    /* Flags 0 as iap2cli and dio_manager: /dev/ipod0 is a read-only directory, O_RDWR fails with EINVAL. */
    void *dev = iap2_connect(IAP2_DEVICE, 0);
    int rc, err;

    if (!dev) {
        return -errno;
    }
    rc = iap2_raw_msg_send(dev, msg, n);
    err = errno;
    iap2_disconnect(dev);
    return rc < 0 ? -err : 0;
}

static unsigned long now_ms(void)
{
    struct timespec t;

    clock_gettime(CLOCK_MONOTONIC, &t);
    return (unsigned long)t.tv_sec * 1000ul + (unsigned long)(t.tv_nsec / 1000000l);
}

static int wanted(void)
{
    char c = '0';
    int fd = open(WANT_FILE, O_RDONLY);

    if (fd < 0) {
        return 0;
    }
    if (read(fd, &c, 1) != 1) {
        c = '0';
    }
    close(fd);
    return c == '1';
}

static void write_guidance(const struct helper *h, int receiving, unsigned long heartbeat)
{
    static char text[4096];
    size_t n = mibr_rgi_guidance_text(&h->g, receiving, heartbeat, text, sizeof(text));
    int fd;

    if (!n) {
        return;
    }
    fd = open(GUIDANCE, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd < 0) {
        return;
    }
    (void)write(fd, text, n);
    close(fd);
}

int main(void)
{
    static struct helper h;
    static char chunk[4096];
    pid_t parent = getppid();
    off_t offset = 0;
    unsigned attempts = 0, written_seq = ~0u;
    unsigned long last_send = 0, last_state = 0;
    int received = 0, fd;
    time_t ident_time = 0;
    struct stat st;

    if (access(ENABLE_FILE, F_OK) != 0) {
        return 0;
    }
    mibr_rgi_scan_reset(&h.scan);
    mibr_rgi_guidance_reset(&h.g);
    /* Start reading at the current end: older 0x52xx belong to an earlier connection. */
    if (stat(IAP2_LOG, &st) == 0) {
        offset = st.st_size;
    }
    out("helper started (parent %d)", (int)parent);
    while (getppid() == parent && access(ENABLE_FILE, F_OK) == 0) {
        unsigned long now = now_ms();
        int want = wanted();

        /* Every Identification rewrites READY_FILE: a new connection needs a new start. */
        if (stat(READY_FILE, &st) == 0 && st.st_mtime != ident_time) {
            if (ident_time) {
                out("new identification: route guidance restarts");
            }
            ident_time = st.st_mtime;
            attempts = 0;
            last_send = 0;
            received = 0;
            mibr_rgi_guidance_reset(&h.g);
        }
        if (want != h.wanted) {
            out("CarPlay-Navigation %s by the HMI", want ? "wanted" : "not wanted");
            if (!want && (received || attempts)) {
                int rc = send_control(0);

                out("0x5203 stop: %s (%d)", rc == 0 ? "sent" : "failed", rc);
            }
            h.wanted = want;
            attempts = 0;
            last_send = 0;
            received = 0;
            mibr_rgi_guidance_reset(&h.g);
        }
        fd = open(IAP2_LOG, O_RDONLY);
        if (fd >= 0) {
            off_t end = lseek(fd, 0, SEEK_END);
            ssize_t n;

            if (end < offset) {
                offset = 0; /* log restarted */
                mibr_rgi_scan_reset(&h.scan);
            }
            lseek(fd, offset, SEEK_SET);
            while ((n = read(fd, chunk, sizeof(chunk))) > 0) {
                unsigned before = h.updates + h.maneuvers + h.lanes;

                if (h.wanted) {
                    mibr_rgi_scan_feed(&h.scan, chunk, (size_t)n, on_message, &h);
                }
                if (!received && h.updates + h.maneuvers + h.lanes != before) {
                    received = 1;
                    out("first route guidance message received after %u start attempt(s)", attempts);
                }
                offset += n;
            }
            close(fd);
        }
        if (h.wanted && !received && access(READY_FILE, F_OK) == 0 &&
            (!last_send || now - last_send >= (attempts < 10 ? 2000ul : 30000ul))) {
            int rc = send_control(1);

            last_send = now;
            attempts++;
            if (attempts <= 3 || attempts == 10 || rc == 0) {
                out("0x5200 attempt %u: %s (%d)", attempts, rc == 0 ? "sent" : "failed", rc);
            }
        }
        if (h.g.seq != written_seq || now - last_state >= 1000ul) {
            write_guidance(&h, received, now / 1000ul);
            written_seq = h.g.seq;
        }
        if (now - last_state >= 1000ul) {
            write_state(&h);
            last_state = now;
        }
        usleep(200000);
    }
    if (h.wanted && (received || attempts)) {
        (void)send_control(0);
    }
    mibr_rgi_guidance_reset(&h.g);
    write_guidance(&h, 0, now_ms() / 1000ul);
    write_state(&h);
    out("helper stopped");
    return 0;
}
