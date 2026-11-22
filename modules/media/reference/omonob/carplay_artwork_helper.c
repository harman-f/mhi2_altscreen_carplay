/*
 * carplay_artwork_helper - resident daemon that pulls the real CarPlay album cover.
 * =============================================================================
 * We are the MISSING CONSUMER of mm-ipod's artwork (PATCH_JOURNAL §17, on-car proven):
 * the JPEG is reassembled in mm-ipod, keyed by transfer-id, and only leaves when a client
 * PULLS it by id via the OEM iap2_filexfer_read() on /dev/ipod0. Nothing native pulls it,
 * so we do. No LD_PRELOAD, no interposition.
 *
 * LOOP (started on CarPlay connect, when /dev/ipod0 already exists):
 *   connect once (iap2_connect O_RDONLY + 0x9999 handshake, as a 2nd client - verified safe);
 *   poll /ramdisk/pps/iap2/nowplaying for MediaItemArtworkFileTransferIdentifier;
 *   when the id CHANGES to a new non-zero value: iap2_filexfer_read(id) -> if FF D8 JPEG,
 *     atomic-write /var/app/icab/tmp/cp_cover.jpg (.tmp + rename);
 *   exit cleanly when /dev/ipod0 disappears (CarPlay disconnected).
 *
 * SIMPLEST FORM (Phase 2): plain cp_cover.jpg, overwrite each new cover. No _N suffix, no jar
 * handshake yet - race hardening is deferred (Phase 5).
 *
 * SAFETY: read-only session; only writes the one cover file. Single instance via a lockfile.
 * No threads, no __sync (QNX loader rejects unresolved __sync_*). Verified pull recipe from §17.
 *
 * BUILD (QNX 6.5 VM): ntoarmv7-gcc -O2 -std=gnu99 carplay_artwork_helper.c -o carplay_artwork_helper \
 *                       -L<dir-with-libiap2client.so.1> -Wl,-rpath-link,<same> -liap2client
 * =============================================================================
 */

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>

/* Bundled codecs: MIT option, see vendor/PROVENANCE.md. Keep the historical
 * helper's 128x128 output; no claim that this determines the cluster resolution.
 * Bound input dimensions before decode to cap memory use on the head unit. */
#define STBI_MAX_DIMENSIONS 2048
#define STB_IMAGE_IMPLEMENTATION
#define STBI_ONLY_JPEG
#define STBI_NO_STDIO
#include "vendor/stb_image.h"
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "vendor/stb_image_write.h"

/* OEM client API (libiap2client.so.1) - prototypes derived from disassembly (no header). */
extern void   *iap2_connect(const char *path, int oflag);
extern int     iap2_filexfer_read(void *handle, int transfer_id, void *buf, int len);
extern void    iap2_disconnect(void *handle);

#define IPOD_DEV      "/dev/ipod0"
#define PPS_NOWPLAY   "/ramdisk/pps/iap2/nowplaying"
#ifndef COVER_OUT
#define COVER_OUT     "/ramdisk/cpmap-info/cp_cover.jpg"
#define COVER_TMP     "/ramdisk/cpmap-info/cp_cover.jpg.tmp"
/* Coordination for the jar (kills the cover-lag race): ACTIVE = heartbeat (mtime = daemon alive);
 * ID = the transfer-id that cp_cover.jpg currently holds (contents, overwritten - NOT per-id files). */
#define ACTIVE_PATH   "/ramdisk/cpmap-info/cp_cover.active"
#define ID_PATH       "/ramdisk/cpmap-info/cp_cover.id"
#define ID_TMP        "/ramdisk/cpmap-info/cp_cover.id.tmp"
#define LOCK_PATH     "/ramdisk/cpmap-info/artwork.lock"
#endif
#define ART_KEY       "MediaItemArtworkFileTransferIdentifier"
/* Track-signature keys. The signature written to ID_PATH must be byte-identical to CarplayBusListener.
 * trackSig(): bundleId\x01title\x01artist\x01album, each missing field empty. */
#define BUNDLE_KEY    "PlaybackAppBundleID"
#define TITLE_KEY     "MediaItemTitle"
#define ARTIST_KEY    "MediaItemArtist"
#define ALBUM_KEY     "MediaItemAlbumTitle"
#define ART_MAX       (1024 * 1024)
/* nowplaying can carry ~35 UTF-8 attributes incl. long titles; read generously so no field is truncated
 * past the buffer (an under-read would drop a field and corrupt the signature). */
#define PPS_BUF       (32 * 1024)
#define SIG_MAX       2048
#define COVER_DIM       128
#define JPEG_QUALITY    75
#define POLL_MS         250
#define RECONNECT_MS    1000
#define STARTUP_WAIT_MS 30000

static volatile sig_atomic_t g_stop;

static void on_sig(int sig) { (void) sig; g_stop = 1; }

static void cleanup_files(void)
{
    /* Do not unlink the lock inode: another process could otherwise lock a
     * replacement inode while this process still owns the original lock. */
    unlink(ACTIVE_PATH);
    unlink(ID_PATH);
    unlink(ID_TMP);
    unlink(COVER_OUT);
    unlink(COVER_TMP);
}

static void msleep(long ms)
{
    struct timespec ts;
    ts.tv_sec  = ms / 1000;
    ts.tv_nsec = (ms % 1000) * 1000000L;
    nanosleep(&ts, 0);
}

/* Kernel-held lock is released after a crash; no stale PID file blocks restart. */
static int take_lock(void)
{
    int fd = open(LOCK_PATH, O_WRONLY | O_CREAT, 0644);
    if (fd < 0) return -1;
    struct flock guard;
    memset(&guard, 0, sizeof(guard));
    guard.l_type = F_WRLCK;
    guard.l_whence = SEEK_SET;
    if (fcntl(fd, F_SETLK, &guard) < 0) { close(fd); return -1; }
    (void) ftruncate(fd, 0);
    char pid[16];
    int n = snprintf(pid, sizeof(pid), "%d\n", (int) getpid());
    (void) write(fd, pid, n);
    return fd;
}

/* /dev/ipod0 present only while CarPlay is active - its absence is our exit signal. */
static int ipod_present(void)
{
    struct stat st;
    return stat(IPOD_DEV, &st) == 0;
}

/* Read the whole nowplaying PPS object once into buf (NUL-terminated). Returns byte count, or -1. */
static int read_nowplaying(char *buf, size_t cap)
{
    int fd = open(PPS_NOWPLAY, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, buf, cap - 1);
    close(fd);
    if (n <= 0) return -1;
    buf[n] = 0;
    return (int) n;
}

/* Extract the artwork transfer-id from an already-read nowplaying buffer. Returns id, or -1. */
static int id_from(const char *buf)
{
    const char *p = strstr(buf, ART_KEY);
    if (!p) return -1;
    p = strstr(p, "::");
    if (!p) return -1;
    return atoi(p + 2);
}

/* Extract one PPS field into out, byte-identically to the jar's parsePps: find the key at line start,
 * take everything after the FIRST "::" up to (but excluding) the newline, RAW (no trimming of the value).
 * Writes "" if the key is absent. Matches CarplayBusListener.parsePps value semantics. */
static void pps_field(const char *buf, const char *key, char *out, size_t outcap)
{
    out[0] = 0;
    size_t klen = strlen(key);
    const char *p = buf;
    while ((p = strstr(p, key)) != 0) {
        int at_line_start = (p == buf) || (p[-1] == '\n');
        const char *after = p + klen;
        /* require the key to be immediately followed by "::" so "MediaItemAlbumTitle" doesn't match inside
         * "MediaItemAlbumTrackCount", and to be at the start of a PPS line. */
        if (at_line_start && after[0] == ':' && after[1] == ':') {
            const char *v = after + 2;
            const char *nl = strchr(v, '\n');
            size_t vlen = (nl ? (size_t)(nl - v) : strlen(v));
            if (vlen >= outcap) vlen = outcap - 1;
            memcpy(out, v, vlen);
            out[vlen] = 0;
            return;
        }
        p = after;
    }
}

/* Build the track signature bundleId\x01title\x01artist\x01album from a nowplaying buffer, byte-identical to
 * CarplayBusListener.trackSig(). Returns 0 on success, -1 if it would overflow. */
static int build_sig(const char *buf, char *out, size_t outcap)
{
    char bundle[512], title[1024], artist[512], album[512];
    pps_field(buf, BUNDLE_KEY, bundle, sizeof(bundle));
    pps_field(buf, TITLE_KEY,  title,  sizeof(title));
    pps_field(buf, ARTIST_KEY, artist, sizeof(artist));
    pps_field(buf, ALBUM_KEY,  album,  sizeof(album));
    int n = snprintf(out, outcap, "%s\x01%s\x01%s\x01%s", bundle, title, artist, album);
    return (n < 0 || (size_t) n >= outcap) ? -1 : 0;
}

/* Nearest-neighbor RGB resize (luka-dev's proven kernel). Contain-fit into dw x dh with black letterbox. */
static void resize_rgb_contain(const uint8_t *src, int sw, int sh, uint8_t *dst, int dw, int dh)
{
    memset(dst, 0, (size_t) dw * dh * 3);
    if (!src || sw <= 0 || sh <= 0) return;
    double sx = (double) dw / sw, sy = (double) dh / sh;
    double scale = (sx < sy) ? sx : sy;
    int nw = (int) (sw * scale + 0.5), nh = (int) (sh * scale + 0.5);
    if (nw < 1) nw = 1;
    if (nh < 1) nh = 1;
    if (nw > dw) nw = dw;
    if (nh > dh) nh = dh;
    int x0 = (dw - nw) / 2, y0 = (dh - nh) / 2;
    for (int y = 0; y < nh; y++) {
        int syi = y * sh / nh;
        const uint8_t *srow = src + (size_t) syi * sw * 3;
        uint8_t *drow = dst + ((size_t) (y0 + y) * dw + x0) * 3;
        for (int x = 0; x < nw; x++) {
            const uint8_t *p = srow + (size_t) (x * sw / nw) * 3;
            drow[x * 3 + 0] = p[0]; drow[x * 3 + 1] = p[1]; drow[x * 3 + 2] = p[2];
        }
    }
}

/* stb_image_write JPEG sink -> accumulate into COVER_TMP fd. */
struct jpeg_output { int fd; int failed; };
static void jpeg_sink(void *ctx, void *data, int size)
{
    struct jpeg_output *sink = (struct jpeg_output *) ctx;
    int fd = sink->fd;
    if (sink->failed || size <= 0) return;
    const uint8_t *p = (const uint8_t *) data;
    int off = 0;
    while (off < size) {
        ssize_t w = write(fd, p + off, size - off);
        if (w < 0 && errno == EINTR) continue;
        if (w <= 0) { sink->failed = 1; return; }
        off += (int) w;
    }
}

/* Decode the pulled JPEG, resize to COVER_DIM x COVER_DIM, re-encode JPEG, atomic-write to COVER_OUT. */
/* Milliseconds elapsed since a start timespec (for stage timing). */
static long ms_since(const struct timespec *t0)
{
    struct timespec t1;
    clock_gettime(CLOCK_MONOTONIC, &t1);
    return (t1.tv_sec - t0->tv_sec) * 1000L + (t1.tv_nsec - t0->tv_nsec) / 1000000L;
}

/* Timing captured per pull so the log shows exactly where the seconds go (pull / decode / resize / encode). */
static long g_ms_decode, g_ms_resize, g_ms_encode;
static int  g_src_w, g_src_h;

static int write_cover_resized(const uint8_t *jpg, int jlen)
{
    struct timespec t;
    int w = 0, hgt = 0, comp = 0;

    if (jlen < 2 || jlen > ART_MAX ||
        !stbi_info_from_memory(jpg, jlen, &w, &hgt, &comp) ||
        w <= 0 || hgt <= 0 || w > 2048 || hgt > 2048) return -1;

    clock_gettime(CLOCK_MONOTONIC, &t);
    uint8_t *rgb = stbi_load_from_memory(jpg, jlen, &w, &hgt, &comp, 3);
    g_ms_decode = ms_since(&t);
    if (!rgb) return -1;
    g_src_w = w; g_src_h = hgt;

    uint8_t *out = (uint8_t *) malloc((size_t) COVER_DIM * COVER_DIM * 3);
    if (!out) { stbi_image_free(rgb); return -1; }
    clock_gettime(CLOCK_MONOTONIC, &t);
    resize_rgb_contain(rgb, w, hgt, out, COVER_DIM, COVER_DIM);
    g_ms_resize = ms_since(&t);
    stbi_image_free(rgb);

    clock_gettime(CLOCK_MONOTONIC, &t);
    int fd = open(COVER_TMP, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) { free(out); return -1; }
    struct jpeg_output sink = { fd, 0 };
    int ok = stbi_write_jpg_to_func(jpeg_sink, &sink, COVER_DIM, COVER_DIM, 3, out, JPEG_QUALITY);
    free(out);
    int closed = close(fd);
    if (sink.failed || !ok || closed < 0) { unlink(COVER_TMP); return -1; }
    int rc = rename(COVER_TMP, COVER_OUT);
    g_ms_encode = ms_since(&t);
    return rc;
}

/* Heartbeat: touch ACTIVE_PATH so the jar knows the daemon is alive (jar checks mtime freshness). */
static void touch_active(void)
{
    int fd = open(ACTIVE_PATH, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd >= 0) { (void) write(fd, "1", 1); close(fd); }
}

/* Publish the track SIGNATURE that cp_cover.jpg now holds (single file, contents = sig, atomic overwrite).
 * The jar reads this file, trims trailing whitespace, and compares for exact equality against its own
 * trackSig(), so we write the sig followed by a single newline. */
static void write_cover_sig(const char *sig)
{
    int fd = open(ID_TMP, O_WRONLY | O_CREAT | O_TRUNC, 0666);
    if (fd < 0) return;
    size_t len = strlen(sig);
    (void) write(fd, sig, len);
    (void) write(fd, "\n", 1);
    close(fd);
    (void) rename(ID_TMP, ID_PATH);
}

/* Pull artwork for transfer-id N; if it's a JPEG, resize to 128x128 and write. Returns 0 on a written cover.
 * Logs a per-stage timing breakdown (pull / decode / resize / encode) so the slow stage is visible on-car. */
static int pull_and_write(void *h, int id, uint8_t *buf)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    int got = iap2_filexfer_read(h, id, buf, ART_MAX);
    long ms_pull = ms_since(&t);

    if (got > 1 && buf[0] == 0xFF && buf[1] == 0xD8) {
        if (write_cover_resized(buf, got) == 0) {
            fprintf(stderr, "carplay_artwork_helper: cover id=%d %d bytes src=%dx%d "
                            "[pull=%ldms decode=%ldms resize=%ldms encode=%ldms] -> %s (%dx%d)\n",
                    id, got, g_src_w, g_src_h, ms_pull, g_ms_decode, g_ms_resize, g_ms_encode,
                    COVER_OUT, COVER_DIM, COVER_DIM);
            return 0;
        }
        fprintf(stderr, "carplay_artwork_helper: id=%d decode/resize failed (pull=%ldms)\n", id, ms_pull);
        return -1;
    }
    fprintf(stderr, "carplay_artwork_helper: id=%d got=%d pull=%ldms (not a JPEG)\n", id, got, ms_pull);
    return -1;
}

int main(void)
{
    int lock = take_lock();
    if (lock < 0) { fprintf(stderr, "carplay_artwork_helper: already running, exiting\n"); return 75; }

    signal(SIGTERM, on_sig);
    signal(SIGINT,  on_sig);
    atexit(cleanup_files);

    uint8_t *buf = malloc(ART_MAX);
    if (!buf) { fprintf(stderr, "carplay_artwork_helper: malloc failed\n"); return 1; }

    fprintf(stderr, "carplay_artwork_helper: started (pid %d)\n", (int) getpid());

    /* Clear stale coordination/cover files from a previous session (e.g. if the last run was SIGKILL'd and
     * couldn't clean up), so the jar never matches an old id or shows an old cover before we write fresh. */
    cleanup_files();

    /* Startup grace: when launched on CarPlay connect (before mm-ipod finishes creating /dev/ipod0), wait up
     * to STARTUP_WAIT_MS for the node to appear rather than exiting immediately. */
    for (long waited = 0; !g_stop && !ipod_present() && waited < STARTUP_WAIT_MS; waited += POLL_MS)
        msleep(POLL_MS);

    while (!g_stop && ipod_present()) {
        void *h = iap2_connect(IPOD_DEV, O_RDONLY);
        if (!h) {
            fprintf(stderr, "carplay_artwork_helper: iap2_connect failed (%s), retry\n", strerror(errno));
            msleep(RECONNECT_MS);
            continue;
        }
        fprintf(stderr, "carplay_artwork_helper: connected\n");

        int last_id = -1;
        char pps[PPS_BUF];
        char sig[SIG_MAX];
        while (!g_stop && ipod_present()) {
            touch_active();   /* heartbeat: jar treats a fresh mtime as "daemon alive, wait for cover" */
            if (read_nowplaying(pps, sizeof(pps)) < 0) { msleep(POLL_MS); continue; }
            int id = id_from(pps);
            if (id > 0 && id != last_id) {
                /* Detect + pull by artwork-id (arrives LAST in PPS, so title/artist/album in this same
                 * snapshot are already the new track's), but publish the TRACK SIGNATURE - not the id -
                 * so the jar matches on the stable, synchronous key it also computes. */
                if (pull_and_write(h, id, buf) == 0 && build_sig(pps, sig, sizeof(sig)) == 0)
                    write_cover_sig(sig);   /* cp_cover.jpg is for this sig -> let the jar proceed */
                last_id = id;               /* don't re-pull a non-pullable id every tick */
            }
            msleep(POLL_MS);
        }
        iap2_disconnect(h);
    }

    free(buf);
    cleanup_files();   /* also runs via atexit() on any return path; clears heartbeat -> jar app-logo fallback */
    fprintf(stderr, "carplay_artwork_helper: exit (ipod gone or signalled)\n");
    return 0;
}
