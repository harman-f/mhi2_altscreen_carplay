/* SPDX-License-Identifier: GPL-3.0-or-later
 * MU1440 route guidance, mm-ipod side (LD_PRELOAD into mm-ipod only).
 *
 * The stock QNX iAP2 driver ipod-drvr-iap2.so (sha256 7149a3e7..., MHI2_ER_SKG13_P4526) builds the
 * Identification from iap2.cfg. It has no route-guidance component, and its control-message table
 * row 0x52 is empty, so link_handle_reply returns 22 for every 0x52xx packet and transport_recv_pkt
 * then never returns that packet to the receive pool (3 buffers): a few route updates would stall
 * the link. This library therefore does exactly two data changes, both only after every anchor
 * matched the known build, and offers group 30 only when both are in place:
 *   1. row 0x52 gets entries 1/2/4 (flags 2, no reply bit): link_handle_reply returns 0, the
 *      message switch has no case and returns 0, the packet goes back to the pool. The row keeps
 *      a NULL group name, so print_packet logs "--?-- [msgid=52xx] CTRL[..]" with the full payload,
 *      which the mibr-rgi helper reads.
 *   2. ident_info_funcs[22] (Location builder) is wrapped: after the stock Location component, a
 *      RouteGuidanceDisplayComponent (group 30) is appended with packet_addparam_blob.
 * Message ID lists (0x5200/0x5203 sent, 0x5201/0x5202/0x5204 received) come from an [ident]
 * section that this library appends to the RAM config copy (RAM_CFG, made by the mm-ipod-rgi
 * wrapper from /etc/mm/iap2.cfg) only after every check passed; the driver parses the config after
 * DT_INIT. Any mismatch, a missing enable file, or two unfinished starts in a row leave mm-ipod
 * stock. An IdentificationRejected writes REJECTED_FILE, and the wrapper then starts the next
 * connection fully stock until reboot.
 * Addresses: own static analysis of the MU1440 driver (DESIGN_R1_2026-10-30.md). The approach
 * follows the public description in perkthefox/mst2-cluster-nav (no code copied).
 */
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include "mibr_rgi_wire.h"
#include "../../../../carplay/source/alt111-settings/include/mibr_paths.h"

#define ENABLE_FILE MIBR_CONFIG_DIR "/features/rgi.on"
#define READY_FILE  "/dev/shmem/mibr-rgi-ready"
#define GUARD_FILE  "/dev/shmem/mibr-rgi-ipod.guard"
#define LOG_FILE    "/tmp/mibr-rgi-ipod.log"
#define RAM_CFG     "/dev/shmem/mibr-rgi-iap2.cfg"
#define REJECTED_FILE "/dev/shmem/mibr-rgi-rejected"
#define DRIVER      "ipod-drvr-iap2.so"

/* Offsets from the exported ipod_module object (VA 0x27e7c) of the known build. */
#define OFF_MODULE      0x27e7cu
#define OFF_ADD_BLOB    0x1e2c4u
#define OFF_IDENT_FUNCS 0xa9af0u
#define OFF_MSG_TABLE   0xace80u
#define OFF_LOCATION_FN 0x0cb70u
#define LOCATION_SLOT   22u
#define LOCATION_GROUP  0x16u
#define DEV_REJECTS     0xa8u /* incremented per IdentificationRejected (link_handle_iap2pkt 0x1369c) */

struct msg_info {
    const char *name;
    uint16_t flags, reply;
    const void *params;
};

struct msg_group {
    const char *name;
    struct msg_info *info;
    uint32_t count;
};

typedef int (*build_fn)(void *dev, void *packet);
typedef int (*add_blob_fn)(void *dev, void *packet, unsigned id, const void *data, unsigned len);

static struct msg_info route_msgs[5] = {
    [1] = {"RouteGuidanceUpdate", 2, 0, NULL},
    [2] = {"RouteGuidanceManeuverUpdate", 2, 0, NULL},
    [4] = {"LaneGuidanceInformation", 2, 0, NULL},
};

static build_fn stock_location;
static add_blob_fn add_blob;
static int guard_cleared;

static void rgi_log(const char *fmt, ...)
{
    char line[256];
    va_list ap;
    int fd, n;

    n = snprintf(line, sizeof(line), "%ld ", (long)time(NULL));
    va_start(ap, fmt);
    n += vsnprintf(line + n, sizeof(line) - (size_t)n - 1, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof(line) - 2) {
        n = (int)sizeof(line) - 2;
    }
    line[n++] = '\n';
    fd = open(LOG_FILE, O_WRONLY | O_CREAT | O_APPEND, 0644);
    if (fd >= 0) {
        (void)write(fd, line, (size_t)n);
        close(fd);
    }
}

static int read_guard(void)
{
    char c = '0';
    int fd = open(GUARD_FILE, O_RDONLY);

    if (fd < 0) {
        return 0;
    }
    if (read(fd, &c, 1) != 1) {
        c = '0';
    }
    close(fd);
    return c >= '0' && c <= '9' ? c - '0' : 9;
}

static void write_guard(int value)
{
    char c = (char)('0' + (value > 9 ? 9 : value));
    int fd;

    if (!value) {
        unlink(GUARD_FILE);
        return;
    }
    fd = open(GUARD_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd >= 0) {
        (void)write(fd, &c, 1);
        close(fd);
    }
}

static void set_ready(int offered)
{
    int fd;

    if (!offered) {
        unlink(READY_FILE);
        return;
    }
    fd = open(READY_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (fd >= 0) {
        (void)write(fd, "offered\n", 8);
        close(fd);
    }
}

static int build_location(void *dev, void *packet)
{
    uint8_t component[MIBR_RGI_COMPONENT_MAX];
    unsigned n;
    int result = stock_location(dev, packet);

    if (!guard_cleared) {
        guard_cleared = 1;
        write_guard(0); /* mm-ipod reached its first Identification: start counted as good */
    }
    if (result < 0) {
        set_ready(0);
        return result;
    }
    if (*(const uint32_t *)((const uint8_t *)dev + DEV_REJECTS)) {
        int fd = open(REJECTED_FILE, O_WRONLY | O_CREAT | O_TRUNC, 0644);

        if (fd >= 0) {
            close(fd);
        }
        set_ready(0);
        rgi_log("identification retried after rejection: group 30 omitted, next start stock");
        return result;
    }
    n = mibr_rgi_component(component, sizeof(component));
    if (!n || add_blob(dev, packet, MIBR_RGI_IDENT_GROUP, component, n) < 0) {
        set_ready(0);
        rgi_log("group 30 did not fit: stock identification");
        return result;
    }
    set_ready(1);
    rgi_log("identification: route guidance group 30 offered");
    return result;
}

static int append_ident_section(void)
{
    static const char section[] = "\n[ident]\nsendmsgs=0x5200,0x5203\nrecvmsgs=0x5201,0x5202,0x5204\n";
    int fd = open(RAM_CFG, O_WRONLY | O_APPEND);
    int ok;

    if (fd < 0) {
        return -1;
    }
    ok = write(fd, section, sizeof(section) - 1) == (ssize_t)(sizeof(section) - 1);
    close(fd);
    return ok ? 0 : -1;
}

static int is_mm_ipod(void)
{
    void *main_image = dlopen(NULL, RTLD_LAZY);

    return main_image && dlsym(main_image, "ipod_log");
}

__attribute__((visibility("default"))) void mibr_rgi_ipod_init(void)
{
    void *driver, *module;
    uintptr_t base;
    uint32_t *slot;
    struct msg_group *table;
    int starts;

    if (!is_mm_ipod() || access(ENABLE_FILE, F_OK) != 0) {
        return;
    }
    starts = read_guard();
    if (starts >= 2) {
        rgi_log("two unfinished mm-ipod starts: stock behaviour until reboot");
        return;
    }
    write_guard(starts + 1);
    set_ready(0);

    /* Same name as mm-ipod's own dlopen("ipod-drvr-%s.so"), so its later load reuses this mapping. */
    driver = dlopen(DRIVER, RTLD_LAZY | RTLD_GLOBAL);
    module = driver ? dlsym(driver, "ipod_module") : NULL;
    if (!module || (uintptr_t)module < OFF_MODULE) {
        rgi_log("driver not loaded: stock behaviour");
        write_guard(0);
        return;
    }
    base = (uintptr_t)module - OFF_MODULE;
    if ((uintptr_t)dlsym(driver, "packet_addparam_blob") != base + OFF_ADD_BLOB ||
        (uintptr_t)dlsym(driver, "ident_info_funcs") != base + OFF_IDENT_FUNCS ||
        (uintptr_t)dlsym(driver, "iap2_ctrl_msg_table") != base + OFF_MSG_TABLE) {
        rgi_log("driver build mismatch: no data changed");
        write_guard(0);
        return;
    }
    slot = (uint32_t *)(base + OFF_IDENT_FUNCS + LOCATION_SLOT * 8u);
    table = (struct msg_group *)(base + OFF_MSG_TABLE);
    if (slot[0] != LOCATION_GROUP || slot[1] != base + OFF_LOCATION_FN) {
        rgi_log("Location builder slot mismatch: no data changed");
        write_guard(0);
        return;
    }
    if (table[0x52].name || table[0x52].info || table[0x52].count) {
        rgi_log("message row 0x52 not empty: no data changed");
        write_guard(0);
        return;
    }
    if (append_ident_section() < 0) {
        rgi_log("RAM config not writable: no data changed");
        write_guard(0);
        return;
    }
    add_blob = (add_blob_fn)(base + OFF_ADD_BLOB);
    stock_location = (build_fn)(uintptr_t)slot[1];
    table[0x52].info = route_msgs;
    table[0x52].count = 5;
    slot[1] = (uint32_t)(uintptr_t)build_location;
    rgi_log("driver checked: [ident] appended, row 0x52 declared, Location builder wrapped");
}
