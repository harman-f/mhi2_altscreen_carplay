#include "ipod_transport_v2.h"

#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define BT_PRIV_FD_INDEX 0
#define BT_PRIV_READY_INDEX 1
#define BT_PRIV_LINK0_INDEX 2
#define BT_PRIV_LINK1_INDEX 3
#define BT_PRIV_LINK2_INDEX 4

static struct ipod_transport_v2 bt_transport;

static int hex_nibble(int c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static int decode_link_params(const char *hex, uint8_t out[IPOD_LINK_PARAMS_SIZE])
{
    size_t i;

    if (!hex || strlen(hex) != IPOD_LINK_PARAMS_SIZE * 2)
        return EINVAL;

    for (i = 0; i < IPOD_LINK_PARAMS_SIZE; ++i) {
        int hi = hex_nibble((unsigned char)hex[i * 2]);
        int lo = hex_nibble((unsigned char)hex[i * 2 + 1]);
        if (hi < 0 || lo < 0)
            return EINVAL;
        out[i] = (uint8_t)((hi << 4) | lo);
    }
    return 0;
}

static void store_link_params(struct ipod_transport_v2 *self,
                              const uint8_t params[IPOD_LINK_PARAMS_SIZE])
{
    memcpy(&self->private_words[BT_PRIV_LINK0_INDEX],
           params, IPOD_LINK_PARAMS_SIZE);
}

static void load_link_params(const struct ipod_transport_v2 *self,
                             uint8_t params[IPOD_LINK_PARAMS_SIZE])
{
    memcpy(params, &self->private_words[BT_PRIV_LINK0_INDEX],
           IPOD_LINK_PARAMS_SIZE);
}

static int parse_required_options(const char *options,
                                  char *path,
                                  size_t path_cap,
                                  uint8_t link_params[IPOD_LINK_PARAMS_SIZE])
{
    char *copy;
    char *item;
    char *save = NULL;
    int have_path = 0;
    int have_link = 0;
    int rc = EINVAL;

    if (!options || !*options || !path || path_cap < 2)
        return EINVAL;

    copy = strdup(options);
    if (!copy)
        return ENOMEM;

    for (item = strtok_r(copy, ",", &save);
         item != NULL;
         item = strtok_r(NULL, ",", &save)) {
        if (strncmp(item, "path=", 5) == 0) {
            const char *value = item + 5;
            size_t n = strlen(value);
            if (n == 0 || n >= path_cap)
                goto out;
            memcpy(path, value, n + 1);
            have_path = 1;
        } else if (strncmp(item, "linkparams=", 11) == 0) {
            rc = decode_link_params(item + 11, link_params);
            if (rc != 0)
                goto out;
            have_link = 1;
        } else if (*item != '\0') {
            /*
             * Refuse unknown options. A vehicle probe should never silently
             * accept a typo and fall back to an unsafe/default behavior.
             */
            rc = EINVAL;
            goto out;
        }
    }

    rc = (have_path && have_link) ? 0 : EINVAL;
out:
    free(copy);
    return rc;
}

static int btstream_init(struct ipod_transport_v2 *self,
                         const char *mount_base,
                         const char *options)
{
    char path[256];
    uint8_t params[IPOD_LINK_PARAMS_SIZE];
    int fd;
    int rc;

    (void)mount_base;
    if (!self)
        return EINVAL;

    memset(path, 0, sizeof(path));
    memset(params, 0, sizeof(params));

    rc = parse_required_options(options, path, sizeof(path), params);
    if (rc != 0)
        return rc;

    /*
     * The endpoint path is deliberately mandatory. We currently have no
     * exact-target proof that MU1440 uses /dev/iapDevice, /dev/ipod*, or any
     * other particular pathname for Bluetooth iAP.
     */
    fd = open(path, O_RDWR);
    if (fd < 0)
        return errno ? errno : EIO;

    self->private_words[BT_PRIV_FD_INDEX] = (uint32_t)fd;
    self->private_words[BT_PRIV_READY_INDEX] = 1;
    store_link_params(self, params);
    return 0;
}

static int btstream_link_params_get(struct ipod_transport_v2 *self,
                                    void *out_12_bytes)
{
    uint8_t params[IPOD_LINK_PARAMS_SIZE];

    if (!self || !out_12_bytes ||
        self->private_words[BT_PRIV_READY_INDEX] == 0)
        return EINVAL;

    load_link_params(self, params);
    memcpy(out_12_bytes, params, sizeof(params));
    return 0;
}

static int btstream_type_get(struct ipod_transport_v2 *self, uint8_t *out_type)
{
    (void)self;
    if (!out_type)
        return EINVAL;
    *out_type = IPOD_TRANSPORT_TYPE_BLUETOOTH;
    return 0;
}

static int btstream_caps_get(struct ipod_transport_v2 *self,
                             int capability,
                             void *out_value)
{
    (void)self;
    (void)capability;
    (void)out_value;
    return 0;
}

static int btstream_audiopath_get(struct ipod_transport_v2 *self)
{
    (void)self;
    return 0;
}

static ssize_t btstream_data_send(struct ipod_transport_v2 *self,
                                  const void *buffer,
                                  size_t length)
{
    const uint8_t *p = (const uint8_t *)buffer;
    size_t done = 0;
    int fd;

    if (!self || (!buffer && length) ||
        self->private_words[BT_PRIV_READY_INDEX] == 0) {
        errno = EINVAL;
        return -1;
    }

    fd = (int)self->private_words[BT_PRIV_FD_INDEX];
    while (done < length) {
        ssize_t n = write(fd, p + done, length - done);
        if (n < 0) {
            if (errno == EINTR)
                continue;
            return -1;
        }
        if (n == 0) {
            errno = EIO;
            return -1;
        }
        done += (size_t)n;
    }
    return (ssize_t)done;
}

static ssize_t btstream_data_recv(struct ipod_transport_v2 *self,
                                  void *buffer,
                                  size_t length,
                                  int timeout_ms)
{
    struct pollfd pfd;
    int fd;
    int rc;

    if (!self || (!buffer && length) ||
        self->private_words[BT_PRIV_READY_INDEX] == 0) {
        errno = EINVAL;
        return -1;
    }

    fd = (int)self->private_words[BT_PRIV_FD_INDEX];
    pfd.fd = fd;
    pfd.events = POLLIN;
    pfd.revents = 0;

    do {
        rc = poll(&pfd, 1, timeout_ms);
    } while (rc < 0 && errno == EINTR);

    if (rc < 0)
        return -1;
    if (rc == 0)
        return 0;
    if ((pfd.revents & POLLIN) == 0) {
        errno = EIO;
        return -1;
    }

    do {
        rc = (int)read(fd, buffer, length);
    } while (rc < 0 && errno == EINTR);
    return rc;
}

static struct ipod_transport_v2 bt_transport = {
    .interface_name = "ipod_transport",
    .reserved_04 = 0,
    .reserved_08 = 0,
    .host_context = NULL,
    .reserved_10 = 0,
    .init = btstream_init,
    .link_params = btstream_link_params_get,
    .type_get = btstream_type_get,
    .caps_get = btstream_caps_get,
    .audiopath_get = btstream_audiopath_get,
    .data_send = btstream_data_send,
    .data_recv = btstream_data_recv,
    .private_words = {0}
};

/*
 * This symbol/name/layout is what exact stock MU1440 mm-ipod resolves with
 * dlsym(). Keep default ELF visibility.
 */
__attribute__((visibility("default")))
struct ipod_module_v2 ipod_module = {
    .module_name = "transport_btstream",
    .interface_version = IPOD_TRANSPORT_V2_VERSION,
    .reserved = {0,0,0,0,0,0},
    .transport = &bt_transport
};
